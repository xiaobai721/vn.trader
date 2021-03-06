# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'NetCurve.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from eventEngine import *
import logging, os, sys
# from datetime import datetime
import collections
import numpy as np
from operator import itemgetter
import matplotlib.pyplot as plt
from itertools import groupby, product
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


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

class NetCurveManager(QtGui.QDialog):

    def __init__(self, analysisEngine, Dialog, path, parent = None):
        QtGui.QDialog.__init__(self, parent)  # 调用父类初始化方法
        # super(NetCurveManager, self).__init__(parent)
        # self.setWindowTitle('NetCurve')
        self.analysisEngine = analysisEngine
        if 'Curr' in path:
            self.path = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\ctaLogFile\\ctaPosFile'
        else:
            self.path = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\ctaLogFile\\ctaPosFile\\his'
        # Dialog = QtGui.QDialog()
        # ui = NetCurveManager()
        self.setupUi(Dialog)
        self.loadInitData()
        self.triggerEvent()
        Dialog.show()
        # ui.triggerEvent()
        # ui.on_draw()
        # self.show()

    def setupUi(self, Dialog):

        Dialog.setObjectName(_fromUtf8("NetCurve"))
        Dialog.resize(1012, 689)
        self.horizontalLayoutWidget = QtGui.QWidget(Dialog)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(40, 30, 941, 101))
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
        # self.labelAcctName.setFont(font)
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
        self.cbContract.addItem('')
        self.horizontalLayout.addWidget(self.cbContract)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.labelAmount = QtGui.QLabel(self.horizontalLayoutWidget)
        self.labelAmount.setObjectName(_fromUtf8("labelAmount"))
        self.horizontalLayout.addWidget(self.labelAmount)
        self.lineAmount = QtGui.QLineEdit(self.horizontalLayoutWidget)
        self.lineAmount.setObjectName(_fromUtf8("lineAmount"))
        self.lineAmount.setText('10000000')
        self.horizontalLayout.addWidget(self.lineAmount)
        # checkbox
        self.verticalLayoutWidget = QtGui.QWidget()
        # self.verticalLayoutWidget.setGeometry(QtCore.QRect(600, 230, 101, 231))
        self.verticalLayoutWidget.setObjectName(_fromUtf8("verticalLayoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))

        # horizontalLayoutWidget_2
        self.horizontalLayoutWidget_2 = QtGui.QWidget(Dialog)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(40, 330, 941, 331))
        self.horizontalLayoutWidget_2.setObjectName(_fromUtf8("horizontalLayoutWidget_2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))

        self.ButtonStart = QtGui.QPushButton(self.horizontalLayoutWidget_2)
        self.ButtonStart.setObjectName(_fromUtf8("ButtonStart"))
        self.horizontalLayout_2.addWidget(self.ButtonStart)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.horizontalLayout_2.addWidget(self.canvas)

        # verticalLayout for checkbox
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))

        self.editMetrics = QtGui.QTextEdit(Dialog)
        self.editMetrics.setGeometry(QtCore.QRect(50, 140, 921, 171))
        self.editMetrics.setText(_fromUtf8(""))
        self.editMetrics.setObjectName(_fromUtf8("editMetrics"))
        self.editMetrics.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.editMetrics.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        #
        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    # ----------------------------------------------------------------------
    def retranslateUi(self, Dialog):
        # Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.labelAcctName.setText(_translate("Dialog", "账户", None))
        self.labelContract.setText(_translate("Dialog", "标的", None))
        self.labelAmount.setText(_translate("Dialog", "初始金额", None))
        self.ButtonStart.setText(_translate("Dialog", "分析", None))

    # ----------------------------------------------------------------------
    def triggerEvent(self):
        self.ButtonStart.clicked.connect(self.startCalculate)
    # ----------------------------------------------------------------------
    def on_draw(self, dateList, tempCapital):
        """ Redraws the figure
        """
        self.figure.clf()
        # ax = self.figure
        ax = self.figure.add_subplot(111)
        showN = 20
        n = len(dateList)
        variables = locals()
        # # ax.xlabel("Date")
        # # ax.ylabel("Net")
        # # ax.title("Selected Net Curve")
        # ax.grid()
        labels = []
        for index, i in enumerate(tempCapital.keys()):
            if 'sum' not in i:
                labels.append(i.split('\\')[-1][:-4])
            else:
                labels.append(i)
            variables['var_%s' % index], = ax.plot(range(n), tempCapital[i], label=labels)

        # a = tuple(m for m in variables.keys() if 'var_' in m])
        # b = tuple(labels.sort())
        # print a,b
        ax.legend()

        # for test
        # a, = ax.plot(range(4), [2,4,5,6], label="netCurve")
        # b, = ax.plot(range(4), [0,1,2,3], label="test")
        # ax.legend((a,b), ("abc","dge"))
        self.canvas.draw_idle()

    # ----------------------------------------------------------------------
    def showMetrics(self,e):
        str = ''
        # for i in range(3):
        #     str = str.join('abc' + '\n')

        for i in e.keys():
            if 'sum' in i:
                labels = i
            else:
                labels = i.split('\\')[-1][:-4]
            str = str + "Instance=%s annualRet=%.2f sharp=%.2f sortino=%.2f maxDrawdown=%.2f meanDrawdown=%.2f maxDrawdownDay=%.2f meanDrawdownDay=%.2f\n"\
                  %(labels,e[i]['annualRet'],e[i]['sharp'],e[i]['sortino'],e[i]['maxDrawdown'],e[i]['meanDrawdown'],e[i]['maxDrawdownDay'],e[i]['meanDrawdownDay'])
        # print str
        self.editMetrics.setText(str)
    # ----------------------------------------------------------------------
    def loadInitData(self):
        tree = lambda: collections.defaultdict(tree)
        self.dataList = tree()
        self.fileName = []
        # names = locals()

        self.loadAllPosFile()
        self.cbAccount.addItems([k for k in self.groupByPosFile('account').keys()])
        self.cbContract.addItems([k for k in self.groupByPosFile('contract').keys()])

        self.names = locals()
        for k in self.groupByPosFile('strategy').keys():
            self.batchAssignment(k)

        # 加总净值曲线
        self.batchAssignment('Sum')
        self.horizontalLayout_2.addLayout(self.verticalLayout)
    # ----------------------------------------------------------------------

    def batchAssignment(self,i):

        self.names['self.s_%s' % i] = QtGui.QCheckBox(self.horizontalLayoutWidget_2)
        self.names['self.s_%s' % i].setObjectName(_fromUtf8('box' + i))
        self.names['self.s_%s' % i].setText(_translate("Dialog", i, None))
        self.verticalLayout.addWidget(self.names['self.s_%s' % i])

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

    # ----------------------------------------------------------------------
    def pathIter(self, assembledList):
        """文件查询迭代函数"""
        pathList = []
        filePathList = []
        for i in assembledList:
            try:
                if len(i) > 2:
                    pathList.extend(filter(lambda x:x['account'] == i[0] and x['contract'] == i[1] and x['strategy'] == i[2],self.fileName))
                else:
                    pathList.extend(filter(lambda x: x['account'] == i[0] and x['strategy'] == i[1],self.fileName))

            except Exception as e:
                    print e

        # return set(pathList)
        for i in pathList:
            if i != []:
                filePathList.append(str(self.path + '\\' + i['name']))

        func = lambda g, k: g if k in g else g + [k]
        return reduce(func, [[], ] + filePathList)
    # ----------------------------------------------------------------------
    def startCalculate(self):
        acct, con = [], []
        if self.cbAccount.currentText() != {}:
            acct.append(str(self.cbAccount.currentText()))
        else:
            QtGui.QMessageBox.warning(self, u'Warning', u'请选择账户！')
            acct = None

        con.append(str(self.cbContract.currentText()) if self.cbContract.currentText() != {} else None)
        strategyList = [a.split('_')[1] for a in self.names.keys() if 'self.s_' in a and self.names[a].isChecked()]

        produceList = product(acct,con,strategyList) if con != [''] else product(list(acct),strategyList)
        produceList = list(produceList)
        try:
            sum_sign = True if self.names['self.s_Sum'].isChecked() else False
            dateList, tempCapital, e = self.analysisEngine.calculateNetCurve(self.analysisEngine.sumNet(self.pathIter(produceList)),int(self.lineAmount.text()),sum_sign)
            self.on_draw(dateList, tempCapital)
            self.showMetrics(e)
            # print 'done!'
        except Exception as e:
            print e


if __name__ == '__main__':
    app = 0
    app = QtGui.QApplication(sys.argv)
    Dialog = QtGui.QDialog()
    ui = NetCurveManager()
    ui.setupUi(Dialog)
    ui.loadInitData()
    ui.triggerEvent()
    ui.on_draw()
    Dialog.show()
    sys.exit(app.exec_())