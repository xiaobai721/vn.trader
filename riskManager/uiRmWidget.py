# encoding: UTF-8

'''
风控模块相关的GUI控制组件
'''


from uiBasicWidget import QtGui, QtCore
from eventEngine import *


########################################################################
# class RmSpinBox(QtGui.QSpinBox):
#     """调整参数用的数值框"""
#
#     #----------------------------------------------------------------------
#     def __init__(self, value):
#         """Constructor"""
#         super(RmSpinBox, self).__init__()
#
#         # self.setMinimum(0)
#         # self.setMaximum(1000000)
#
#         self.setValue(value)
#
#
#

########################################################################
class RmLine(QtGui.QFrame):
    """水平分割线"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        super(RmLine, self).__init__()
        self.setFrameShape(self.HLine)
        self.setFrameShadow(self.Sunken)
    
    
  

########################################################################
class RmEngineManager(QtGui.QWidget):
    """风控引擎的管理组件"""

    #----------------------------------------------------------------------
    def __init__(self, rmEngine, eventEngine, parent=None):
        """Constructor"""
        super(RmEngineManager, self).__init__(parent)
        
        self.rmEngine = rmEngine
        self.eventEngine = eventEngine
        
        self.initUi()
        self.updateEngineStatus()

    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'风险管理')
        
        # 设置界面
        self.buttonSwitchEngineStatus = QtGui.QPushButton(u'风控模块未启动')

        # self.spinaccountMarginRatio = RmSpinBox(self.rmEngine.accountMarginRatio)
        # self.spintradeCountLimit = RmSpinBox(self.rmEngine.tradeCountLimit)
        # self.spinstrategyInstanceOpenLimit = RmSpinBox(self.rmEngine.strategyInstanceOpenLimit)
        # self.spinstrategyInstancePositionLimit = RmSpinBox(self.rmEngine.strategyInstancePositionLimit)
        # self.spincontractPositionLimit = RmSpinBox(self.rmEngine.contractPositionLimit)
        
        # buttonClearOrderFlowCount = QtGui.QPushButton(u'清空流控计数')
        # buttonClearTradeCount = QtGui.QPushButton(u'清空累计交易计数')
        # buttonSaveSetting = QtGui.QPushButton(u'保存设置')
        
        # Label = QtGui.QLabel
        # grid = QtGui.QGridLayout()
        # grid.addWidget(Label(u'工作状态'), 0, 0)
        # grid.addWidget(self.buttonSwitchEngineStatus, 0, 1)
        # grid.addWidget(RmLine(), 1, 0, 1, 2)
        # grid.addWidget(Label(u'账户保证金比例上限'), 2, 0)
        # grid.addWidget(self.spinaccountMarginRatio, 2, 1)
        # # grid.addWidget(Label(u'流控清空（秒）'), 3, 0)
        # # grid.addWidget(self.spinOrderFlowClear, 3, 1)
        # grid.addWidget(RmLine(), 3, 0, 1, 2)
        # grid.addWidget(Label(u'单日累计交易次数上限'), 4, 0)
        # grid.addWidget(self.spintradeCountLimit, 4, 1)
        # grid.addWidget(RmLine(), 5, 0, 1, 2)
        # grid.addWidget(Label(u'单策略实例开仓上限'), 6, 0)
        # grid.addWidget(self.spinstrategyInstanceOpenLimit, 6, 1)
        # grid.addWidget(RmLine(), 7, 0, 1, 2)
        # grid.addWidget(Label(u'单策略实例持仓上限'), 8, 0)
        # grid.addWidget(self.spinstrategyInstancePositionLimit, 8, 1)
        
        # hbox = QtGui.QHBoxLayout()
        # hbox.addWidget(buttonSwitchEngineStatus)
        # hbox.addWidget(buttonClearTradeCount)
        # hbox.addStretch()
        # hbox.addWidget(buttonSaveSetting)
        
        # vbox = QtGui.QVBoxLayout()
        # vbox.addLayout(grid)
        # vbox.addLayout(hbox)
        # self.setLayout(vbox)
        
        # # 连接组件信号
        # self.spinaccountMarginRatio.valueChanged.connect(self.rmEngine.setAccountMarginRatio)
        # self.spintradeCountLimit.valueChanged.connect(self.rmEngine.setTradeCountLimit)
        # self.spinstrategyInstanceOpenLimit.valueChanged.connect(self.rmEngine.setStrategyInstanceOpenLimit)
        # self.spinstrategyInstancePositionLimit.valueChanged.connect(self.rmEngine.setStrategyInstancePositionLimit)
        # self.spincontractPositionLimit.valueChanged.connect(self.rmEngine.setContractPositionLimit)
        #
        self.buttonSwitchEngineStatus.clicked.connect(self.switchEngineStatus)
        # buttonClearOrderFlowCount.clicked.connect(self.rmEngine.clearOrderFlowCount)
        # buttonClearTradeCount.clicked.connect(self.rmEngine.clearTradeCount)
        # buttonSaveSetting.clicked.connect(self.rmEngine.saveSetting)
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget( self.buttonSwitchEngineStatus)
        grid = QtGui.QGridLayout()
        grid.addLayout(buttonHBox, 0, 0, 1, 1)
        self.setLayout(grid)

        # 设为固定大小
        self.setFixedSize(self.sizeHint())
        
    #----------------------------------------------------------------------
    def switchEngineStatus(self):
        """控制风控引擎开关"""
        self.rmEngine.switchEngineStatus()
        self.updateEngineStatus()
        
    #----------------------------------------------------------------------
    def updateEngineStatus(self):
        """更新引擎状态"""
        if self.rmEngine.active:
            self.buttonSwitchEngineStatus.setText(u'风控模块运行中')
        else:
            self.buttonSwitchEngineStatus.setText(u'风控模块未启动')
 
    