# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python.failure import Failure



class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Event):
            obj = obj._json_encoder()
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

    RE_LOAD_STR = re.compile(r'^([^{}]+)({(.*)})?$')


    def __init__(self, name=None, *args):
        # Event data
        self.name = name
        self.args = args[:]

        # Event execution metas
        self.success = None  # Callback successful. True or False execution has occurred
        self.result = None   # Callback command result

        # Event network seq metas
        self.seq = None       # Network sequence number for transport


    def __repr__(self):
        t = ''
        if len(self.args) < 5:
            s = [str(a) for a in self.args]
        else:
            s = ['...%s args...' %(len(self.args))]
        if self.success is not None:
            s.append('<%s,%s>' %(self.success, self.result))
        # Uncomment this to print the id of the object
        #s.append(' ' + hex(id(self)))
        #if s:
        t = '{' + ','.join(s) + '}'
        return "%s%s" %(self.name, t)


    def copy(self):
        ''' Return new copy of this object.  '''
        other = Event()
        other.name = self.name
        other.args = self.args[:]
        return other


    #----- IMPORT and EXPORT functions ------

    def _json_encoder(self):
        ''' Internal JSON encoder '''
        js = {
            'name': self.name,
            'args': self.args,
        }
        if self.seq is not None:
            js.update({
                'seq': self.seq,
            })
        if self.success is not None:
            js.update({
                'success': self.success,
                'result': self.result,
            })
        return js


    # -- dict import/export

    def load_dict(self, other):
        ''' Load the data from a dict '''
        self.name = other.get('name')
        if self.name is None:
            raise ValueError("Missing event name")
        self.name = other.get('name')
        self.args = other.get('args', [])
        self.success = other.get('success')
        self.seq = other.get('seq')

        result = other.get('result')

        # FIXME: What does this do?
        if isinstance(result, dict) and 'seq' in result:
            result = Event().load_dict(result)

        self.result = result

        return self


    # -- JSON import/export

    def dump_json(self):
        ''' Return a json representation of the instance data '''
        return json.dumps(self, cls=MyEncoder)

    def load_json(self, string):
        ''' Load the data from a json string '''
        js = json.loads(string, encoding='ascii')
        self.load_dict(js)
        return self

    def load_json_args(self, string):
        ''' Load args from a json string '''
        if string:
            self.args = json.loads(string, encoding='ascii')
        else:
            self.args = []
        return self


    # -- String import/export

    # Unused it seems
    def dump_str(self):
        ''' Dump the data a string '''
        (s, t) = ([str(a) for a in self.args], '')
        if s:
            t = '{' + ','.join(s) + '}'
        return "%s%s" %(self.name, t)


    def load_str(self, string, parseEvent=None, shell=False):
        ''' Load the data from a string '''
        string = string.encode('ascii')

        # Support shell-like command parsing
        if shell:
            args = shlex.split(string)
            if not len(args):
                return self
            self.name = args[0]
            self.args = args[1:]
            return self

        m = self.RE_LOAD_STR.match(string)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(string))
        self.name = m.group(1)
        opts = m.group(3)
        if opts:
            self.args = opts.split(',')
        else:
            self.args = []

        # If '$' agruments is encountered, replace with positional argument
        # from parseEvent
        if parseEvent and opts:
            args = []
            for arg in self.args:
                if arg == '$*':
                    args += parseEvent.args
                elif arg == '$n':
                    args.append(parseEvent.name)
                elif arg.startswith('$'):
                    index = arg[1:]
                    opt = arg
                    try:
                        opt = parseEvent.args[int(index)-1]
                    except IndexError:
                        raise IndexError(
                            "%s argument index error '$%s', but event/request has %s args" %(
                                self.name, index, len(parseEvent.args)))
                    except ValueError:
                        raise ValueError(
                            "%s argument value error '$%s'" %(
                                self.name, index))
                    args.append(opt)
                else:
                    args.append(arg)
            self.args = args

        return self


    #----- SEQUENCE NUMBERS ------

    # Sequence number stored as class attribute
    __seq = 0

    def gen_seq(self):
        Event.__seq += 1
        seq = self.seq = Event.__seq
        return seq

    # Unused it seems
    #def del_seq(self):
    #    self.seq = None


    #----- EXECUTION ------

    #def reset(self):
    #    self.success = None
    #    self.result = None


    def set_success(self, result):
        ''' Set event commant to succeed '''
        self.success = True
        if isinstance(result, Event):
            self.result = result.result
        else:
            self.result = result


    def set_fail(self, exc):
        ''' Set event command state to fail '''
        # If this is run in the scope of an errback, exc will be a Failure object which
        # contains the actual exception in exc.value
        if isinstance(exc, Failure):
            (failure, exc) = (exc, exc.value)
        self.success = False
        self.result = (exc.__class__.__name__, str(exc.message))


    #----- DEFERRED ------

    #def get_defer(self):
    #    if self.defer:
    #        return self.defer
    #
    #    self.defer = Deferred()
    #    return self.defer
