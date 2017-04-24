# encoding: UTF-8

'''
本文件中实现了风控引擎，用于提供一系列常用的风控功能：
1. 委托流控（单位时间内最大允许发出的委托数量）
2. 总成交限制（每日总成交数量限制）
3. 单笔委托的委托数量控制
'''

import json
import os
import platform

from eventEngine import *
from vtConstant import *
from vtGateway import VtLogData


########################################################################
class RmEngine(object):
    """风控引擎"""
    settingFileName = 'RM_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)    
    
    name = u'风控模块'

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 是否启动风控
        self.active = False
        # 账户保证金比例
        self.accountMarginRatio = EMPTY_FLOAT
        self.contractMarginRatio = EMPTY_FLOAT
        # 单日累计交易次数
        self.tradeCountLimit = EMPTY_INT
        # 单策略
        self.strategyInstanceOpenLimit = EMPTY_INT
        self.strategyInstancePositionLimit = EMPTY_INT
        # 单标的
        self.contractPositionLimit = EMPTY_INT

        self.loadSetting()
        self.registerEvent()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取配置"""
        with open(self.settingFileName) as f:
            d = json.load(f)
            
            # 设置风控参数
            self.active = d['active']
            
            self.accountMarginRatio = d['accountMarginRatio']
            self.contractMarginRatio = d['contractMarginRatio']
            
            self.tradeCountLimit = d['tradeCountLimit']
            
            self.strategyInstanceOpenLimit = d['strategyInstanceOpenLimit']
            self.strategyInstancePositionLimit = d['strategyInstancePositionLimit']
            
            self.contractPositionLimit = d['contractPositionLimit']
        
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存风控参数"""
        with open(self.settingFileName, 'w') as f:
            # 保存风控参数
            d = {}

            d['active'] = self.active
            
            d['accountMarginRatio'] = self.accountMarginRatio
            d['contractMarginRatio'] = self.contractMarginRatio
            
            d['tradeCountLimit'] = self.tradeCountLimit
            
            d['strategyInstanceOpenLimit'] = self.strategyInstanceOpenLimit
            d['strategyInstancePositionLimit'] = self.strategyInstancePositionLimit

            d['contractPositionLimit'] = self.contractPositionLimit
            
            # 写入json
            jsonD = json.dumps(d, indent=4)
            f.write(jsonD)
        
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TRADE, self.updateTrade)
        # self.eventEngine.register(EVENT_TIMER, self.updateTimer)
        self.eventEngine.register(EVENT_TRADE, self.qryOpenCount)
        self.eventEngine.register(EVENT_POSITION, self.qryPosition)
        self.eventEngine.register(EVENT_ACCOUNT, self.qryMargin)

    #----------------------------------------------------------------------
    def updateTrade(self, event):
        """更新成交数据"""
        trade = event.dict_['data']
        self.tradeCount += trade.volume

    # ----------------------------------------------------------------------
    def qryMargin(self,event):
        """查询单账户保证金比例"""
        marginRatio = event.dict_['data']
        self.acctMarginRatio = marginRatio.margin

    #----------------------------------------------------------------------
    def qryPosition(self,event):
        """查询单策略实例累计持仓"""
        siPositionLimit = event.dict_['data']
        self.siPositionLimit = siPositionLimit.position

    # ---------------------------------------------------------------------
    def qryOpenCount(self,event):
        """查询单策略实例开仓"""
        siOpenCount = event.dict_['data']
        if siOpenCount.offset == u'开仓':
            self.siOpenLimit += siOpenCount
    # ---------------------------------------------------------------------

    # def updateTimer(self, event):
    #     """更新定时器"""
    #     self.orderFlowTimer += 1
    #
    #     # 如果计时超过了流控清空的时间间隔，则执行清空
    #     if self.orderFlowTimer >= self.orderFlowClear:
    #         self.orderFlowCount = 0
    #         self.orderFlowTimer = 0
        
    #----------------------------------------------------------------------
    def writeRiskLog(self, content):
        """快速发出日志事件"""
        # 发出报警提示音

        if platform.uname() == 'Windows':
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ASYNC) 
        
        # 发出日志事件
        log = VtLogData()
        log.logContent = content
        log.gatewayName = self.name
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)      
    
    #----------------------------------------------------------------------
    def checkRisk(self, orderReq):
        """检查风险"""
        # 如果没有启动风控检查，则直接返回成功
        if not self.active:
            return True

        # 检查单策略实例单次开仓限制
        if self.siOpenLimit > self.strategyInstanceOpenLimit:
            self.writeRiskLog(u'单策略实例单次开仓数量%s，超过限制%s'
                             %(self.siOpenLimit, self.strategyInstanceOpenLimit))
            return False

        # 检查单策略累计持仓限制
        if self.siPositionLimit > self.strategyInstancePositionLimit:
            self.writeRiskLog(u'单策略实例累计持仓%s，超过限制%s'
                              % (self.siPositionLimit, self.strategyInstancePositionLimit))
            return False

        # # 检查单标的合约累计持仓限制
        # if self.contract.position > self.contractPositionLimit:
        #     self.writeRiskLog(u'单标的合约累计持仓%s, 超过限制%s'
        #                       %(self.contract.position, self.contractPositionLimit))
        #     return False

        # 检查单账户保证金比例限制
        if self.acctMarginRatio > self.accountMarginRatio:
            self.writeRiskLog(u'单账户保证金比例限制%s, 超过持仓%s'
                              %(self.acctMarginRatio, self.accountMarginRatio))
            return False

        # 对单日累计交易次数的提示
        if self.tradeCount > self.tradeCountLimit:
            self.writeRiskLog(u'单日累计交易次数%s, 超过限制%s'
                              %(self.tradeCount, self.tradeCountLimit))
            return True


        # # 检查委托数量
        # if orderReq.volume > self.orderSizeLimit:
        #     self.writeRiskLog(u'单笔委托数量%s，超过限制%s'
        #                       %(orderReq.volume, self.orderSizeLimit))
        #     return False
        #
        # # 检查成交合约量
        # if self.tradeCount >= self.tradeLimit:
        #     self.writeRiskLog(u'今日总成交合约数量%s，超过限制%s'
        #                       %(self.tradeCount, self.tradeLimit))
        #     return False
        #
        # # 检查流控
        # if self.orderFlowCount >= self.orderFlowLimit:
        #     self.writeRiskLog(u'委托流数量%s，超过限制每%s秒%s'
        #                       %(self.orderFlowCount, self.orderFlowClear, self.orderFlowLimit))
        #     return False
        #
        # # 检查总活动合约
        # workingOrderCount = len(self.mainEngine.getAllWorkingOrders())
        # if workingOrderCount >= self.workingOrderLimit:
        #     self.writeRiskLog(u'当前活动委托数量%s，超过限制%s'
        #                       %(workingOrderCount, self.workingOrderLimit))
        #     return False
        #
        # # 对于通过风控的委托，增加流控计数
        # self.orderFlowCount += 1
        
        return True    
    
    #----------------------------------------------------------------------
    # def clearOrderFlowCount(self):
    #     """清空流控计数"""
    #     self.orderFlowCount = 0
    #     self.writeRiskLog(u'清空流控计数')
        
    #----------------------------------------------------------------------
    def clearTradeCount(self):
        """清空成交数量计数"""
        self.tradeCount = 0
        self.writeRiskLog(u'清空累计交易计数')
        
    #----------------------------------------------------------------------
    def setAccountMarginRatio(self, n):
        """设置账户保证金限制"""
        self.accountMarginRatio = n
        
    #----------------------------------------------------------------------
    def setStrategyInstanceOpenLimit(self, n):
        """设置流控清空时间"""
        self.strategyInstanceOpenLimit = n
        
    #----------------------------------------------------------------------
    def setStrategyInstancePositionLimit(self, n):
        """设置委托最大限制"""
        self.strategyInstancePositionLimit = n
        
    #----------------------------------------------------------------------
    def setTradeCountLimit(self, n):
        """设置成交限制"""
        self.tradeCountLimit = n
        
    #----------------------------------------------------------------------
    def setContractPositionLimit(self, n):
        """设置活动合约限制"""
        self.contractPositionLimit = n
        
    #----------------------------------------------------------------------
    def switchEngineStatus(self):
        """开关风控引擎"""
        self.active = not self.active
        
        if self.active:
            self.writeRiskLog(u'风险管理功能启动')
        else:
            self.writeRiskLog(u'风险管理功能停止')
