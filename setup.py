#!/usr/bin/python
"""
A tool kit for analysis, visualization and classification 
of single cell data (Mainly Spatial Transcriptomics data)
"""

import os
import io
import glob
from setuptools import setup, find_packages
from stpipeline.version import version_number

# Get the long description from the relevant file
here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name = 'stanalysis',
  version = version_number,
  description = __doc__.split("\n", 1)[0],
  long_description = long_description,
  keywords = 'rna-seq analysis spatial transcriptomics toolkit',
  author = 'Jose Fernandez Navarro',
  author_email = 'jose.fernandez.navarro@scilifelab.se',
  license = 'BSD',
  packages = find_packages(exclude=('tests*')),
  include_package_data = False,
  package_data = {'': ['RELEASE-VERSION']},
  zip_safe = False,
  install_requires = [
    'setuptools',
    'argparse',
    'scipy',
    'numpy',
    'pandas',
    'sklearn',
    'matplotlib'
  ],
  test_suite = 'tests',
  scripts = glob.glob('scripts/*.py'),
  classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Science/Research',
    'Topic :: Software Development',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
    'License :: BSD:: Copyright Jose Fernandez Navarro',
    'Programming Language :: Python :: 2.7',
    'Environment :: Console',
  ],
)