Lumina
======

> **Home theater automation controller framework**

**Homepage:** <https://github.com/sveinse/lumina>

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

History
-------

This project started as a one-off installation in the authors home cinema.
The plugins mainly represents the author's own equipment. The project is
a work in progress.


License
=======

| Copyright 2010-2017, Svein Seldal <<sveinse@seldal.com>>

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software:
you are free to change and redistrbute it. There is no warranty to the
extent permitted by law.
