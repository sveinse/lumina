# -*- python -*-
import re
import json
from twisted.python import log


class Event(object):
    ''' Event object.
           event = Event(name,*args,**kw)

        Event name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''
    def __init__(self, name=None, *args, **kw):
        self.name = name
        self.args = args[:]
        self.kw = kw.copy()


    def copy(self):
        return Event(self.name,*self.args,**self.kw)


    def __repr__(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' {' + ','.join(s) + '}'
        return "<EV:%s%s>" %(self.name,t)


    def dump_json(self):
        js = {
            'name': self.name,
            'args': self.args,
            'kw': self.kw,
        }
        return json.dumps(js)


    def parse_json(self, s):
        js = json.loads(s,encoding='ascii')
        self.name = js.get('name')
        self.args = js.get('args')
        self.kw = js.get('kw')
        return self


    def dump_str(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def parse_str(self, s):
        m = re.match(r'^([^{}]+)({(.*)})?$', s)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(s))
        self.name = m.group(1)
        opts = m.group(3)
        if opts:
            self.args = []
            self.kw = {}
            for arg in opts.split(','):
                if '=' in arg:
                    k = arg.split('=')
                    self.kw[k[0]] = k[1]
                else:
                    self.args.append(arg)
        return self
