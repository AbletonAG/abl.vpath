from setuptools import setup, find_packages
import versioneer

# Add README as description
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="abl.vpath",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="A OO-abstraction of file-systems",
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Stephan Diehl",
    author_email="stephan.diehl@ableton.com",
    license="MIT",
    url='https://github.com/AbletonAG/abl.vpath',
    install_requires=[
        "decorator",
        "abl.util",
        ],
    packages=find_packages(exclude=['ez_setup', 'tests']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
