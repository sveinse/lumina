#!/usr/bin/python

import sys,os
import serial
import time

port = '/dev/ttyUSB0'


# HW50 Protocol
# 38500, 8 bits, even parity, one stop bit
# 8 byte packets
#     B0: SOF 0xA9
#     B1: COMMAND / RESPONSE
#     B2: COMMAND / RESPONSE
#     B3: OPERATION
#     B4: DATA
#     B5: DATA
#     B6: CHECKSUM (OR of B1-B5)
#     B7: EOF 0x9A

FRAMESIZE=8

# FRAMING
SOF=0xA9
EOF=0x9A

# Operations
SET=0x00
GET=0x01
RESPONSE=0x02
ACKNAK=0x03

# RESPONSE TYPES
ACK_OK = 0x0000
NAK_UNKNOWNCOMMAND = 0x0101
NAK_SIZEERROR = 0x0104
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
              NAK_SIZEERROR: "Frame size error",
              NAK_SELECTERR: "Select error",
              NAK_RANGEOVER: "Range over error",
              NAK_NA: "Not applicable command",
              NAK_CHECKSUM: "Check sum error",
              NAK_FRAMINGERR: "Framing error",
              NAK_PARITYERR: "Parity error",
              NAK_OVERRUN: "Overrun error",
              NAK_OTHERERR: "Other error" }

# COMMANDS
CALIB_PRESET = 0x0002
CALIB_PRESET_CINEMA1 = 0x0000
CALIB_PRESET_CINEMA2 = 0x0001
CALIB_PRESET_REF = 0x0002
CALIB_PRESET_TV = 0x0003
CALIB_PRESET_PHOTO = 0x0004
CALIB_PRESET_GAME = 0x0005
CALIB_PRESET_BRTCINE = 0x0006
CALIB_PRESET_BRTTV = 0x0007
CALIB_PRESET_USER = 0x0008

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
ASPECT = 0x0020
OVERSCAN = 0x0023
SCREEN_AREAD = 0x0024
INPUT = 0x0001
MUTE = 0x0030

STATUS_ERROR = 0x0101
STATUS_ERROR_OK = 0x0000
STATUS_ERROR_LAMP = 0x0001
STATUS_ERROR_FAN = 0x0002
STATUS_ERROR_COVER = 0x0004
STATUS_ERROR_TEMP = 0x0008
STATUS_ERROR_D5V = 0x0010
STATUS_ERROR_POWER = 0x0020
STATUS_ERROR_TEMP = 0x0040
STATUS_ERROR_NVM = 0x0080

STATUS_POWER = 0x0102
STATUS_POWER_STANDBY = 0x0000
STATUS_POWER_STARTUP = 0x0001
STATUS_POWER_STARTUPLAMP = 0x0002
STATUS_POWER_POWERON = 0x0003
STATUS_POWER_COOLING1 = 0x0004
STATUS_POWER_COOLING2 = 0x0005
STATUS_POWER_SAVINGCOOLING1 = 0x0006
STATUS_POWER_SAVINGCOOLING2 = 0x0007
STATUS_POWER_SAVINGSTANDBY = 0x0008

STATUS_ERROR2 = 0x0125
STATUS_ERROR2_OK = 0x0000
STATUS_ERROR2_HIGHLAND = 0x0020

LAMP_TIMER = 0x0113

IRCMD    = 0x1700
IRCMD_E  = 0x1900
IRCMD_EE = 0x1B00

IR_PWRON = IRCMD | 0x2E
IR_PWROFF = IRCMD | 0x2F

IR_MUTE = IRCMD | 0x24

IR_STATUSON = IRCMD | 0x25
IR_STATUSOFF = IRCMD | 0x26



class NAKException(Exception):
    pass


def encode(command, operation=GET, data=0x0):

    b = bytearray(b"\x00" * FRAMESIZE)
    print b

    # B0 - SOF
    b[0] = SOF

    b[1] = (command&0xFF00)>>8
    b[2] = (command&0xFF)

    b[3] = operation

    b[4] = (data&0xFF00)>>8
    b[5] = (data&0xFF)

    c = 0
    for x in range(1,6):
        c |= b[x]
    b[6] = c

    # B7 - EOF
    b[7] = EOF

    print '<<<  [',
    for x in b:
        print "%02x" %(x),
    print ']'

    return b


