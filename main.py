#!/usr/bin/python3
# This is a sample Python script.

# Only needed for access to command line arguments
import sys
import glob
import os
import random

# to find execution script directory
from inspect import currentframe, getframeinfo
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QLabel, QTextEdit, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QPixmap, QCursor, QTextCursor, QAction
from PyQt6 import QtGui, QtCore, Qt6, uic
from threading import Thread
from XmitRcvUART import XmitRcvUART

from msggenerator import (SendMorseMsg,
                          PlayMorseMsg,
                          SendSideTone,
                          bitbash,
                          SerialCmdCode,
                          ReceiveTextChar,
                          prosignTable,
                          StopMorseMsg,
                          morseCharToken,
                          SendFarnsworth,
                          morseCharSeqEntry,
                          morseElementenum,
                          ping)

from queue import Empty, Queue
#from MorseTrain import Ui_CWmainWin
from morseAnalyzerDialog import morseAnalyzerDialog
from LoremIpsum import LoremIpsumText
import time
from PyQt6.QtCore import (
    pyqtSignal,
    QEvent,
    QObject,
    QPoint
)
from PyQt6.QtCore import pyqtSignal
import platform
import serial.tools.list_ports
# =====================================================================================================================

class Consumer(QtCore.QThread):

    updateMorseMsg = QtCore.pyqtSignal(list)

    def __init__(self, msgRcvQueue, parent=None):
        super(QtCore.QThread, self).__init__(parent)
        self.msgRcvQueue = msgRcvQueue
        self.ConsumerEnabled = True
        self.consumer_thread = Thread(
            target=self.consumer,
            args=(self.msgRcvQueue,),
            daemon=True
        )

    def startRCV(self):
        self.consumer_thread.start()

    def killMe(self):
        self.ConsumerEnabled = False

    def Join(self):
        self.consumer_thread.join()

    def consumer(self, Q):
        BB = bitbash()
        while self.ConsumerEnabled:
            try:
                msg = Q.get(timeout=1, block=True)
            except Empty:
                continue
            print("Unqueue msg", end=': ')
            BB.dsplyMsg(msg)
            self.updateMorseMsg.emit(msg)
            del msg
        print("Consumer thread ends.")

# =============================================================================
class serialCommPortDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("serialCommPortDlg.ui", self)
        self.show()
        self.setWindowTitle("Arduino Serial Communications")
        ports = self.serial_ports()
        self.currentItem = ""
        if ports == []:
            msgBox = QMessageBox()
            msgBox.setText("No unencumbered serial ports detected. Sorry.")
            msgBox.setWindowTitle("Abandon all hope")
            returnValue = msgBox.exec()
        else:
            self.selectCommPort.addItems(ports)
            #self.selectCommPort.setCurrentText(ports[0])

            # Default
            self.setCurrentItem()
            #detect user selection
            self.selectCommPort.activated.connect(self.setCurrentItem)

    def cancelEvent(self, event):
        print("Cancelled.")

    def setCurrentItem(self):
        self.currentItem = self.selectCommPort.currentText()

    def getCurrentItem(self):
        return self.currentItem

    def serial_ports(self):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

