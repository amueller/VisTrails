identifier = 'org.vistrails.vistrails.sklearn'
name = 'sklearn'
version = '0.15.2'


def package_requirements():
    from vistrails.core.requirements import require_python_module

    require_python_module('sklearn', {
        'pip': 'scikit-learn',
        'linux-debian': 'python-sklearn',
        'linux-ubuntu': 'python-sklearn'})
    require_python_module('scipy', {
        'pip': 'scipy',
        'linux-debian': 'python-scipy',
        'linux-ubuntu': 'python-scipy'})
    require_python_module('numpy', {
        'pip': 'numpy',
        'linux-debian': 'python-numpy',
        'linux-ubuntu': 'python-numpy'})
