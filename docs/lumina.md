# Lumina design

This document describes the design and architecture of Lumina.


## Overview

Lumina is written in Python 2 and is using the
[Twisted](http://twistedmatrix.com/trac/) framework. Lumina is designed to
run in a distributed system using multiple devices. One of the design goals
of Lumina is to be able to run on embedded linux devices, such as the
Raspberry Pi. 

**Note:** All refrences to files in this document refers to the files located
in the [`lumina/`](../lumina/) directory.


## Architecture

Lumina is a network communication and controller framework that can run
on one or more hosts. The network topology is a client-server architecture,
where data connection flows from clients, named **nodes**, to a central
server. The server acts as a connection point and a message hub.

The functionality of Lumina is divided into loadable **plugins**, each which
performs a certain task or role. One host must run the **server**.
**Node** plugins provides the main interface to external equipment and
feeds data in or out of the server. The node can accept **commands** from the
server, or issue asynchronous **events** from the node to the
server.

Plugins may subscribe to incoming **events**. E.g. the `responder` plugin
provides the main glue logic for the functionality of Lumina. It has a set of
rules that determines the actions (that is commands) in response to incoming
events coming from nodes.

### Nodes

A node is the connector between external equipment or interfaces and the
Lumina server. A node will connect to the server using TCP and declare its
capabilities, that is *commands* and *events*.


## Configuration


## Plugins

Lumina is a system consisting of configurable plugins. The current
list of plugins are:

 Plugin | Description
 ------ | -----------
 [`admin    `](../lumina/plugins/admin.py) | Administration plugin, will be started automatically in each instance.
 [`graphite `](../lumina/plugins/graphite.py) | (OLD)
 [`hw50     `](../lumina/plugins/hw50.py) | (OLD)
 [`led      `](../lumina/plugins/led.py) | LED strip control using DMX
 [`oppo     `](../lumina/plugins/oppo.py) | (OLD)
 [`responder`](../lumina/plugins/responder.py) | Main event controller for handling responses to incoming events.
 [`rules    `](../lumina/plugins/rules.py) |
 [`server   `](../lumina/plugins/server.py) | Main Lumina server
 [`telldus  `](../lumina/plugins/telldus.py) | Telldus home automation interface
 [`utils    `](../lumina/plugins/utils.py) | (OLD)
 [`web      `](../lumina/plugins/web.py) | Web interface
 [`yamaha   `](../lumina/plugins/yamaha.py) | (OLD)


## Python files

 File | Description
 ---- | -----------
 [`__init__.py`  ](../lumina/__init__.py) | The Lumina version is defined here
 [`__main__.py`  ](../lumina/__main__.py) | Main command line dispatcher
 [`callback.py`  ](../lumina/callback.py) | (OLD)
 [`config.py`    ](../lumina/config.py) | Handling the Lumina configuation file.
 [`event.py`     ](../lumina/event.py) | The main client-server message class
 [`exceptions.py`](../lumina/exceptions.py) | Lumina exceptions
 [`log.py`       ](../lumina/log.py) | Logger resources
 [`lumina.py`    ](../lumina/lumina.py) | Main server manager
 [`node.py`      ](../lumina/node.py) | Base class for nodes, Lumina data collectors
 [`protocol.py`  ](../lumina/protocol.py) | Lumina communication protocol
 [`state.py`     ](../lumina/state.py) | State variable class.
 [`utils.py`     ](../lumina/utils.py) | Collection of helper functions


## Writing plugins

A Lumina plugin must be located in [`lumina/plugins/`](../lumina/plugins/).
A plugin is expected to inherit the `Plugin` class from
[`plugin.py`](../lumina/plugin.py):

```python
from __future__ import absolute_import
from lumina.plugin import Plugin

class MyPlugin(Plugin):
    ''' Plugin docstring '''

PLUGIN = MyPlugin
```

The class must provide a short docstring to present the purpose of the
plugin. The plugin must create a reference to the plugin class.

**NOTE:** If the plugin overrides any of the super class methods, please 
remember to call them manually from your implementation of the method.
Python does not automatically call super methods in classes.


#### `self.CONFIG` (optional)

If the plugin has configuration options, this can be specified by listing
them in a class attribute dict named `CONFIG`:

```python
class MyPlugin(Plugin):
    CONFIG = {
        'option': dict(default='foo', help='Option help', type=str),
    }
```

This config option is avaible from the configuration file as
`'myplugin.option = ...'` when the name of the plugin is `myplugin`.

The option `common=True` can be used to indicate a global configuration option.
This will make the config available in the global scope, which would be
`'option = ...'` for the example above.

The plugin can be loaded with an alternative name. E.g. the config
`'PLUGINS = "myplugin(mp)"'` will change the config option to become
`'mp.option = ...'`.


#### `self.configure()` (optional)

The `configure()` class method is the first method to be called and is intended
to prepare and configure the class if needed. The super `Plugin.configure()`
does not need to be called.


#### `self.setup()`

The `setup()` class method shall set up the plugin and start the appropriate
services for the plugin. The super 'Plugin.setup()' must be called first in
this method. The main argument represents a reference to the main Lumina
instance.

```python
   def setup(self, main):
       Plugin.setup(self, main)
```


#### `self.log`

A [`Logger()`](../lumina/log.py) is available in `self.log` to
provide logging mechanisms in the plugin. E.g.

```python
   self.log.info("Made it")
```


#### `self.status`

All plugins must keep a simple status of its current running state. This
is done through the `status` attribute, which is a [`ColorState()`](../lumina/state.py) instance. It is created by `Plugin.setup()`. The status
can be set using:

```python
   self.status.set_GREEN(why)
```

The colors are intended to convey a simple overview of the status of the
plugin. An optional short one-line description of the cause can be given with the
`why` argument.

  | Color | Description |
  | --- | --- |
  OFF | Disconnected, off, not active
  RED | Malfunction, error
  YELLOW | Pending, warning, in progress
  GREEN | Normal, OK


### Plugin execution

The main Lumina controller [`lumina.py`](../lumina/lumina.py) sets
up the plugin in the following manner:

 1. Instantiate the object indicated by `PLUGIN`

    ```python
      plugin = PLUGIN()
    ```

 2. Set name attributes

    ```python
      plugin.name = name          # The configured name of the plugin
      plugin.module = module      # The plugin module name
      plugin.sequence = sequence  # Plugin sequence number
    ```

 3. Call `configure()`. This function is intended populate any internal
    attributes the class might need. This is particularly significant in nodes
    (see below).

    ```python
      plugin.configure()
    ```

 4. Register the config options as given in `plugin.CONFIG`

 5. Call `setup()`. This function shall set up and run the plugin. The `main`
    argument is a reference to the main `Lumina()` engine instance.

    ```python
      plugin.setup(main)
    ```

 6. The engine will after this start other plugins and start the main event
    loop. When the server is shut down it will eventually call the close
    function:

    ```python
      plugin.close()
    ```


## Writing nodes

Nodes provides the interfaces to external equipment and interfaces. A node
shall inherit the `Node` class from [`node.py`](../lumina/node.py). A
node is a plugin, and thus `Node` is a subclass of `Plugin`.
The node must be written in accordance to the plugin requirements above with
the additions outlined in this section.

To create a node, make a custom class inheriting `Node`:

```python
from __future__ import absolute_import
from lumina.node import Node

class MyNode(Node):
    ''' Node docstring '''
```

#### `self.CONFIG`

As a plugin, the node can also provide configuration options. Note that the
parent Node class has a set of configuration options that must be preserved. 
The parent node class configs must must be merged
with the node's configuration options using the `configure()` method:

```python
    def configure(self):
        self.CONFIG = Node.CONFIG.copy()
        self.CONFIG.update(MyNode.CONFIG)
```


#### `self.command` and `self.configure`

The node plugin must provide `self.command` and `self.configure` to specify
the node's functionality to the server. These attributes must be setup before
the `setup()` method returns. It is customary to set it up from the
`configure()` class method:

```python
    def configure(self):
        self.events = [
            'myevent',
        ]

        self.commands = {
            'mycommand': lambda a: self.mycommand(a.args[0]),
        }
```

`events` is a simple list of all the messages that this node can emit 
asynchronously to the server. `commands` is a dict with the command name and
a corresponding callback function for that specific function. The function can
return a
['Deferred'](https://twistedmatrix.com/documents/current/core/howto/defer.html)-object
if a result cannot be returned immediately. The `a` argument is the
receiving command from the server, an ['Event`](../lumina/event.py) object and
it can carry arguments.

**NOTE:** The `events` and `commands` will be prefixed with their node name
on the server. E.g. the node named `foo` which emits the event `bar` will be
processed on the server as an event named `foo/bar`.


#### `self.setup()`

The `setup()` method shall setup the services for communicating with the 
external equipment or interface. Please remember to call the super
`Node.setup()` method first in the implementation of this function.
