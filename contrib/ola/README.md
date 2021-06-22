# Open Lighting Architecture

> **[https://www.openlighting.org](https://www.openlighting.org)**


### Motivation

To be able to control low-voltage RGBW LED strips from Lumina, a LED controller
will be needed. I found the following DMX controller on ebay:
[DMX512 Decoder 4CH Channel 16A RGBW Controller led stage Dj lighting CMOS Output](http://www.ebay.com/itm/171445263573)

It uses DMX, and consequently a method of controller DMX from a Rasberry Pi is
required. The following USB adapter provides this:
[Satge Lighting Controller Dimmer USB to DMX Interface Adapter DMX512 Computer PC](http://www.ebay.com/itm/321654347049).

The software library needed to control DMX from Lumina is provided by `ola`.


### Links

Download and install:

  * https://www.openlighting.org/ola/getting-started/downloads/
  * https://www.openlighting.org/ola/linuxinstall/
  * https://www.openlighting.org/ola/tutorials/ola-on-raspberry-pi/

Releases:

  * https://github.com/OpenLightingProject/ola/releases

The codebase:

  * https://github.com/OpenLightingProject/ola


## Installation

Per 2017-02-12 Ubuntu 16.04 contains `ola` version 0.9.8 and Rasbian 0.9.1,
which is both old. Current latest version is 0.10.3. Rasbian stretch (testing)
contains 0.10.3. All of these versions seems to work with Lumina.

This directory contains a custom patched version of `ola`, removing many of
the unneeded plugins. It was a part of an attempt to see if the performance
of ola could be increased. This custom version is not required to run
Lumina. 

Install official version with:
```
$ sudo apt install ola ola-python
```


## Configuration

Disable all devices that is not needed. Edit `/etc/ola/*.conf` and set
`enabled = false`. For the current Rasbian installation, the following files
had to be changed:

  * `ola-artnet.conf`
  * `ola-pathport.conf`
  * `ola-shownet.conf`
  * `ola-sandnet.conf`
  * `ola-osc.conf`
  * `ola-kinet.conf`
  * `ola-espnet.conf` 
  * `ola-e131.conf`

Alternative script:
    (for f in *.conf; do echo $f; sed -i -e 's/enabled = true/enabled = false/' $f; done)

To verify run:

```
$ ola_dev_info
Device 1: Dummy Device
  port 0, OUT Dummy Port, RDM supported
Device 2: Anyma USB Device
  port 0, OUT
```

Lumina assumes using universe 0, and it will need to be patched to the
appropriate device:

```
$ ola_patch --device 2 --port 0 --universe 0
```

To verify operations run

```
$ ola_set_dmx --universe --dmx 255,0,0,0
$ ola_dmxconsole        # Not present in older versions
```


### Manual configuration

All plugins can be listed with:

```
$ ola_plugin_info
   Id	Plugin Name
--------------------------------------
   ...
   12	USB
   ...
--------------------------------------
```

Edit `/etc/ola/ola-port.conf` and add:

```
12-2-O-0 = 0
```

Using encoding plugin 12 - device 2 - output - port 0 = universe 0


## Custom build

The [`build`](build) script in this directory provides an easy method to
build ola.

 1. Setup docker image. See [`contrib/docker/README.md`](../docker/README.md)

 2. Run the compilation using the docker builder:

    ```
    $ ../docker/run-docker rpi -- ./build -b build-rpi
    ```

    The `rpi` argument indicates building using the Raspberry build image, and
    `build-rpi` denotes the directory where the output files will be
    placed.

 3. Copy the `build-rpi/*.deb` files to the target system and install them.
    For lumina it suffices to install the following:

    ```
    $ sudo dpkg -i ola_*.deb ola-python_*.deb
    $ sudo apt -f install
    ```

    The last operation will install all the missing packages required by
    ola.
