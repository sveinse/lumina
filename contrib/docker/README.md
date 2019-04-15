# Docker Lumina Build

This directory contains various scripts for setting up build environments
in Docker containers, named *lub* (Lumina Build).

Currently the supported build environments:

  * **xenial** - Ubuntu native Xenial (16.04)
  * **rpi** - Raspberry Pi Raspbian

**Note:** The author is running Ubuntu, so all these procedures and package
names refer to Ubuntu package names. Your mileage might vary for other distros.
Contributions are very welcome.


## Installation

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

   Then chose one or more target machines that you'd like to create
   build image for. It will create Docker images named `lub:<VARIANT>`

   ```
   # Raspberry Pi Build image (lub:rpi)
   ./setup-docker-lub-rpi <IMAGE.img>

   # Ubuntu native 16.04 Xenial build image (lub:xenial)
   ./setup-docker-lub-xenial
   ```

   **Note:** The `setup-docker-lub-rpi` script will require sudo root access to
   be able to read the files from the SD-Card image. Please cat the script if
   you want to inspect the operations.

   The operation for the ARM variants does not install very fast, outright slow,
   as it runs ARM code under emulated QEmu environment. Sometimes this emulation
   fails miserably and the installation completely stops.


## Usage

The `run-docker` script is provided to make it easy to run commands using the
docker images. The script binds the base directory of the Lumina source
directory to the docker directory `/build`. When the docker command is run
the container is removed ensuring that the doker image remains unchanged from
previous runs.

Usage:
```
run-docker [OPTIONS] NAME [--] [COMMAND [ARGS]]
```

 * `NAME` - The `lub:NAME` docker image to run from
 * `COMMAND` - The command to run. If omitted, a interactive shell will
   be used.
 * `ARGS` - Command arguments. Please use the `--` separator to separate
   the options for `run-docker` from the `COMMAND`.

The most common use case is to use `run-docker` to call a build script under
docker. E.g. telldus is build using

```
../docker/run-docker rpi -- ./build -b build-rpi
```

This runs `./build -b build-rpi` under the `lub:rpi` docker container.
