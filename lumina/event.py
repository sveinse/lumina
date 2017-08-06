# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python.failure import Failure
from lumina.utils import str_object, listify_dict


DEBUG=False


class EventEncoder(json.JSONEncoder):
    def default(self, obj):    # pylint: disable=E0202
        if isinstance(obj, Event):
            obj = obj.json_encoder()
        else:
            obj = super(EventEncoder, self).default(obj)
        return obj


class Event(object):
    ''' Event object.
           event = Event(name,*args)

        Event name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''

    def __init__(self, name=None, *args):
        # Event data
        self.name = name
        self.args = args

        # Event request and execution metas
        self.response = None  # Set if response to a command
        self.result = None    # Command result

        # Event network requestid meta for transport
        self.requestid = None


    def __repr__(self):
        alist = []
        if DEBUG:
            alist.append('0x' + hex(id(self))[-6:])
        if self.response is not None:
            alist.append('=<%s,%s>' %(self.response, str_object(self.result, max_elements=5)))
        if DEBUG and self.requestid:
            alist.append('#%s' %(self.requestid))
        if DEBUG and hasattr(self, 'defer'):
            alist.append('d=%s' %(str(self.defer),))
        alist += list(self.args)
        return "%s{%s}" %(self.name, str_object(alist, max_elements=5, brackets=False))


    def copy(self):
        ''' Return new copy of this object.  '''
        return Event(self.name, *self.args)


    #----- IMPORT and EXPORT functions ------

    def json_encoder(self):
        ''' JSON encoder for Event objects '''
        jdict = {
            'name': self.name,
            'args': self.args,
        }
        if self.requestid is not None:
            jdict.update({
                'requestid': self.requestid,
            })
        if self.response is not None:
            jdict.update({
                'response': self.response,
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
        self.response = other.get('response')
        self.requestid = other.get('requestid')

        result = other.get('result')

        # FIXME: What does this do?
        #if isinstance(result, dict) and 'requestid' in result:
        #    result = Event().load_dict(result)

        self.result = result

        return self


    # -- JSON import/export

    def dump_json(self):
        ''' Return a json representation of the instance data '''
        return json.dumps(self, cls=EventEncoder)

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


    #----- REQUEST ID NUMBERS ------

    # Sequence number stored as class attribute
    __sequence = 0

    def gen_requestid(self):
        Event.__sequence += 1
        requestid = self.requestid = Event.__sequence
        return requestid

    # Unused it seems
    #def del_requestid(self):
    #    self.requestid = None


    #----- EXECUTION ------

    #def reset(self):
    #    self.response = None
    #    self.result = None


    def set_success(self, result):
        ''' Set event commant to succeed '''
        self.response = True
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
        self.response = False
        self.result = (exc.__class__.__name__, str(exc.message))


    #----- DEFERRED ------

    #def get_defer(self):
    #    if self.defer:
    #        return self.defer
    #
    #    self.defer = Deferred()
    #    return self.defer
