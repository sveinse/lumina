# Lumina

> **Home theater automation controller framework**

**Homepage:** [https://github.com/sveinse/lumina](https://github.com/sveinse/lumina)

Lumina is a distributed framework for controlling lighting and home theater
equipment (such as AV receivers, projectors). It can provide programmable
action when events occur, either from the equipment and sensors or from the
built-in web-server.

It is well-suited for being used by small embedded Linux devices, such as the
Rasberry Pi, connected in a distributed networks. Each node (client) connects to
a central server which provides messaging services. It also provides a small
built-in web-interface.

The Lumina framework is written in Python 2.7 using Twisted. It use plugin
based client-server scheme, giving great flexibility.

### History

This project started as a one-off installation for controlling the equipment
in the authors home cinema. As a consequence, the current plugins offered
by Lumina mainly represents the author's own equipment.



## Source layout

The sources comprise of the following files:

 * `bin/` - Binary tools
   * `bin/lumina.py` - Development tool to be able to run lumina in-source.
 * `conf/` - Lumina configuration example
 * `contrib/` - Supporing tools and utilities not part of Lumina
 * `debian/` - Debian package descriptions
 * `lumina/` - Main Lumina Python sources
   * `lumina/__init__.py` - The VERSION of Lumina
   * `lumina/plugins/` - Lumina plugins
   * `lumina/plugins/tests/` - Plugins for testing
 * `www/` - The web-pages and scripts for Lumina
 * `LICENSE`
 * `Makefile` - Build and packaging helper
 * `MANIFEST.in` - Python package manifest
 * `README.md` - This file (main readme)
 * `README.rst` - Python package readme. Contains except from `README.md`.
 * `setup.py` - Main Python installation script
 * `TODO.md` - All things dreamt of but not yet accomplished

### contrib/ layout

`contrib/` contains a number of extra tools and utilities for implementing
Lumina on embedded devices, such as Raspberry Pi.

 * `contrib/broot/` - Docker build image for setting up a compilation
   environment for building Lumina and other supporting packages for
   embedded hosts. 
   [More information...](contrib/broot/README.md)
 * `contrib/deploy/` - Deployment script for the authors implementation
   of Lumina. It can serve as an example in how to deploy Lumina to multiple
   devices.
   [More information...](contrib/deploy/README.md)
 * `contrib/ola/` - The Open Lighting Architecture required by the `led`
   plugin.
   [More information...](contrib/ola/README.md)
 * `contrib/rpi/` - Setup description in how to setup and prepare a
   Raspberry Pi for Lumina.
   [More information...](contrib/rpi/README.md)
 * `contrib/telldus/` - Packages for Telldus.
   [More informaion...](contrib/telldus/README.md)


## Installation

Lumina can be installed using the standard python setuptools or by using `pip`.

```
python setup.py install    #  *or*

pip install .
```

A good way of using python is through virtualenv. It provides an isolated
environment for this application to run. For more information see the 
virtualenv documentation.

```
virtualenv venv
. venv/bin/activate
pip install -e .
lumina --help   # Or any other userful options
deactivate
```

The `venv/` directory is safe to delete after use. As a convenience, the
`Makefile` contains a small shortcut for doing the steps above:
`make mk-venv`

**Note:** The python module installation does not install Lumina as a
system service. To get it installed as a system service, plase consider
installing the Debian package.


### Debian package

A Debian package can be build using the `Makefile` target

```
make debs
```

It will build the package in `build/` and produce the debian files in `dist/`.

**Note:** If you don't want to clobber your host environment with the
build depends for building this package, please consider running this in
a Docker container. See below.


### Cross building

Lumina is made for running on embedded targets, e.g the Raspberry Pi or
on Ubuntu for ARM. The `contrib/broot/` directory contains tools to setup a
cross build environment to build Lumina using Docker and Qemu. It currently
support Raspberry Pi, Ubuntu 16.04 ARM. It also support building native
Ubuntu 16.04 packages. This allows building the packages without clobbering
the host system.

To build Lumina do the following steps:

1. **Setup**. Setup the docker build root. This will have to be done
   once. Please see [Docker build root](contrib/broot/README.md) for
   instructions how to set it up.

2. **Build**

    ```
    make docker-debs t=<VARIANT>
    ```

    This will call `contrib/broot/run-docker` to build the debian files under
    Docker image `broot:<VARIANT>`. Example: `make docker-debs t=rpi` will
    build Rasberry Pi packages. It will build in `build-rpi/` and place the
    output in `dist-rpi/`.

    **Tips:** If you don't want to clobber the host environment for building
    the native Debian package, using this prodcedure for the `xenial` will
    generate debian package for your host.


## License

Copyright 2010-2017, Svein Seldal <<sveinse@seldal.com>>

This application is licensed under
[GNU GPL version 3](http://gnu.org/licenses/gpl.html). This is free software:
you are free to change and redistrbute it. There is no warranty to the
extent permitted by law.

Read the full [License](LICENSE)
