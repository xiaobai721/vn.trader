# encoding: UTF-8

"""
套利策略，尚未解决的问题：
1. 委托价格超出涨跌停价导致的委托失败
2. 断网交易状态恢复
3. 策略配置的自检代码
4. 根据tick数据的波动幅度对报价有效期进行调节，更进一步对单边报价有效期进行调节，当前调节过于频繁
5. 数据输入改为由数据记录引擎完成,排除在策略之外,需要先确定数据存储方式
"""


from ctaBase import *
from ctaTemplate import CtaTemplate
import numpy as np
import time
from datetime import datetime, timedelta

########################################################################
class CtaDummy(CtaTemplate):
    """套利策略Demo"""
    # className = 'CtaSingle'
    author = u'ly'
    
    # 策略参数
    # beta1 = 1         	# 标准差系数
    # beta2 = 3     		# 滑点系数
    # initMins = 150 		# 参数计算所需分钟线数
    # waitSeconds = 30 	# 参数计算所需分钟线数
    # waitHours = 1    # 参数计算所需分钟线数
    # slip = 10			# 滑点（可读取）
    # volume = 1          # 开仓量，当前设置保证一次追单成功
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'vtSymbol',
                 'cycle']     
    
    # 变量列表，保存了变量的名称 多数变量定义为实例变量，变量列表是否能正常访问不确定
    varList = ['inited',
               'trading']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(CtaDummy, self).__init__(ctaEngine, setting)

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略初始化')        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送"""
        pass

    #----------------------------------------------------------------------
    def onBar(self,data):
        """收到Bar推送"""
        pass

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送"""
        super(CtaDummy, self).onOrder(order)
        self.writeCtaLog(u'策略收到订单回报-----错误!')

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送"""
        super(CtaDummy, self).onTrade(trade)
        self.writeCtaLog(u'策略收到订单回报-----错误!')
