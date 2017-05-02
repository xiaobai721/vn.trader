# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'NetCurve.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from eventEngine import *
import logging, os, sys
from datetime import datetime
import collections
from operator import itemgetter
from itertools import groupby



try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class NetCurveManager(QtGui.QWidget):

    def setupUi(self, Dialog):
        self.path = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir,os.pardir)) + 'vn.trader\\ctaLogFile\\ctaPosFile'
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(755, 515)
        self.horizontalLayoutWidget = QtGui.QWidget(Dialog)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(40, 30, 661, 80))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.labelAcctName = QtGui.QLabel(self.horizontalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setItalic(False)
        font.setUnderline(False)
        font.setStrikeOut(False)
        font.setStyleStrategy(QtGui.QFont.PreferDefault)
        self.labelAcctName.setFont(font)
        self.labelAcctName.setObjectName(_fromUtf8("labelAcctName"))
        self.horizontalLayout.addWidget(self.labelAcctName)
        self.cbAccount = QtGui.QComboBox(self.horizontalLayoutWidget)
        self.cbAccount.setObjectName(_fromUtf8("cbAccount"))
        self.horizontalLayout.addWidget(self.cbAccount)
        self.labelContract = QtGui.QLabel(self.horizontalLayoutWidget)
        self.labelContract.setObjectName(_fromUtf8("labelContract"))
        self.horizontalLayout.addWidget(self.labelContract)
        self.cbContract = QtGui.QComboBox(self.horizontalLayoutWidget)
        self.cbContract.setObjectName(_fromUtf8("cbContract"))
        self.horizontalLayout.addWidget(self.cbContract)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.labelAmount = QtGui.QLabel(self.horizontalLayoutWidget)
        self.labelAmount.setObjectName(_fromUtf8("labelAmount"))
        self.horizontalLayout.addWidget(self.labelAmount)
        self.lineAmount = QtGui.QLineEdit(self.horizontalLayoutWidget)
        self.lineAmount.setObjectName(_fromUtf8("lineAmount"))
        self.horizontalLayout.addWidget(self.lineAmount)
        self.verticalLayoutWidget = QtGui.QWidget(Dialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(600, 230, 101, 231))
        self.verticalLayoutWidget.setObjectName(_fromUtf8("verticalLayoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        # self.checkBox_2 = QtGui.QCheckBox(self.verticalLayoutWidget)
        # self.checkBox_2.setObjectName(_fromUtf8("checkBox_2"))
        # self.verticalLayout.addWidget(self.checkBox_2)
        # self.checkBox = QtGui.QCheckBox(self.verticalLayoutWidget)
        # self.checkBox.setObjectName(_fromUtf8("checkBox"))
        # self.verticalLayout.addWidget(self.checkBox)
        # self.checkBox_3 = QtGui.QCheckBox(self.verticalLayoutWidget)
        # self.checkBox_3.setObjectName(_fromUtf8("checkBox_3"))
        # self.verticalLayout.addWidget(self.checkBox_3)
        self.graphicsView = QtGui.QGraphicsView(Dialog)
        self.graphicsView.setGeometry(QtCore.QRect(110, 231, 461, 231))
        self.graphicsView.setObjectName(_fromUtf8("graphicsView"))
        self.ButtonStart = QtGui.QPushButton(Dialog)
        self.ButtonStart.setGeometry(QtCore.QRect(50, 320, 51, 23))
        self.ButtonStart.setObjectName(_fromUtf8("ButtonStart"))
        self.labelMetrics = QtGui.QLabel(Dialog)
        self.labelMetrics.setGeometry(QtCore.QRect(40, 150, 661, 41))
        self.labelMetrics.setText(_fromUtf8(""))
        self.labelMetrics.setObjectName(_fromUtf8("labelMetrics"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    # ----------------------------------------------------------------------
    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.labelAcctName.setText(_translate("Dialog", "账户", None))
        self.labelContract.setText(_translate("Dialog", "标的", None))
        self.labelAmount.setText(_translate("Dialog", "初始金额", None))
        # self.checkBox_2.setText(_translate("Dialog", "con2", None))
        # self.checkBox.setText(_translate("Dialog", "con1", None))
        # self.checkBox_3.setText(_translate("Dialog", "Sum", None))
        self.ButtonStart.setText(_translate("Dialog", "分析", None))

    # ----------------------------------------------------------------------
    def loadInitData(self):
        tree = lambda: collections.defaultdict(tree)
        self.dataList = tree()
        self.fileName = []
        # names = locals()

        self.loadAllPosFile()
        self.cbAccount.addItems([k for k in self.groupByPosFile('account').keys()])
        self.cbContract.addItems([k for k in self.groupByPosFile('contract').keys()])


        for k in self.groupByPosFile('strategy').keys():
            self.batchAssignment(k)

        # 加总净值曲线
        self.batchAssignment('Sum')

    # ----------------------------------------------------------------------

    def batchAssignment(self,i):
        self.names = locals()
        self.names['self.%s' % i] = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.names['self.%s' % i].setObjectName(_fromUtf8('box' + i))
        self.names['self.%s' % i].setText(_translate("Dialog", i, None))

        self.verticalLayout.addWidget(self.names['self.%s' % i])
    # ----------------------------------------------------------------------

    def loadAllPosFile(self):
        self.fileName = []
        for i in os.walk(self.path):
            if len(i[-1]) > 0 and 'txt' in i[-1][0]:
                for j in i[-1]:
                    self.dataList = {}
                    self.dataList['name'] = j
                    self.dataList['account'] = j.split('_', 1)[0]
                    self.dataList['strategy'] = j.split('_', 2)[1]
                    self.dataList['contract'] = j.split('_', 2)[2][:-4]
                    self.fileName.append(self.dataList)
            break

    # ----------------------------------------------------------------------
    def groupByPosFile(self, field):

        try:
            return dict([(g, list(k)) for g, k in groupby(self.fileName, key=lambda x: x[field])])
        except Exception as e:
            print e
            return []


if __name__ == '__main__':
    app = 0
    app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = NetCurveManager()
    ui.setupUi(Dialog)
    ui.loadInitData()
    Dialog.show()
    sys.exit(app.exec_())