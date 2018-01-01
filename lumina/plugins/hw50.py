# -*-python-*-
from __future__ import absolute_import

from Queue import Queue

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import EIGHTBITS, PARITY_EVEN, STOPBITS_ONE
from twisted.internet.task import LoopingCall

from lumina.node import Node
from lumina.exceptions import LuminaException, TimeoutException, CommandRunException
from lumina.serial import ReconnectingSerialPort


class FrameException(LuminaException):
    pass


# HW50 Protocol
# 38500, 8 bits, even parity, one stop bit
# 8 byte packets
#     B0: SOF 0xA9
#     B1: ITEM
#     B2: ITEM
#     B3: TYPE
#     B4: DATA
#     B5: DATA
#     B6: CHECKSUM (OR of B1-B5)
#     B7: EOF 0x9A


# FRAMING
FRAMESIZE = 8
SOF = 0xA9
EOF = 0x9A

# REQUEST/RESPONSE TYPES
SET_RQ = 0x00
GET_RQ = 0x01
GET_RS = 0x02
ACK_RS = 0x03
TYPES = {SET_RQ: "SET.rq",
         GET_RQ: "GET.rq",
         GET_RS: "GET.rs",
         ACK_RS: "ACK.rs",
        }

# RESPONSE TYPES
ACK_OK = 0x0000
NAK_UNKNOWNCOMMAND = 0x0101
NAK_SIZEERR = 0x0104
NAK_SELECTERR = 0x0105
NAK_RANGEOVER = 0x0106
NAK_NA = 0x010A
NAK_CHECKSUM = 0xF010
NAK_FRAMINGERR = 0xF020
NAK_PARITYERR = 0xF030
NAK_OVERRUN = 0xF040
NAK_OTHERERR = 0xF050
RESPONSES = {ACK_OK: "OK",
             NAK_UNKNOWNCOMMAND: "Unknown command",
             NAK_SIZEERR: "Frame size error",
             NAK_SELECTERR: "Select error",
             NAK_RANGEOVER: "Range over error",
             NAK_NA: "Not applicable command",
             NAK_CHECKSUM: "Checksum error",
             NAK_FRAMINGERR: "Framing error",
             NAK_PARITYERR: "Parity error",
             NAK_OVERRUN: "Overrun error",
             NAK_OTHERERR: "Other error"
            }

# ITEMS for picture
CALIB_PRESET = 0x0002
CONTRAST = 0x0010
BRIGHTNESS = 0x0011
COLOR = 0x0012
HUE = 0x0013
SHARPNESS = 0x0014
COLOR_TEMP = 0x0017
LAMP_CONTROL = 0x001A
CONTRAST_ENHANCER = 0x001C
ADVANCED_IRIS = 0x001D
REAL_COLOR_PROCESSING = 0x001E
FILM_MODE = 0x001F
GAMMA_CORRECTION = 0x0022
NR = 0x0025
COLOR_SPACE = 0x003B
USER_GAIN_R = 0x0050
USER_GAIN_G = 0x0051
USER_GAIN_B = 0x0052
USER_BIAS_R = 0x0053
USER_BIAS_G = 0x0054
USER_BIAS_B = 0x0055
IRIS_MANUAL = 0x0057
FILM_PROJECTION = 0x0058
MOTION_ENHANCER = 0x0059
XV_COLOR = 0x005A
REALITY_CREATION = 0x0067
RC_RESOLUTION = 0x0068
RC_NOISEFILTER = 0x0069
MPEG_NR = 0x006C

# ITEMS for screen
ASPECT = 0x0020
OVERSCAN = 0x0023
SCREEN_AREA = 0x0024

# ITEMS for setup
INPUT = 0x0001
MUTE = 0x0030
HDMI1_DYNRANGE = 0x006E
HDMI2_DYNRANGE = 0x006F
SETTINGS_LOCK = 0x0073

# ITEMS for 3D
DISPSEL_3D = 0x0060
FORMAT_3D = 0x0061
FORMAT_DEPTH = 0x0062
EFFECT_3D = 0x0063
GLASS_BRIGHTNESS = 0x0065

