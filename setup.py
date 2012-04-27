#!/usr/bin/env python
from setuptools import setup, find_packages

def readme():
    try:
        return open('README.md').read()
    except:
        return ""

setup(name='ma-shell',
      version='0.2',
      description='The Memset API interactive shell',
      long_description=readme(),
      author='Juan J. Martinez',
      author_email='juan@memset.com',
      url="http://www.memset.com/apidocs/",
      license='MIT',
      include_package_data=True,
      scripts=['ma-shell.py'],
      classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        ],
      )
