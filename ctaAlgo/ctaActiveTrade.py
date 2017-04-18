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
class CtaActiveTrade(CtaTemplate):
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
                 'cycle',
                 'Beta1',
                 'Beta3',
                 'Beta2',
                 'slip',
                 'stopTime',
                 'volume',
                 'breakTh',
                 'days']     
    
    # 变量列表，保存了变量的名称 多数变量定义为实例变量，变量列表是否能正常访问不确定
    varList = ['inited',
               'trading',
               'lossStop',
               'orderTracking']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(CtaActiveTrade, self).__init__(ctaEngine, setting)

        self.orderTracking = False
        self.tradeSignal = 0
        self.cSymbol = self.vtSymbol[-1]
        self.barUpdateTime = datetime.now()
        self.bullBearSign = 0

        self.startTime = datetime.now()
        self.openPrice = 0

        self.buyAccVolume = 0
        self.buyPriceChange = 0.0
        self.sellAccVolume = 0
        self.sellPriceChange = 0.0
        self.lossStop = 0.0
        self.targetStop = 0.0
        self.highPrice = 0.0
        self.lowPrice = 1000000.0

        self.closeAllSign = False

        self.waitTime = datetime.now()

        self.stopTime1 = datetime.strptime(self.stopTime[0],'%Y%m%d %H:%M:%S').replace(day=datetime.now().day,year=datetime.now().year,month=datetime.now().month)
        self.stopTime2 = datetime.strptime(self.stopTime[1],'%Y%m%d %H:%M:%S').replace(day=datetime.now().day,year=datetime.now().year,month=datetime.now().month)
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略初始化')        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略启动')
        self.orderTracking = False
        readData = self.tradeCacheLoad()
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略停止')
        writeData = {}
        self.tradeCacheSave(writeData)
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送"""
        
            
        # 非交易时间段暂停交易
        if (tick.datetime.hour > 15 and tick.datetime.hour < 20) or \
        (tick.datetime.hour > 1 and tick.datetime.hour < 8):
            self.trading = False
        else:
            # self.trading = True #######################自动交易功能，删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉————
            pass

        if self.startTime < tick.datetime - timedelta(minutes=2):
            self.startTime = tick.datetime
            self.openPrice = tick.lastPrice
            self.highPrice = tick.lastPrice
            self.lowPrice = tick.lastPrice

        if self.closeAllSign == False:
            if tick.datetime > self.stopTime1 and tick.datetime.hour < 16 and tick.datetime.hour > 8 :
                self.closeAll(self.Beta2)
                self.closeAllSign = True
                self.trading = False
            elif tick.datetime.hour > self.stopTime2.hour or (tick.datetime.hour == self.stopTime2.hour and tick.datetime.minute > self.stopTime2.minute) : 
                self.closeAll(self.Beta2)
                self.closeAllSign = True
                self.trading = False

        # else:
        #     self.closeAllSign = False
        #     print 2,self.closeAllSign

        if ((tick.datetime.hour >= 9 and tick.datetime.hour < 15) or \
        (tick.datetime.hour >= 21) or (tick.datetime.hour >= 0 and tick.datetime.hour < 1)) and self.trading == True:

            if self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime'] <= tick.datetime and self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime'] != self.barUpdateTime :

                if isinstance(self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['data'].barData,(int,float)):
                    return

                dataTemp = self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['data'].barData
                self.onBar(dataTemp)
                self.barUpdateTime = self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime']

            self.tradeSignal = 0
            # 交易信号生成
            if self.startTime <= tick.datetime - timedelta(minutes=1):
                # dataTemp = self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['data'].barData[-1-self.Nf:,:]
                if tick.datetime >= self.waitTime :
                    if self.buyAccVolume > self.sellAccVolume and tick.lastPrice > self.openPrice and abs((tick.lastPrice-self.openPrice)>(self.highPrice-self.lowPrice))*self.breakTh and \
                    self.bullBearSign == 1:
                        self.tradeSignal = 1
                    elif self.buyAccVolume < self.sellAccVolume and tick.lastPrice < self.openPrice and abs((tick.lastPrice-self.openPrice)>(self.highPrice-self.lowPrice))*self.breakTh and \
                    self.bullBearSign == -1:
                        self.tradeSignal = -1
                    # elif self.buyAccVolume < self.sellAccVolume and tick.lastPrice > self.openPrice and abs((tick.lastPrice-self.openPrice)>(self.highPrice-self.lowPrice))*self.breakTh and self.bullBearSign == 1:
                    #     self.tradeSignal = 1
                    # elif self.buyAccVolume > self.sellAccVolume and tick.lastPrice < self.openPrice and abs((tick.lastPrice-self.openPrice)>(self.highPrice-self.lowPrice))*self.breakTh and self.bullBearSign == -1:
                    #     self.tradeSignal = -1
                    else:
                        pass

                self.openPrice = tick.lastPrice
                self.highPrice = tick.lastPrice
                self.lowPrice = tick.lastPrice
                self.startTime = tick.datetime
                self.buyAccVolume = tick.volume
                self.sellAccVolume = tick.volume

            elif self.tickData[tick.vtSymbol]['lastPrice'] != EMPTY_FLOAT:
                if tick.lastPrice <= self.tickData[tick.vtSymbol]['bidPrice1']:
                    self.sellAccVolume = self.sellAccVolume+tick.volume
                elif tick.lastPrice >= self.tickData[tick.vtSymbol]['askPrice1']:
                    self.buyAccVolume = self.buyAccVolume+tick.volume
                else:
                    pass
                self.highPrice = max([tick.lastPrice,self.highPrice])
                self.lowPrice = max([tick.lastPrice,self.lowPrice])

            # 交易执行部分
            if self.orderTracking == False:
                if self.Status[self.cSymbol]['pos'] == 0:
                    if self.tradeSignal == 1:
                        self.Status[self.cSymbol]['orderId'] = self.buy(tick.lastPrice + self.slip, self.volume, self.cSymbol)
                        self.lossStop = tick.lastPrice - self.Beta1*self.slip
                        self.targetStop = tick.lastPrice + self.Beta3*self.slip
                        self.orderTracking = True
                    elif self.tradeSignal == -1:
                        self.Status[self.cSymbol]['orderId'] = self.short(tick.lastPrice - self.slip, self.volume, self.cSymbol)
                        self.lossStop = tick.lastPrice + self.Beta1*self.slip
                        self.targetStop = tick.lastPrice - self.Beta3*self.slip
                        self.orderTracking = True

                elif self.Status[self.cSymbol]['pos'] > 0:
                    if self.tradeSignal == -1:
                        self.Status[self.cSymbol]['orderId'] = self.sell(tick.lastPrice - self.slip, self.volume, self.cSymbol)
                        self.Status[self.cSymbol]['orderId'] = self.short(tick.lastPrice - self.slip, self.volume, self.cSymbol)
                        self.lossStop = tick.lastPrice + self.Beta1*self.slip
                        self.targetStop = tick.lastPrice - self.Beta3*self.slip
                        self.orderTracking = True
                    else:
                        if tick.lastPrice < self.lossStop :
                            self.Status[self.vtSymbol[0]]['orderId'] = self.sell(tick.lastPrice - self.slip, self.volume, self.cSymbol)
                            self.orderTracking = True
                        elif tick.lastPrice > self.targetStop :
                            self.Status[self.vtSymbol[0]]['orderId'] = self.sell(tick.lastPrice - self.slip, self.volume, self.cSymbol)
                            self.waitTime = tick.datetime + timedelta(minutes=1)
                            self.orderTracking = True

                elif self.Status[self.cSymbol]['pos'] < 0:
                    if self.tradeSignal == 1:
                        self.Status[self.cSymbol]['orderId'] = self.cover(tick.lastPrice + self.slip, self.volume, self.cSymbol)
                        self.Status[self.cSymbol]['orderId'] = self.buy(tick.lastPrice + self.slip, self.volume, self.cSymbol)
                        self.lossStop = tick.lastPrice - self.Beta1*self.slip
                        self.targetStop = tick.lastPrice + self.Beta3*self.slip
                        self.orderTracking = True
                    else:
                        if tick.lastPrice > self.lossStop :
                            self.Status[self.vtSymbol[0]]['orderId'] = self.cover(tick.lastPrice + self.slip, self.volume, self.cSymbol)
                            self.orderTracking = True
                        elif tick.lastPrice < self.targetStop :
                            self.Status[self.vtSymbol[0]]['orderId'] = self.cover(tick.lastPrice + self.slip, self.volume, self.cSymbol)
                            self.waitTime = tick.datetime + timedelta(minutes=1)
                            self.orderTracking = True

        if tick.vtSymbol in self.vtSymbol:
            self.tickData[tick.vtSymbol]['lastPrice']=tick.lastPrice
            self.tickData[tick.vtSymbol]['bidPrice1']=tick.bidPrice1
            self.tickData[tick.vtSymbol]['askPrice1']=tick.askPrice1
        # 发出状态更新事件
        self.putEvent()
    #----------------------------------------------------------------------
    def onBar(self,data):
        """收到Bar推送"""
        # 长周期30分钟线的20周期均线判断方向、规避强势影响
        data = np.array(data)
        cTemp = data[:,4]
        N = min([len(cTemp),20])
        if cTemp[-1] > sum(cTemp[len(cTemp)-N:])/len(cTemp[len(cTemp)-N:]):
            self.bullBearSign = 1
        elif cTemp[-1] < sum(cTemp[len(cTemp)-N:])/len(cTemp[len(cTemp)-N:]):
            self.bullBearSign = -1
        else:
            self.bullBearSign = 0

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送"""
        super(CtaActiveTrade, self).onOrder(order)

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送"""
        super(CtaActiveTrade, self).onTrade(trade)
        self.orderTracking = False
