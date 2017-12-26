# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python.failure import Failure
from lumina.utils import str_object


DEBUG = False


class MessageEncoder(json.JSONEncoder):
    def default(self, obj):    # pylint: disable=E0202
        if isinstance(obj, Message):
            obj = obj.json_encoder()
        else:
            obj = super(MessageEncoder, self).default(obj)
        return obj


class Message(object):
    ''' Message object.
           message = Message(name,*args)

        Message name text syntax:
           'foo'
           'bar{1,2}'
           'nul{arg1=foo,arg2=bar}'
           'nul{arg1=foo,arg2=bar,5}'
    '''

    TYPE = 'message'

    def __init__(self, name=None, *args):
        # Message data
        self.name = name
        self.args = args

        # Message request and execution metas
        self.response = None  # Not None if response to a command
        self.result = None    # Command result

        # Message network requestid meta for transport
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
        if self.args is not None:
            alist += list(self.args)
        return "%s:%s{%s}" %(self.TYPE, self.name, str_object(alist, max_elements=5, brackets=False))


    def copy(self):
        ''' Return new copy of this object.  '''
        return type(self)(self.name, *self.args)


    #----- IMPORT and EXPORT functions ------

    def json_encoder(self, jdict=None):
        ''' JSON encoder for Message objects '''
        if not jdict:
            jdict = {}
        jdict.update({
            'type': self.TYPE,
            'name': self.name,
        })
        if self.args is not None:
            jdict.update({
                'args': self.args,
            })
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
            raise ValueError("Missing message name")

        self.args = other.get('args', tuple())

        self.requestid = other.get('requestid')

        self.response = other.get('response')
        self.result = other.get('result')

        return self


    # -- JSON import/export

    def dump_json(self):
        ''' Return a json representation of the instance data '''
        return json.dumps(self, cls=MessageEncoder)

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
                            "%s argument index error '$%s', but message has %s args" %(
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
        Message.__sequence += 1
        requestid = self.requestid = Message.__sequence
        return requestid

    # Unused it seems
    #def del_requestid(self):
    #    self.requestid = None


    #----- EXECUTION ------

    #def reset(self):
    #    self.response = None
    #    self.result = None


    def set_success(self, result):
        ''' Set message command to succeess '''
        self.response = True
        self.args = None
        if isinstance(result, Message):
            self.result = result.result
        else:
            self.result = result


    def set_fail(self, exc):
        ''' Set message command state to failed '''
        # If this is run in the scope of an errback, exc will be a Failure object which
        # contains the actual exception in exc.value
        if isinstance(exc, Failure):
            (failure, exc) = (exc, exc.value)
        self.response = False
        self.args = None
        self.result = (exc.__class__.__name__, str(exc.message))


    #----- DEFERRED ------

    #def get_defer(self):
    #    if self.defer:
    #        return self.defer
    #
    #    self.defer = Deferred()
    #    return self.defer


    #----- STATIC METHODS ------

    @staticmethod
    def load_json(string):
        ''' Create a new Message() object from a json string '''
        jdict = json.loads(string, encoding='ascii')

        msgtype = jdict.get('type')
        if msgtype is None:
            raise ValueError("Missing message type")

        for cls in MSGTYPES:
            if cls.TYPE == msgtype:
                return cls().load_dict(jdict)
        raise ValueError("Uknown message type '%s'" %(msgtype))


class MsgEvent(Message):
    ''' Event message '''
    TYPE = 'event'
    WANT_RESPONSE = False


class MsgCommand(Message):
    ''' Command message '''
    TYPE = 'command'
    WANT_RESPONSE = True


# List of all message types
MSGTYPES = (
    MsgEvent,
    MsgCommand
)
