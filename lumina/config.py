# -*- python -*-
""" Configuration module """
from __future__ import absolute_import

import re
import json

from lumina.log import Logger
from lumina.exceptions import ConfigException


LOG = Logger(namespace='config')



def verify_type(key, obj, otype):
    ''' Verify that obj is of type otype. Fail with ValueError()
    '''

    # None indicates that we don't check type
    if otype is None:
        return

    tobj = type(obj)

    equivalents = (
        (unicode, str),
        (str, unicode),
        (tuple, list),
        (list, tuple),
    )
    if tobj is not otype:
        comps = [tobj is a and otype is b for a, b in equivalents]
        if any(comps):
            return
        else:
            raise ConfigException("Config '%s' is type '%s', expecting '%s'" %(
                key, tobj.__name__, otype.__name__))



class Config(object):
    ''' Lumina configuration object '''


    def __init__(self):
        self.config = {}


    def update_v(self, k):
        ''' Update the key value
        '''
        e = self.config[k]
        if 'value' in e:
            v = e['value']
        elif 'config' in e:
            v = e['config']
        elif 'default' in e:
            v = e['default']
        else:
            raise KeyError(k)
        self.config[k]['v'] = v
        return v


    def add_templates(self, templates, name=None):
        ''' Register new configuration templates to the config class
        '''

        LOG.info("Adding {n} config templates", n=len(templates))
        for (k, template) in templates.items():
            if name:
                k = name + '.' + k

            e = self.config.get(k, {})
            e.update(template)
            self.config[k] = e

            v = self.update_v(k)
            verify_type(k, v, e.get('type'))


    def readconfig(self, filename):
        ''' Read configuration file entries from 'filename'
        '''

        with open(filename, 'r') as f:
            data = f.read(1024000)

        # Remove any comments
        data = re.sub(r'(?m)//.*$', '', data)

        try:
            jso = json.loads(data, encoding='utf-8')
        except (SyntaxError, ValueError) as e:
            raise ConfigException("%s: Failed to load config file. %s" %(filename, str(e)))

        if not isinstance(jso, dict):
            raise ConfigException("%s: Config is not a dict." %(filename, ))

        for (k, v) in jso.items():

            e = self.config.get(k, {}).copy()
            e['config'] = v

            verify_type(k, v, e.get('type'))
            self.config[k] = e
            self.update_v(k)


    def __setitem__(self, k, v):
        ''' Set a config value '''

        e = self.config.get(k, {}).copy()
        e['value'] = v

        verify_type(k, v, e.get('type'))
        self.config[k] = e
        self.update_v(k)


    def __getitem__(self, k):
        ''' Return the config value of 'k' '''
        return self.config[k]['v']


    def get(self, k, name=None):
        ''' Return the config value of 'name.k' '''

        if name:
            return self[name + '.' + k]
        else:
            return self[k]


    #def keys(self):
    #    ''' Return the config keys '''
    #    return self.config.keys()


    #def getdict(self, k):
    #    return self.config[k].copy()


    def items(self):
        ''' Get all config items retured as a dict '''
        return self.config.items()


    def __len__(self):
        ''' Return the number of configuration items '''
        return len(self.config)
