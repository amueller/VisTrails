###############################################################################
##
## Copyright (C) 2011-2014, NYU-Poly.
## Copyright (C) 2006-2011, University of Utah. 
## All rights reserved.
## Contact: contact@vistrails.org
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without 
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice, 
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright 
##    notice, this list of conditions and the following disclaimer in the 
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the University of Utah nor the names of its 
##    contributors may be used to endorse or promote products derived from 
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################
""" Contains classes for persisting running executions to disk

"""

from vistrails.core.configuration import get_vistrails_configuration
from vistrails.core.system import current_dot_vistrails
from vistrails.core.modules.vistrails_module import NotCacheable, \
    ModuleError, ModuleSuspended

from uuid import uuid1

import datetime
import getpass
import json
import os
import time
import unittest
import weakref

class JobMixin(NotCacheable):
    """ Mixin for suspendable modules.

    Provides a compute method implementing job handling.
    The package developer needs to implement the sub methods readInputs(),
    setResults(), startJob(), getMonitor() and finishJob().
    """

    def compute(self):
        """ Calls user-implemented methods at the right times
            It should always call addJob or setCache so that the callback works

        """
        jm = self.job_monitor()

        cache = jm.getCache(self.signature)
        if cache is not None:
            jm.setCache(self.signature, cache.parameters)
            # Result is available and cached
            self.setResults(cache.parameters)
            return

        job = jm.getJob(self.signature)
        if job is None:
            params = self.readInputs()
            params = self.startJob(params)
        else:
            params = job.parameters
        jm.addJob(self.signature, params, self.getName())

        # Might raise ModuleSuspended
        jm.checkJob(self, self.signature, self.getMonitor(params))

        # Didn't raise: job is finished
        params = self.finishJob(params)
        jm.setCache(self.signature, params)
        self.setResults(params)

    def update_upstream(self):
        """ Skip upstream if job exists
        """
        if not hasattr(self, 'signature'):
            raise ModuleError(self, "Module has no signature")
        jm = self.job_monitor()
        if not (jm.getCache(self.signature) or jm.getJob(self.signature)):
            # We need to submit a new job
            # Update upstream, compute() will need it
            super(JobMixin, self).update_upstream()

    def readInputs(self):
        """ readInputs() -> None
            Should read inputs, and return them in a dict
        """
        raise NotImplementedError

    def startJob(self, params):
        """ startJob(params: dict) -> None
            Should start the job, and return a dict with the
            parameters needed to check the job
        """
        raise NotImplementedError

    def finishJob(self, params):
        """ finishJob(params: dict) -> None
            Should finish the job and set outputs
        """
        raise NotImplementedError

    def setResults(self, params):
        """ setResults(params: dict) -> None
            Sets outputs using the params dict
        """
        raise NotImplementedError

    def getMonitor(self, params):
        """ getMonitor(params: dict) -> None
            Should return an implementation of BaseMonitor, whose methods will
            be used to check the job state.
        """
        return None

    def getId(self, params):
        """ getId(params: dict) -> job identifier
            Should return an string completely identifying this job
            Class name + input values are usually unique
            DEPRECATED
        """
        return self.signature

    def getName(self):
        # use module description if it exists
        if 'pipeline' in self.moduleInfo and self.moduleInfo['pipeline']:
            p_modules = self.moduleInfo['pipeline'].modules
            p_module = p_modules[self.moduleInfo['moduleId']]
            if p_module.has_annotation_with_key('__desc__'):
                return p_module.get_annotation_by_key('__desc__').value
        return self.__class__.__name__
 

