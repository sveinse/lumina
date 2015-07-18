# -*- python -*-
import re

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


    def __repr__(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t=' {' + ','.join(s) + '}'
        return "<EV:%s%s>" %(self.name,t)


    def dump(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def parse(self, name, *args, **kw):
        m = re.match(r'^([^{}]+)({(.*)})?$', name)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(name))
        self.name = m.group(1)
        self.args = []
        self.kw = {}
        opts = m.group(3)
        if opts:
            for arg in opts.split(','):
                if '=' in arg:
                    k = arg.split('=')
                    self.kw[k[0]] = k[1]
                else:
                    self.args.append(arg)
        # Update optional variable arguments from constructor. Append the args, and update
        # the kw args. This will override any colliding kw options that might have been present
        # in the text string.
        self.args += args
        self.kw.update(kw)
        return self
