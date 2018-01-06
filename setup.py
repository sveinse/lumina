from setuptools import setup, find_packages
from codecs import open
from glob import glob
import os
import io
import re


HERE = os.path.dirname(__file__)


def read(fname):
    return io.open(os.path.join(HERE, fname), encoding='utf-8').read()


def data_files(dirname, dest):
    dirname = os.path.join(HERE, dirname)
    datalist = []
    for base, dirs, files in os.walk(dirname):
        base = base.replace(dirname, dest)
        files = [os.path.relpath(os.path.join(dirname, p)) for p in files]
        datalist.append((base, files))
    return datalist


def find_version(fname):

    version_file = read(fname)
    version_match = re.search(r"^\s*__version__\s*=\s*['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")



setup(
    name='lumina',
    version=find_version('lumina/__init__.py'),
    description='Home Theater Automation Controller',
    long_description=read('README.rst'),
    url='https://github.com/sveinse/lumina',
    author='Svein Seldal',
    author_email='sveinse@seldal.com',
    license='GPL3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        #'Intended Audience :: Developers',
        #'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],

    # What does your project relate to?
    #keywords='utility directory',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #py_modules=['lumina'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'twisted>=16.0.0',
        'setproctitle',
        'pyserial',
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    #extras_require={
    #    'dev': ['check-manifest'],
    #    'test': ['coverage'],
    #},

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    #package_data={
    #    '': ['www/*'],
    #},
    include_package_data=True,

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=data_files('www', 'share/lumina/www'),

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'lumina=lumina.main:main',
        ],
    },

)
