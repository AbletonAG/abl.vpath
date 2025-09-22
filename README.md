# abl.vpath

abl.vpath offers an object-oriented abstraction layer over multiple file
system implementations. Paths are wrapped in `URI` objects that provide a
familiar API inspired by `os.path`, while connectors translate each operation
into calls against a concrete backend.

## Highlights

- Uniform API for local folders, in-memory storage, and ZIP archives.
- Compose paths with the `/` operator and call helpers like `exists()`,
  `open()`, `walk()`, and `copy()` directly on the URI.
- Extend the library by registering additional connectors via Python entry
  points.

## Installation

```bash
pip install abl.vpath
```

## Quick start

```python
from abl.vpath.base import URI, WorkingDirectory

root = URI("file:///tmp/example-project")
(root / "src").makedirs()

with (root / "src" / "main.py").open("w") as handle:
    handle.write("print('hello world')\n")

with WorkingDirectory(root):
    readme = URI("file://./README.txt")
    if not readme.exists():
        with readme.open("w") as handle:
            handle.write("Generated from abl.vpath\n")
```

URI instances automatically resolve and cache a connector, so subsequent
operations on the same path reuse the underlying file system connection.

## Built-in connectors

abl.vpath ships with three connectors that cover the most common scenarios:

| Scheme | Description | Example |
| --- | --- | --- |
| `file://` | Interact with the local file system on POSIX and Windows. | `URI("file:///var/tmp/project")` |
| `memory://` | An in-memory filesystem that is ideal for tests. Data lives for the lifetime of the process. | `URI("memory:///tmp/cache")` |
| `zip://((…))/` | Treat members of a ZIP archive as regular paths. Embed the archive URI between double parentheses. | `URI("zip://((file:///tmp/archive.zip))/logs/output.txt")` |

All connectors expose the same API surface, so features such as `listdir()`,
`walk()`, and `copy()` behave consistently across backends.

## Extending abl.vpath

Custom connectors can be registered through the `abl.vpath.plugins` entry
point group. A minimal setuptools configuration looks like this:

```toml
[project.entry-points."abl.vpath.plugins"]
s3 = "myapp.s3:S3FileSystem"
```

Your implementation only needs to inherit from
`abl.vpath.base.fs.FileSystem`, set a unique `scheme`, and provide an
accompanying `uri` class that extends `abl.vpath.base.fs.BaseUri`. Once
installed, new URIs such as `URI("s3://bucket/path")` will automatically
resolve to your connector.

## Documentation

Additional guides and the full API reference live under `docs/`. Build the
Sphinx documentation with:

```bash
make -C docs html
```

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

## License

abl.vpath is distributed under the MIT license (see LICENSE).
