# -*- python -*-
from __future__ import absolute_import

import os

from lumina.log import Logger
from lumina.exceptions import ConfigException


log = Logger(namespace='config')


class Config(object):

    def __init__(self, settings=None):
        self.c = {}
        self.fileconf = {}
        if settings is not None:
            self.register(settings)


    def register(self, settings, name=None):
        ''' Register new configuration settings to the config class '''
        for (k, v) in settings.items():
            if name:
                k = name + '.' + k
            e = self.c.get(k, {})
            e.update(v)
            self.c[k] = e
        self.merge_fileconf()


    def merge_fileconf(self):
        for (k, v) in self.fileconf.items():
            if k in self.c:
                self.c[k]['value'] = Config.parsevalue(v, self.c[k].get('type'))
                del self.fileconf[k]


    def __getitem__(self, k):
        if k in self.c:
            e = self.c[k]
            if 'value' in e:
                return e['value']
            if 'default' in e:
                return e['default']
        raise KeyError(k)


    def set(self, k, v):
        if k in self.c:
            self.c[k]['value'] = v
            return
        raise KeyError(k)


    def get(self, k, name=None):
        if name:
            return self[name + '.' + k]
        else:
            return self[k]


    def getall(self):
        c = {}
        for (k, e) in self.c.items():
            c[k] = e.copy()
        return c


    #def __repr__(self):
    #    s=[]
    #    for k,v in self.value.items():
    #        a = []
    #        a.append(str(k) + ':' + str(v))
    #        if k in self.default:
    #            a.append('D='+str(self.default[k]))
    #        if k in self.help:
    #            a.append(str(self.help[k]))
    #        t = ",".join(a)
    #        s.append('('+t+')')
    #    return ",".join(s)



    @staticmethod
    def parsefile(filename, all=False, raw=False):
        with open(filename, 'rU') as f:

            n = 0
            for l in f:
                n += 1
                line = l.strip()

                # Skip empty lines and comments
                if not len(line):
                    if all:
                        yield (n, l, None, None)
                    continue
                if line.startswith('#'):
                    if all:
                        yield (n, l, None, None)
                    continue

                # Split on =. Allow only one =
                li = line.split('=')
                if len(li) < 2:
                    raise ConfigException("%s:%s: Missing '='. '%s'" %(filename, n, l))
                if len(li) > 2:
                    raise ConfigException("%s:%s: Too many '='. '%s'" %(filename, n, l))

                # Remove leading and trailing whitespaces
                key = li[0].strip()
                data = li[1].strip()

                # Do not accept empty key names
                if not len(key):
                    raise ConfigException("%s:%s: Empty key. '%s'" %(filename, n, l))
                key = key.lower()

                # Remove trailing AND leading ". Fail if " is in string
                d2 = data
                if len(d2) > 1 and d2.startswith('"') and d2.endswith('"'):
                    d2 = d2[1:-1]
                if '"' in d2:
                    raise ConfigException("%s:%s: Invalid char in entry. '%s'" %(filename, n, l))

                # Remove the " unless raw mode
                if not raw:
                    data = d2

                # Send back lineno, line, key and data
                yield (n, l, key, data)


    @staticmethod
    def confvalue(v):
        if isinstance(v, list) or isinstance(v, tuple):
            v = " ".join(v)
        else:
            v = str(v)

        if '=' in v:
            raise ConfigException("'=' not valid in config values")
        if '"' in v:
            raise ConfigException("'\"' not valid in config values")

        if ' ' in v:
            v = '"' + v + '"'

        return v


    @staticmethod
    def parsevalue(v, typ=None):
        if typ is None:
            return v
        elif typ is list:
            return v.split()
        elif typ is tuple:
            return tuple(v.split())
        else:
            return typ(v)


    def readconfig(self, conffile):
        conf = {}

        # Process each line in config file
        for (n, l, k, v) in Config.parsefile(conffile):
            if k in conf:
                raise ConfigException("%s:%s: Config entry already used. '%s'" %(conffile, n, l))
            conf[k] = v

        n = len(conf)

        # Update class info and merge with main config memory
        self.fileconf.update(conf)
        self.merge_fileconf()

        log.info("Read %s configuration items from %s (%s unknown items)" %(
            n, conffile, len(self.fileconf)))


    def writeconfig(self, conffile):

        auto_sep = "# Automatically added by Lumina"

        outlines = []
        conf = {}
        for (k, e) in self.c.items():
            if 'value' in e:
                conf[k] = e['value']

        # If the configuration file exists, parse it and merge its contents
        if os.path.exists(conffile):

            # Process each line in existing configuration file
            for (n, l, k, v) in self.parsefile(conffile, all=True, raw=True):

                # If we see the separator in the, we dont add it later to avoid
                # overfilling the conffile with auto separators
                if auto_sep in l:
                    auto_sep = None

                # If a present key is found on the current line, replace its value with
                # the new configuration value
                if k in conf:
                    line = l
                    line = line.replace(v, Config.confvalue(conf[k]))
                    outlines.append(line)
                    del conf[k]

                # Else we leave the line as-is
                else:
                    outlines.append(l)

        # Any remaining configuration entries must be appended to the file
        if conf:

            # Print the separator unless it is already present in the file
            if auto_sep:
                outlines.append("\n" + auto_sep + "\n")

            # Append the next values
            for (k, v) in conf.items():
                outlines.append("%s = %s\n" %(k.upper(), Config.confvalue(v)))

        # And then finally writeout the config
        with open(conffile, 'w') as f:
            for line in outlines:
                f.write(line)
