from PyQt6 import QtCore, QtGui, QtWidgets
from morseAnalyzer import Ui_DialogMorseAnalyzer
from PyQt6.QtGui import QPixmap, QColor, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QDialog,
    QCheckBox,
    QWidget
)
from msggenerator import bitbash, ReceiveTextChar, prosignTable,morseCharSeqEntry,morseElementenum, prosignTable

class morseAnalyzerDialog(QDialog):

    def __init__(self, MCT):
        QDialog.__init__(self)

        self.MCT = MCT
        self.prosignList = prosignTable()

        self.DialogMorseAnalyzer = QDialog()
        self.ui = Ui_DialogMorseAnalyzer()
        self.ui.setupUi(self.DialogMorseAnalyzer)
        self.widget = QWidget()
        self.ui.outerlayout = QHBoxLayout()
        self.ui.anotherLayout = QGridLayout(self.widget)

        Tdit = MCT.getTdit()
        fTdit = float(Tdit)

        self.myFont = QFont('Ariel', 15)
        self.myFont.setBold(True)

        self.anotherFont = QFont('Ariel', 12)
        self.anotherFont.setBold(False)

        self.ui.TditLabel = QLabel()
        self.ui.TditLabel.setText("Tdit = {0:d}mS".format(Tdit))
        self.ui.TditLabel.setFont(self.myFont)

        self.ui.wpmLabel = QLabel()
        self.ui.wpmLabel.setText("WPM = {0:d}".format(MCT.getWPM()))
        self.ui.scoreLabel = QLabel()
        self.ui.scoreLabel.setText("Score = {0:d}".format(MCT.getScore()))

        self.ui.morseCharLabel = QLabel()
        if MCT.isProsign():
            morseProIdx = MCT.getMorsePro()
            morsePro = '\\' + self.prosignList.prosign[morseProIdx]
            self.ui.morseCharLabel.setText("Prosign = '{0:s}'".format(morsePro))
        else:
            if MCT.valid:
                morseChar = MCT.getMorseChar()
            else:
                morseChar = chr(0xBF)
            self.ui.morseCharLabel.setText("Char = '{0:s}'".format(morseChar))
        self.ui.morseCharLabel.setFont(self.myFont)

        for x in range(MCT.getLengthSeq()):
            morseCharElement = MCT.getMorseElement(x)
            print(morseCharElement.getMorseElement(), morseCharElement.getDuration())
            self.ui.outerlayout.addWidget(self.displayElement(morseCharElement.getMorseElement(), morseCharElement.getDuration(), float(morseCharElement.getDuration())/fTdit))

        self.ui.anotherLayout.addWidget(self.ui.morseCharLabel, 1, 1)
        self.ui.anotherLayout.addWidget(self.ui.TditLabel, 1, 3)
        self.ui.anotherLayout.addLayout(self.ui.outerlayout, 2, 1, 1, 3)
        self.ui.anotherLayout.addWidget(self.ui.wpmLabel, 3, 1)
        self.ui.anotherLayout.addWidget(self.ui.scoreLabel, 3, 3)

        self.ui.checkboxFarnsworth = QCheckBox()
        self.ui.checkboxFarnsworth.setChecked(MCT.getFarnsworth())
        self.ui.checkboxFarnsworth.setText("Farnsworth")
        self.ui.anotherLayout.addWidget(self.ui.checkboxFarnsworth, 3, 2)
        self.setLayout(self.ui.anotherLayout)

    def displayElement(self, dahditInt, duration, countdits):
        widget = QWidget()
        widget.setFixedWidth(80)
        widget.setFixedHeight(100)

        dahdit = morseElementenum(dahditInt)

        labelDit = QLabel()

        if dahdit == morseElementenum.morseDit:
            dit = QPixmap(8, 8)
            dit.fill(QColor("red"))
            labelDit.setPixmap(dit)
        elif dahdit == morseElementenum.morseDah:
            dit = QPixmap(24, 8)
            dit.fill(QColor("red"))
            labelDit.setPixmap(dit)
        elif dahdit == morseElementenum.morseMark:
            labelDit.setText("[ ]")
        elif dahdit == morseElementenum.morseSpace:
            labelDit.setText("<CHAR SPC>")
        elif dahdit == morseElementenum.morseWordSpace:
            labelDit.setText("<WORD SPC>")
        elif dahdit == morseElementenum.morseIdle:
            labelDit.setText("<<IDLE>>")

        palette = self.palette();
        palette.setColor(self.foregroundRole(), QColor("blue"))
        labelDit.setPalette(palette)

        if dahdit != morseElementenum.morseIdle:
            labelDitDuration = QLabel("{0:d}".format(duration))
            labelDitCountDits = QLabel("{0:2.1f}".format(countdits))
        else:
            labelDitDuration = QLabel("---")
            labelDitCountDits = QLabel("---")

        morseElementDitStatsLayout = QVBoxLayout()
        morseElementDitStatsLayout.addWidget(labelDitDuration, alignment=Qt.AlignmentFlag.AlignCenter)
        morseElementDitStatsLayout.addWidget(labelDitCountDits, alignment=Qt.AlignmentFlag.AlignCenter)

        morseElementDitLayout = QHBoxLayout()
        morseElementDitLayout.addWidget(labelDit, alignment=Qt.AlignmentFlag.AlignCenter)

        morseElementDitOutLayout = QVBoxLayout()
        morseElementDitOutLayout.addLayout(morseElementDitLayout)
        morseElementDitOutLayout.addLayout(morseElementDitStatsLayout)

        ditwidget = QWidget()
        ditwidget.setLayout(morseElementDitOutLayout)

        return ditwidget