# ITEMS for status
STATUS_ERROR = 0x0101
STATUS_POWER = 0x0102
LAMP_TIMER = 0x0113
STATUS_ERROR2 = 0x0125

# ITEMS for IR
IRCMD = 0x1700
IRCMD2 = 0x1900
IRCMD3 = 0x1B00
IRCMD_MASK = 0xFF00

IR_PWRON = IRCMD | 0x2E
IR_PWROFF = IRCMD | 0x2F

IR_MUTE = IRCMD | 0x24

IR_STATUSON = IRCMD | 0x25
IR_STATUSOFF = IRCMD | 0x26


# LIST OF ALL ITEMS
ITEMS = {STATUS_ERROR: "Status Error",
         STATUS_POWER: "Status Power",
         LAMP_TIMER: "Lamp Timer",
         STATUS_ERROR2: "Status Error2",
         IR_PWROFF: "Power Off (IR)",
         IR_PWRON: "Power On (IR)",
         CALIB_PRESET: "Preset",
        }


# DATA FIELDS
CALIB_PRESET_CINEMA1 = 0x0000
CALIB_PRESET_CINEMA2 = 0x0001
CALIB_PRESET_REF = 0x0002
CALIB_PRESET_TV = 0x0003
CALIB_PRESET_PHOTO = 0x0004
CALIB_PRESET_GAME = 0x0005
CALIB_PRESET_BRTCINE = 0x0006
CALIB_PRESET_BRTTV = 0x0007
CALIB_PRESET_USER = 0x0008

STATUS_ERROR_OK = 0x0000
STATUS_ERROR_LAMP = 0x0001
STATUS_ERROR_FAN = 0x0002
STATUS_ERROR_COVER = 0x0004
STATUS_ERROR_TEMP = 0x0008
STATUS_ERROR_D5V = 0x0010
STATUS_ERROR_POWER = 0x0020
STATUS_ERROR_TEMP = 0x0040
STATUS_ERROR_NVM = 0x0080

STATUS_POWER_STANDBY = 0x0000
STATUS_POWER_STARTUP = 0x0001
STATUS_POWER_STARTUPLAMP = 0x0002
STATUS_POWER_POWERON = 0x0003
STATUS_POWER_COOLING1 = 0x0004
STATUS_POWER_COOLING2 = 0x0005
STATUS_POWER_SAVINGCOOLING1 = 0x0006
STATUS_POWER_SAVINGCOOLING2 = 0x0007
STATUS_POWER_SAVINGSTANDBY = 0x0008

STATUS_ERROR2_OK = 0x0000
STATUS_ERROR2_HIGHLAND = 0x0020



#def ison(result):
#    if result == STATUS_POWER_POWERON:
#        return True
#    else:
#        return False


def dump(data):
    ''' Return a printout string of data '''
    msg = bytearray(data)
    s = ' '.join(['%02x' %(x) for x in msg])
    return "(%s) %s" %(len(data), s)


def dumptext(data):
    ''' Return a HW50 frame printout as text '''
    b = bytearray(data)

    item = b[1]<<8 | b[2]
    cmd = b[3]
    data = b[4]<<8 | b[5]

    s1 = TYPES.get(cmd, '???')
    s2 = ''
    s3 = ITEMS.get(item, '???')
    if cmd == GET_RQ:
        s2 = '%04x "%s"' %(item, s3)
    elif cmd in (SET_RQ, GET_RS):
        s2 = '%04x "%s" = %04x' %(item, s3, data)
    elif cmd == ACK_RS:
        s2 = RESPONSES.get(item, '???')
    return s1 + ' ' + s2


