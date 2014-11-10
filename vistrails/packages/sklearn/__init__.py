identifier = 'org.vistrails.vistrails.sklearn'
name = 'sklearn'
version = '0.15.2'


def package_requirements():
    from vistrails.core.requirements import require_python_module

    require_python_module('sklearn')
    require_python_module('numpy')
    require_python_module('scipy')