# =============================================================================
class arduinoCommPath(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ArduinoCommPath.ui", self)
        self.show()

        self.selectedPath = ""
        self.setWindowTitle("Arduino Communications Path Selector")
        self.pushButtonSerial.clicked.connect(self.serialButton)
        self.pushButtonWiFi.clicked.connect(self.wifiButton)


    def serialButton(self):
        print("Serial")
        self.selectedPath = "serial"
        self.close()

    def wifiButton(self):
        print ("WiFi")
        self.selectedPath = "wifi"
        self.close()

    def getSelected(self):
        return self.selectedPath


# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()


        print(platform.system())
        print(platform.release())

        # find the home directory of the executable.
        filename = getframeinfo(currentframe()).filename
        self.parentDirectory = Path(filename).resolve().parent

        self.serialPortInUse = "TBD-Serial"
        self.wifiIpInUse = "TBD-WiFi-IP"
        self.wifiPortInUse = "TBD-WiFi-Port"
        self.commMethodInUse = "TBD"

        self.prosignList = prosignTable()

        uic.loadUi("MorseTrain.ui", self)
        self.show()

        menuBar = self.menuBar()
        actionFile = menuBar.addMenu("Communications")
        commPortAction = QAction('Arduino Comm Path', self)
        commPortAction.triggered.connect(self.userArduinoCommSetup)
        actionFile.addAction(commPortAction)
        actionLoremIpsum = menuBar.addMenu("Lorem Ipsum")
        lorumIpsumAction = QAction('Lorem Ipsum', self)
        lorumIpsumAction.triggered.connect(self.LoremIpsumMsg)
        actionLoremIpsum.addAction(lorumIpsumAction)

        self.ConsumerEnabled = True

        self.msgRcvQueue = Queue()
        self.msgXmitQueue = Queue()
        self.morseAnalyzerQueue = Queue()

        # setup serial communications skeleton
        self.SerialComm = XmitRcvUART(self.msgXmitQueue, self.msgRcvQueue)
        self.SerialComm.startxmit()

        if self.readConfigFile():
            if self.commMethodInUse == "WiFi":
                print("using WiFi")
                self.initWiFiCommunications()
            elif self.commMethodInUse == "Serial":
                print("Using Serial")
                # setup serial port settings and queue interface.But not open yet.
                self.initSerialCommunication()
            else:
                self.userArduinoCommSetup()
        else:
            self.userArduinoCommSetup()

        self.SerialComm.startrcv()

        self.writeConfigFile()

        if (self.commMethodInUse == "Serial"):
            port = self.serialPortInUse
        else:
            port = self.wifiIpInUse+":"+self.wifiPortInUse

        MainWindow.setWindowTitle(self,"KG7IFO CW Practice Trainer/Fist analyzer -- Comm: {0:s}/{1:s}".format(self.commMethodInUse, port))

        self.show()

        self.pushButtonPlay.clicked.connect(self.playMorseText)
        self.pushButtonLoad.clicked.connect(self.loadPlayMorseText)
        self.pushButtonClear.clicked.connect(self.clearMorseText)
        self.pushButtonSideTone.clicked.connect(self.handlepushButtonSideTone)
        self.pushButtonStop.clicked.connect(self.handlepushButtonStop)
        self.pushButtonSaveSession.clicked.connect(self.savePracticeSession)
        self.pushButtonLoadSession.clicked.connect(self.loadPracticeSession)

        self.pushButtonActivateListening.clicked.connect(self.activateListening)
        self.pushButtonRandomPhrase.clicked.connect(self.loadRandomPhrase)
        self.pushButtonReveal.clicked.connect(self.revealSecret)
        self.pushButtonReveal.setEnabled(False)
        self.pushButtonRandomPhrase.setEnabled(False)
        self.pushButtonActivateListening.setStyleSheet("background-color: #00AA00")
        self.pushButtonRandomPhrase.setStyleSheet("background-color: #D6D6D6")
        self.pushButtonReveal.setStyleSheet("background-color: #D6D6D6")
        self.listeningPracticeActive = False
        self.listeningPracticeFile = None
        self.listenList = []
        self.listenPracticetxt = ""

        self.morseTextEdit.mousePressEvent = self.ThemousePressEvent
        self.morseTextEdit.mouseReleaseEvent = self.ThemouseReleaseEvent
        self.morseTextEdit.setCursor(Qt.CursorShape.ArrowCursor)

        self.morseTextStream = []
        self.idxMorseTextStream = -1

        self.morseTextStreamPos = self.morseTextEdit.pos()

        self.pushButtonClearPlay.clicked.connect(self.clearMorseTextPlay)

        self.lineEditSideTone.setValidator(QDoubleValidator(100.0, 1000.0, 3))
        self.lineEditSideTone.installEventFilter(self)
        self.pushButtonSideTone.setDisabled(True)

        self.comboBoxWPM.addItems(["5", "10", "15", "20", "25", "30", "40", "60"])
        self.checkBoxFarnsworth.clicked.connect(self.handlecheckBoxFarnsworth)

        self.toolButtonPlayBack.clicked.connect(self.playbackButton)
        self.lineEditScore.setText("0")
        self.lineEditWPM.setText("0")
        self.charctersReceived = 0
        self.morseTextPosition = 0
        self.analyzeDialogActive = False

        # create a consumer thread and start it
        self.consumerDaemon = Consumer(self.msgRcvQueue)
        self.consumerDaemon.updateMorseMsg.connect(self.ProcessReceived)
        self.consumerDaemon.startRCV()

    def setupArduinoComm(self):

        configFilePath = os.path.join(self.parentDirectory, "Config.cfg")
        try:
            configFile = open(configFilePath, "rt")
        except:
            print("No configuration file.")
            self.userArduinoCommSetup()
        else:
            print("found config file.  Congratulations.")

    def userArduinoCommSetup(self):
        dlg = arduinoCommPath()
        dlg.exec()
        selectedPath = dlg.getSelected()
        if (selectedPath == "serial"):
            print("setup Serial")
            userPort = self.userSetSerialPort()
            if userPort == "":
                print("User picked no port.")
                self.close()
            else:
                self.serialPortInUse = userPort
                self.commMethodInUse = "Serial"
                if not self.initSerialCommunication():
                    print("Could not open comm port")
                    self.close()

        elif (selectedPath == "wifi"):
            print("setup WiFi")
            self.initWiFiCommunications()
        else:
            print("no communications.")
            self.close()

    def initWiFiCommunications(self):
        self.SerialComm.openUDP()
        self.sendPingtoArduino()

    def initSerialCommunication(self):
        self.SerialComm.setSerialPort(self.serialPortInUse)
        try:
            self.SerialComm.openSerialPort()
        except:
            return False
        else:
            return True

    def userSetSerialPort(self):
        if self.SerialComm.getInUse():
            self.SerialComm.closePort()
        dlg = serialCommPortDialog()
        returnedPort = ""
        if dlg.exec():
            print("Success")
            returnedPort = dlg.getCurrentItem()
        else:
            print("Failure")
        print("Serial port = {0:s}".format(returnedPort))
        return returnedPort

    def readConfigFile(self):
        configFilePath = os.path.join(self.parentDirectory, "Config.cfg")
        try:
            configFile = open(configFilePath, "rt")
        except:
            print("No configuration file.")
            return False
        else:
            cfg = configFile.readlines()
            configFile.close()
            try:
                self.commMethodInUse = cfg[0].strip('\n')
                self.serialPortInUse = cfg[1].strip('\n')
                self.wifiIpInUse = cfg[2].strip('\n')
                self.wifiPortInUse = cfg[3].strip('\n')
            except:
                return False
            else:
                return True

    def writeConfigFile(self):
        configFilePath = os.path.join(self.parentDirectory, "Config.cfg")
        print("write config file: {0:s}\n".format(configFilePath))
        try:
            configFile = open(configFilePath, "wt")
        except:
            print("Unwritable configuration file.")
            msgBox = QMessageBox()
            msgBox.setText("Can not write configuration file.")
            msgBox.setWindowTitle("Abandon all hope.")
            msgBox.exec()
        else:
            configFile.write(self.commMethodInUse+"\n")
            configFile.write(self.serialPortInUse+"\n")
            configFile.write(self.wifiIpInUse+"\n")
            configFile.write(self.wifiPortInUse+"\n")
            configFile.close()



    def LoremIpsumMsg(self):
        print("Lorem Ipsum")
        msgBox = QMessageBox()
        msgBox.setText(LoremIpsumText)
        msgBox.setWindowTitle("Lorem Ipsum")
        msgBox.exec()
# ==== end of menu bar handlers

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Leave:
            if self.lineEditSideTone.hasAcceptableInput():
                self.pushButtonSideTone.setDisabled(False)
        return False

    def ThemousePressEvent(self, e):
        print(">>>mousePressEvent<<<")
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            #print("Mouse text cursor position", self.morseTextEdit.cursorForPosition(e.pos()).position())
            textPosition = self.morseTextEdit.cursorForPosition(e.pos()).position()
            #print("textPosition = ", textPosition)
            #print("Length morseTextStream = {0:d}".format(len(self.morseTextStream)))
            if len(self.morseTextStream) != 0:
                for MCT in self.morseTextStream:
                    if (textPosition >= MCT.getEditTextIdxStart()) and (textPosition <= MCT.getEditTextIdxEnd()):
                        self.idxMorseTextStream = MCT
                        self.xeqMorseAnalyzerDialog()
        elif e.button() == QtCore.Qt.MouseButton.RightButton:
            print("Right Button")
        elif e.button() == QtCore.Qt.MouseButton.MiddleButton:
            print("Middle Button")

    def ThemouseReleaseEvent(self, e):
        print("<<<<mouseReleseEvent>>>>")
        if self.analyzeDialogActive:
            self.analyzeDialog.close()
            self.analyzeDialogActive = False

    def closeEvent(self, event):
        self.killConsumer()
        event.accept()

    def xeqMorseAnalyzerDialog(self):
        #print("xeqMorseAnalyzerDialog, idxMorseTextStream = ", self.idxMorseTextStream)
        self.analyzeDialog = morseAnalyzerDialog(self.idxMorseTextStream)
        self.analyzeDialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.analyzeDialogActive = True
        self.analyzeDialog.exec()

    def handlecheckBoxFarnsworth(self):
        enabled = self.checkBoxFarnsworth.isChecked()
        SFW = SendFarnsworth(enabled)
        self.msgXmitQueue.put(SFW.getMsg())

    def playbackButton(self):
        self.plainTextEdit.setPlainText(self.morseTextEdit.toPlainText())
        self.loadPlayMorseText()

    def handlepushButtonStop(self):
        print("Stop!")
        SMM = StopMorseMsg()
        self.msgXmitQueue.put(SMM.getMsg())


    def killConsumer(self):
        self.consumerDaemon.killMe()
        self.consumerDaemon.Join()
        print('Consumer killed')

    def ProcessReceived(self, msg):
        if msg[3] == SerialCmdCode.get('receivetextchar'):
            self.ProcessReceiveTextChar(msg)
        if msg[3] == SerialCmdCode.get('ping'):
            self.echoPingCmmd(msg)

    def ProcessReceiveTextChar(self, msg):
        try:
            RTC = ReceiveTextChar(msg)
            MCT = RTC.getMorseCharToken()
            self.evaluateMorseCharacter(MCT)
        except Exception as e:
            print("Failed receive message!", e)

        self.morseTextEdit.moveCursor(QtGui.QTextCursor.MoveOperation.End, QtGui.QTextCursor.MoveMode.MoveAnchor)

        if MCT.prosign:
            print("Prosign")
            prosignIdx = MCT.getMorsePro()
            morseChar = '\\' + self.prosignList.prosign[prosignIdx]
        else:
            if MCT.valid:
                morseChar = MCT.getMorseChar()
            else:
                morseChar = '*'
                #self.morseTextEdit.appendHtml("<p style=\"color:yellow;white-space:pre\">" + "*" + "</p>")
                #self.morseTextEdit.appendHtml("<p style=\"color:black;white-space:pre\"></p>")
                #self.morseTextEdit.moveCursor(QTextCursor.MoveOperation.End)
        self.morseTextEdit.insertPlainText(morseChar)

        # Get the string index of the latest character. This corresponds to the
        # index mouse cursor position returns when clicking on a specific letter.
        # note that newlines, \n, are embedded as well and count against the position.
        windowContents = self.morseTextEdit.toPlainText()
        startPos = len(windowContents)-1
        endPos = startPos+ (len(morseChar)-1)
        MCT.setEditTextIdxStart(startPos)
        MCT.setEditTextIdxEnd(endPos)

        #print("MCT text char = [{0:s}] pos = ({1:d}, {2:d})".format(morseChar, startPos, endPos))
        if MCT.getSpaceAfter():
            self.morseTextEdit.insertPlainText(" ")
        if MCT.getIdleAfter():
            self.morseTextEdit.insertPlainText("\n")
        try:
            self.morseTextStream.append(MCT)
        except Exception as e:
            print("can not append: ", e)

    def loadPracticeSession(self):
        print("Loading saved keyed session from file")

    def savePracticeSession(self):
        print("Saving keyed session to file")
        saveSessionFilePath = os.path.join(self.parentDirectory, "SaveSession.cvs")
        print("write config file: {0:s}\n".format(saveSessionFilePath))
        try:
            saveSessionFile = open(saveSessionFilePath, "wt")
        except:
            print("Unwritable configuration file.")
            msgBox = QMessageBox()
            msgBox.setText("Can not write configuration file.")
            msgBox.setWindowTitle("Abandon all hope.")
            msgBox.exec()
        else:
            for morseChar in self.morseTextStream:
                print (morseChar.getMorseChar())
                saveSessionFile.write("CW 0, ")
                saveSessionFile.write(morseChar.getMorseChar()+", ")
                saveSessionFile.write(str(morseChar.getTdit())+", ")
                saveSessionFile.write(str(morseChar.getWPM())+", ")
                saveSessionFile.write(str(morseChar.getScore())+", ")
                saveSessionFile.write(str(morseChar.getMorsePro())+", ")
                saveSessionFile.write(str(morseChar.getValid())+", ")
                saveSessionFile.write(str(morseChar.getLengthSeq())+", ")
                saveSessionFile.write(str(morseChar.getFarnsworth())+", ")
                saveSessionFile.write(str(morseChar.getSpaceAfter())+", ")
                saveSessionFile.write(str(morseChar.getIdleAfter())+", ")
                saveSessionFile.write("\n")
            saveSessionFile.close()

    def evaluateMorseCharacter(self, MCT):
        #
        #  WPM
        #
        elementCount = 0
        totalDuration = 0
        for V in range(MCT.getLengthSeq()):
            ME = MCT.getMorseElement(V)
            dahdit = ME.getMorseElement()
            if (dahdit != morseElementenum.morseIdle) and (dahdit != morseElementenum.morseStuck):
                totalDuration += ME.getDuration()

            if (dahdit == morseElementenum.morseDit) or (dahdit == morseElementenum.morseMark):
                elementCount += 1
            if (dahdit == morseElementenum.morseDah) or (dahdit == morseElementenum.morseSpace):
                elementCount += 3
            if dahdit == morseElementenum.morseWordSpace:
                MCT.setSpaceAfter(True)
                elementCount += 7
            if dahdit == morseElementenum.morseIdle:
                MCT.setIdleAfter(True)

        self.charctersReceived += 1
        averageTdit = totalDuration/elementCount
        WPM = self.WPM2ms(averageTdit)
        MCT.setWPM(WPM)

        if self.charctersReceived == 1:
            displayWPM = WPM
            self.lineEditWPM.setText("{0:d}".format(int(displayWPM)))
        else:
            runningWPM = int(self.lineEditWPM.text())
            runningWPM += WPM
            self.lineEditWPM.setText("{0:d}".format(int((runningWPM/2.0)+0.5)))
        #
        # Score (still to come)
        #
        scoreAwarded = 5
        self.lineEditScore.setText("{0:d}".format(scoreAwarded))
        MCT.setScore(scoreAwarded)

    def WPM2ms(self, WPM):
        return 1200/WPM

    def MS2wpm(self, MS):
        return 1200/MS

    def editSideTone(self):
        print("Frequency {0:s}".format(self.lineEditSideTone.text()))

    def editToFloat(self, value):
        if value == '':
            value = 0.0
        return float(value)

    def clearMorseTextPlay(self):
        self.plainTextEdit.setPlainText("")
        SMM = SendMorseMsg("")
        self.msgXmitQueue.put(SMM.getMsg())

    def clearMorseText(self):
        self.morseTextEdit.setPlainText("")
        self.morseTextStream = []
        self.morseTextStreamPos = self.morseTextEdit.pos()
        self.lineEditScore.setText("0")
        self.lineEditWPM.setText("0")
        self.charctersReceived = 0
        self.morseTextPosition = 0

    def loadPlayMorseText(self):
        txt = self.plainTextEdit.toPlainText().replace('\n', "  ")
        SMM = SendMorseMsg(txt)
        self.msgXmitQueue.put(SMM.getMsg())

    def playMorseText(self):
        WPM = int(self.comboBoxWPM.currentText())
        PMM = PlayMorseMsg(WPM)
        self.msgXmitQueue.put(PMM.getMsg())

    def handlepushButtonSideTone(self):
        #print("pushButtonSideTone")
        sidetone = self.editToFloat(self.lineEditSideTone.text())
        SST = SendSideTone(sidetone)
        self.msgXmitQueue.put(SST.getMsg())

    def sendPingtoArduino(self):
        pingMsg = ping()
        pingMsg.newPing(2390)
        self.msgXmitQueue.put(pingMsg.getMsg())

    # wrap-around ping command
    def echoPingCmmd(self, msg):
        pingMsg = ping()
        pingMsg.rcvPing(msg)
        self.msgXmitQueue.put(pingMsg.getMsg())

    def activateListening(self):
        #print("activateListening")
        if self.listeningPracticeActive:
            self.listeningPracticeActive = False
            self.pushButtonReveal.setEnabled(False)
            self.pushButtonRandomPhrase.setEnabled(False)
            self.pushButtonActivateListening.setStyleSheet("background-color: #00AA00")
            self.pushButtonRandomPhrase.setStyleSheet("background-color: #D6D6D6")
            self.pushButtonReveal.setStyleSheet("background-color: #D6D6D6")
        else:
            if self.readListeningPracticeFile():
                self.listeningPracticeActive = True
                self.pushButtonReveal.setEnabled(True)
                self.pushButtonRandomPhrase.setEnabled(True)
                self.pushButtonRandomPhrase.setStyleSheet("background-color: #00AA00")
                self.pushButtonReveal.setStyleSheet("background-color: #00AA00")
                self.pushButtonActivateListening.setStyleSheet("background-color: #ff0000")
                self.readListeningPracticeFile()

    def loadRandomPhrase(self):
        number = random.randint(0, len(self.listenList)-1)
        self.listenPracticetxt = self.listenList[number].strip('\n')
        self.plainTextEdit.setPlainText("".ljust(len(self.listenPracticetxt),'?'))
        SMM = SendMorseMsg(self.listenPracticetxt)
        self.msgXmitQueue.put(SMM.getMsg())

        #print("loadRandomPhrase")
        #print("Random Phrase = {0:s}\n".format(self.listenList[number]))

    def revealSecret(self):
        self.plainTextEdit.setPlainText(self.listenPracticetxt)
        #print("revealSecret")


    def readListeningPracticeFile(self):
        configFilePath = os.path.join(self.parentDirectory, "ListeningPractice.txt")
        try:
            self.listeningPracticeFile = open(configFilePath, "rt")
        except:
            print("No Listening Practice file.")
            return False
        else:
            self.listenList = self.listeningPracticeFile.readlines()
            self.listeningPracticeFile.close()
        return True

# =====================================================================================================================


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    sys.exit(app.exec())