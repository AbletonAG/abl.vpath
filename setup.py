import os
import sys
from setuptools import setup, find_packages

setup(
    name="AbletonVPath",
    version="0.3.8",
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
    namespace_packages = ['abl'],
    # TODO-std: add the classifiers
    classifiers = [
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules'
        'Topic :: System :: Filesystems',
    ],
    entry_points="""
    [abl.vpath.plugins]
    localfilefs=abl.vpath.base.localfs:LocalFileSystem
    memoryfs=abl.vpath.base.memory:MemoryFileSystem
    """,
    zip_safe=False,
)
