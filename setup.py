from unittest import TestLoader
from setuptools import setup, find_packages

def tests():
    return TestLoader().discover('tests')

setup(name='backtest',
      version='0.1',
      description='',
      long_description='',
      classifiers=[
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'License :: OSI Approved :: MIT License'
      ],
      keywords='',
      url='',
      author='dead-beef',
      author_email='contact@dead-beef.tk',
      license='MIT',
      scripts=[],
      packages=find_packages(include=('backtest*',)),
      entry_points={
          'console_scripts': [
              'backtest=backtest.cli:main',
              'backtest-data=backtest.data.cli:main'
          ],
      },
      package_data={
          '': ['README.md', 'LICENSE'],
      },
      #test_loader='unittest:TestLoader',
      test_suite='setup.tests',
      install_requires=['numpy', 'ta-lib', 'matplotlib', 'tqdm'],
      include_package_data=True,
      zip_safe=False)
