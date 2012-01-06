#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding: utf-8
import os
import sys
import codecs
import platform

from distutils.util import convert_path
from fnmatch import fnmatchcase

from version import get_git_version

extra = {}
tests_require = []
if sys.version_info >= (3, 0):
    extra.update(use_2to3=True)
elif sys.version_info < (2, 7):
    tests_require.append("unittest2")

if sys.version_info < (2, 6):
    raise Exception("Extension-manager requires Python 2.6 or higher.")

# Bootstrap installation of Distribute
import distribute_setup
distribute_setup.use_setuptools()

try:
    from setuptools import setup, find_packages, Command
    from setuptools.command.test import test
    from setuptools.command.install import install
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages, Command
    from setuptools.command.test import test
    from setuptools.command.install import install

os.environ["EXTENSION_MANAGER_SETUP"] = "yes"

import tornado_ztask as distmeta

sys.modules.pop("tornado_ztask", None)

class quicktest(test):
    extra_env = dict(SKIP_RLIMITS=1, QUICKTEST=1)
    
    def run(self, *args, **kwargs):
        for env_name, env_value in self.extra_env.items():
            os.environ[env_name] = str(env_value)
        test.run(self, *args, **kwargs)

standard_exclude = ('*.py', '*.pyc', '*~', '.*', '*.bak', '*.swp*')
standard_exclude_directories = ('.*', 'CVS', '_darcs', './build',
                                './dist', 'EGG-INFO', '*.egg-info')

def find_package_data(
    where='.', package='',
    exclude=standard_exclude,
    exclude_directories=standard_exclude_directories,
    only_in_packages=True,
    show_ignored=False):
    """
    Return a dictionary suitable for use in ``package_data``
    in a distutils ``setup.py`` file.
    
    The dictionary looks like::
        
        {'package': [files]}
    
    Where ``files`` is a list of all the files in that package that
    don't match anything in ``exclude``.
    
    If ``only_in_packages`` is true, then top-level directories that
    are not packages won't be included (but directories under packages
    will).
    
    Directories matching any pattern in ``exclude_directories`` will
    be ignored; by default directories with leading ``.``, ``CVS``,
    and ``_darcs`` will be ignored.
    
    If ``show_ignored`` is true, then all the files that aren't
    included in package data are shown on stderr (for debugging
    purposes).
    
    Note patterns use wildcards, or can be exact paths (including
    leading ``./``), and all searching is case-insensitive.
    
    This function is by Ian Bicking.
    """
    
    out = {}
    stack = [(convert_path(where), '', package, only_in_packages)]
    while stack:
        where, prefix, package, only_in_packages = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "Directory %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                if os.path.isfile(os.path.join(fn, '__init__.py')):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + '.' + name
                    stack.append((fn, '', new_package, False))
                else:
                    stack.append((fn, prefix + name + '/', package, only_in_packages))
            elif package or not only_in_packages:
                # is a file
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "File %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out


install_requires = ["distribute"]
try:
    import importlib
except ImportError:
    install_requires.append("importlib")

# install_requires.extend([
#     "xar",
# ])

py_version = sys.version_info
is_jython = sys.platform.startswith("java")
if is_jython:
    install_requires.append("simplejson")

#install_requires.append("archive-manager==dev")
if os.path.exists("README.rst"):
    long_description = codecs.open("README.rst", "r", "utf-8").read()
else:
    long_description = "See http://url"

console_scripts = [
        # 'manage-extension = extension_manager.bin.manage_extension:main',
]

setup(
    name                =   "tornado_ztask",
    version             =   get_git_version(),
    description         =   distmeta.__doc__,
    author              =   distmeta.__author__,
    author_email        =   distmeta.__contact__,
    platforms           =   ["any"],
    license             =   "BSD",
    packages            =   find_packages(exclude=['ez_setup', 'tests', 'tests.*']),
    zip_safe            =   False,
    install_requires    =   install_requires,
    tests_require       =   tests_require,
    cmdclass            =   {
        "test": test,
        "quicktest": quicktest
    },
    scripts = [],
    test_suite          =   "tests",
    classifiers         =   [
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    dependency_links = [
        #"ssh://git@git.fuwui.com:archive-manager.git#egg=archive-manager-dev"
    ],
    # provides = ['virtualenvwrapper.term_utils'],
    namespace_packages = [ 'tornado_ztask' ],
    # requires=['virtualenv',
              # 'virtualenvwrapper (>=2.0)',
              # ],
    include_package_data = True,
    package_data = find_package_data('tornado_ztask',
                                     package='tornado_ztask',
                                     only_in_packages=False,
                                     ),
    entry_points = {
        # 'virtualenvwrapper.initialize': [
        #             'user_scripts = virtualenvwrapper.user_scripts:initialize',
        #             ],
        'tornado.reloaded.management.commands': [
            'commands = tornado_ztask.commands',
        ]
        
        # ... details omitted ...
    },
    long_description = long_description,
    **extra
)
