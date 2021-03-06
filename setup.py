#!/usr/bin/env python

from setuptools import setup
import sys


if sys.version_info < (3,):
    print("bitcoin-arbitrage requires Python version >= 3.0")
    sys.exit(1)

setup(name='bitcoin-arbitrage',
      packages = ["arbitrage"],
      version='0.1',
      description='Bitcoin arbitrage opportunity watcher',
      author='',
      author_email='',
      url='https://github.com/maxme/bitcoin-arbitrage',
      arbitrage=['bin/bitcoin-arbitrage'],
      test_suite='nose.collector',
      tests_require=['nose'], install_requires=['ccxt']
      )
