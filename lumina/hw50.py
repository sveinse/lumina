# -*-python-*-
import os,sys

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort, EIGHTBITS, PARITY_EVEN, STOPBITS_ONE
from serial.serialutil import SerialException

from endpoint import Endpoint
from queue import Queue


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
FRAMESIZE=8
SOF=0xA9
EOF=0x9A

# REQUEST/RESPONSE TYPES
SET_RQ=0x00
GET_RQ=0x01
GET_RS = 0x02
ACK_RS = 0x03
TYPES = { SET_RQ: "SET.rq",
          GET_RQ: "GET.rq",
          GET_RS: "GET.rs",
          ACK_RS: "ACK.rs" }

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
RESPONSES = { ACK_OK: "OK",
              NAK_UNKNOWNCOMMAND: "Unknown command",
              NAK_SIZEERR: "Frame size error",
              NAK_SELECTERR: "Select error",
              NAK_RANGEOVER: "Range over error",
              NAK_NA: "Not applicable command",
              NAK_CHECKSUM: "Checksum error",
              NAK_FRAMINGERR: "Framing error",
              NAK_PARITYERR: "Parity error",
              NAK_OVERRUN: "Overrun error",
              NAK_OTHERERR: "Other error" }

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
IRCMD  = 0x1700
IRCMD2 = 0x1900
IRCMD3 = 0x1B00

IR_PWRON = IRCMD | 0x2E
IR_PWROFF = IRCMD | 0x2F

IR_MUTE = IRCMD | 0x24

IR_STATUSON = IRCMD | 0x25
IR_STATUSOFF = IRCMD | 0x26


