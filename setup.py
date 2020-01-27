#!/usr/bin/env python

from distutils.core import setup


setup(name='python-bittrex3',
      version='0.1.3',
      packages=['bittrex3'],
      modules=['bittrex3'],
      description='Python 3 bindings for bittrex3 API.',
      author='Eric Somdahl, Marcin Repec',
      author_email='eric@corsairconsulting.com, mr@outs.pl',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Operating System :: OS Independent',
          'License :: OSI Approved :: MIT License',
          'Development Status :: 3 - Alpha',
          'Topic :: Office/Business :: Financial',
      ])
