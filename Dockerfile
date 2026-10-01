FROM ubuntu:24.04
ARG environment
ENV LANG=C.UTF-8
# Set a fixed version for setuptools-scm when testing
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ABL_VPATH=1.0.0
RUN apt-get update && apt-get install --assume-yes --no-install-recommends \
        python3.12 \
        python3.12-venv \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/abl.vpath/
COPY . /opt/abl.vpath/
RUN python3.12 -m venv /opt/abl.vpath/.venv
ENV VIRTUAL_ENV=/opt/abl.vpath/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install -e .[test]
