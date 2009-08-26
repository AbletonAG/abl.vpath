import os
import sys
from setuptools import setup, find_packages

setup(
    name="AbletonVPath",
    version="0.1",
    description="A OO-abstraction of file-systems",
    author="Stephan Diehl",
    author_email="stephan.diehl@ableton.com",
    url="",
    license="MIT",
    download_url='',
    install_requires=[
        "paramiko",
        "pysvn",
        ],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    namespace_packages = ['abl', ],
    # TODO-std: add the classifiers
    classifiers = [
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
