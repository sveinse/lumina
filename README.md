# Lumina

> **Home theater automation controller framework**

**Homepage:** [https://github.com/sveinse/lumina](https://github.com/sveinse/lumina)

Lumina is a small lightweight distributed framework for interfacing external
equipment and provide programmable rules for controlling the equipment. The
intended use-case is to control lighting and electronics in a home theater
setup. It provides programmable actions when events occur triggered by events
from equipment or from the built-in web-server.

The Lumina framework is written in Python 2.7 using Twisted. It is well-suited
for being run on small embedded Linux devices, such as the Rasberry Pi. 

### History

This project started as a one-off installation for controlling the equipment
in the authors home cinema. As a consequence, the current plugins offered
by Lumina mainly represents the author's own equipment.

### Architecture

Lumina is a network communication and controller framework that runs on one or
more **hosts** (or instances). Each host runs loadable **plugins**. Plugins
which communicates with external equipment is called **nodes** and can run on
any host. One designated host must run the **server** plugin, which provides
the connection point and messaging central for the nodes. Each node provide
a set of **commands** for executing operation on the equipment and each node
can send **events** to the server.

The **responder** plugin connects the incoming event from a node and execute a
configurable command or chain of commands. The **web** plugin provides a web-
interface to Lumina, which provides a control interface from smartphones and
other computers.

More information about the technical architecture and implementation can
be found here: [`Lumina design`](docs/lumina.md)

### Supported plugins and interfaces

 Plugin | Type | Description
 ------ | -----| ------
 [`hw50     `](lumina/plugins/hw50.py) | Node | Sony VPL-HW50 Projector interface
 [`led      `](lumina/plugins/led.py) | Node | Simple DMX LED strip controller
 [`lirc     `](lumina/plugins/lirc.py) | Interface | Linux IR interface plugin
 [`oppo     `](lumina/plugins/oppo.py) | Node | Oppo BDP-103 media player interface
 [`responder`](lumina/plugins/responder.py) | Server | Main event manager handling responses to incoming events
 [`rxv757   `](lumina/plugins/lirc.py) | Node | Yamaha RX-V757 IR interface
 [`server   `](lumina/plugins/server.py) | Server | Main Lumina node server
 [`telldus  `](lumina/plugins/telldus.py) | Node | Telldus home automation interface
 [`web      `](lumina/plugins/web.py) | Server | Lumina Web interface
 [`yamaha   `](lumina/plugins/yamaha.py) | Node | Yamaha Aventage family interface


## Source layout

The sources comprise of the following files:

 * `bin/` - Binary tools
 * `conf/` - Lumina configuration example
 * `contrib/` - Supporing tools and utilities not part of Lumina
 * `debian/` - Debian package descriptions
 * `docs/` - Documentation
 * `lumina/` - Main Lumina Python sources
   * `lumina/__init__.py` - The VERSION of Lumina
   * `lumina/plugins/` - Lumina plugins
   * `lumina/plugins/tests/` - Plugins for testing
 * `www/` - The web-pages and scripts for Lumina
 * `LICENSE`
 * `MANIFEST.in` - Python package manifest
 * `Makefile` - Build and packaging helper
 * `README.md` - This file (main readme)
 * `README.rst` - Python package readme. Contains except from `README.md`.
 * `TODO.md` - All things dreamt of but not yet accomplished
 * `setup.py` - Main Python installation script

### contrib/ layout

`contrib/` contains a number of extra tools and utilities for implementing
Lumina on embedded devices, such as Raspberry Pi.

 * `contrib/docker/` - Docker build image for setting up a compilation
   environment for building Lumina and other supporting packages for
   embedded hosts.
   [More information...](contrib/docker/README.md)
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
on Ubuntu for ARM. The `contrib/docker/` directory contains tools to setup a
cross build environment to build Lumina using Docker and Qemu. It currently
support Raspberry Pi, Ubuntu 16.04 ARM. It also support building native
Ubuntu 16.04 packages. This allows building the packages without clobbering
the host system.

To build Lumina do the following steps:

1. **Setup**. Setup the docker build image. This will have to be done
   once. Please see [Docker build image](contrib/docker/README.md) for
   instructions how to set it up.

2. **Build**

    ```
    make docker-debs t=<VARIANT>
    ```

    This will call `contrib/docker/run-docker` to build the debian files under
    Docker image `lub:<VARIANT>`. Example: `make docker-debs t=rpi` will
    build Rasberry Pi packages. It will build in `build-rpi/` and place the
    output in `dist-rpi/`.

    **Tips:** If you don't want to clobber the host environment for building
    the native Debian package, using this prodcedure for the `xenial` will
    generate debian package for your host.


## License

Copyright 2010-2018, Svein Seldal <<sveinse@seldal.com>>

This application is licensed under
[GNU GPL version 3](http://gnu.org/licenses/gpl.html). This is free software:
you are free to change and redistrbute it. There is no warranty to the
extent permitted by law.

Read the full [License](LICENSE)
