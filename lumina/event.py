# -*- python -*-
import re
import json
from twisted.python import log

from exceptions import *


id = 0

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,Event):
            obj = obj.to_json()
        else:
            obj = super(MyEncoder, self).default(obj)
        return obj


class Event(object):
    system = 'EVENT'

    ''' Event object.
           event = Event(name,*args,**kw)

        Event name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''
    #def __init__(self, name=None, *args, **kw):
    def __init__(self, name=None, *args):
        self.name = name
        self.args = args[:]
        #self.kw = kw.copy()
        self.fn = None
        self.success = None
        self.result = None
        self.id = None


    def __repr__(self):
        t=''
        if len(self.args) < 5:
            s = [str(a) for a in self.args]
        else:
            s = [ '...%s args...' %(len(self.args)) ]
        #for (k,v) in self.kw.items():
        #    s.append("%s=%s" %(k,v))
        if self.success is not None:
            s.append('=%s: %s' %(self.success,self.result))
        if s:
            t='{' + ','.join(s) + '}'
        #return "%s.%s%s" %(self.name,self.id,t)
        return "%s%s" %(self.name,t)


    def copy(self):
        #return Event(self.name,*self.args,**self.kw)
        o = Event()
        o.name = self.name
        o.args = self.args[:]
        return o


    def gen_id(self):
        # Set the sequence id
        global id
        id = self.id = id+1
    def del_id(self):
        self.id = None


    def to_json(self):
        js = {
            'name': self.name,
            'args': self.args,
            #'kw': self.kw,
        }
        if self.id is not None:
            js.update( {
                'id': self.id,
            } )
        if self.success is not None:
            js.update( {
                'success': self.success,
                'result': self.result,
            } )
        return js


    def dump_json(self):
        return json.dumps(self, cls=MyEncoder)


    def load_dict(self,d):
        self.name = d.get('name')
        if self.name is None:
            raise ValueError("Missing event name")
        self.name = d.get('name')
        self.args = d.get('args',[])
        #self.kw = d.get('kw',{})
        self.success = d.get('success')
        self.id = d.get('id')

        result = d.get('result')
        if isinstance(result,dict) and 'id' in result:
            result = Event().load_dict(result)
        self.result = result

        return self


    def load_json(self, s):
        js = json.loads(s,encoding='ascii')
        self.load_dict(js)
        return self


    def dump_str(self):
        (s,t) = ([str(a) for a in self.args],'')
        #for (k,v) in self.kw.items():
        #    s.append("%s=%s" %(k,v))
        if s:
            t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def load_str(self, s):
        s=s.encode('ascii')
        m = re.match(r'^([^{}]+)({(.*)})?$', s)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(s))
        self.name = m.group(1)
        opts = m.group(3)
        if opts:
            #self.args = []
            #self.kw = {}
            #for arg in opts.split(','):
            #    if '=' in arg:
            #        k = arg.split('=')
            #        self.kw[k[0]] = k[1]
            #    else:
            #        self.args.append(arg)
            self.args = opts.split(',')
        return self


    def cmd_ok(self,result):
        self.success = True
        self.result = result
        log.msg("    %s: %s" %(self.name,result), system=self.system)
        return self


    def cmd_error(self,failure):
        cls = failure.value.__class__.__name__
        text = str(failure.value)
        self.success = False
        self.result = (cls,text)
        log.msg("    %s FAILED: %s [%s]" %(self.name,text,cls), system=self.system)

        if not failure.check(CommandException):
            if not failure.check(UnknownCommandException):
                log.msg(failure.getTraceback(), system=self.system)
            return failure


    def cmd_except(self,exc):
        ''' Save the error into the command object '''
        cls = exc.__class__.__name__
        text = exc.message
        self.success = False
        self.result = (cls,text)
        log.msg("    %s FAILED: %s [%s]" %(self.name,text,cls), system=self.system)
        log.err(system=self.system)
