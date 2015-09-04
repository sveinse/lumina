# -*- python -*-
import os,sys


class ConfigException(Exception):
    pass



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



class Config(object):

    def __init__(self, defaults=None):
        self.conf = {}
        if defaults is not None:
            self.conf.update(defaults)


    def __getitem__(self,*a):
        return self.conf.__getitem__(*a)
    def get(self,*a):
        return self.conf.get(*a)


    def parsefile(self, filename, all=False, raw=False):
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



    def readconfig(self, conffile):
        conf = {}

        # Process each line. The generator returns
        for (n,l,k,v) in self.parsefile(conffile):
            if k in conf:
                raise ConfigException("%s:%s: Config entry already used. '%s'" %(conffile,n,l))
            conf[k] = v

        # Update class dict
        self.conf.update(conf)

        # Split certain keys on SPACE
        for k,d in self.conf.items():
            if k in ( 'services', 'modules', 'plugins' ):
                self.conf[k] = tuple(d.split())



    def writeconfig(self, conffile):

        auto_sep = "# Automatically added by Lumina"

        conf = self.conf.copy()
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
                    line = line.replace(v,confvalue(conf[k]))
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
                outlines.append("%s = %s\n" %(k.upper(),confvalue(v)))

        # And then finally writeout the config
        with open(conffile,'w') as f:
            for line in outlines:
                f.write(line)
