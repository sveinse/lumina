# Telldus - Wireless Smart Home Control

> **[http://www.telldus.se](http://www.telldus.se)**


### Motivation

Telldus makes equipment which is capable of controlling a wide range of
commodity smart home sensors and actuators.

Lumina support a [Tellstick Duo](http://telldus.se/produkt/tellstick-duo/) to
connect to a Raspberry Pi to read switches and control lighting.


### Links

The Telldus codebase can be found at:

  * http://developer.telldus.se/browser
  * https://github.com/telldus/telldus  (mirror)
    
    `$ git clone https://github.com/telldus/telldus.git`

Description for Debian based installations:

  * http://developer.telldus.com/wiki/TellStickInstallationUbuntu

A Debian repo is found here (probably outdated)

  * http://download.telldus.com/debian/

Some old descriptions in how to get Telldus up and running on the
Raspberry Pi

  * https://lassesunix.wordpress.com/2013/08/12/installing-telldus-core-on-raspberry-pi/



## Build

Telldus has to be build manually because most disto repos (noteably Raspbian)
does not have Telldus available. This directory contains a custom patched
version. The patch contains additional changes required to be able to build it
under Ubuntu 16.04 and some small code improvements taken from newer telldus
sources.

The [`build`](build) script in this directory provides an easy method to
build the telldus packages needed by Lumina.

 1. Setup broot. See [`contrib/broot/README.md`](../broot/README.md)

 2. Run the compilation using the broot builder:

    ```
    $ ../broot/run-docker rpi -- ./build -b build-rpi
    ```

    The `rpi` argument indicates building using the Raspberry build root, and
    `build-rpi` denotes the directory where the output files will be
    placed.

 3. Copy the `build-rpi/*.deb` files to the target system and install them.
    For lumina it suffices to install the following:

    ```
    $ sudo dpkg -i telldus-core_*.deb libtelldus-core2_*.deb
    $ sudo apt -f install
    ```

    The last operation will install all the missing packages required by
    telldus.



## Configuration

Configuration is found in `/etc/tellstick.conf`. When telldus has been
configured, it can be restarted using:

```
$ sudo service telldusd restart
```

Telldus can be verified using

```
$ tdtool --dimlevel 255 --dim 105
$ tdtool.py --dimplevel 255 --dim 105
```



## Sources

The original Debian source distribution consists of:

  * `telldus-core_2.1.2-1.dsc`
  * `telldus-core_2.1.2.orig.tar.gz`
  * `telldus-core_2.1.2-1.debian.tar.gz`

How to fetch:
```
$ sudo nano /etc/apt/sources.list.d/telldus.list
      deb-src http://download.telldus.com/debian/ stable main
$ sudo wget -q http://download.telldus.se/debian/telldus-public.key -O- | apt-key add -
$ sudo apt update
$ apt source telldus
```

or browse directly into the debian pool
http://download.telldus.com/debian/pool/stable/ and download the files
manually.

See the `telldus-core_*.dsc` file for the hash-sums of the `telldus-core_2.1.2.orig.tar.gz` file.

From what I can tell this repo is identical as commit 1f93cf in the upstream
repos. Two noteable changes are interesting and have been included in below patch
    
  * commit `ed3ce3` upstream
  * commit `4401b1` in https://github.com/telldus/telldus/pull/8/commits/4401b10551cff09469c93dbc77db7360c05a8f57
