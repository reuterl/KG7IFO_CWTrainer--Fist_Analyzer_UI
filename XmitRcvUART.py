import time
import serial
import socket
import time
from queue import Empty, Queue
from threading import Thread
from machinedetat import machine_detat
from msggenerator import bitbash
import platform
from enum import Enum

# =============================================================================
class commMethod(Enum):
    NoMethod = 1
    Serial = 2
    WiFi = 3
# =============================================================================
class XmitRcvUART():
    def __init__(self, msgXmitQueue, MsgRcvQueue):
#            self.serialPort = "/dev/ttyUSB0"

        self.method = commMethod(commMethod.NoMethod)

        self.inUse = False

        # Serial/UART parameters
        self.baud = 9600
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.bytesize = serial.EIGHTBITS

        # UDP parameters
        self.udpIP = "10.0.0.198"
        self.udpPort  = 2390
        self.sock = socket.socket()

        # Daemonic threads die automatically at main thread exit
        self.xmitThread = Thread(target=self.msgSend)
        self.xmitThread.daemon = True

        self.rcvThread = Thread(target=self.msgReceive)
        self.rcvThread.daemon = True

        self.msg = []

        # Send and receive queues between threads and mainline
        self.msgXmitQueue = msgXmitQueue
        self.MsgRcvQueue = MsgRcvQueue
        self.mde = machine_detat(self.MsgRcvQueue)
        self.enabled = True

    def setSerialPort(self, port):
        self.serialPort = port
    def setUdpIP(self, IP):
        self.udpIP = IP
    def setUdpPort(self, port):
        self.udpPort = port

    def openUDP(self):
        print("Open UDP")
        print("UDP target IP: %s" % self.udpIP)
        print("UDP target port: %s" % self.udpPort)

        self.sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP

        self.sock.bind(('', self.udpPort))

        self.inUse = True
        self. method = commMethod.WiFi

    def openSerialPort(self):
        print("Open Serial")
        self.serialPort = serial.Serial(
            port=self.serialPort,
            dsrdtr=False,
            timeout=None,
            baudrate=self.baud,
            parity=self.parity,
            stopbits=self.stopbits,
            bytesize=self.bytesize
        )
        self.inUse = True
        self. method = commMethod.Serial

    def getInUse(self):
        return self.inUse

    def __del__(self):
        if self.method == commMethod.Serial:
            byte = self.serialPort.close()
        print("XmitRcvUART: destructor.")

    def msgStream(self):
        if self.method == commMethod.Serial:
            bytebyte = self.serialPort.read(size=1)
            byte = int.from_bytes(bytebyte, 'big', signed=False)
            try:
                st = bytebyte.decode("utf-8")
            except:
                st = "?"
            #print("Receive byte = 0x{:02X} [{}]".format(byte, st))
            # print("Receive byte = {:02X}".format(byte))
            self.mde.msgParser(byte)
        elif self.method == commMethod.WiFi:
            print("Rcv: WiFi")
            data, addr = self.sock.recvfrom(1024)  # buffer size is 1024 bytes
            print("addr %s", addr)
            for y in range(len(data)):
                self.mde.msgParser(data[y])
        else:
            raise ValueError("RCV: No communications method selected. Use 'Serial, or 'WiFi'.")

    def msgReceive(self):
        print("Receive thread commences.")
        while self.enabled:
            try:
                byte = self.msgStream()
            except:
                if self.enabled:
                    print("receive: read cancelled.")
                else:
                    print("receive: read failed.")
                break

        print("Receive thread complete.")

    def msgSend(self):
        print("Xmit thread commences.")
        BB = bitbash()
        while self.enabled:
            self.msg = self.msgXmitQueue.get()
            BB.dsplyMsg(self.msg)
            self.msgXmitStream()
            #self.serialPort.write(self.msg)

        print("Xmit thread complete.")

    def msgXmitStream(self):
        if self.method == commMethod.Serial:
            print("Xmit: Serial")
            self.serialPort.write(self.msg)
        elif self.method == commMethod.WiFi:
            print("Xmit: WiFi")
            self.sock.sendto(bytes(self.msg), (self.udpIP, self.udpPort))
        else:
            raise ValueError("Xmit: No communications method selected. Use 'Serial, or 'WiFi'.")

    def startxmit(self):
        self.xmitThread.start()

    def startrcv(self):
        self.rcvThread.start()

    def closePort(self):
        try:
            self.serialPort.close()
        except:
            print("Serial Port mot closed. (not open?)")
        self.inUse = False
        #self.disbleXmtRcv()
        print("Arduino communications closed.")

    def disbleXmtRcv(self):
        self.enabled = False