def decode_hw50frame(frame):
    ''' Decode an input frame '''
    b = bytearray(frame)

    if len(frame) != FRAMESIZE:
        raise FrameException("Incomplete frame")
    if b[0] != SOF:
        raise FrameException("Wrong SOF field")
    if b[7] != EOF:
        raise FrameException("Wrong EOF field")

    c = 0
    for x in range(1, 6):
        c |= b[x]
    if b[6] != c:
        raise FrameException("Checksum failure")

    item = b[1]<<8 | b[2]
    cmd = b[3]
    data = b[4]<<8 | b[5]

    if cmd == ACK_RS:
        if item not in RESPONSES:
            raise FrameException("Unknown ACK/NAK response error")
    elif cmd == GET_RS:
        pass
    else:
        raise FrameException("Unknown response type")

    return (item, cmd, data)


def encode_hw50frame(item, cmd, data):
    ''' Return an encoded frame '''
    b = bytearray(b"\x00" * FRAMESIZE)

    b[0] = SOF
    b[1] = (item&0xFF00)>>8
    b[2] = (item&0xFF)
    b[3] = cmd
    b[4] = (data&0xFF00)>>8
    b[5] = (data&0xFF)

    c = 0
    for x in range(1, 6):
        c |= b[x]
    b[6] = c
    b[7] = EOF

    return b



class HW50Protocol(Protocol):
    timeout = 3
    keepalive_interval = 60

    def __init__(self, parent):
        self.parent = parent
        self.log = parent.log
        self.status = parent.status
        self.rxbuffer = bytearray()
        self.queue = Queue()
        self.lastmsg = None


    def connectionMade(self):
        self.log.info("Connected to HW50")
        self.status.set_YELLOW('Connected, waiting for data')
        self.lastmsg = None

        # Setup a regular keepalive heartbeat (this operation will also
        # set the state green when the response is given)
        self.heartbeat = LoopingCall(self.keepalive)
        self.heartbeat.start(self.keepalive_interval, True)


    def connectionLost(self, reason):  # pylint: disable=W0222
        self.log.info("Lost connection with HW50: {e}", e=reason.getErrorMessage())
        self.status.set_RED("Lost connection")
        if self.timer:
            self.timer.cancel()
            self.timer = None
        self.heartbeat.stop()
        self.parent.sp.connectionLost(reason)


    def dataReceived(self, data):
        self.log.debug('', rawin=data)
        msg = bytearray(data)
        self.rxbuffer += msg

        # Search for data frames in the incoming data buffer. Search for SOF and EOF markers.
        # It will only iterate if the buffer is large enough for a complete frame
        buf = self.rxbuffer
        for x in range(0, len(buf)-FRAMESIZE+1):

            # Search for SOF and EOF markers
            if buf[x] == SOF and buf[x+FRAMESIZE-1] == EOF:

                try:
                    # Decode the response-frame
                    frame = buf[x:x+FRAMESIZE]
                    self.log.debug("     >>>  {f} - {t}", f=dump(frame), t=dumptext(frame))
                    (item, cmd, data) = decode_hw50frame(frame)

                except FrameException as e:

                    # Frame decode fails, do iteration
                    self.log.info("Decode failure: {e}", e=e)
                    continue

                # Consume all data up until the frame (including pre-junk) and
                # save the data after the frame for later processing
                self.rxbuffer = buf[x+FRAMESIZE:]
                if x > 0 or len(self.rxbuffer) > 0:
                    self.log.info("Discarded junk in data, '{b}' before, '{a}' after",
                                  b=dump(buf[:x]), a=dump(self.rxbuffer))

                # From here on, consider this a valid frame
                self.status.set_GREEN()

                # Process the reply frame
                if self.lastmsg:

                    # Clean up
                    self.lastmsg = None
                    self.timer.cancel()
                    self.timer = None

                    # Treat either A) Unknown frame type commands or
                    #              B) ACK_RS types with non-ACK_OK responses
                    # as errors
                    if cmd not in TYPES or (cmd == ACK_RS and item != ACK_OK):
                        self.defer.errback(CommandRunException(RESPONSES.get(item, item)))
                    else:
                        self.defer.callback(data)

                    # Proceed to the next command
                    self.send_next()
                    return

                # Not interested in the received message
                self.log.info("-IGNORED-")


    def command(self, item, cmd=GET_RQ, data=0x0):

        # Compile next request
        msg = encode_hw50frame(item, cmd, data)

        defer = Deferred()
        self.queue.put((defer, msg, item))
        self.send_next()
        return defer


    def send_next(self):
        # Don't send if communication is pending
        if self.lastmsg:
            return

        while self.queue.qsize():
            (defer, msg, item) = self.queue.get(False)

            # Send the command
            self.log.debug("     <<<  {m} - {t}", m=dump(msg), t=dumptext(msg))
            self.transport.write(str(msg))

            # Prepare for reply where applicable
            ircmd = item & IRCMD_MASK

            # IR-commands does not reply, so they can be replied to immediately
            # and can proceed to next command
            if ircmd in (IRCMD, IRCMD2, IRCMD3):
                defer.callback(None)
                continue

            # Expect reply, setup timer and return
            self.lastmsg = msg
            self.defer = defer
            self.timer = reactor.callLater(self.timeout, self.timedout)
            return


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        self.log.info("Command {c} timed out", c=dumptext(self.lastmsg))
        self.status.set_RED('Timeout')
        self.timer = None
        self.lastmsg = None
        self.defer.errback(TimeoutException())
        self.send_next()


    def keepalive(self):
        defer = self.command(STATUS_POWER)
        defer.addBoth(lambda a: None)



