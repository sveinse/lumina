# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python.failure import Failure
from lumina.utils import str_object, listify_dict



class MyEncoder(json.JSONEncoder):
    def default(self, obj):    # pylint: disable=E0202
        if isinstance(obj, Event):
            obj = obj.json_encoder()
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

    def __init__(self, name=None, *args, **kw):
        # Event data
        self.name = name
        self.args = args
        self.kw = kw

        # Event execution metas
        self.success = None  # Callback successful. True or False execution has occurred
        self.result = None   # Callback command result

        # Event network seq metas
        self.seq = None       # Network sequence number for transport


    def __repr__(self):
        alist = []
        if self.success is not None:
            alist.append('<%s,%s>' %(self.success, str_object(self.result, max_elements=5)))
        alist += list(self.args)
        alist += listify_dict(self.kw)
        # Uncomment this to print the id of the object
        #alist.insert(0,' ' + hex(id(self)))
        return "%s{%s}" %(self.name, str_object(alist, max_elements=5, brackets=False))


    def copy(self):
        ''' Return new copy of this object.  '''
        return Event(self.name, *self.args, **self.kw)


    #----- IMPORT and EXPORT functions ------

    def json_encoder(self):
        ''' Internal JSON encoder '''
        jdict = {
            'name': self.name,
            'args': self.args,
            'kw': self.kw,
        }
        if self.seq is not None:
            jdict.update({
                'seq': self.seq,
            })
        if self.success is not None:
            jdict.update({
                'success': self.success,
                'result': self.result,
            })
        return jdict


    # -- dict import/export

    def load_dict(self, other):
        ''' Load the data from a dict '''
        self.name = other.get('name')
        if self.name is None:
            raise ValueError("Missing event name")
        self.name = other.get('name')
        self.args = other.get('args', tuple())
        self.kw = other.get('kw', {})
        self.success = other.get('success')
        self.seq = other.get('seq')

        result = other.get('result')

        # FIXME: What does this do?
        #if isinstance(result, dict) and 'seq' in result:
        #    result = Event().load_dict(result)

        self.result = result

        return self


    # -- JSON import/export

    def dump_json(self):
        ''' Return a json representation of the instance data '''
        return json.dumps(self, cls=MyEncoder)

    def load_json(self, string):
        ''' Load the data from a json string '''
        jdict = json.loads(string, encoding='ascii')
        self.load_dict(jdict)
        return self

    def load_json_args(self, string):
        ''' Load args only from a json string '''
        if string:
            self.args = json.loads(string, encoding='ascii')
        else:
            self.args = tuple()
        return self


    # -- String import/export

    # Regex to load from string
    RE_LOAD_STR = re.compile(r'^([^{}]+)({(.*)})?$')


    def load_str(self, string, parse_event=None, shell=False):
        ''' Load the data from a string '''
        string = string.encode('ascii')

        # Support shell-like command parsing
        if shell:
            args = shlex.split(string)
            if not len(args):
                return self
            self.name = args[0]
            self.args = args[1:]
            self.kw = tuple()
            return self

        m = self.RE_LOAD_STR.match(string)
        if not m:
            raise SyntaxError("Invalid syntax '%s'" %(string))
        opts = m.group(3)
        args = []
        if opts:
            args = opts.split(',')

        self.name = m.group(1)
        self.args = tuple(args)
        self.kw = tuple()  # Load from string does not support kw yet

        # If '$' agruments is encountered, replace with positional argument
        # from parse_event
        if parse_event and opts:
            args = []
            for arg in self.args:
                if arg == '$*':
                    args += parse_event.args
                elif arg == '$n':
                    args.append(parse_event.name)
                elif arg.startswith('$'):
                    index = arg[1:]
                    opt = arg
                    try:
                        opt = parse_event.args[int(index)-1]
                    except IndexError:
                        raise IndexError(
                            "%s argument index error '$%s', but event/request has %s args" %(
                                self.name, index, len(parse_event.args)))
                    except ValueError:
                        raise ValueError(
                            "%s argument value error '$%s'" %(
                                self.name, index))
                    args.append(opt)
                else:
                    args.append(arg)
            self.args = tuple(args)

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
