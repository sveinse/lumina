# Docker Build Root

This directory contains various scripts for setting up build environments, 
called *broot*, using [Docker](https://www.docker.com/)

Currently the supported build roots:

  * **xenial** - Ubuntu native Xenial (16.04)
  * **xu** - Ubuntu armhf Xenial (16.04)
  * **rpi** - Raspberry Pi Raspbian

(The name *xu* comes from a Odroid XU device which runs Ubuntu armhf.)

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
   build root image for. It will create Docker images named `broot:<VARIANT>`

   ```
   # Raspberry Pi Build root (broot:rpi)
   ./build-rpi <IMAGE.img>

   # Ubuntu armhf 16.04 Xenial build root (broot:xu)
   ./build-xu

   # Ubuntu native 16.04 Xenial build root (broot:xenial)
   ./build-xenial
   ```

   **Note:** The `build-rpi` script will require sudo root access to be able to
   read the files from the SD-Card image. Please inspect the script if you want to 
   inspect the operations.

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

 * `NAME` - The `broot:NAME` docker image to run from
 * `COMMAND` - The command to run. If omitted, a interactive shell will
   be used.
 * `ARGS` - Command arguments. Please use the `--` separator to separate
   the options for `run-docker` from the `COMMAND`.

The most common use case is to use `run-docker` to call a build script under
docker. E.g. telldus is build using

```
../broot/run-docker rpi -- ./build -b build-rpi
```

This runs `./build -b build-rpi` under the `broot:rpi` docker container.
