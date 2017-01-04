# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python import log

from .exceptions import *
from .log import *


# Global unique sequence number
seq = 0


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,Event):
            obj = obj.to_json()
        else:
            obj = super(MyEncoder, self).default(obj)
        return obj


class Event(object):

    ''' Event object.
           event = Event(name,*args,**kw)

        Event name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''
    def __init__(self, name=None, *args):
        # Event data
        self.name = name
        self.args = args[:]

        # Event execution metas
        self.fn = None       # Callback function
        self.success = None  # Callback successful. True or False execution has occurred
        self.result = None   # Callback command result

        # Event network seq metas
        self.seq = None       # Network sequence number for transport


    def __repr__(self):
        t=''
        if len(self.args) < 5:
            s = [str(a) for a in self.args]
        else:
            s = [ '...%s args...' %(len(self.args)) ]
        if self.success is not None:
            s.append('<%s,%s>' %(self.success,self.result))
        # Uncomment this to print the id of the object
        #s.append(' ' + hex(id(self)))
        #if s:
        t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def copy(self):
        ''' Return new copy of this object.  '''
        o = Event()
        o.name = self.name
        o.args = self.args[:]
        return o


    def gen_seq(self):
        # Set the sequence seq
        global seq
        seq = self.seq = seq+1
    def del_seq(self):
        log("Cleanup")
        self.seq = None


    def to_json(self):
        js = {
            'name': self.name,
            'args': self.args,
        }
        if self.seq is not None:
            js.update( {
                'seq': self.seq,
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
        self.success = d.get('success')
        self.seq = d.get('seq')

        result = d.get('result')
        if isinstance(result,dict) and 'seq' in result:
            result = Event().load_dict(result)
        self.result = result

        return self


    def load_json(self, s):
        js = json.loads(s,encoding='ascii')
        self.load_dict(js)
        return self


    def load_json_args(self, s):
        if len(s):
            self.args = json.loads(s,encoding='ascii')
        else:
            self.args = []
        return self


    def dump_str(self):
        (s,t) = ([str(a) for a in self.args],'')
        if s:
            t='{' + ','.join(s) + '}'
        return "%s%s" %(self.name,t)


    def load_str(self, s, parseEvent=None, shell=False):
        s=s.encode('ascii')

        # Support shell-like command parsing
        if shell:
            l = shlex.split(s)
            if not len(l):
                return self
            self.name = l[0]
            self.args = l[1:]
            return self

        m = re.match(r'^([^{}]+)({(.*)})?$', s)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(s))
        self.name = m.group(1)
        opts = m.group(3)
        if opts:
            self.args = opts.split(',')

            # If '$' agruments is encountered, replace with positional argument
            # from parseEvent
            if parseEvent:
                args = []
                for a in self.args:
                    if a == '$*':
                        args += parseEvent.args
                    elif a == '$n':
                        args.append(parseEvent.name)
                    elif a.startswith('$'):
                        index = a[1:]
                        o = a
                        try:
                            o = parseEvent.args[int(index)-1]
                        except IndexError:
                            raise IndexError("%s argument index error '$%s', but event/request has %s args" %(
                                self.name, index, len(parseEvent.args)) )
                        except ValueError:
                            raise ValueError("%s argument value error '$%s'" %(
                                self.name, index) )
                        args.append(o)
                    else:
                        args.append(a)
                self.args = args

        else:
            self.args = []
        return self


    #----- HELPER METHODS ------

    def set_fail(self,exc):
        ''' Set event command state to fail '''
        self.success = False
        self.result = (exc.__class__.__name__,str(exc.message))
