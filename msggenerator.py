import time
from enum import Enum
import math
import copy

SerialCmdCode = {'addTone': 0xC0,
                 'enableTone': 0xC1,
                 'disableTone': 0xC2,
                 'reqconfig': 0xC3,

                 'sendmorsemsg': 0xD0,
                 'playmorsemsg': 0xD1,
                 'sendsidetone': 0xD2,
                 'sendfarnsworth': 0xD3,
                 'stopmorsemsg': 0xD4,

                 'receivetextchar': 0xF0,

                 'sendConfig': 0xA0,
                 'ping': 0xAA
                 }

class prosignTable:
    def __init__(self):
        self.prosign = ["AA", "AR", "AS", "BT", "CQ", "CT", "EE", "IMI", "KN", "SK", "SN", "SOS"]

    def getPro(self, idx):
        return self.Pro[idx]

class bitbash:
    def __init__(self):
        return

    def encode16(self, msg, idx, value):
        msg[idx] = self.usb16(value)
        msg[idx+1] = self.lsb16(value)

    def decode16(self, msg, idx):
        return (msg[idx] << 8) | msg[idx+1]

    def usw32(self, value):
        return (value & 0xFFFF0000) >> 16

    def lsw32(self, value):
        return (value & 0x0000FFFF)

    def encode32(self, msg, idx, value):
        lsw = self.lsw32(value)
        usw = self.usw32(value)
        msg[idx] = self.usb16(usw)
        msg[idx+1] = self.lsb16(usw)
        msg[idx+2] = self.usb16(lsw)
        msg[idx+3] = self.lsb16(lsw)

    def encode32Float(self, msg, idx, value):
        self.encode32(msg, idx, int(value*1000.0))

    def MsgToFloat32(self, msg, idx):
        fixed = (msg[idx] << 24) | (msg[idx+1] << 16) | (msg[idx+2] << 8) | msg[idx+3]
        return float(fixed)/1000.0

    def usb16(self, value):
        return (value & 0xFF00) >> 8

    def lsb16(self, value):
        return (value & 0x00FF)

    def getMsg(self):
        return self.msg

    def MsgToFloat16(self, msg, idx):
        fixed = msg[idx+1] | (msg[idx] << 8)
        return float(fixed)/10.0


    def initMsg(self, length):
        msg = [ord('C'), ord('Q'), length]
        for n in range(length-3):
            msg.append(0xEF)
        msg[2] = length
        return msg

    def dsplyMsg(self, msg):
        if isinstance(msg, list):
            print("[", end=" ")
            # C Q {Length}
            for n in range(3):
                print(f"0x{msg[n]:02X}", end=" ")
            print(end="  ")
            # {Command Code}
            print(f"0x{msg[3]:02X}", end="  < ")
            # Message Body
            for n in range(4, len(msg)-2):
                print(f"0x{msg[n]:02X}", end=" ")
            print(end=">  ")
            # Checksum
            for n in range(len(msg)-2, len(msg)):
                print(f"0x{msg[n]:02X}", end=" ")
            print("]", end=" {")
            for n in range(len(msg)):
                C = chr(msg[n])
                if C.isprintable():
                    print(C, end="")
                else:
                    print(".", end="")
            print("}")
        else:
            print("<", msg, ">", " is not a [list]. Try again.")

class CzeckSum(bitbash):
    def __init__(self, msg):
        Sum = 0
        Len = msg[2]
        for pos in range(Len-2):
            Sum += int(msg[pos])
        msg[Len-1] = self.lsb16(Sum)
        msg[Len-2] = self.usb16(Sum)