def decode(data):

    b = bytearray(data)
    print '>>>  [',
    for x in b:
        print "%02x" %(x),
    print ']'

    if not data:
        return

    if len(data) != FRAMESIZE:
        raise Exception("Incomplete frame")
    if b[0] != SOF:
        raise Exception("Wrong SOF field")
    if b[7] != EOF:
        raise Exception("Wrong EOF field")

    c = 0
    for x in range(1,6):
        c |= b[x]
    if b[6] != c:
        raise Exception("Checksum failure")

    response = b[1]<<8 | b[2]
    operation = b[3]
    data = b[4]<<8 | b[5]

    if operation == ACKNAK:
        print '     ACKNAK: %04x' %(response)
        if response not in RESPONSES:
            raise Exception("Unknown ACK/NAK response error")
        if response != ACK_OK:
            raise NAKException("Command NAK-ed '%s'" %(RESPONSES[response]))

    elif operation == RESPONSE:
        print '     RESPONSE: %04x = %04x' %(response, data)

    else:
        raise Exception("Unknown response operation/type")

    return (response, operation, data)



def send(command, operation=GET, data=0x0, expect_response=True):
    tx = encode(command, operation, data)
    ser.write(tx)
    if not expect_response:
        return (None, None, None)
    rx = ser.read(FRAMESIZE)
    if rx:
        return decode(rx)
    return (None, None, None)


# Composite operations
def getcmd(command, expect_response=True):

    (response, operation, data) = send(command, GET, 0, expect_response=expect_response)

    if operation and operation != RESPONSE:
        raise Exception("Unexpected response type");
    if response and response != command:
        raise Exception("Unexpected response command");

    return data


def setcmd(command, data=0, expect_response=True):

    (response, operation, rdata) = send(command, SET, data, expect_response=expect_response)

    if operation and operation != ACKNAK:
        raise Exception("Unexpected response type");


# High level commands
def poweron():
    setcmd(IR_PWRON, expect_response=False)
    time.sleep(0.1)
    setcmd(IR_PWRON, expect_response=False)

def poweroff():
    setcmd(IR_PWROFF, expect_response=False)

def mute():
    setcmd(IR_MUTE, expect_response=False)

def statuson():
    setcmd(IR_STATUSON, expect_response=False)

def statusoff():
    setcmd(IR_STATUSOFF, expect_response=False)

def status_power():
    return getcmd(STATUS_POWER)

def get_lamp_timer():
    return getcmd(LAMP_TIMER)

def get_preset():
    return getcmd(CALIB_PRESET)

def set_preset(preset):
    setcmd(CALIB_PRESET, preset)

def ison():
    try:
        getcmd(STATUS_POWER, expect_response=False)
        time.sleep(0.1)
        getcmd(STATUS_POWER, expect_response=True)
        print "Unit is on"
        return True
    except NAKException:
        print "Unit is off"
        return False

def full_info():
    print 'Input:', getcmd(INPUT)
    #print 'Preset:', getcmd(CALIB_PRESET)
    print 'Status Power:', getcmd(STATUS_POWER)
    print 'Status Error:', getcmd(STATUS_ERROR)
    print 'Lamp Timer:', getcmd(LAMP_TIMER)


ser = None

def open():
    global ser
    if not ser:
        ser = serial.Serial('/dev/ttyUSB0', baudrate=38400, bytesize=serial.EIGHTBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=3 )

def close():
    global ser
    if ser:
        ser.close()

#full_info()
#ser.close()



# TODO:
#  - Handle 0.1s between commands
#  - Better NAK handling with exceptions
#  - Make sure rx is drained even if reply is unexpected.
#    E.g. using status_power() might respond depending on state of projector
#  - Handle out-of sync issues, perhaps drain rx buffer on TX