class Workflow(object):
    """ Represents a workflow that has jobs.

    It can have one or several suspended modules.
    It can be serialized to disk.
    """
    def __init__(self, version, name='untitled', id=None, user=None,
                 start=None, jobs=None):
        """ __init__(version: str/int, name: str, id: str,
            user: str, start: str, jobs: list) -> None

            version - workflow version
            name - a human readable name for the job
            id - persistent identifier
            user - who started the job
            start - start time
            jobs - a dict with jobs
        """
        self.version = version
        self.name = name
        self.id = id if id else str(uuid1())
        self.user = getpass.getuser()
        self.start = start if start else datetime.datetime.now().isoformat()
        self.jobs = jobs if jobs else {}
        # parent modules are stored as temporary exceptions
        self.parents = {}

    def to_dict(self):
        wf = dict()
        wf['version'] = self.version
        wf['id'] = self.id
        wf['name'] = self.name
        wf['user'] = self.user
        wf['start'] = self.start
        wf['jobs'] = self.jobs.keys()
        return wf

    @staticmethod
    def from_dict(wf):
        return Workflow(wf['version'], wf['name'], wf['id'],
                        wf['user'], wf['start'], wf['jobs'])

    def __eq__(self, other):
        if self.version != other.version: return False
        if self.name != other.name: return False
        if self.id != other.id: return False
        if self.user != other.user: return False
        if self.start != other.start: return False
        if len(self.jobs) != len(other.jobs): return False
        if set(self.jobs) != set(other.jobs): return False
        return True

    def reset(self):
        for job in self.jobs.itervalues():
            job.reset()
        self.parents = {}

    def completed(self):
        """ Returns true if there are no suspended jobs
        """
        for job in self.jobs.itervalues():
            if not job.finished:
                return False
        return True


class Job(object):
    """A suspended module.
    """
    def __init__(self, id, parameters, name='', start=None, finished=False):
        """ __init__(id: str, parameters: dict, name: str, start: str,
                     finished: bool)

            id - persistent identifier
            parameters - either output values or job parameters
            start - start time
            finished - is it finished or running?
        """
        self.id = id
        self.parameters = parameters
        self.name = name
        self.start = start if start else datetime.datetime.now().isoformat()
        self.finished = finished
        self.updated = True

    def reset(self):
        self.updated = False

    def mark(self):
        self.updated = True

    def finish(self, params=None):
        self.params = params if params else {}
        self.finished = True

    def description(self):
        return self.parameters.get('__desc__', '')

    def to_dict(self):
        m = dict()
        m['id'] = self.id
        m['parameters'] = self.parameters
        m['name'] = self.name
        m['start'] = self.start
        m['finished'] = self.finished
        return m

    @staticmethod
    def from_dict(m):
        return Job(m['id'], m['parameters'], m['name'], m['start'], m['finished'])

    def __eq__(self, other):
        if self.id != other.id: return False
        if self.parameters != other.parameters: return False
        if self.start != other.start: return False
        if self.finished != other.finished: return False
        return True

class JobMonitor(object):
    """ Keeps a list of running jobs and the current job for a vistrail.

    Jobs are added by the interpreter are saved with the vistrail.
    A callback mechanism is used to interact with the associated GUI component.
    """

    def __init__(self, json_string=None):
        self._current_workflow = None
        self.workflows = {}
        self.jobs = {}
        self.callback = None
        if json_string is not None:
            self.unserialize(json_string)

    def setCallback(self, callback=None):
        """ setCallback(callback: class) -> None
            Sets a callback when receiving commands

        """
        self.callback = weakref.proxy(callback)

