# -*- python -*-
from __future__ import absolute_import

import re
import json
import shlex
from twisted.python.failure import Failure
from lumina.utils import str_object


DEBUG = False
MAX_ELEMENTS = (5,5)
#MAX_ELEMENTS = (5,5,3)   # Useful in debug


class MessageEncoder(json.JSONEncoder):
    def default(self, obj):    # pylint: disable=E0202
        if isinstance(obj, Message):
            # Transform our message into a dict, which the JSON encoder can handle
            obj = obj.dump_dict()
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

    type = 'message'
    want_response = False

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
        tdict = {
            'message': 'm',
            'command': 'c',
            'event':   'e',
        }
        alist = []
        if DEBUG:
            alist.append('0x' + hex(id(self))[-6:])
        if self.response is not None:
            alist.append('=<%s,%s>' %(self.response,
                                      str_object(self.result, max_elements=MAX_ELEMENTS)))
        if DEBUG and self.requestid:
            alist.append('#%s' %(self.requestid))
        if DEBUG and hasattr(self, 'defer'):
            alist.append('d=%s' %(str(self.defer),))
        if self.args is not None:
            alist += list(self.args)
        return "%s:%s{%s}" %(tdict.get(self.type,'?'),
                             self.name,
                             str_object(alist,
                                        max_elements=MAX_ELEMENTS,
                                        brackets=False))


    def copy(self):
        ''' Return new copy of this object '''
        return type(self)(self.name, *self.args)


    def is_type(self, msgtype):
        ''' Return boolean if this object is of type msgtype '''
        return self.type == msgtype


    #----- REQUEST ID NUMBERS ------

    # Sequence number stored as class attribute
    __sequence = 0

    def get_requestid(self):
        Message.__sequence += 1
        requestid = self.requestid = Message.__sequence
        return requestid


    #----- EXECUTION ------

    def set_success(self, result):
        ''' Set message command to succeess '''
        self.response = True
        self.args = None
        if isinstance(result, Message):
            self.result = result.result
        else:
            self.result = result
        return self


    def set_fail(self, exc):
        ''' Set message command state to failed '''
        # If this is run in the scope of an errback, exc will be a Failure object which
        # contains the actual exception in exc.value
        if isinstance(exc, Failure):
            (failure, exc) = (exc, exc.value)  # pylint: disable=unused-variable
        self.response = False
        self.args = None
        self.result = (exc.__class__.__name__, str(exc.message))
        return self


    #----- IMPORT and EXPORT functions ------

    def load_json(self, other):
        ''' Load the instance data from json '''
        jdict = json.loads(other, encoding='ascii')
        return self.load_dict(jdict)


    def load_json_args(self, other):
        ''' Load args only from a json string '''
        if other:
            self.args = json.loads(other, encoding='ascii')
        else:
            self.args = tuple()
        return self


    def dump_json(self):
        ''' Return a json representation of the instance data '''
        return json.dumps(self, cls=MessageEncoder)


    def load_dict(self, other):
        ''' Load the instance data from a dict '''
        self.name = other.get('name')
        if self.name is None:
            raise ValueError("Missing message name")
        self.args = other.get('args', tuple())
        self.requestid = other.get('requestid')
        self.response = other.get('response')
        self.result = other.get('result')
        return self


    def dump_dict(self, other=None):
        ''' Dict encoder for Message objects '''
        if not other:
            other = {}
        other.update({
            'type': self.type,
            'name': self.name,
        })
        if self.args is not None:
            other.update({
                'args': self.args,
            })
        if self.requestid is not None:
            other.update({
                'requestid': self.requestid,
            })
        if self.response is not None:
            other.update({
                'response': self.response,
                'result': self.result,
            })
        return other


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


    #----- FACTORY METHODS ------

    @staticmethod
    def create(msgtype, *args, **kw):
        ''' Create a new Message() object '''

        for cls in Message.__subclasses__():
            if cls.type == msgtype:
                return cls(*args, **kw)
        raise ValueError("Uknown message type '%s'" %(msgtype))


    @staticmethod
    def create_from_json(other):
        ''' Create a new Message() object from a json string '''

        jdict = json.loads(other, encoding='ascii')
        msgtype = jdict.get('type')
        if msgtype is None:
            raise ValueError("Missing message type in json")

        return Message.create(msgtype).load_dict(jdict)



class MsgEvent(Message):
    ''' Event message '''
    type = 'event'
    want_response = False


class MsgCommand(Message):
    ''' Command message '''
    type = 'command'
    want_response = True
