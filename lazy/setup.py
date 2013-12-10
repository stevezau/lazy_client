#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='lazy',
    version='0.1.1',
    description='Lazy Toolset',
    author='Steve',
    author_email='no@thanks.com',
    packages=find_packages(),
    long_description="""\
     lazy is a cool tool
      """,
      keywords='tool',
      license='GPL',
      install_requires=[
        'setuptools',
        'tvdb_api',
        'easy_extract',
        'flexget',
      ],
      entry_points = {
      'console_scripts': [
          'lazy = lazy:main',
      ]
    }
    )