##############################################################################
# Running Workflows

    def serialize(self):
        """ serialize() -> None
            serializes the running jobs to json

        """
        _dict = {}

        jobs = dict()
        for id, job in self.jobs.items():
            jobs[id] = job.to_dict()
        _dict['jobs'] = jobs

        workflows = dict()
        for id, workflow in self.workflows.items():
            workflows[id] = workflow.to_dict()
        _dict['workflows'] = workflows

        return json.dumps(_dict)

    def unserialize(self, s):
        """ unserialize(s: str) -> None
            unserializes the running jobs from json

        """

        _dict = json.loads(s)
        
        jobs = _dict.get('jobs', {})        
        self.jobs = {}
        for id, job in jobs.iteritems():
            self.jobs[id] = Job.from_dict(job)

        workflows = _dict.get('workflows', {})
        self.workflows = {}
        for id, workflow in workflows.iteritems():
            workflow['jobs'] = dict([(i, self.jobs[i])
                                     for i in workflow['jobs']
                                     if i in self.jobs])
            wf = Workflow.from_dict(workflow)
            self.workflows[id] = wf
        return self.workflows

    def addWorkflow(self, workflow):
        """ addWorkflow(workflow: Workflow) -> None

        """
        self.workflows[workflow.id] = workflow
        for id, job in workflow.jobs.iteritems():
            self.jobs[id] = job

    def getWorkflow(self, id):
        """ getWorkflow(id: str) -> Workflow

            Checks if a workflow exists using its id and returns it

        """
        return self.workflows.get(id, None)

    def deleteWorkflow(self, id):
        """ deleteWorkflow(id: str) -> None
            deletes a workflow

        """
        workflow = self.workflows[id]
        del self.workflows[id]
        # delete jobs that only occur in this workflow
        for job_id in workflow.jobs:
            delete = True
            for wf in self.workflows.values():
                if job_id in wf.jobs:
                    delete = False
            if delete:
                del self.jobs[job_id]
        if self.callback:
            self.callback.deleteWorkflow(id)

    def deleteJob(self, id):
        """ deleteJob(id: str, parent_id: str) -> None
            deletes a job from all workflows
        """
        del self.jobs[id]
        for wf in self.workflows.itervalues():
            if id in wf.jobs:
                del wf.jobs[id]
        if self.callback:
            self.callback.deleteJob(id)

##############################################################################
# _current_workflow methods

    def currentWorkflow(self):
        """ currentWorkflow() -> Workflow

        """
        return self._current_workflow

    def startWorkflow(self, workflow):
        """ startWorkflow(workflow: Workflow) -> None

        """
        if self._current_workflow:
            raise Exception("A workflow is still running!: %s" %
                            self._current_workflow)
        workflow.reset()
        self._current_workflow = workflow
        if self.callback:
            self.callback.startWorkflow(workflow)

    def addJobRec(self, obj, parent_id=None):
        workflow = self.currentWorkflow()
        id = obj.module.signature
        if obj.children:
            for child in obj.children:
                self.addJobRec(child, id)
            return
        if id in workflow.jobs:
            # this is an already existing new-style job
            # mark that it has been used
            workflow.jobs[id].mark()
            return
        if id in workflow.jobs:
            # this is an already existing new-style job
            # mark that it has been used
            workflow.jobs[id].mark()
            return
        # this is a new old-style job that we need to add
        self.addJob(id, {'__message__':obj.msg}, obj.name)

    def finishWorkflow(self):
        """ finish_job() -> None

            Finishes the running workflow

        """
        workflow = self._current_workflow
        # untangle parents
        # only keep the top item
        c = set()
        for exception in workflow.parents.itervalues():
            if exception.children:
                c.update([id(child) for child in exception.children])
        for child in c:
            if child in workflow.parents:
                del workflow.parents[child]
        for parent in workflow.parents.itervalues():
            self.addJobRec(parent)

        # Assume all unfinished jobs that were not updated are now finished
        for job in workflow.jobs.values():
            if not job.finished and not job.updated:
                job.finish()
        if self.callback:
            self.callback.finishWorkflow(workflow)
        self._current_workflow = None

    def addJob(self, id, params=None, name='', finished=False):
        """ addJob(id: str, params: dict, name: str, finished: bool) -> uuid

            Adds a job to the currently running workflow

        """

        params = params if params is not None else {}

        if self.hasJob(id):
            # update job attributes
            job = self.getJob(id)
            job.parameters = params
            if name:
                job.name = name
            job.finished = finished
            # we want to keep the start date
        else:
            job = Job(id, params, name, finished=finished)
            self.jobs[id] = job

        workflow = self.currentWorkflow()
        if workflow:
            workflow.jobs[id] = job
            # we add workflows permanently if they have at least one job
            self.workflows[workflow.id] = workflow
        if self.callback:
            self.callback.addJob(self.getJob(id))

    def addParent(self, error):
        """ addParent(id: str, name: str, finished: bool) -> None

            Adds an exception to be used later

        """
        workflow = self.currentWorkflow()
        if not workflow:
            return # ignore non-monitored jobs
        workflow.parents[id(error)] = error

    def setCache(self, id, params, name=''):
        self.addJob(id, params, name, True)

    def checkJob(self, module, id, monitor):
        """ checkJob(module: VistrailsModule, id: str, monitor: instance) -> None
            Starts monitoring the job for the current running workflow
            module - the module to suspend
            id - the job identifier
            monitor - a class instance with a finished method for
                      checking if the job has completed

        """
        if not self.currentWorkflow():
            if not monitor or not self.isDone(monitor):
                raise ModuleSuspended(module, 'Job is running',
                                      monitor=monitor)
        job = self.getJob(id)
        if self.callback:
            self.callback.checkJob(module, id, monitor)
            return

        conf = get_vistrails_configuration()
        interval = conf.jobCheckInterval
        if interval and not conf.jobAutorun:
            if monitor:
                # wait for module to complete
                try:
                    while not self.isDone(monitor):
                        time.sleep(interval)
                        print ("Waiting for job: %s,"
                               "press Ctrl+C to suspend") % job.name
                except KeyboardInterrupt, e:
                    raise ModuleSuspended(module, 'Interrupted by user, job'
                                           ' is still running', monitor=monitor,
                                           job_id=id)
        else:
            if not monitor or not self.isDone(monitor):
                raise ModuleSuspended(module, 'Job is running', monitor=monitor,
                                      job_id=id)

    def getJob(self, id):
        """ getJob(id: str) -> Job

        """
        return self.jobs.get(id, None)

    def getCache(self, id):
        """ getCache(id: str) -> Job
            Checks if a completed module exists using its id and returns it
        """
        job = self.jobs.get(id, None)
        return job if job and job.finished else None

    def hasJob(self, id):
        """ hasJob(id: str) -> bool

            Checks if a job exists

        """
        return id in self.jobs

    def updateUrl(self, new, old):
        for workflow in self.workflows.values():
            if workflow.vistrail == old:
                workflow.vistrail = new

    def isDone(self, monitor):
        """ isDone(self, monitor) -> bool

            A job is done when it reaches finished or failed state
            val() is used by stable batchq branch
        """
        finished = monitor.finished()
        if type(finished)==bool:
            if finished:
                return True
        else:
            if finished.val():
                return True
        if hasattr(monitor, 'failed'):
            failed = monitor.failed()
            if type(failed)==bool:
                if failed:
                    return True
            else:
                if failed.val():
                    return True
        return False