# LIST OF ALL ITEMS
ITEMS = { STATUS_ERROR: "Status Error",
          STATUS_POWER: "Status Power",
          LAMP_TIMER: "Lamp Timer",
          STATUS_ERROR2: "Status Error(2)",
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




def dump(data):
    msg = bytearray(data)
    s=' '.join([ '%02x' %(x) for x in msg ])
    return "(%s) %s" %(len(data),s)

def dumptext(data):
    b = bytearray(data)

    item = b[1]<<8 | b[2]
    operation = b[3]
    data = b[4]<<8 | b[5]

    s1=TYPES.get(operation,'???')
    s2=''
    s3 = ITEMS.get(item,'???')
    if operation == GET_RQ:
        s2 = '%04x "%s"' %(item,s3)
    elif operation in (SET_RQ, GET_RS):
        s2 = '%04x "%s" = %04x' %(item,s3,data)
    elif operation == ACK_RS:
        s2 = RESPONSES.get(item,'???')
    return s1 + ' ' + s2



class FrameException(Exception):
    pass


class HW50Protocol(Protocol):

    timeout = 3

    def __init__(self,parent):
        self.parent = parent
        self.rxbuffer = bytearray()
        self.queue = Queue()


    def connectionMade(self):
        self.parent.event('hw50/connected')


    def connectionLost(self,reason):
        self.parent.event('hw50/disconnected',reason)


    def dataReceived(self, data):
        #msg = bytearray([0x01,0x02,0xa9,0x01,0x02,0x02,0x00,0x00,0x03,0x9a,0x03,0x04])
        msg = bytearray(data)
        log.msg("RAW  >>>  %s" %(dump(data)), system='HW50')
        self.rxbuffer += msg

        # Search for data frames in the incoming data buffer. Search for SOF and EOF markers.
        # It will only iterate if the buffer is large enough for a complete frame
        buffer = self.rxbuffer
        for x in range(0,len(buffer)-FRAMESIZE+1):

            # Search for SOF and EOF markers
            if buffer[x] == SOF and buffer[x+FRAMESIZE-1] == EOF:

                try:
                    # Decode the response-frame
                    frame = buffer[x:x+FRAMESIZE]
                    log.msg("     >>>  %s - %s" %(dump(frame),dumptext(frame)), system='HW50')
                    (item,operation,data) = self.decode(frame)

                except FrameException as e:

                    # Frame decode fails, do iteration
                    log.msg("Decode failure: %s" %(e), system='HW50')
                    continue

                # Consume all data up until the frame (including pre-junk) and save the data
                # after the frame for later processing
                self.rxbuffer = buffer[x+FRAMESIZE:]
                if x > 0 or len(self.rxbuffer) > 0:
                    log.msg("Discard junk in data, '%s' before, '%s' after" %(dump(buffer[:x]),dump(self.rxbuffer)),
                            system='HW50')

                # Process the frame here...
                if self.queue.active:
                    self.queue.response(data)
                    self.send_next()
                    return

                log.msg("-IGNORED-", system='HW50')
                return


    def decode(self, data):
        b = bytearray(data)

        if len(data) != FRAMESIZE:
            raise FrameException("Incomplete frame")
        if b[0] != SOF:
            raise FrameException("Wrong SOF field")
        if b[7] != EOF:
            raise FrameException("Wrong EOF field")

        c = 0
        for x in range(1,6):
            c |= b[x]
        if b[6] != c:
            raise FrameException("Checksum failure")

        item = b[1]<<8 | b[2]
        operation = b[3]
        data = b[4]<<8 | b[5]

        if operation == ACK_RS:
            if item not in RESPONSES:
                raise FrameException("Unknown ACK/NAK response error")
        elif operation == GET_RS:
            pass
        else:
            raise FrameException("Unknown response type")

        return (item, operation, data)


    def encode(self, item, operation, data):
        b = bytearray(b"\x00" * FRAMESIZE)

        b[0] = SOF
        b[1] = (item&0xFF00)>>8
        b[2] = (item&0xFF)
        b[3] = operation
        b[4] = (data&0xFF00)>>8
        b[5] = (data&0xFF)

        c = 0
        for x in range(1,6):
            c |= b[x]
        b[6] = c
        b[7] = EOF

        return b


    def command(self, item, operation=GET_RQ, data=0x0):
        msg = self.encode(item,operation,data)
        d = self.queue.add(data=msg)
        self.send_next()
        return d


    def send_next(self):
        if self.queue.get_next():

            # Send data
            msg = self.queue.active['data']
            log.msg("     <<<  %s - %s" %(dump(msg),dumptext(msg)), system='HW50')
            self.transport.write(str(msg))

            # Set timeout
            self.queue.set_timeout(self.timeout, self.timedout)


    def timedout(self):
        # The timeout response is to fail the request and proceed with the next command
        self.queue.fail(None)
        self.send_next()



class Hw50(Endpoint):

    # --- Interfaces
    def get_events(self):
        return [
            'hw50/starting',
            'hw50/stopping',
            'hw50/connected',
            'hw50/disconnected',
            'hw50/error',
        ]

    def get_actions(self):
        return {
            'hw50/status_power' : lambda a : self.protocol.command(STATUS_POWER),
            'hw50/lamp_timer'   : lambda a : self.protocol.command(LAMP_TIMER),
            'hw50/off'          : lambda a : self.protocol.command(IR_PWROFF,operation=SET_RQ),
            'hw50/on'           : lambda a : self.protocol.command(IR_PWRON,operation=SET_RQ),
        }


    # --- Initialization
    def __init__(self, port):
        self.port = port
        self.sp = None

    def setup(self):
        try:
            self.protocol = HW50Protocol(self)
            self.sp = SerialPort(self.protocol, self.port, reactor,
                                 baudrate=38400,
                                 bytesize=EIGHTBITS,
                                 parity=PARITY_EVEN,
                                 stopbits=STOPBITS_ONE,
                                 xonxoff=0,
                                 rtscts=0)
            log.msg('STARTING', system='HW50')
            self.event('hw50/starting')
        except SerialException as e:
            log.msg("Error %s" %(e.message), system='HW50')
            self.event('hw50/error',e.message)

    def close(self):
        if self.sp:
            self.sp.loseConnection()
        self.event('hw50/stopping')
