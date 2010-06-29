###########################################################################
##
## Copyright (C) 2006-2010 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################
"""This package implements a very simple Qt GUI over the PythonCalc
package to provide an example of how a package may add GUI elements
including independent windows, menu items as well as dependency
requirements.

If you're interested in developing new modules for VisTrails, you
should also consult the documentation in the User's Guide and in
core/modules/vistrails_module.py.
"""

identifier = 'edu.utah.sci.vistrails.pythoncalcqt'
name = 'PythonCalcQt'
version = '0.0.1'

def package_dependencies():
    return ['edu.utah.sci.vistrails.pythoncalc']
