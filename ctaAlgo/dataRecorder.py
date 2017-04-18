# encoding: UTF-8

"""
套利策略，记录数据用
"""

from ctaBase import *
from ctaTemplate import CtaTemplate
import numpy as np
import time
from datetime import datetime, timedelta
import csv,os

class DataRecorder(CtaTemplate):
    """记录套利策略用数据"""
    className = 'DataRecorder'
    author = u'ly'
    
    # 策略的基本参数
    name = EMPTY_UNICODE            # 策略实例名称
    vtSymbol = EMPTY_STRING         # 交易的合约vt系统代码    
    
    # 策略的变量
    bar = None                      # K线数据对象 
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading']    

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DataRecorder, self).__init__(ctaEngine, setting)

        self.barMinute={}          # 本地记录合约登记时间

        for vts in self.vtSymbol :
            self.barMinute[vts]={}

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化"""
        self.writeCtaLog(u'数据记录工具初始化')
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'数据记录工具启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'数据记录工具停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送"""
        
        # 计算K线
        tickMinute = tick.datetime.minute
        
        if tick.vtSymbol in self.vtSymbol:
            if tickMinute != self.barMinute[tick.vtSymbol]:    # 如果分钟变了，则把旧的K线插入数据库，并生成新的K线
                self.insertBar(tick.vtSymbol,[time.mktime(tick.datetime.replace(second=0,microsecond=0).timetuple()),tick.lastPrice,tick.datetime,datetime.now()])
                self.barMinute[tick.vtSymbol] = tickMinute

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送"""
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送"""
        pass
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送"""
        pass