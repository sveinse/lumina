TODO
====

* 2017-12-31 @sveinse

    * Rename 'main' to 'master'?

* 2017-09-17 @sveinse

    * Fix better error handling in lumina.configure_plugin(). What happens
      when if the plugin fails to load?
    * The current implementation of plugin and nodes does not behave
      consistently on close()
    * Implement RX757 as a separate plugin. The plugin will have to be stateful
      on power on/off to track the proper state of the pure_direct function.
    * Implement protection delay from issuing rxv757 on to pure_direct can be
      issued. Or any other commands?

* 2017-01-29 @sveinse

    * Add timestamps and counters on
        - nodes
        - commands
        - events
    * To be able handle server status aggregation, the `State()` object
      must support multiple callbacks

* 2017-01-28 @sveinse

    * Allow web to be a remote plugin. This implies making web into a node
      and the server must be able to send commands to the server. A `@` syntax?
    * The web node must be able to request the hostid of the server
    * Aggregate status of all connected nodes
    * Fix status styler on web

* 2017-01-27 @sveinse

    * Separate commands between actions and idempotent requests. This matters
      when using web API as the former uses POST and the latter cacheable
      GET.

* 2017-01-08 @sveinse

    * Rename `alias-list` in `responder.py` to something more descriptive?


COMPLETED OR DISCARDED
======================

* 2017-09-22 @sveinse

    * The serial protocols don't have any retry mechanisms with them. If the
      connection is lost, there is no mechanism for retrying to reopen the
      serial connection. If the connect fails, the plugin simply gives up.
      -- [OK 2017-09-23]

* 2017-09-17 @sveinse

    * Implement a DEPENDS feature in plugins to ensure they will only
      load if the dependecies are not met. Might require reordering of
      loading the packages. -- [OK 2017-09-17]

* 2017-02-07 @sveinse

    * Debian installer should use `conf/example.conf`, or perhaps
      `conf/default.conf` instead of `debian/lumina.default`.
      -- [OK 2017-02-10]
    * Fix setting package version in one location. -- [OK 2017-02-10]
    * Autogenerate `data_files` in `setup.py` from actual contents in `www/`
      -- [OK 2017-02-10]
    * Change `setup.py` to read `README.md` and convert it to the rst format
      -- [NO 2017-02-10]

* 2017-01-08 @sveinse

    * Add parser for event to support `telldus/event{14244686,0,15,turnoff} ->
      telldus/remote/15/off`
      -- [NO 2017-01-09, handled via telldus_config]
    * ..or to support parameters `telldus/event{14244686,0,15,turnoff}` in alias
      and responses -- [NO 2017-01-09]
    * Implement per-plugin logging -- [DONE 2017-01-27]
    * Implement `**kw` in `Events`? -- [DONE 2017-01-27]

* 2016-08-02 @sveinse

    * Add support for running lumina in-source via virtualenv, both local and
      remotes -- [OK 2017-01-08]
    * Add proper deployment of config to all remotes (`deploy/deploy-*`)
      -- [OK 2017-01-08]
    * Implement start-all in-source? -- [OK 2017-01-08]
    * Fixup logging for systemd based remotes -- [OK 2017-01-08]
    * Upgrade to newer raspbian on the remotes -- [OK 2017-01-08]
