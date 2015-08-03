# -*- python -*-
import re
import json
#import json_mod
from twisted.python import log

id = 0

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
        self.fn = None
        self.success = None
        self.result = None
        global id
        id = self.id = id+1


    def copy(self):
        return Event(self.name,*self.args,**self.kw)


    def __repr__(self):
        t=''
        if len(self.args) < 5:
            s = [str(a) for a in self.args]
        else:
            s = [ '...%s args...' %(len(self.args)) ]
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if self.success is not None:
            s.append('=%s: %s' %(self.success,self.result))
        if s:
            t='{' + ','.join(s) + '}'
        return "%s.%s%s" %(self.name,self.id,t)


    #def to_json(self):
    #    return "{'id': 12}"


    def dump_json(self):
        js = {
            'name': self.name,
            'args': self.args,
            'success': self.success,
            'id': self.id,
            'result': self.result,
            #'kw': self.kw,
        }
        return json.dumps(js)


    def parse_json(self, s):
        js = json.loads(s,encoding='ascii')
        self.name = js.get('name')
        self.args = js.get('args',[])
        #self.kw = js.get('kw',{})
        self.success = js.get('success',None)
        self.id = js.get('id')
        self.result = js.get('result')
        if self.name is None:
            raise ValueError("Missing event name")
        return self


    def dump_str(self):
        (s,t) = ([str(a) for a in self.args],'')
        for (k,v) in self.kw.items():
            s.append("%s=%s" %(k,v))
        if s:
            t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def parse_str(self, s):
        s=s.encode('ascii')
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
