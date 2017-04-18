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
class CtaGap(CtaTemplate):
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
                 'author',
                 'vtSymbol',
                 'cycle',
                 'hisDadaLen',
                 'slip',
                 'breakTh',
                 'Nf',
                 'days',
                 'volume',
                 'trBeta',
                 'lossTh']     
    
    # 变量列表，保存了变量的名称 多数变量定义为实例变量，变量列表是否能正常访问不确定
    varList = ['inited',
               'trading',
               'orderType',
               'lossStop',
               'bestPrice',
               'orderTracking',
               'position']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(CtaGap, self).__init__(ctaEngine, setting)

        self.barUpdateTime = datetime.now()
        self.orderType = 0
        self.tradeSignal = 0
        self.lossStop = 0
        self.bestPrice = 0

        # 引入dr引擎部分
        # 策略变量
        # 参数实验
        self.orderTracking = False
        self.position = 0

        # for vts in self.vtSymbol :
        #     self.Status[vts]['orderTime']=datetime.now()

        # self.lastOrder = None
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略初始化:读取历史'+str(self.cycle)+u'分钟数据')
        
        # 初始化方式需要详细确定
        for vts in self.vtSymbol:
            self.loadBar(vts, self.cycle, self.days)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略启动')
        self.orderTracking = False
        readData = self.tradeCacheLoad()
        try:
            for vts in self.vtSymbol :
                self.lossStop = readData['lossStop']
                self.bestPrice = readData['bestPrice']
                self.position = self.Status[vts]['pos']
        except Exception as e:
            self.writeCtaLog(u'策略私有参数传递失败!')

        self.putEvent()
        
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略停止')
        writeData = {}
        print self.lossStop,self.bestPrice

        writeData['lossStop'] = self.lossStop
        writeData['bestPrice'] = self.bestPrice
        self.tradeCacheSave(writeData)
        # self.closeAll(self.beta2)
        self.putEvent()

        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        if tick.vtSymbol in self.vtSymbol:
            self.tickData[tick.vtSymbol]['lastPrice']=tick.lastPrice
            self.tickData[tick.vtSymbol]['bidPrice1']=tick.bidPrice1
            self.tickData[tick.vtSymbol]['askPrice1']=tick.askPrice1
            
        # debug使用，检测是否正常接收数据
        # print self.vtSymbol[0], self.tickData[self.vtSymbol[0]]
        # 非交易时间段暂停交易
        if (tick.datetime.hour > 15 and tick.datetime.hour < 20) or \
        (tick.datetime.hour > 1 and tick.datetime.hour < 8):
            self.trading = False
        else:
            # self.trading = True #######################自动交易功能，删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉————
            pass


        if ((tick.datetime.hour >= 9 and tick.datetime.hour < 15) or \
        (tick.datetime.hour >= 21) or (tick.datetime.hour >= 0 and tick.datetime.hour < 1)) and self.trading == True:

            # K 线交易信号生成/交易
            if self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime'] <= tick.datetime and self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime'] != self.barUpdateTime :

                if isinstance(self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['data'].barData,(int,float)):
                    return

                dataTemp = self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['data'].barData[-1-self.Nf:]
                self.onBar(dataTemp)
                self.barUpdateTime = self.ctaEngine.drEngine.barDict[self.vtSymbol[0]][self.cycle]['updateTime']

            if self.bestPrice!= 0 and self.orderTracking == False:
                # print self.vtSymbol[0],self.Status[self.vtSymbol[0]]['pos'],tick.lastPrice,self.lossStop
                if self.Status[self.vtSymbol[0]]['pos'] > 0 :
                    self.bestPrice = max([self.bestPrice,tick.lastPrice])
                    if tick.lastPrice < self.lossStop :
                        self.Status[self.vtSymbol[0]]['orderId'] = self.sell(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                        self.orderTracking = True
                    elif tick.lastPrice < self.bestPrice*(1-self.lossTh) and self.bestPrice/self.Status[self.vtSymbol[0]]['entryPrice'] > 1+3*self.lossTh:
                        self.Status[self.vtSymbol[0]]['orderId'] = self.sell(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                        self.orderTracking = True
                elif self.Status[self.vtSymbol[0]]['pos'] < 0 :
                    self.bestPrice = min([self.bestPrice,tick.lastPrice])
                    if tick.lastPrice > self.lossStop :
                        self.Status[self.vtSymbol[0]]['orderId'] = self.cover(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                        self.orderTracking = True
                    elif tick.lastPrice > self.bestPrice*(1+self.lossTh) and self.Status[self.vtSymbol[0]]['entryPrice']/self.bestPrice > 1+3*self.lossTh:
                        self.Status[self.vtSymbol[0]]['orderId'] = self.cover(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                        self.orderTracking = True

        # 发出状态更新事件
        self.putEvent()
    #----------------------------------------------------------------------
    def onBar(self,data):
        """收到Bar推送（必须由用户继承实现）"""
        data = np.array(data)
        realData = data
        oTemp = realData[:, 1]
        hTemp = realData[:, 2]
        lTemp = realData[:, 3]
        cTemp = realData[:, 4]
        # cBarO = data[-1, 1]
        # cBarH = data[-1, 2]
        # cBarL = data[-1, 3]
        # cBarC = data[-1, 4]
        # cBarT = data[-1, 0]
        
        Nlag = 9
        if data.shape[0] < Nlag:
            return
            
        if oTemp[-1]/cTemp[-2] < 1 - self.breakTh and cTemp[-1] > oTemp[-1] :
            self.tradeSignal = 1
            self.orderType = 1
        elif oTemp[-1]/cTemp[-2] > 1 + self.breakTh and cTemp[-1] < oTemp[-1] :
            self.tradeSignal = -1
            self.orderType = 1
        elif oTemp[-1]/cTemp[-2] < 1 - self.breakTh and cTemp[-1] < oTemp[-1] :
            self.tradeSignal = -1
            self.orderType = 2
        elif oTemp[-1]/cTemp[-2] > 1 + self.breakTh and cTemp[-1] > oTemp[-1] :
            self.tradeSignal = 1
            self.orderType = 2
        else:
            self.tradeSignal = 0

        if self.orderTracking is False:
            if self.Status[self.vtSymbol[0]]['pos'] == 0:
                if self.tradeSignal == 1:
                    self.Status[self.vtSymbol[0]]['orderId'] = self.buy(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                    tI = np.where(realData[:,3]==min(realData[-Nlag:,3]))
                    tI = max([2,tI[0][-1]])
                    TR = max([realData[tI, 2] - realData[tI, 3], abs(realData[tI, 2] - realData[tI - 1, 4]),
                              abs(realData[tI, 3] - realData[tI - 1, 4])])
                    if self.orderType == 2 and lTemp[-1] > hTemp[-2]:
                        TR = TR - abs(realData[-1,1]-realData[-2,4])
                    self.lossStop = min([realData[tI,3],self.tickData[self.vtSymbol[0]]['lastPrice']])-self.trBeta*TR
                    self.orderTracking = True
                    self.bestPrice = self.tickData[self.vtSymbol[0]]['lastPrice']

                elif self.tradeSignal == -1:
                    self.Status[self.vtSymbol[0]]['orderId'] = self.short(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                    tI = np.where(realData[:, 2] == max(realData[-Nlag:, 2]))
                    tI = max([2,tI[0][-1]])
                    TR = max([realData[tI, 2] - realData[tI, 3], abs(realData[tI, 2] - realData[tI - 1, 4]),
                              abs(realData[tI, 3] - realData[tI - 1, 4])])
                    if self.orderType == 2 and hTemp[-1] < lTemp[-2]:
                        TR = TR - abs(realData[-1, 1] - realData[-2, 4])
                    self.lossStop = max(
                        [realData[tI, 2], self.tickData[self.vtSymbol[0]]['lastPrice']]) + self.trBeta * TR
                    self.orderTracking = True
                    self.bestPrice = self.tickData[self.vtSymbol[0]]['lastPrice']

            elif self.Status[self.vtSymbol[0]]['pos'] > 0:
                if self.tradeSignal == -1:
                    self.Status[self.vtSymbol[0]]['orderId'] = self.sell(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                    self.Status[self.vtSymbol[0]]['orderId'] = self.short(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                    tI = np.where(realData[:,2]==max(realData[-Nlag:,2]))
                    tI = max([2,tI[0][-1]])
                    TR = max([realData[tI,2]-realData[tI,3], abs(realData[tI,2]-realData[tI-1,4]), abs(realData[tI,3]-realData[tI-1,4])])
                    if self.orderType == 2 and hTemp[-1] < lTemp[-2]:
                        TR = TR - abs(realData[-1,1]-realData[-2,4])
                    self.lossStop = max([realData[tI,2],self.tickData[self.vtSymbol[0]]['lastPrice']])+self.trBeta*TR
                    self.orderTracking = True
                    self.bestPrice = self.tickData[self.vtSymbol[0]]['lastPrice']

            elif self.Status[self.vtSymbol[0]]['pos'] < 0:
                if self.tradeSignal == 1:
                    self.Status[self.vtSymbol[0]]['orderId'] = self.cover(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                    self.Status[self.vtSymbol[0]]['orderId'] = self.buy(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                    tI = np.where(realData[:, 3] == min(realData[-Nlag:, 3]))
                    tI = max([2,tI[0][-1]])
                    TR = max([realData[tI, 2] - realData[tI, 3], abs(realData[tI, 2] - realData[tI - 1, 4]),
                              abs(realData[tI, 3] - realData[tI - 1, 4])])
                    if self.orderType == 2 and lTemp[-1] > hTemp[-2]:
                        TR = TR - abs(realData[-1, 1] - realData[-2, 4])
                    self.lossStop = min(
                        [realData[tI, 3], self.tickData[self.vtSymbol[0]]['lastPrice']]) - self.trBeta * TR
                    self.orderTracking = True
                    self.bestPrice = self.tickData[self.vtSymbol[0]]['lastPrice']

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送"""
        super(CtaGap, self).onOrder(order)

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送"""
        super(CtaGap, self).onTrade(trade)
        self.orderTracking = False
        self.position = self.Status[trade.vtSymbol]['pos']