class addTone(CzeckSum, bitbash):
    def __init__(self):
        self.Length = 20
        self.msg = self.initMsg(self.Length)
        self.index = -1
        self.cmmdCode = SerialCmdCode.get('addTone')
        self.msg[3] = self.cmmdCode
        self.Freq = 0.0
        self.Phase = 0.0

    def __exit__(self):
        print("addTone Destructor")

    def encode(self, idx, ampl, freq, phase, waveformtype):
        self.index = idx
        self.Ampl = ampl
        self.Freq = freq
        self.Phase = phase
        self.waveformType = waveformtype

        self.msg[4] = self.index
        self.msg[5] = self.waveformType

        self.encode32Float(self.msg, 6, self.Ampl)
        self.encode32Float(self.msg, 10, self.Freq)
        self.encode32Float(self.msg, 14, self.Phase)

        CzeckSum(self.msg)

    def decode(self, msg):
        self.msg = msg
        self.Length = self.msg[2]
        self.cmmdCode = self.msg[3]
        self.index = self.msg[4]

        self.Ampl = self.MsgToFloat32(self.msg, 6)
        self.Freq = self.MsgToFloat32(self.msg, 10)
        self.Phase = self.MsgToFloat32(self.msg, 14)


    def getMsg(self):
        return self.msg

    def getFreq(self):
        return self.Freq

    def getPhase(self):
        return self.Phase

    def getIndex(self):
        return self.index

class enableTone(CzeckSum, bitbash):
    def __init__(self):
        self.Length = 7
        self.msg = self.initMsg(self.Length)
        self.index = -1
        self.cmmdCode = SerialCmdCode.get('enableTone')
        self.msg[3] = self.cmmdCode

    def encode(self, idx):
        self.index = idx
        self.msg[4] = self.index
        CzeckSum(self.msg)

    def decode(self, msg):
        self.msg = msg
        self.Length = self.msg[2]
        self.index = self.msg[4]
        self.cmmdCode = self.msg[3]

    def getMsg(self):
        return self.msg

    def getIndex(self):
        return self.index

class disableTone(CzeckSum, bitbash):
    def __init__(self):
        self.Length = 7
        self.msg = self.initMsg(self.Length)
        self.index = -1
        self.cmmdCode = SerialCmdCode.get('disableTone')
        self.msg[3] = self.cmmdCode

    def encode(self, idx):
        self.index = idx
        self.msg[4] = self.index
        CzeckSum(self.msg)

    def decode(self, msg):
        self.msg = msg
        self.Length = self.msg[2]
        self.index = self.msg[4]
        self.cmmdCode = self.msg[3]

    def getMsg(self):
        return self.msg

    def getIndex(self):
        return self.index

class toneUtil(bitbash):
    def __init__(self):
        return

class rcvMsg(addTone, enableTone, disableTone):

    def __new__(self, msg):
        cmmdCode = msg[3]
        if cmmdCode == SerialCmdCode.get('addTone'):
            x = addTone()
        elif cmmdCode == SerialCmdCode.get('enableTone'):
            x = enableTone()
        elif cmmdCode == SerialCmdCode.get('disableTone'):
            x = disableTone()
        else:
            return f"bad command code 0x{cmmdCode: 02X}"
        x.decode(msg)
        return x

