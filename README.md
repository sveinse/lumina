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

This project started as a one-off installation in the authors home cinema.
The plugins mainly represents the author's own equipment. The project is
a work in progress.



## Source layout

The sources comprise of the following files:

 * `bin/` - Binary tools
 * `conf/` - Lumina configuration example
 * `contrib/` - Various additions and 
   * `contrib/broot` - Docker based build roots scripts
   * `contrib/deploy` - Deployment scripts for the author's home cinema
   * `contrib/ola` - Open Lighting Architecture (for DMX)
   * `contrib/rpi` - Rasberry Pi installation (Raspian) notes
   * `contrib/telldus` - Telldus Packages (for lighting and sensor communication)
 * `debian/` - Debian package descriptions
 * `lumina/` - Main Lumina Python sources
   * `lumina/__init__.py` - The VERSION of Lumina
   * `lumina/plugins` - Lumina plugins
   * `lumina/plugins/tests` - Plugins for testing
 * `www/` - The web-pages and scripts for Lumina
 * `LICENSE`
 * `Makefile` - Build and packaging helper
 * `README.md` - This file
 * `setup.py` - Main Python installation script
 * `TODO.md` - All things dreamt of but never accomplished


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


### Debian package

A Debian package can be build using the `Makefile` target

```
make debs
```

It will build the package in `build/` and produce the debian files in `debs/`.

**Note:** It is not recommended to build the Debian package directly like this. 
Debian pre-cleans the sources before building, and this clean can erase too
much if there are other directories or packages being worked on in `contrib/`.
See below for a Docker based build environment.

### Cross building

Lumina is made for running on embedded targets, e.g the Raspberry Pi or
on Ubuntu for ARM. The `contrib/broot/` directory contains tools to setup a
cross build environment to build Lumina using Docker and Qemu. It currently
support Raspberry Pi, Ubuntu 16.04 ARM and Ubuntu 16.04 native *).

*(The latter target is not an embedded platform per se, but through Docker
it offers a convenient isolated build environment that does not clobber the
host.)*

**Note:** The author is running Ubuntu, so all these procedures and package
names refer to Ubuntu package names. Your mileage might vary for other distros. 
Contributions are very welcome.

A simple procedure for setting up and cross build Lumina is:

1. **Download**. If building for Raspberry Pi, download the Jessie Light
   image from
   [Raspbian SDCard images](https://www.raspberrypi.org/downloads/raspbian/)
   and unpack the image file.

2. **Install Docker and qemu**. On an Ubuntu this is

   ```
   apt install docker-engine qemu-user-static debootstrap
   ```

   **Note:** Some setting up is probably required, which is outside the scope
   of this description.

3. **Create Docker image**

   ```
   cd contrib/broot
   ```

   Then chose one (or all) of the target machines that you'd like to create
   build root image for. It will create 
   Docker images named `broot:<VARIANT>`

   ```
   # Raspberry Pi Build root (broot:rpi)
   contrib/broot/build-rpi <IMAGE.img>

   # Ubuntu armhf 16.04 Xenial build root (broot:xu)
   contrib/broot/build-xu

   # Ubuntu native 16.04 Xenial build root (broot:xenial)
   contrib/broot/build-xenial
   ```

   **Note:** The `build-rpi` script will require sudo root access to be able to
   read the files from the SD-Card image. Please inspect the script if you want to 
   inspect the operations.

   The operation for the ARM variants does not install very fast, outright slow,
   as it runs ARM code under emulated QEmu environment. Sometimes this emulation
   fails miserably and the installation completely stops.

Steps 1 - 3 needs only be executed once. To build Lumina do the following
steps:

4. **Build**

    ```
    make docker-debs t=<VARIANT>
    ```

    will call `contrib/broot/run-docker` to build the debian files under
    Docker image `broot:<VARIANT>`. Example: `make docker-debs t=rpi` will
    build Rasberry Pi packages. It will build in `build-rpi/` and place the
    output in `debs-rpi/`.

    **Tips:** If you don't want to clobber the host environment for building
    the native Debian package, using this prodcedure for the `xenial` will
    generate debian package for your host.


## License

Copyright 2010-2017, Svein Seldal <<sveinse@seldal.com>>

This application is licensed under
[GNU GPL version 3](http://gnu.org/licenses/gpl.html). This is free software:
you are free to change and redistrbute it. There is no warranty to the
extent permitted by law.
