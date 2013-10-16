###############################################################################
##
## Copyright (C) 2011-2013, NYU-Poly.
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
import os
import re
import shutil
import tempfile

from vistrails.core.utils import VistrailsInternalError

from vistrails.core.system.unix import executable_is_in_path,\
     list2cmdline, execute_cmdline, execute_cmdline2, \
     get_executable_path, execute_piped_cmdlines


__all__ = ['executable_is_in_path', 'list2cmdline', 'execute_cmdline',
           'execute_cmdline2', 'get_executable_path', 'execute_piped_cmdlines',

           'guess_total_memory',
           'home_directory', 'remote_copy_program', 'remote_shell_program',
           'graph_viz_dot_command_line', 'remove_graph_viz_temporaries',
           'link_or_copy', 'XDestroyWindow',
           'shell_font_face', 'shell_font_size',
           'TestLinux']

################################################################################

_meminfo_fmt = re.compile(r'([^:]+):\s+([0-9]+)(?: (kB|B))?\n$')

def parse_meminfo():
    """parse_meminfo() -> dictionary
    Parses /proc/meminfo and returns appropriate dictionary. Only available on
    Linux."""
    info = {}
    with open('/proc/meminfo') as fp:
        for line in fp:
            m = _meminfo_fmt.match(line)
            if m is None:
                raise VistrailsInternalError("Invalid format found in "
                                             "/proc/meminfo")
            key, value, unit = m.groups()
            if unit == 'kB':
                value = int(value) * 1000
            else:
                value = int(value)
            info[key] = value
    return info

def guess_total_memory():
    """ guess_total_memory() -> int
    Return system memory in bytes.

    """
    return parse_meminfo()['MemTotal']

def home_directory():
    """ home_directory() -> str
    Returns user's home directory using environment variable $HOME

    """
    return os.getenv('HOME')

def remote_copy_program():
    return "scp -p"

def remote_shell_program():
    return "ssh -p"

def graph_viz_dot_command_line():
    return 'dot -Tplain -o '

def remove_graph_viz_temporaries():
    """ remove_graph_viz_temporaries() -> None
    Removes temporary files generated by dot

    """
    os.unlink(tempfile.gettempdir() + "dot_output_vistrails.txt")
    os.unlink(tempfile.gettempdir() + "dot_tmp_vistrails.txt")

def link_or_copy(src, dst):
    """link_or_copy(src:str, dst:str) -> None
    Tries to create a hard link to a file. If it is not possible, it will
    copy file src to dst

    """
    # Links if possible, but we're across devices, we need to copy.
    try:
        os.link(src, dst)
    except OSError, e:
        if e.errno == 18:
            # Across-device linking is not possible. Let's copy.
            shutil.copyfile(src, dst)
        else:
            raise e

def get_libX11():
    """ get_libX11() -> CDLL
    Return the X11 library loaded with ctypes. Only available on
    Linux.  We also need a way to find the correct X11 library name on
    different machines. Right now, libX11.so.6 is used.

    """
    from vistrails.core.bundles import py_import
    ctypes = py_import('ctypes', {
            'pip': 'ctypes',
            'linux-debian': 'python-ctypes',
            'linux-ubuntu': 'python-ctypes'})
    c_void_p = ctypes.c_void_p
    CDLL = ctypes.CDLL
    return CDLL('libX11.so.6')

def XDestroyWindow(displayId, windowId):
    """ XDestroyWindow(displayId: void_p_str, windowId: void_p_str) -> None
    Destroy the X window specified by two strings displayId and
    windowId containing void pointer string of (Display*) and (Window)
    type.
    This is specific for VTKCell to remove the top shell window. Since
    VTK does not expose X11-related functions to Python, we have to
    use ctypes to hi-jack X11 library and call XDestroyWindow to kill
    the top-shell widget after reparent the OpenGL canvas to another
    Qt widget

    """
    from vistrails.core.bundles import py_import
    ctypes = py_import('ctypes', {
            'pip': 'ctypes',
            'linux-debian': 'python-ctypes',
            'linux-ubuntu': 'python-ctypes'})
    c_void_p = ctypes.c_void_p
    displayPtr = c_void_p(int(displayId[1:displayId.find('_void_p')], 16))
    windowPtr = c_void_p(int(windowId[1:windowId.find('_void_p')], 16))
    libx = get_libX11()
    libx.XDestroyWindow(displayPtr, windowPtr)

def shell_font_face():
    return 'Fixed'

def shell_font_size():
    return 12

################################################################################

import unittest

class TestLinux(unittest.TestCase):
    """ Class to test Linux specific functions """

    def test1(self):
        """ Test if guess_total_memory() is returning an int >= 0"""
        result = guess_total_memory()
        assert isinstance(result, (int, long))
        assert result >= 0

    def test2(self):
        """ Test if home_directory is not empty """
        result = home_directory()
        assert result != ""

    def test3(self):
        """ Test if origin of link_or_copy'ed file is deleteable. """
        import tempfile
        import os
        (fd1, name1) = tempfile.mkstemp()
        os.close(fd1)
        (fd2, name2) = tempfile.mkstemp()
        os.close(fd2)
        os.unlink(name2)
        link_or_copy(name1, name2)
        try:
            os.unlink(name1)
        except:
            self.fail("Should not throw")
        os.unlink(name2)

    def test_executable_file_in_path(self):
        # Should exist in any POSIX shell
        self.assertTrue(executable_is_in_path('ls'))

if __name__ == '__main__':
    unittest.main()
