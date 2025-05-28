from queue import Empty, Queue
from enum import Enum

class msgState(Enum):
    st_sea = 1
    st_Q = 2
    st_len = 4
    st_fill = 5

class machine_detat():
    def __init__(self, MsgQueue):
        self. state = msgState.st_sea
        self.q_msg = MsgQueue
        self.msg = []
        self.msgLength = 0
        self.remaining = 0
        self.corruptMsg = 0

    def initmsg(self):
        self.msg = [ord('C'), ord('Q')]

    def msgParser(self, byte):
        if self.state == msgState.st_sea:
            if byte == ord('C'):
                self.state = msgState.st_Q
            else:
                self.state == msgState.st_sea
        elif self.state == msgState.st_Q:
            if byte == ord('Q'):
                self.state = msgState.st_len
            else:
                self.state == msgState.st_sea
        elif self.state == msgState.st_len:
            self.initmsg()
            self.msg.append(byte)
            self.msgLength = byte
            self.state = msgState.st_fill
            self.remaining = self.msgLength-3
        elif self.state == msgState.st_fill:
            self.remaining -= 1
            self.msg.append(byte)
            if self.remaining == 0:
                czecksum = 0
                for n in range(len(self.msg)-2):
                    czecksum += self.msg[n]
                msgChecksum = self.msg[self.msgLength-1]
                msgChecksum |= self.msg[self.msgLength-2] << 8
                if msgChecksum == czecksum:
                    self.q_msg.put(self.msg)
                else:
                    self.corruptMsg += 1
                    print("Corrupt!")
                self.state = msgState.st_sea
        else:
            print("default!")
