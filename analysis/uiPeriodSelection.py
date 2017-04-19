# encoding: UTF-8

'''
分析模块中的时间段选取组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *
import logging, os, sys
from datetime import datetime

class PeriodSelection(QtGui.QWidget):
    """周期选择"""

    def __init__(self, parent = None):
        # QtGui.QWidget.__init__(self)  # 调用父类初始化方法
        # self.__analysisEngine = analysisEngine
        super(PeriodSelection, self).__init__()
        self.initUi()
        # gridlayout = QtGui.QGridLayout()  # 创建布局组件

    def initUi(self):
        self.setWindowTitle('PeriodSelection')  # 设置窗口标题

        #设置组件
        labelStart = QtGui.QLabel(u'起始时间')
        labelEnd = QtGui.QLabel(u'终止时间')

        self.editStart = QtGui.QLineEdit()
        self.editEnd = QtGui.QLineEdit()

        buttonConfirm = QtGui.QPushButton(u'确认')
        buttonCancel = QtGui.QPushButton(u'取消')

        buttonConfirm.clicked.connect(self.confirm)
        buttonCancel.clicked.connect(self.close)

        # 设置布局
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget(buttonConfirm)
        buttonHBox.addWidget(buttonCancel)

        self.editStart.setMinimumWidth(200)

        grid = QtGui.QGridLayout()
        grid.addWidget(labelStart, 0, 0)
        grid.addWidget(labelEnd, 1, 0)
        grid.addWidget(self.editStart, 0, 1)
        grid.addWidget(self.editEnd, 1, 1)
        grid.addLayout(buttonHBox, 2, 0, 1, 2)
        self.setLayout(grid)

    def confirm(self):
        print 'OK'
        startdate = str(self.editStart.text())
        enddate = str(self.editEnd.text())

        self.close()

    def closeEvent(self, event):
        """关闭事件处理"""
        print 'Cancel'
        # event.accept()


def main():
    app = 0
    app = QtGui.QApplication(sys.argv)
    mywindow = PeriodSelection()
    mywindow.show()
    app.exec_()

if __name__ == '__main__':
    main()
