"""setup.py for the Scriptter project.

Based on:
https://github.com/pypa/sampleproject
"""
import sys
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
import os
import re

HERE = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the relevant file
with open(os.path.join(HERE, 'README.rst'), encoding='utf-8') as fi:
    LONG_DESCRIPTION = fi.read()


def find_version(file_path):
    with open(os.path.join(HERE, file_path), encoding='utf-8') as fi:
        version_file = fi.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


VERSION = find_version('scriptter.py')


if sys.argv[-1] == 'tag':
    os.system("git tag -a %s -m 'version %s'" % (VERSION, VERSION))
    os.system("git push --tags")
    sys.exit()


if sys.argv[-1] == 'dist':
    os.system("rm -rf dist/")
    os.system("python setup.py sdist bdist_wheel")
    sys.exit()


if sys.argv[-1] == 'publish':
    os.system("twine upload dist/*")
    sys.exit()


setup(
    name='scriptter',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=VERSION,

    description='cron\'s missing brain. Stateful, time-based scripting.',
    long_description=LONG_DESCRIPTION,

    # The project's main homepage.
    url='https://github.com/eykd/scriptter',

    # Author details
    author='David Eyk',
    author_email='deyk@crossway.org',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Office/Business :: Scheduling',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    # What does your project relate to?
    keywords='social media twitter scheduling cron',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    py_modules=['scriptter'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        "six==1.9.0",
        "docopt==0.6.2",
        "parsedatetime==1.4",
        "path.py==7.3",
        "pytz==2015.2",
        "PyYAML==3.11",
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage', 'coveralls',
                 'ensure', 'green', 'mock', 'pep8', 'tox'],
    },

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'scriptter=scriptter:main',
        ],
    },
)
