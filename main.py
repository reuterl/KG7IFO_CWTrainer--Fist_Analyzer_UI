#!/usr/bin/python3
# This is a sample Python script.

# Only needed for access to command line arguments
import sys
import os
import signal
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QLabel, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QPixmap, QCursor, QTextCursor
from PyQt6 import QtGui, QtCore, Qt6
from threading import Thread
from FRDM_K22_COMM import XmitRcvUART
from msggenerator import (SendMorseMsg,
                          PlayMorseMsg,
                          SendSideTone,
                          bitbash,
                          ReceiveTextChar,
                          prosignTable,
                          StopMorseMsg,
                          morseCharToken,
                          SendFarnsworth,
                          morseCharSeqEntry,
                          morseElementenum)
from queue import Empty, Queue
from MorseTrain import Ui_CWmainWin
from morseAnalyzerDialog import morseAnalyzerDialog

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


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        print(platform.system())
        print(platform.release())
        print(list(serial.tools.list_ports.comports()))

        self.prosignList = prosignTable()

        self.UI = Ui_CWmainWin()
        self.UI.setupUi(self)

        #self.resize(830, 640)

        self.ConsumerEnabled = True

        self.msgRcvQueue = Queue()
        self.msgXmitQueue = Queue()
        self.morseAnalyzerQueue = Queue()

        self.SerialComm = XmitRcvUART(self.msgXmitQueue, self.msgRcvQueue)
        self.SerialComm.startrcv()
        self.SerialComm.startxmit()

        self.UI.pushButtonPlay.clicked.connect(self.playMorseText)
        self.UI.pushButtonLoad.clicked.connect(self.loadPlayMorseText)
        self.UI.pushButtonClear.clicked.connect(self.clearMorseText)
        self.UI.pushButtonSideTone.clicked.connect(self.pushButtonSideTone)
        self.UI.pushButtonStop.clicked.connect(self.pushButtonStop)

        self.UI.morseTextEdit.mousePressEvent = self.ThemousePressEvent
        self.UI.morseTextEdit.mouseReleaseEvent = self.ThemouseReleaseEvent
        self.UI.morseTextEdit.setCursor(Qt.CursorShape.ArrowCursor)

        self.morseTextStream = []
        self.idxMorseTextStream = -1

        self.morseTextStreamPos = self.UI.morseTextEdit.pos()

        self.UI.pushButtonClearPlay.clicked.connect(self.clearMorseTextPlay)

        self.UI.lineEditSideTone.setValidator(QDoubleValidator(100.0, 1000.0, 3))
        self.UI.lineEditSideTone.installEventFilter(self)
        self.UI.pushButtonSideTone.setDisabled(True)

        self.UI.comboBoxWPM.addItems(["5", "10", "15", "20", "25", "30", "40", "60"])
        self.UI.checkBoxFarnsworth.clicked.connect(self.checkBoxFarnsworth)

        self.UI.toolButtonPlayBack.clicked.connect(self.playbackButton)
        self.UI.lineEditScore.setText("0")
        self.UI.lineEditWPM.setText("0")
        self.charctersReceived = 0
        self.morseTextPosition = 0

        # create a consumer thread and start it
        self.consumerDaemon = Consumer(self.msgRcvQueue)
        self.consumerDaemon.updateMorseMsg.connect(self.ProcessReceived)
        self.consumerDaemon.startRCV()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Leave:
            if self.UI.lineEditSideTone.hasAcceptableInput():
                self.UI.pushButtonSideTone.setDisabled(False)
        return False

    def leaf(self):
        print("--EventFilter--")
        if self.UI.lineEditSideTone.hasAcceptableInput():
            self.UI.pushButtonSideTone.setDisabled(False)

    def ThemousePressEvent(self, e):
        print(">>>mousePressEvent<<<")
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            print("Mouse text cursor position", self.UI.morseTextEdit.cursorForPosition(e.pos()).position())
            textPosition = self.UI.morseTextEdit.cursorForPosition(e.pos()).position()
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
        self.analyzeDialog.close()

    def closeEvent(self, event):
        self.killConsumer()
        event.accept()

    def xeqMorseAnalyzerDialog(self):
        self.analyzeDialog = morseAnalyzerDialog(self.idxMorseTextStream)
        self.analyzeDialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.analyzeDialog.exec()

    def checkBoxFarnsworth(self):
        enabled = self.UI.checkBoxFarnsworth.isChecked()
        SFW = SendFarnsworth(enabled)
        self.msgXmitQueue.put(SFW.getMsg())

    def playbackButton(self):
        self.UI.plainTextEdit.setPlainText(self.UI.morseTextEdit.toPlainText())
        self.loadPlayMorseText()

    def pushButtonStop(self):
        print("Stop!")
        SMM = StopMorseMsg()
        self.msgXmitQueue.put(SMM.getMsg())


    def killConsumer(self):
        self.consumerDaemon.killMe()
        self.consumerDaemon.Join()
        print('Consumer killed')

    def ProcessReceived(self, msg):
        if msg[3] == 0xF0:
            self.ProcessReceiveTextChar(msg)

    def ProcessReceiveTextChar(self, msg):

        try:
            RTC = ReceiveTextChar(msg)
            MCT = RTC.getMorseCharToken()
            self.evaluateMorseCharacter(MCT)
        except Exception as e:
            print("Failed receive message!", e)

        self.UI.morseTextEdit.moveCursor(QtGui.QTextCursor.MoveOperation.End, QtGui.QTextCursor.MoveMode.MoveAnchor)

        MCT.setEditTextIdxStart(self.UI.morseTextEdit.cursorForPosition(self.UI.morseTextEdit.pos()).position())

        if MCT.prosign:
            print("Prosign")
            prosignIdx = MCT.getMorsePro()
            morseChar = '\\' + self.prosignList.prosign[prosignIdx]
            MCT.setEditTextIdxEnd(self.UI.morseTextEdit.cursorForPosition(self.UI.morseTextEdit.pos()).position()+len(morseChar)-1)
        else:
            if MCT.valid:
                morseChar = MCT.getMorseChar()
            else:
                morseChar = chr(0xBF)

            MCT.setEditTextIdxEnd(self.UI.morseTextEdit.cursorForPosition(self.UI.morseTextEdit.pos()).position())
        self.UI.morseTextEdit.insertPlainText(morseChar)
        if MCT.getSpaceAfter():
            self.UI.morseTextEdit.insertPlainText(" ")
        if MCT.getIdleAfter():
            self.UI.morseTextEdit.insertPlainText("\r\n")
        try:
            self.morseTextStream.append(MCT)
        except Exception as e:
            print("can not append: ", e)


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
            self.UI.lineEditWPM.setText("{0:d}".format(int(displayWPM)))
        else:
            runningWPM = int(self.UI.lineEditWPM.text())
            runningWPM += WPM
            self.UI.lineEditWPM.setText("{0:d}".format(int((runningWPM/2.0)+0.5)))
        #
        # Score
        #
        scoreAwarded = 5
        self.UI.lineEditScore.setText("{0:d}".format(scoreAwarded))
        MCT.setScore(scoreAwarded)

    def WPM2ms(self, WPM):
        return 1200/WPM

    def MS2wpm(self, MS):
        return 1200/MS

    def editSideTone(self):
        print("Frequency {0:s}".format(self.UI.lineEditSideTone.text()))

    def editToFloat(self, value):
        if value == '':
            value = 0.0
        return float(value)

    def clearMorseTextPlay(self):
        self.UI.plainTextEdit.setPlainText("")

    def clearMorseText(self):
        self.UI.morseTextEdit.setPlainText("")
        self.morseTextStream = []
        self.morseTextStreamPos = self.UI.morseTextEdit.pos()
        self.UI.lineEditScore.setText("0")
        self.UI.lineEditWPM.setText("0")
        self.charctersReceived = 0
        self.morseTextPosition = 0

    def loadPlayMorseText(self):
        txt = self.UI.plainTextEdit.toPlainText()
        SMM = SendMorseMsg(txt)
        self.msgXmitQueue.put(SMM.getMsg())

    def playMorseText(self):
        WPM = int(self.UI.comboBoxWPM.currentText())
        PMM = PlayMorseMsg(WPM)
        self.msgXmitQueue.put(PMM.getMsg())

    def pushButtonSideTone(self):
        print("pushButtonSideTone")
        sidetone = self.editToFloat(self.UI.lineEditSideTone.text())
        SST = SendSideTone(sidetone)
        self.msgXmitQueue.put(SST.getMsg())
# =====================================================================================================================


if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.setWindowTitle("KG7IFO CW Practice Trainer/Fist analyzer")
    window.show()
    sys.exit(app.exec())