class ReqConfig(CzeckSum, bitbash):
    def __init__(self):
        self.Length = 6
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('reqconfig')
        self.msg[3] = self.cmmdCode
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg

    class SendConfig(CzeckSum, bitbash):
        Phreq = {
        'Index'    : 0,
        'Waveform': 0,
        'Amplitude': 0.0,
        'Frequency': 0.0,
        'Phase'    : 0.0,
        'Defined'  : False,
        'Enabled'  : False
    }

    def __init__(self):
        self.Length = -1
        self.cmmdCode = -1
        self.NumTones = -1
        self.ToneListEntrySize = 16
        self.CmmnModeAmpl = -1.0
        self.ToneList = {}

    def encode(self):
        pass

    def decode(self, msg):
        self.msg = msg.copy()

        self.Length = self.msg[2]
        self.cmmdCode = self.msg[3]
        self.NumTones = self.msg[4]
        self.CmmnModeAmpl = self.MsgToFloat32(self.msg, 5)

        StartIdx = 9
        for F in range(self.NumTones):
            self.ToneList.update({F: self.DecodeToneListEntry(msg, StartIdx)})
            StartIdx += self.ToneListEntrySize


    def DecodeToneListEntry(self, msg, idx):
        self.Phreq['Index'] = msg[idx]
        self.Phreq['Waveform'] = msg[idx+1]
        self.Phreq['Amplitude'] = self.MsgToFloat32(msg, idx+2)
        self.Phreq['Frequency'] = self.MsgToFloat32(msg, idx+6)
        self.Phreq['Phase'] = self.MsgToFloat32(msg, idx+10)
        self.Phreq['Defined'] = msg[idx+14]
        self.Phreq['Enabled'] = msg[idx+15]
        return self.Phreq.copy()

    def getNumTones(self):
        return self.NumTones

    def getCmmnModeAmpl(self):
        return self.CmmnModeAmpl

    def getToneIndex(self, idx):
        return self.ToneList[idx]['Index']

    def getAmplitude(self, idx):
        return self.ToneList[idx]['Amplitude']

    def getWaveformType(self, idx):
        return self.ToneList[idx]['Waveform']

    def getWaveformTypeIndex(self, idx):
        Waveform = self.getWaveformType(idx)
        if Waveform == 0xF0:
            return 0
        elif Waveform == 0xF1:
            return 1
        elif Waveform == 0xF2:
            return 2
        elif Waveform == 0xF3:
            return 3
        else:
            return -1

        return self.ToneList[idx]['Waveform']

    def getFreq(self, idx):
        return self.ToneList[idx]['Frequency']

    def getPhase(self, idx):
        return self.ToneList[idx]['Phase']

    def getDefined(self, idx):
        return self.ToneList[idx]['Defined']

    def getEnabled(self, idx):
        return self.ToneList[idx]['Enabled']

class SendMorseMsg(CzeckSum, bitbash):
    def __init__(self, msgText):
        self.sizeMsg = len(msgText)
        if self.sizeMsg > 255:
            print("Message truncated to 255 characters. Sorry.")
            self.sizeMsg = 255
        self.textMsg = msgText[:255]
        self.Length = 7 + self.sizeMsg
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('sendmorsemsg')
        self.msg[3] = self.cmmdCode
        fillindex = 5
        for idx in range(self.sizeMsg):
            self.msg[fillindex] = ord(self.textMsg[idx])
            fillindex += 1
        self.msg[4] = self.sizeMsg
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg


class PlayMorseMsg(CzeckSum, bitbash):
    def __init__(self, WPM):
        self.Length = 7
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('playmorsemsg')
        self.msg[3] = self.cmmdCode
        self.WPM = WPM
        self.msg[4] = self.WPM
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg

class StopMorseMsg(CzeckSum, bitbash):
    def __init__(self):
        self.Length = 6
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('stopmorsemsg')
        self.msg[3] = self.cmmdCode
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg


class SendSideTone(CzeckSum, bitbash):
    def __init__(self, sidetone):
        self.Length = 10
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('sendsidetone')
        self.msg[3] = self.cmmdCode
        self.sideTone = sidetone
        self.encode32Float(self.msg, 4, self.sideTone)
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg


class SendFarnsworth(CzeckSum, bitbash):
    def __init__(self, enable):
        self.Length = 7
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('sendfarnsworth')
        self.msg[3] = self.cmmdCode
        if enable:
            self.enableFarnsworth = 1
        else:
           self.enableFarnsworth = 0
        self.msg[4] = self.enableFarnsworth
        CzeckSum(self.msg)

    def getMsg(self):
        return self.msg

class morseElementenum(Enum):
    morseDit = 101
    morseDah = 102
    morseMark = 103
    morseSpace = 104
    morseWordSpace = 105
    morseIdle = 106
    morseStuck = 666

class morseCharSeqEntry():
    def __init__(self, morseElement, Duration):
        self.morseElement = morseElement
        self.Duration = Duration

    def getMorseElement(self):
        return self.morseElement

    def getDuration(self):
        return self.Duration

