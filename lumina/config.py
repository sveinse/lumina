# -*- python -*-
import os,sys


class ConfigException(Exception):
    pass



class Config(object):

    def __init__(self, settings=None):
        self.keys = set()
        self.value = {}
        self.default = {}
        self.help = {}
        if settings is not None:
            self.amend(settings)


    # Dict methods
    def __getitem__(self,k):
        if k in self.value:
            return self.value[k]
        if k in self.default:
            return self.default[k]
        raise KeyError(k)
    def get(self,*a):
        return self.value.get(*a)
    def set(self,k,v):
        if k not in self.keys:
            raise KeyError("Key '%s' not present" %(k))
        self.value[k]=v
    #def items(self,*a):
    #    return self.value.items(*a)

    # Special methods
    def getall(self):
        d = {}
        for k in self.keys:
            a = { 'key': k }
            if k in self.value:
                a['value'] = self.value[k]
            if k in self.default:
                a['default'] = self.default[k]
            if k in self.help:
                a['help'] = self.help[k]
            d[k]=a
        return d


    def __repr__(self):
        s=[]
        for k,v in self.value.items():
            a = []
            a.append(str(k) + ':' + str(v))
            if k in self.default:
                a.append('D='+str(self.default[k]))
            if k in self.help:
                a.append(str(self.help[k]))
            t = ",".join(a)
            s.append('('+t+')')
        return ",".join(s)


    def amend(self,settings):
        ''' Amend new configuration settings to the config class '''
        for (k,v) in settings.items():
            self.keys.add(k)
            if 'default' in v:
                self.default[k] = v['default']
            if 'help' in v:
                self.help[k] = v['help']
            if 'value' in v:
                self.value[k] = v['value']



    @staticmethod
    def parsefile(filename, all=False, raw=False):
        with open(filename, 'rU') as f:

            n=0
            for l in f:
                n+=1
                line = l.strip()

                # Skip empty lines and comments
                if not len(line):
                    if all:
                        yield (n,l,None,None)
                    continue
                if line.startswith('#'):
                    if all:
                        yield (n,l,None,None)
                    continue

                # Split on =. Allow only one =
                li = line.split('=')
                if len(li) < 2:
                    raise ConfigException("%s:%s: Missing '='. '%s'" %(filename,n,l))
                if len(li) > 2:
                    raise ConfigException("%s:%s: Too many '='. '%s'" %(filename,n,l))

                # Remove leading and trailing whitespaces
                key  = li[0].strip()
                data = li[1].strip()

                # Do not accept empty key names
                if not len(key):
                    raise ConfigException("%s:%s: Empty key. '%s'" %(filename,n,l))
                key = key.lower()

                # Remove trailing AND leading ". Fail if " is in string
                d2=data
                if len(d2)>1 and d2.startswith('"') and d2.endswith('"'):
                    d2=d2[1:-1]
                if '"' in d2:
                    raise ConfigException("%s:%s: Invalid char in entry. '%s'" %(filename,n,l))

                # Remove the " unless raw mode
                if not raw:
                    data=d2

                # Send back lineno, line, key and data
                yield (n,l,key,data)


    @staticmethod
    def confvalue(v):
        if isinstance(v,list) or isinstance(v,tuple):
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


    def readconfig(self, conffile):
        conf = {}

        # Process each line. The generator returns
        for (n,l,k,v) in Config.parsefile(conffile):
            if k in conf:
                raise ConfigException("%s:%s: Config entry already used. '%s'" %(conffile,n,l))
            conf[k] = v

        # Update class dict
        self.value.update(conf)

        # Split certain keys on SPACE
        for k,d in self.value.items():
            if k in ( 'services', 'modules', 'plugins' ):
                self.value[k] = tuple(d.split())



    def writeconfig(self, conffile):

        auto_sep = "# Automatically added by Lumina"

        conf = self.value.copy()
        outlines = [ ]

        # If the configuration file exists, parse it and merge its contents
        if os.path.exists(conffile):

            # Process each line in existing configuration file
            for (n,l,k,v) in self.parsefile(conffile,all=True,raw=True):

                # If we see the separator in the, we dont add it later to avoid
                # overfilling the conffile with auto separators
                if auto_sep in l:
                    auto_sep = None

                # If a present key is found on the current line, replace its value with
                # the new configuration value
                if k in conf:
                    line = l
                    line = line.replace(v,Config.confvalue(conf[k]))
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
            for (k,v) in conf.items():
                outlines.append("%s = %s\n" %(k.upper(),Config.confvalue(v)))

        # And then finally writeout the config
        with open(conffile,'w') as f:
            for line in outlines:
                f.write(line)
