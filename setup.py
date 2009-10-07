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
        "decorator",
        ],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    namespace_packages = ['abl', 'abl.vpath'],
    # TODO-std: add the classifiers
    classifiers = [
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    entry_points="""
    [abl.vpath.plugins]
    localfilefs=abl.vpath.localfs:LocalFileSystem
    memoryfs=abl.vpath.memory:MemoryFileSystem
    """
)
