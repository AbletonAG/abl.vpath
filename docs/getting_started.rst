Getting Started
===============

This guide walks through the day-to-day API offered by :mod:`abl.vpath`.
If you are familiar with :mod:`os.path` or :mod:`pathlib`, the URI objects
provided by abl.vpath will feel immediately familiar.

Creating URIs
-------------

Use :class:`abl.vpath.base.fs.URI` to wrap a path string. The scheme component
chooses the connector; if omitted, abl.vpath assumes ``file://``:

.. code-block:: python

   from abl.vpath.base import URI

   local = URI("/tmp/project")                # resolved as file:///tmp/project
   memory = URI("memory:///tmp/cache")        # handled by the in-memory backend

URIs can be combined with the ``/`` operator or by calling
:meth:`~abl.vpath.base.fs.BaseUri.join`:

.. code-block:: python

   config = local / "config" / "settings.json"

Reading and writing
-------------------

URI objects expose file-like helpers that automatically talk to the
underlying connector:

.. code-block:: python

   data_dir = local / "data"
   data_dir.makedirs()

   payload = data_dir / "payload.txt"
   with payload.open("w") as handle:
       handle.write("hello world\n")

   with payload.open() as handle:
       print(handle.read())

The same code works for the in-memory and ZIP connectors without any
changes.

Listing and walking directories
-------------------------------

Directory-oriented helpers mirror the behaviour of :mod:`os`:

.. code-block:: python

   for entry in data_dir.listdir():
       print(entry)

   for root, dirs, files in data_dir.walk():
       print(root, files)

The ``root`` variable returned by :meth:`~abl.vpath.base.fs.BaseUri.walk` is
also a URI, so you can keep using the URI helpers inside the loop.

Working within a URI
--------------------

:class:`abl.vpath.base.misc.WorkingDirectory` temporarily switches the
process' current directory, making it straightforward to reuse code that
expects relative ``file://`` URIs:

.. code-block:: python

   from abl.vpath.base import WorkingDirectory

   with WorkingDirectory(local):
       readme = URI("file://./README.txt")
       print(readme.exists())

At the end of the context manager the previous working directory is restored.

Accessing ZIP archives
----------------------

The ZIP connector treats archive contents as if they were regular paths.
Embed the archive URI between double parentheses to point abl.vpath at the
container:

.. code-block:: python

   archive_member = URI("zip://((file:///tmp/archive.zip))/logs/output.txt")
   if archive_member.exists():
       print(archive_member.open().read())

This works with in-memory archives as well, e.g.
``zip://((memory:///buffer.zip))/document.txt``.
