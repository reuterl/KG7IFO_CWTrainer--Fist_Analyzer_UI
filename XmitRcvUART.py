import time
import serial
import time
from queue import Empty, Queue
from threading import Thread
from machinedetat import machine_detat
from msggenerator import bitbash
import platform


class XmitRcvUART():
    def __init__(self, msgXmitQueue, MsgRcvQueue):
#            self.serialPort = "/dev/ttyUSB0"

        self.inUse = False

        self.baud = 9600
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        self.bytesize = serial.EIGHTBITS

        # Daemonic threads die automatically at main thread exit
        self.xmitThread = Thread(target=self.UARTsend)
        self.xmitThread.daemon = True

        self.rcvThread = Thread(target=self.UARTreceive)
        self.rcvThread.daemon = True

        self.msg = []

        # Send and receive queues between threads and mainline
        self.msgXmitQueue = msgXmitQueue
        self.MsgRcvQueue = MsgRcvQueue
        self.mde = machine_detat(self.MsgRcvQueue)
        self.enabled = True

    def setSerialPort(self, port):
        self.serialPort = port

    def openSerialPort(self):
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

    def getInUse(self):
        return self.inUse

    def __del__(self):
        byte = self.serialPort.close()
        print("XmitRcvUART: destructor.")

    def UARTreceive(self):
        while self.enabled:
            try:
                bytebyte = self.serialPort.read(size=1)
            except:
                if self.enabled:
                    print("UARTreceive: read cancelled.")
                else:
                    print("UARTreceive: read failed.")
                break
            byte = int.from_bytes(bytebyte, 'big', signed=False)
            try:
                st = bytebyte.decode("utf-8")
            except:
                st = "?"
            #print("Receive byte = 0x{:02X} [{}]".format(byte, st))
            # print("Receive byte = {:02X}".format(byte))
            self.mde.msgParser(byte)

        print("Rcv task complete.")

    def UARTsend(self):
        BB = bitbash()
        while self.enabled:
            self.msg = self.msgXmitQueue.get()
            BB.dsplyMsg(self.msg)
            self.serialPort.write(self.msg)

        print("Xmit task complete.")

    def startxmit(self):
        self.xmitThread.start()

    def startrcv(self):
        self.rcvThread.start()

    def closePort(self):
        self.serialPort.close()
        self.inUse = False
        self.disbleXmtRcv()
        print("Serial Port Closed.")

    def disbleXmtRcv(self):
        self.enabled = False
