import os
import sys
from setuptools import setup, find_packages

setup(
    name="abl.vpath",
    version="0.6.9",
    description="A OO-abstraction of file-systems",
    author="Stephan Diehl",
    author_email="stephan.diehl@ableton.com",
    license="MIT",
    url='http://hg.ableton.com/abl.vpath',
    install_requires=[
        "decorator",
        "abl.util",
        ],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    #namespace_packages = ['abl', 'abl.vpath'],
    # TODO-std: add the classifiers
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Filesystems',
    ],
    entry_points="""
    [abl.vpath.plugins]
    localfilefs=abl.vpath.base.localfs:LocalFileSystem
    memoryfs=abl.vpath.base.memory:MemoryFileSystem
    zipfs=abl.vpath.base.zip:ZipFileSystem
    """,
    zip_safe=False,
)
