# encoding: UTF-8

'''
分析模块中的净值显示组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *
import logging, os, sys
from datetime import datetime
import collections
from operator import itemgetter
from itertools import groupby

class NetCurveManager(QtGui.QWidget):
    def __init__(self,analysisEngine):          # 初始化方法
        QtGui.QWidget.__init__(self)      # 调用父类初始化方法
        self.setWindowTitle('NetCurve')       # 设置窗口标题
        self.path = os.getcwd() + '/ctaLogFile/ctaPosFile'
        # self.path = os.getcwd() + '/statement/netSource'
        self.analysisEngine = analysisEngine
#        self.resize(300,200)        # 设置窗口大小
        gridlayout = QtGui.QGridLayout()     # 创建布局组件

        self.cbAccount = QtGui.QComboBox()
        self.cbContract = QtGui.QComboBox()
        self.buttonStart = QtGui.QPushButton()
        self.lineedit = QtGui.QLineEdit('1000000')

        self.labelAcct = QtGui.QLabel(u'账户')
        self.labelCon = QtGui.QLabel(u'标的')
        self.labelAmount = QtGui.QLabel(u'初始金额')
        self.labelEvaluate = QtGui.QLabel()

        tree = lambda: collections.defaultdict(tree)
        self.dataList = tree()
        self.fileName = []

        self.loadAllPosFile()
        self.cbAccount.addItems([k for k in self.groupByPosFile('name').keys()])
        self.cbContract.addItems([k for k in self.groupByPosFile('contract').keys()])
#         self.checkList = checkboxList(self.path,self.analysisEngine)
#         self.showList = showList()
# #        self.checkList.setMinimumSize(600, 1000)
#
#         scroll1 = QtGui.QScrollArea()
#         scroll1.setWidget(self.checkList)
#         scroll1.setAutoFillBackground(True)
#         scroll1.setWidgetResizable(True)
#
#         scroll2 = QtGui.QScrollArea()
#         scroll2.setWidget(self.showList)
#         scroll2.setAutoFillBackground(True)
#         scroll2.setWidgetResizable(True)
#
#         button_GenList = QtGui.QPushButton('GenList')   # 创建按钮
#         gridlayout.addWidget(button_GenList, 1, 1, 1, 2)
#         button_choosePath = QtGui.QPushButton('choosePath')   # 创建按钮
#         gridlayout.addWidget(button_choosePath, 2, 1, 1, 2)
#
#         button_initCheckBoxList = QtGui.QPushButton('initCheckBoxList')   # 创建按钮
#         gridlayout.addWidget(button_initCheckBoxList, 3, 1, 1, 2)
#
#         button_GenCurve = QtGui.QPushButton('GenCurve')   # 创建按钮
#         gridlayout.addWidget(button_GenCurve, 1, 3, 1, 2)
#
#         self.lineedit = QtGui.QLineEdit()
#         self.lineedit.setText('1000000')
#         gridlayout.addWidget(self.lineedit, 2, 3, 1, 2)
#
#         gridlayout.addWidget(scroll2,4,3,10,2)
#
#         gridlayout.addWidget(scroll1,4,1,10,2)
#
#
#         self.setLayout(gridlayout)       # 向窗口中添加布局组件
#
#         self.connect(button_GenList,        # 按钮事件
#             QtCore.SIGNAL('clicked()'),
#             self.OnButton_GenList)
#
#         self.connect(button_choosePath,        # 按钮事件
#             QtCore.SIGNAL('clicked()'),
#             self.OnButton_choosePath)
#
#         self.connect(button_GenCurve,        # 按钮事件
#             QtCore.SIGNAL('clicked()'),
#             self.OnButton_GenCurve)
#
#         self.connect(button_initCheckBoxList,        # 按钮事件
#             QtCore.SIGNAL('clicked()'),
#             self.OnButton_initCheckBoxList)
#
#         self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
    # ----------------------------------------------------------------------
    def loadAllPosFile(self):
        for i in os.walk(self.ctaCurrPosFile):
            if len(i[-1]) > 0 and 'txt' in i[-1][0]:
                for j in i[-1] :
                    self.dataList['name'] = j
                    self.dataList['account'] = j.split('_',1)[0]
                    self.dataList['strategy'] = j.split('_',2)[1]
                    self.dataList['contract'] = j.split('_',2)[2][:-4]
                    self.fileName.append(self.dataList)

    # ----------------------------------------------------------------------
    def groupByPosFile(self,field):

        try:
            return  dict([(g, list(k)) for g, k in groupby(self.fileName, key=lambda x: x[field])])
        except Exception as e:
            print e
            return []

    # ----------------------------------------------------------------------
#     def OnButton_GenList(self):          # 生成list
#         self.pathList = []
#         self.showList.clearList()
#         for key in self.checkList.checkboxDict.keys():
#             if self.checkList.checkboxDict[key].isChecked():
#                 self.pathList.append(str(key))
# #                print self.checkList.checkboxDict[key]
#                 self.showList.updateList(str(key))
#
#     # ----------------------------------------------------------------------
#     def OnButton_GenCurve(self):          # 生成曲线
#         try:
#             e = self.analysisEngine.calculateNetCurve(self.analysisEngine.sumNet(self.pathList),int(self.lineedit.text()))
#
#             self.showList.updateList('')
#             # uiResult = showResult()
#             for k in e.keys():
#                 self.showList.updateList(k+':'+str(e[k]))
#             # uiResult.show()
#
#         except Exception as e:
#             print e
#
#     # ----------------------------------------------------------------------
#     def OnButton_initCheckBoxList(self):          # 初始化list
#         self.checkList.initUI(self.path)
#
#     def OnButton_choosePath(self):          # 选择路径
#         self.path = QtGui.QFileDialog.getExistingDirectory().replace('\\','/')
#         print self.path
#         if hasattr(self.checkList, 'gridlayout'):
#             self.checkList.gridlayout.destroyed()
#
#         # self.checkList.initUI(self.path)
#
# class checkboxList(QtGui.QWidget):
#     def __init__(self,path,analysisEngine):
#         QtGui.QWidget.__init__(self)
#         self.setWindowTitle('checkList')       # 设置窗口标题
#         self.analysisEngine = analysisEngine
#         self.gridlayout = QtGui.QGridLayout()
#
#         # self.initUI(path)
#     def initUI(self,path):
#         pathList = self.analysisEngine.pathIter(path)
#         self.checkboxDict = {}
#         self.gridlayout.update()
#         self.gridlayout.layout()
#         for i in range(len(pathList)):
#             self.checkboxDict[pathList[i]] = QtGui.QCheckBox(str(pathList[i]))
#             self.gridlayout.addWidget(self.checkboxDict[pathList[i]], i+3, 1)
#         # for i in range(10000):
#             # self.checkboxDict[i] = QtGui.QCheckBox('check '+str(i))
#             # self.gridlayout.addWidget(self.checkboxDict[i], i+3, 1)
#         self.setLayout(self.gridlayout)       # 向窗口中添加布局组件
#         self.gridlayout.update()
#
# class showList(QtGui.QWidget):
#     def __init__(self):
#         QtGui.QWidget.__init__(self)
#         self.setWindowTitle('showList')       # 设置窗口标题
#         self.initUI()
#     def initUI(self):
#         # CTA组件的日志监控
#         self.ctaLogMonitor = QtGui.QTextEdit()
#         self.ctaLogMonitor.setReadOnly(True)
#         self.gridlayout = QtGui.QGridLayout()
#         self.gridlayout.addWidget(self.ctaLogMonitor)
#         self.setLayout(self.gridlayout)       # 向窗口中添加布局组件
#     def updateList(self,rows):
#         self.ctaLogMonitor.append(rows)
#     def clearList(self):
#         self.ctaLogMonitor.clear()
#
# class showResult(QtGui.QWidget):
#     def __init__(self):
#         QtGui.QWidget.__init__(self)
#         self.setWindowTitle('showResult')       # 设置窗口标题
#         self.initUI()
#     def initUI(self):
#         # CTA组件的日志监控
#         self.ctaLogMonitor = QtGui.QTextEdit()
#         self.ctaLogMonitor.setReadOnly(True)
#         self.gridlayout = QtGui.QGridLayout()
#         self.gridlayout.addWidget(self.ctaLogMonitor)
#         self.setLayout(self.gridlayout)       # 向窗口中添加布局组件
#     def updateList(self,rows):
#         self.ctaLogMonitor.append(rows)
#     def clearList(self):
#         self.ctaLogMonitor.clear()
#
#
# if __name__ == '__main__':
#     app = 0
#     app = QtGui.QApplication(sys.argv)
#     # checkList = showList()
#     # checkList.show()
# #    checkList.updateList(str(1111))
# #     mywindow = MyWindow()
# #     mywindow.show()
#     app.exec_()