##############################################################################
# Testing


class TestJob(unittest.TestCase):

    def test_job(self):
        jm = JobMonitor()
        job1 = Job('`13/5', {'a':3, 'b':'7'})
        job2 = Job('3', {'a':6}, 'my_name', 'a_string_date', True)
        # test module to/from dict
        job3 = Job.from_dict(job2.to_dict())
        self.assertEqual(job2, job3)

        workflow1 = Workflow(26)
        workflow2 = Workflow('tagname', 'myjob', 'myid', 'tommy',
                             '2013-10-07 13:06',
                             {job1.id: job1, job2.id: job2})
        # test workflow to/from dict
        workflow3 = Workflow.from_dict(workflow2.to_dict())
        self.assertEqual(workflow2, workflow3)

        # test start/finish job
        jm.startWorkflow(workflow2)
        self.assertEqual(workflow2, jm._current_workflow)
        jm.finishWorkflow()
        self.assertEqual(None, jm._current_workflow)

        # test add job
        jm.startWorkflow(workflow2)
        jm.addJob('my_uuid_id', {'myparam': 0})
        self.assertIn('my_uuid_id', workflow2.jobs)
        jm.finishWorkflow()

        # test serialization
        jm.addWorkflow(workflow1)
        jm.addWorkflow(workflow2)
        jm.unserialize(jm.serialize())
        self.assertIn(workflow1.id, jm.workflows)
        self.assertIn(workflow2.id, jm.workflows)
        self.assertEqual(workflow1, jm.workflows[workflow1.id])
        self.assertEqual(workflow2, jm.workflows[workflow2.id])
