# encoding: UTF-8

'''
分析模块中的时间段选取组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *
import logging, os, sys
from datetime import datetime
from analysis.uiNetCurve import NetCurveManager

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
        # labelStart = QtGui.QLabel(u'起始时间')
        # labelEnd = QtGui.QLabel(u'终止时间')
        #
        # self.editStart = QtGui.QLineEdit()
        # self.editEnd = QtGui.QLineEdit()

        buttonData = QtGui.QPushButton(u'数据统计')
        buttonNet = QtGui.QPushButton(u'净值分析')

        buttonData.clicked.connect(self.data)
        buttonNet.clicked.connect(self.net)

        # 设置布局
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget(buttonData)
        buttonHBox.addWidget(buttonNet)

        # self.editStart.setMinimumWidth(200)

        grid = QtGui.QGridLayout()
        # grid.addWidget(labelStart, 0, 0)
        # grid.addWidget(labelEnd, 1, 0)
        # grid.addWidget(self.editStart, 0, 1)
        # grid.addWidget(self.editEnd, 1, 1)
        grid.addLayout(buttonHBox, 0, 0, 1, 2)
        self.setLayout(grid)

    def data(self):
        print 'data'
        LogFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\ctaLogFile\\temp'
        dirName = []
        try:
            for i in os.listdir(LogFile):
                # i = i[:8]
                if i[:8].isdigit():
                    dirName.append(i)
            dirName.sort()
            for j in dirName:
                self.analysisEngine.loadLog(j)
                self.mainEngine.dbConnect()
                lastTickData = self.mainEngine.dbQuery('MTS_lastTick_DB',"20170331",None)
                self.analysisEngine.loadTradeHolding(lastTickData)
            QtGui.QMessageBox.information(self, u'Information', u'基础数据分析完成!')
        except Exception, e:
            print e

        self.close()

    def net(self):
        print 'net'
        try:
            self.widgetDict['netCurve'].showMaximized()
        except KeyError:
            self.widgetDict['netCurve'] = NetCurveManager(self.analysisEngine)
            self.widgetDict['netCurve'].showMaximized()

        self.close()
        # event.accept()


def main():
    app = 0
    app = QtGui.QApplication(sys.argv)
    mywindow = EventSelection()
    mywindow.show()
    app.exec_()

if __name__ == '__main__':
    main()
