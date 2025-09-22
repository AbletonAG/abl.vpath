Extending abl.vpath
===================

abl.vpath discovers connectors through the ``abl.vpath.plugins`` entry point
group. Shipping your own backend therefore only requires two pieces:

1. A subclass of :class:`abl.vpath.base.fs.FileSystem` (plus a matching URI
   type) that implements the operations you care about.
2. An entry point declaration so abl.vpath can load the connector at runtime.

Implementing a connector
------------------------

A minimal connector needs to provide a :pyattr:`scheme` attribute and a
:pyattr:`uri` pointing at a :class:`abl.vpath.base.fs.BaseUri` subclass. The
methods you override depend on your storage system, but the helpers defined
on :class:`~abl.vpath.base.fs.FileSystem` make it straightforward to build on
existing implementations.

.. code-block:: python

   # myapp/s3.py
   from abl.vpath.base.fs import FileSystem, BaseUri

   class S3Uri(BaseUri):
       pass

   class S3FileSystem(FileSystem):
       scheme = "s3"
       uri = S3Uri

       def _initialize(self):
           self._client = create_s3_client(self.extras)

       def exists(self, path):
           return self._client.object_exists(path.path)

       def open(self, path, options=None, mimetype="application/octet-stream"):
           if options and "w" in options:
               return self._client.open_for_write(path.path)
           return self._client.open_for_read(path.path)

Registering the connector
-------------------------

Expose the connector through your project's packaging metadata. With
``pyproject.toml`` this looks like:

.. code-block:: toml

   [project.entry-points."abl.vpath.plugins"]
   s3 = "myapp.s3:S3FileSystem"

As soon as the distribution is installed, new URIs such as
``URI("s3://bucket/path")`` will automatically use the connector.

Tips for connector authors
--------------------------

- Forward the ``extras`` keyword arguments you receive to your backend, as
  callers can pass information (for example credentials) when constructing
  the URI.
- Reuse the helpers exposed on :class:`~abl.vpath.base.fs.FileSystem` where
  possible; methods like :meth:`copy`, :meth:`remove`, and :meth:`walk` offer
  solid defaults.
- Write tests with the in-memory connector to simulate interactions with
  your backend. The bundled `tests/` directory includes many fixtures that
  can be repurposed.
