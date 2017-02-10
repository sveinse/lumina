TODO
====

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

    * Implement a DEPENDS feature in plugins to ensure they will only
      load if the dependecies are not met. Might require reordering of
      loading the packages.
    * Separate commands between actions and idempotent requests. This matters
      when using web API as the former uses POST and the latter cacheable
      GET.

* 2017-01-08 @sveinse

    * Rename `alias-list` in `responder.py` to something more descriptive?


COMPLETED OR DISCARDED
======================

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
