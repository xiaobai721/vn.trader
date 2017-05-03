# encoding: UTF-8

'''
分析模块中的时间段选取组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *
import logging, os, sys
from datetime import datetime
from analysis.uiQtNetCurve_bk import NetCurveManager

class EventSelection(QtGui.QWidget):
    """分析功能选择"""

    def __init__(self, mainEngine,analysisEngine,parent = None):
        # QtGui.QWidget.__init__(self)  # 调用父类初始化方法
        # self.__analysisEngine = analysisEngine
        super(EventSelection, self).__init__()
        self.mainEngine = mainEngine
        self.analysisEngine = analysisEngine
        self.initUi()
        self.widgetDict = {}  # 用来保存子窗口的字典


    def initUi(self):
        self.setWindowTitle('EventSelection')  # 设置窗口标题

        #设置组件

        self.buttonData = QtGui.QPushButton(u'数据统计')
        self.buttonNet = QtGui.QPushButton(u'净值分析')

        self.radioCurrData = QtGui.QRadioButton(u'当前数据统计')
        self.radioHisData = QtGui.QRadioButton(u'历史数据统计')
        self.radioCurrData.setChecked(True)

        self.buttonData.clicked.connect(self.data)
        self.buttonNet.clicked.connect(self.net)

        # 设置布局
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget(self.buttonData)
        buttonHBox.addWidget(self.buttonNet)

        # self.editStart.setMinimumWidth(200)

        grid = QtGui.QGridLayout()
        grid.addWidget(self.radioCurrData, 1, 2)
        grid.addWidget(self.radioHisData, 2, 2)
        # grid.addWidget(labelEnd, 1, 0)
        # grid.addWidget(self.editStart, 0, 1)
        # grid.addWidget(self.editEnd, 1, 1)
        grid.addLayout(buttonHBox, 0, 0, 1, 2)
        self.setLayout(grid)

    def data(self):
        # print 'data'
        LogFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\ctaLogFile\\temp'
        dirName = []
        for i in os.listdir(LogFile):
            if i[:8].isdigit():
                dirName.append(i)
        dirName.sort()
        for j in dirName:
            try:
                self.analysisEngine.loadLog(j)
                self.mainEngine.dbConnect()
                lastTickData = self.mainEngine.dbQuery('MTS_lastTick_DB',"20170331",None)
                self.analysisEngine.loadTradeHolding(lastTickData)

            except Exception, e:
                print e
                continue
        QtGui.QMessageBox.information(self, u'Information', u'基础数据分析完成!')

        self.close()

    def net(self):
        # print 'net'
        self.analysisEngine.backupHisPos()

        if self.radioCurrData.isChecked():
            sign = 'Curr'
        elif self.radioHisData.isChecked():
            sign = 'His'

        try:
            self.Dialog = QtGui.QDialog()
            self.widgetDict['netCurve'] = NetCurveManager(self.analysisEngine, self.Dialog, parent=self)
            self.Dialog.show()
        except Exception, e:
            print e

            # self.widgetDict['netCurve'].show()

        self.close()


def main():
    app = 0
    app = QtGui.QApplication(sys.argv)
    mywindow = EventSelection()
    mywindow.show()
    app.exec_()

if __name__ == '__main__':
    main()
