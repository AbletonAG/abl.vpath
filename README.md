# abl.vpath

the abl.vpath module provides a file system abstraction layer
for local files, remote files accessed via ssh, (http, ftp) and subversion.

An URI object represents a path. It will initialized with an uri string.
For example `URI('/tmp/some/dir')` represents a local file '/tmp/some/dir'
and is the same as `URI('file:///tmp/some/dir')`.
A remote file accessed via ssh could look like `URI('ssh://host:/remote/path')`.

Additional info that can't be encoded in the uri can be given as
keyword arguments.
Example: `URI('ssh://host:/path', key_filename='/local/path/to/key')`

Any supported scheme has a backend.

Currently supported are:

* file
* svn
* ssh

## License

abl.vpath is distributed under the MIT license (see LICENSE).

## Set up a Working Environment

To set up your working environment, run:

```bash
pip install -e '.[dev,test]'
```

## Release a New Version

You can build a new version by running:

```bash
python -m build
```

When developing on your branch, running the build will create tarballs with versions like:

```text
0.14.dev1+g13691ed.d20250211
```

To release a new official version, follow these steps:

1. Ensure all tests pass.
2. Make a pull request, get it reviewed, and merge it back to `main`.
3. Checkout `main` and pull the latest changes.
4. Check existing tags with:

```bash
git tag
```

5. Tag the new version:

```bash
git tag <your_new_version_number>
```

6. Push the tags:

```bash
git push --tags
```

Now when you run build the version number will be whatever you specified.

⚠️ Running `git push --tags` is crucial. If you don't, nobody else will be able to figure out where your version came from, version numbers will get weird, and we will be sad.