class Hw50SerialPort(ReconnectingSerialPort):
    noisy = False
    maxDelay = 10
    factor = 1.6180339887498948

    #def connectionLost(self, reason):
    #    ReconnectingSerialPort.connectionLost(self, reason)

    def connectionFailed(self, reason):
        self.protocol.status.set_RED(reason.getErrorMessage())
        self.protocol.log.error('HW50 connect failed: {e}', e=reason.getErrorMessage())
        ReconnectingSerialPort.connectionFailed(self, reason)



class Hw50(Node):
    ''' Sony VPL-HW50 projector interface
    '''

    CONFIG = {
        'port': dict(default='/dev/ttyUSB0', help='HW50 serial port'),
    }


    # --- Initialization
    def __init__(self, master):  # pylint: disable=W0231
        self.sp = None


    # --- Interfaces
    def configure(self, master):

        self.events = [
        ]

        self.commands = {
            'off'          : lambda a : self.c(IR_PWROFF,cmd=SET_RQ),
            'on'           : lambda a : self.c(IR_PWRON,cmd=SET_RQ),

            'preset/film1' : lambda a : self.c(CALIB_PRESET,cmd=SET_RQ,data=CALIB_PRESET_CINEMA1),
            'preset/film2' : lambda a : self.c(CALIB_PRESET,cmd=SET_RQ,data=CALIB_PRESET_CINEMA2),
            'preset/tv'    : lambda a : self.c(CALIB_PRESET,cmd=SET_RQ,data=CALIB_PRESET_TV),
            
            #'raw'          : lambda a : self.c(int(a.args[0],16),int(a.args[1],16),int(a.args[2],16)),
            #'ison'         : lambda a : self.c(STATUS_POWER).addCallback(ison),
            #'status_error' : lambda a : self.c(STATUS_ERROR),
            #'status_power' : lambda a : self.c(STATUS_POWER),
            #'lamp_timer'   : lambda a : self.c(LAMP_TIMER),
            #'preset'       : lambda a : self.c(CALIB_PRESET),
        }


    # --- Initialization
    def setup(self, master):
        Node.setup(self, master)

        self.port = master.config.get('port', name=self.name)
        self.protocol = HW50Protocol(self)
        self.sp = Hw50SerialPort(self.protocol, self.port,
                                 baudrate=38400,
                                 bytesize=EIGHTBITS,
                                 parity=PARITY_EVEN,
                                 stopbits=STOPBITS_ONE,
                                 xonxoff=0,
                                 rtscts=0)
        self.sp.log = self.log
        self.sp.connect()


    def close(self):
        Node.close(self)
        self.sp.loseConnection()


    # --- Convenience
    def c(self, *args, **kw):
        return self.protocol.command(*args, **kw)



PLUGIN = Hw50