class morseCharToken(morseCharSeqEntry):
    def __init__(self, Tdit, valid, prosign, farnsworth):
        self.Tdit = Tdit
        self.WPM = 0
        self.score = 5
        self.morseChar = 'x'
        self.morsePro = 0xFF
        self.valid = valid
        self.prosign = prosign
        self.lengthSeq = 0
        self.morseCharSeq = []
        self.farnsworth = farnsworth
        self.editTextIdxStart = 0
        self.editTextIdxEnd = 0
        self.wordspaceAfter = False
        self.idleAfter = False

    def getIdleAfter(self):
        return self.idleAfter

    def setIdleAfter(self, idle):
        self.idleAfter = idle

    def getSpaceAfter(self):
        return self.wordspaceAfter

    def setSpaceAfter(self, isSpace):
        self.wordspaceAfter = isSpace

    def isProsign(self):
        return self.prosign

    def getScore(self):
        return self.score

    def setScore(self, Score):
        self.score = Score

    def getWPM(self):
        return int(self.WPM+0.5)

    def setWPM(self, WPM):
        self.WPM = WPM

    def getTdit(self):
        return self.Tdit

    def getLengthSeq(self):
        return self.lengthSeq

    def setMorseChar(self, morseChar):
        self.morseChar = morseChar

    def getMorseChar(self):
        return self.morseChar

    def setMorsePro(self, morsePro):
        self.morsePro = morsePro

    def getMorsePro(self):
        return self.morsePro

    def getFarnsworth(self):
        return self.farnsworth

    def setEditTextIdxStart(self, idx):
        self.editTextIdxStart = idx

    def getEditTextIdxStart(self):
        return self.editTextIdxStart

    def setEditTextIdxEnd(self, idx):
        self.editTextIdxEnd = idx

    def getEditTextIdxEnd(self):
        return self.editTextIdxEnd

    def addMorseElement(self, morseElement, Duration):
        self.morseCharSeq.append(morseCharSeqEntry(morseElement, Duration))
        self.lengthSeq += 1

    def getMorseElement(self, idx):
        return self.morseCharSeq[idx]

class ReceiveTextChar( morseCharToken, bitbash):
    def __init__(self, msg):
        self.msg = msg.copy()
        self.Length = self.msg[2]
        self.cmmdCode = self.msg[3]
        self.receivedChecksum = (msg[self.Length-2] << 8) | msg[self.Length-1]
        self.valid = self.msg[5] != 0x00
        self.prosign = self.msg[6] != 0x00
        self.lengthSeq = self.msg[7]
        self.farnsworth = self.msg[8] != 0x00
        self.Tdit = self.decode16(self.msg, 9)

        self.morseCharToken = morseCharToken(self.Tdit, self.valid, self.prosign, self.farnsworth)

        if self.prosign:
            self.morseCharToken.setMorsePro(self.msg[4])
        else:
            self.morseCharToken.setMorseChar(chr(self.msg[4]))

        msgIdx = 0
        try:
            for eye in range(self.lengthSeq):
                self.morseCharToken.addMorseElement(morseElementenum(self.msg[11+msgIdx]), self.decode16(self.msg, 12+msgIdx))
                msgIdx += 3
        except:
            print("Exception: probable bad morseElement enum code. Sorry.")
    def getMorseCharToken(self):
        return copy.copy(self.morseCharToken)

    def getValid(self):
        return self.valid

class ping(morseCharToken, bitbash):
    def __init__(self):
        self.Length = 8
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('ping')
        self.receivedChecksum = 0
        self.payload = 0

    def rcvPing(self, msg):
        self.msg = msg.copy()
        self.Length = self.msg[2]
        self.cmmdCode = self.msg[3]
        self.receivedChecksum = (msg[self.Length - 2] << 8) | msg[self.Length - 1]
        self.payload = self.decode16(self.msg, 4)

    # send back verbatum
    def echoPing(self):
        return self.msg

    def newPing(self, payload):
        self.Length = 8
        self.msg = self.initMsg(self.Length)
        self.cmmdCode = SerialCmdCode.get('ping')
        self.msg[3] = self.cmmdCode
        self.payload = payload
        self.encode16(self.msg, 4, payload)
        CzeckSum(self.msg)
