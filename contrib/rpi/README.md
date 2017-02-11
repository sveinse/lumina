# Raspberry Pi installation for Lumina

This document outlines how to setup a usable Raspberry Pi image to be used
with Lumina.

Last update: 2017-02-10


 1. **Download image.** Any Rasbian is ok, but Jessie Lite will suffice.

    > https://www.raspberrypi.org/downloads/raspbian/


 2. **Unpack and install**

    ```
    $ unzip 2017-01-11-raspbian-jessie-lite.zip
    $ sudo dcfldd bs=4M if=2017-01-11-raspbian-jessie-lite.img of=/dev/mmcblk0
    ```

    `dcfldd` is an improved version of `dd`. It works well with ordinary `dd`.


 3. **Boot target** and log in.

    ```
    login: pi
    password: raspberry
    ```

    Use `sudo su -` to become root. Whenever a line below begins with `'#'`
    denotes a command executed by root, either directly as root or via
    `sudo <command>`.

    From now on, all commands below is to be executed on the target Raspberry
    Pi system.


 4. **Configure device**.

    ```
    # raspi-config
    ```

    Set the following operations (where applicable):

    * Change user password
    * Internationalisation options
        - Add locales. Optional if the default is OK.
            - `en_US.UTF-8` and make it default
            - `nb_NO.UTF-8`   (author's convenience)
        - Set timezone
        - Set keyboard layout
        - Set Wifi country
    * Advanced options
        - Set hostname
        - Enable SSH (if this service is wanted)


 5. **Update software**

    ```
    # apt update
    # apt dist-upgrade    # Will take some time
    ```

 6. **Setup WiFi** -- optional

    Edit `/etc/wpa_supplicant/wpa_supplicant.conf` and add the following
    text with the appropriate information for your WiFi network:

    ```
    network={
        ssid="yourSSID"
        psk="password"
    }
    ```    

 7. **Update boot config** -- optional

    If you experience problems with the screen resolution when using HDMI
    out, I've found to resolve some of my screen issues. Edit
    `/boot/config.txt`

    ```
    # Force HDMI mode
    hdmi_group = 1
    hdmi_mode = 16    # 16=1080p, 4=720p

    # Disable audio
    #dtparam=audio=on
    ```

 8. **SSH shared key** for automatic login -- optional

    If you want to have automatic login using your SSH key, do the following
    steps:

    ```
    $ mkdir .SSH
    $ chmod 700 .ssh
    $ touch .ssh/authorized_keys
    $ chmod 600 .ssh/authorized_keys
    ```

    Edit the `.ssh/authorized_keys` file and paste your public key into the
    editor and save it.

    In convenience I also find use for the following configuration in the
    remote desktop user's machine's `.ssh/config`:

    ```
    Host mypi.local
        HostName mypi.local
        User pi
        IdentityFile %d/.ssh/my_pi_id
    ```

 9. **Reboot**

    At this point it can be wise to reboot the machine. Cleaning up
    after any update with `apt-get clean` is also smart for saving space.


## Application specific setup

### Lumina development

1. For development, the following tools will need to be installed:
   ```
   # apt install rsync
   ```

> * **`rsync`** installs `rsync`

### Lumina runtime

Lumina requires Twisted >=16.0.0 and unfortunately this is not available
out of box per 2017-02. Luckily it is available in the Raspberry Pi
development repo, *stretch*.

1. Create `/etc/apt/preferences.d/stretch.pref`:
   ```
   Package: *
   Pin: release n=jessie
   Pin-Priority: 900

   Package: *
   Pin: release n=stretch
   Pin-Priority: 750
   ```

3. Create `/etc/apt/sources.list.d/stretch.list`:
   ```
   deb http://mirrordirector.raspbian.org/raspbian/ stretch main 
   ```

4. Update sources and install packages
   ```
   # apt update
   # apt install python-setproctitle
   # apt install python-twisted -t stretch
   ```

> * **`python-secproctitle`** installs `python-setproctitle`
> * **`python-twisted`** installs `libssl1.1 python-attr python-cffi-backend
  python-click python-colorama python-constantly python-cryptography
  python-enum34 python-idna python-incremental python-ipaddress python-openssl
  python-pam python-pkg-resources python-pyasn1 python-pyasn1-modules
  python-serial python-service-identity python-setuptools python-six
  python-twisted python-twisted-bin python-twisted-core python-zope.interface`


### Telldus

See build instructions in [`contrib/telldus/REAME.md`](../telldus/README.md).

> * **`telldus-core libtelldus-core2`** installs `libconfuse-common libconfuse0 libftdi1`
