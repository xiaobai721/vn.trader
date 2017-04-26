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
        self.active = AutoValidation()
        # 账户保证金比例
        self.accountMarginRatio = AutoValidation()
        self.acctMarginRatio = AutoValidation()
        # 单日累计交易次数
        self.tradeCountLimit = AutoValidation()
        self.tradeCount = AutoValidation()
        # 存储orderID
        self.orderList = AutoValidation()
        # 单标的持仓信息
        self.posDict = AutoValidation()
        self.contractPositionLimit =  AutoValidation()


        self.loadSetting()
        self.registerEvent()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取配置"""
        with open(self.settingFileName) as f:
            d = json.load(f)
            for i in d.keys():
                # 设置风控参数
                self.active[i] = d[i]['active']

                self.accountMarginRatio[i] = d[i]['accountMarginRatio']

                self.tradeCountLimit[i] = d[i]['tradeCountLimit']

                self.contractPositionLimit[i]['long'] = d[i]['contractPositionLimit']['long']
                self.contractPositionLimit[i]['short'] = d[i]['contractPositionLimit']['short']

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TRADE, self.updateTrade)
        self.eventEngine.register(EVENT_POSITION, self.qryPosition)
        self.eventEngine.register(EVENT_ACCOUNT, self.qryMargin)

    #----------------------------------------------------------------------
    def updateTrade(self, event):
        """更新成交次数数据"""
        trade = event.dict_['data']
        orderId = trade.vtOrderID
        self.orderList[trade.accountID].append(orderId)
        self.tradeCount  = len(set(self.orderList[trade.accountID]))

    # ----------------------------------------------------------------------
    def qryMargin(self,event):
        """查询单账户保证金比例"""
        margin = event.dict_['data']
        if margin.balance != 0:
            self.acctMarginRatio[margin.accountID] = float(margin.margin/margin.balance)
        else:
            self.acctMarginRatio[margin.accountID] = 0

    #----------------------------------------------------------------------
    def qryPosition(self,event):
        """查询单标的合约实例累计持仓"""
        pos= event.dict_['data']
        if pos.direction == DIRECTION_LONG:
            self.posDict[pos.accountID][pos.vtSymbol]['Long'] = pos.position
        elif pos.direction == DIRECTION_SHORT:
            self.posDict[pos.accountID][pos.vtSymbol]['Short'] = pos.position



    # ---------------------------------------------------------------------
    # def qryOpenCount(self,event):
    #     """查询单策略实例开仓"""
    #     siOpenCount = event.dict_['data']
    #     if siOpenCount.offset == u'开仓':
    #         self.siOpenLimit += siOpenCount
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
    def checkRisk(self, orderReq, accountName):
        """检查风险"""
        accountName = orderReq.accountID
        # 如果没有启动风控检查，则直接返回成功
        if not self.active[accountName]:
            return True

        # 检查单账户保证金比例限制
        if self.acctMarginRatio[accountName] >= self.accountMarginRatio[accountName]:
            self.writeRiskLog(u'账户保证金比例限制%s, 超过持仓%s'
                              %(self.acctMarginRatio, self.accountMarginRatio[accountName]))
            return False

        # 对单日累计交易次数的提示
        if self.tradeCount[accountName] >= self.tradeCountLimit[accountName]:
            self.writeRiskLog(u'单日累计交易次数%s, 超过限制%s'
                              %(self.tradeCount, self.tradeCountLimit[accountName]))


        # 单标的合约实例累计持仓的限制
        direction = EMPTY_STRING
        if orderReq.direction == DIRECTION_LONG:
            direction = 'long'
        elif orderReq.direction == DIRECTION_SHORT:
            direction = 'short'
        else:
            pass

        if self.posDict[accountName][orderReq.vtSymbol][direction] != {} and self.posDict[accountName][orderReq.vtSymbol][direction] >= self.contractPositionLimit[accountName][direction]:
            self.writeRiskLog(u'标的合约累计交易次数%s, 超过限制%s'
                            %(self.posDict[accountName][orderReq.vtSymbol][orderReq.direction], self.contractPositionLimit[accountName][direction]))
            return False


        return True
    #----------------------------------------------------------------------
    def switchEngineStatus(self):
        """开关风控引擎"""
        self.active = not self.active
        
        if self.active:
            self.writeRiskLog(u'风险管理功能启动')
        else:
            self.writeRiskLog(u'风险管理功能停止')


class AutoValidation(dict):
    """Implementation of perl's AutoValidation feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
