identifier = 'org.vistrails.vistrails.sklearn'
name = 'sklearn'
version = '0.15.2'


def package_dependencies():
    import vistrails.core.packagemanager
    manager = vistrails.core.packagemanager.get_package_manager()
    dependencies = []
    if manager.has_package('org.vistrails.vistrails.spreadsheet'):
        dependencies.append('org.vistrails.vistrails.spreadsheet')
    return dependencies


def package_requirements():
    import vistrails.core.requirements
    if not vistrails.core.requirements.python_module_exists('sklearn'):
        raise vistrails.core.requirements.MissingRequirement('sklearn')
    if not vistrails.core.requirements.python_module_exists('numpy'):
        raise vistrails.core.requirements.MissingRequirement('numpy')
    if not vistrails.core.requirements.python_module_exists('scipy'):
        raise vistrails.core.requirements.MissingRequirement('scipy')
