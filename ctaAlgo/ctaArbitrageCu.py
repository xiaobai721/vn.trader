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
class CtaArbitrageCu(CtaTemplate):
    """套利策略Demo"""
    className = 'ArbitrageDemo'
    author = u'ly'
    
    # 策略参数
    # beta1 = 1         	# 标准差系数
    # beta2 = 3     		# 滑点系数
    # initMins = 150 		# 参数计算所需分钟线数
    # waitSeconds = 30 	# 参数计算所需分钟线数
    # waitHours = 1    # 参数计算所需分钟线数
    # slip = 10			# 滑点（可读取）
    volume = 3          # 开仓量，当前设置保证一次追单成功
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'beta1',
                 'beta2',
                 'initMins',
                 'waitSeconds',
                 'waitHours',
                 'slip']     
    
    # 变量列表，保存了变量的名称 多数变量定义为实例变量，变量列表是否能正常访问不确定
    varList = ['inited',
               'trading',
               'waiting',
               'res',
               'sMean',
               'sStd',
               'pth',
               'nth',
               'loss',
               'pos_1',
               'price_1',
               'pos_2',
               'price_2']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(CtaArbitrageCu, self).__init__(ctaEngine, setting)

        self.startTime = datetime.now()           # 订单跟踪起始时间
        self.startAjTime = datetime.now()         # AjBeta 调整起始时间
        self.startHoldingTime = datetime.now()         # AjBeta 调整起始时间
        self.res = 0 
        self.resOpen = 0         # 是否处于亏损等待状态
        self.spread = []             # 价差数组
        self.sMean = EMPTY_FLOAT     # 价差均值
        self.sStd = EMPTY_FLOAT      # 价差方差
        self.pth = EMPTY_FLOAT       # 价差上限
        self.nth = EMPTY_FLOAT       # 价差下限
        self.loss = EMPTY_FLOAT      # 上一根的快速EMA
        self.Status={}          # 本地记录策略实例的订单状态
        self.waiting = False         # 是否处于亏损等待状态
        self.atsCount = 0         # 是否处于亏损等待状态
        self.AjBeta = 0         # 是否处于亏损等待状态
        self.Tail = False         # 是否处于亏损等待状态

        # 交易持仓与开仓价格
        self.pos_1 = EMPTY_FLOAT
        self.price_1 = EMPTY_FLOAT
        self.pos_2 = EMPTY_FLOAT
        self.price_2 = EMPTY_FLOAT

        # 策略变量
        # 参数实验
        self.paramChange = False
        self.orderTracking = False
        self.spreadMinute = {}
        self.tickData={}
        self.bartime={}
        self.signal={}

        for vts in self.vtSymbol :
            self.tickData[vts]={}
            self.tickData[vts]['lastPrice']=EMPTY_FLOAT
            self.tickData[vts]['bidPrice1']=EMPTY_FLOAT
            self.tickData[vts]['askPrice1']=EMPTY_FLOAT
            self.Status[vts]={}
            self.Status[vts]['orderId']=EMPTY_INT
            self.Status[vts]['tradeOrderId']=EMPTY_INT
            self.Status[vts]['orderStatus']=STATUS_UNKNOWN
            self.Status[vts]['pos']=EMPTY_INT
            self.Status[vts]['tradePrice']=EMPTY_FLOAT
            self.Status[vts]['offset']=OFFSET_NONE
            self.Status[vts]['direction']=DIRECTION_NONE
            self.Status[vts]['entryPrice']=EMPTY_FLOAT
            self.Status[vts]['exitPrice']=EMPTY_FLOAT
            self.Status[vts]['profit']=EMPTY_FLOAT
            self.Status[vts]['orderPrice']=EMPTY_FLOAT

        self.lastOrder = None
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'套利策略初始化:读取分钟数据')

        # 初始化方式需要详细确定
        dataDict={}
        for vts in self.vtSymbol:
            dataDict[vts]=self.loadBar(2,vts)
        # 分钟数据取交集
        temp = dataDict[self.vtSymbol[0]].merge(dataDict[self.vtSymbol[1]],on='barTime')
        # print temp
        # 分钟数据做差
        temp1 = temp[self.vtSymbol[0]]-temp[self.vtSymbol[1]]
        # 按照需要的长度进行截取
        self.spread=temp1[len(temp1)-self.initMins-1:len(temp1)-1]
        self.spread=self.spread.tolist()

        # 调用分钟线函数
        self.onBar(self.spread)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'套利策略启动')
        self.orderTracking = False
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'套利策略停止')
        self.closeAll(self.beta2)
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 判断买卖
        if tick.vtSymbol in self.vtSymbol:
            self.tickData[tick.vtSymbol]['lastPrice']=tick.lastPrice
            self.tickData[tick.vtSymbol]['bidPrice1']=tick.bidPrice1
            self.tickData[tick.vtSymbol]['askPrice1']=tick.askPrice1
            
        # debug使用，检测是否正常接收数据
        # print self.vtSymbol[0], self.tickData[self.vtSymbol[0]]
        # 非交易时间段暂停交易
        if (tick.datetime.hour > 15 and tick.datetime.hour < 20) or \
        (tick.datetime.hour > 1 and tick.datetime.hour < 8):
            self.Tail = False
            self.trading = False
        else:
            self.trading = True #######################自动交易功能，删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉——————删掉————
            # pass

        # 14:55 0:55 之后平掉全部仓位
        if ((tick.datetime.hour == 14 and tick.datetime.minute >= 55) or \
        (tick.datetime.hour == 0 and tick.datetime.minute >= 45)) and self.Tail == False:
            self.writeCtaLog(u'尾盘平仓！')
            self.waiting = True
            self.startTime = datetime.now()
            self.closeAll(self.beta2+5)
            self.Tail = True

        # 两个tick都存在的时候
        if self.tickData[self.vtSymbol[0]] and self.tickData[self.vtSymbol[1]]:
            self.res = self.tickData[self.vtSymbol[0]]['lastPrice'] - self.tickData[self.vtSymbol[1]]['lastPrice']
            res1 = self.tickData[self.vtSymbol[0]]['bidPrice1'] - self.tickData[self.vtSymbol[1]]['askPrice1']
            res2 = self.tickData[self.vtSymbol[0]]['askPrice1'] - self.tickData[self.vtSymbol[1]]['bidPrice1']
            res1BS = self.tickData[self.vtSymbol[0]]['askPrice1'] - self.tickData[self.vtSymbol[0]]['bidPrice1']
            res2BS = self.tickData[self.vtSymbol[1]]['askPrice1'] - self.tickData[self.vtSymbol[1]]['bidPrice1']

        longSpread  = self.res<self.nth+self.slip and self.res>self.nth-self.loss    # 突破价差下限，做多价差
        shortSpread = self.res>self.pth-self.slip and self.res<self.pth+self.loss    # 死叉下穿
        # 该平仓价差判断可能较为严格，期望获利更多，需要看模拟情况进行进一步调整
        longCover = self.res<self.nth-self.loss or ((res1>self.sMean or res1>self.resOpen+self.loss) and res1BS<=2*self.slip and res2BS<=(self.beta2-1)*self.slip)# 价差多头平仓
        shortCover = self.res>self.pth+self.loss or ((res2<self.sMean or res2<self.resOpen-self.loss) and res1BS<=2*self.slip and res2BS<=(self.beta2-1)*self.slip)   # 价差空头平仓

        # longCover = self.res<self.nth-self.loss or (self.res>self.sMean-self.slip or self.res>=self.resOpen+self.loss)  # 价差多头平仓
        # shortCover = self.res>self.pth+self.loss or (self.res<self.sMean+self.slip or self.res<=self.resOpen-self.loss)    # 价差空头平仓

        # longSpread  = self.res<self.nth and self.res>self.nth-self.loss    # 突破价差下限，做多价差
        # shortSpread = self.res>self.pth and self.res<self.pth+self.loss    # 死叉下穿
        # longCover = self.res<self.nth-self.loss or self.res>self.sMean     # 价差多头平仓
        # shortCover = self.res>self.pth+self.loss or self.res<self.sMean    # 价差空头平仓

        if ((tick.datetime.hour >= 9 and tick.datetime.hour < 15) or \
        (tick.datetime.hour >= 21) or (tick.datetime.hour >= 0 and tick.datetime.hour < 1)) and \
        self.waiting == False:
            # 所有的委托均以最新价进行挂单
            # 测试1阶段，同时以买价、卖价挂单

            ## 修改了longSpread，shortSpread，longCover，shortCover，同时修改了下单价格，以本价操作
            # 20160719 将longSpread，shortSpread，longCover，shortCover修改为最原始状态：价差超过上下限后以最新价挂单
            if longSpread and self.orderTracking == False:
                if self.Status[self.vtSymbol[0]]['pos']== 0 and self.Status[self.vtSymbol[1]]['pos']== 0:
                    self.Status[self.vtSymbol[0]]['orderId']=self.buy(self.tickData[self.vtSymbol[0]]['lastPrice']-self.slip, self.volume, self.vtSymbol[0])
                    self.Status[self.vtSymbol[1]]['orderId']=self.short(self.tickData[self.vtSymbol[1]]['lastPrice']+self.slip, self.volume, self.vtSymbol[1])
                    self.orderTracking = True
                    self.startTime = tick.datetime
                    self.Status[self.vtSymbol[0]]['profit']=EMPTY_FLOAT
                    self.Status[self.vtSymbol[1]]['profit']=EMPTY_FLOAT
                    self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_OPEN
                    self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_OPEN
                    self.writeCtaLog(u'下单策略状态，res：%s，sMean：%s，sStd：%s，pTh：%s，nTh：%s，loss：%s' 
                         %(self.res, self.sMean, self.sStd, self.pth, self.nth, self.loss))
            elif shortSpread and self.orderTracking == False:
                if self.Status[self.vtSymbol[0]]['pos']== 0 and self.Status[self.vtSymbol[1]]['pos']== 0:
                    self.Status[self.vtSymbol[0]]['orderId']=self.short(self.tickData[self.vtSymbol[0]]['lastPrice']+self.slip, self.volume, self.vtSymbol[0])
                    self.Status[self.vtSymbol[1]]['orderId']=self.buy(self.tickData[self.vtSymbol[1]]['lastPrice']-self.slip, self.volume, self.vtSymbol[1])
                    self.orderTracking = True
                    self.startTime = tick.datetime
                    self.Status[self.vtSymbol[0]]['profit']=EMPTY_FLOAT
                    self.Status[self.vtSymbol[1]]['profit']=EMPTY_FLOAT
                    self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_OPEN
                    self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_OPEN
                    self.writeCtaLog(u'下单策略状态，res：%s，sMean：%s，sStd：%s，pTh：%s，nTh：%s，loss：%s' 
                         %(self.res, self.sMean, self.sStd, self.pth, self.nth, self.loss))
            elif longCover and self.orderTracking == False:
                if self.Status[self.vtSymbol[0]]['pos'] > 0 and self.Status[self.vtSymbol[1]]['pos'] < 0:
                    # 针对平仓修条件修改为卖价买价判断，对应将平仓单修改为超价平仓,原平仓挂单同开仓，使用的是更理想的平仓价（更多获利），等待成交之后进行追单
                    self.Status[self.vtSymbol[0]]['orderId']=self.sell(self.tickData[self.vtSymbol[0]]['lastPrice']-self.beta2*self.slip, abs(self.Status[self.vtSymbol[0]]['pos']), self.vtSymbol[0])
                    self.Status[self.vtSymbol[1]]['orderId']=self.cover(self.tickData[self.vtSymbol[1]]['lastPrice']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
                    self.orderTracking = True
                    self.startTime = tick.datetime
                    self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                    self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                    self.writeCtaLog(u'下单策略状态，res：%s，sMean：%s，sStd：%s，pTh：%s，nTh：%s，loss：%s' 
                         %(self.res, self.sMean, self.sStd, self.pth, self.nth, self.loss))
            elif shortCover and self.orderTracking == False:
                if self.Status[self.vtSymbol[0]]['pos'] < 0 and self.Status[self.vtSymbol[1]]['pos'] > 0:
                    # 针对平仓修条件修改为卖价买价判断，对应将平仓单修改为超价平仓
                    self.Status[self.vtSymbol[0]]['orderId']=self.cover(self.tickData[self.vtSymbol[0]]['lastPrice']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[0]]['pos']), self.vtSymbol[0])
                    self.Status[self.vtSymbol[1]]['orderId']=self.sell(self.tickData[self.vtSymbol[1]]['lastPrice']-self.beta2*self.slip, abs(self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
                    self.orderTracking = True
                    self.startTime = tick.datetime
                    self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                    self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                    self.writeCtaLog(u'下单策略状态，res：%s，sMean：%s，sStd：%s，pTh：%s，nTh：%s，loss：%s' 
                         %(self.res, self.sMean, self.sStd, self.pth, self.nth, self.loss))

            # if longSpread and self.orderTracking == False:
            #     if self.Status[self.vtSymbol[0]]['pos']== 0 and self.Status[self.vtSymbol[1]]['pos']== 0:
            #         self.Status[self.vtSymbol[0]]['orderId']=self.buy(self.tickData[self.vtSymbol[0]]['lastPrice'], self.volume, self.vtSymbol[0])
            #         self.Status[self.vtSymbol[1]]['orderId']=self.short(self.tickData[self.vtSymbol[1]]['lastPrice'], self.volume, self.vtSymbol[1])
            #         self.orderTracking = True
            #         self.startTime = tick.datetime
            #         self.Status[self.vtSymbol[0]]['profit']=EMPTY_FLOAT
            #         self.Status[self.vtSymbol[1]]['profit']=EMPTY_FLOAT
            #         self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_OPEN
            #         self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_OPEN
            # elif shortSpread and self.orderTracking == False:
            #     if self.Status[self.vtSymbol[0]]['pos']== 0 and self.Status[self.vtSymbol[1]]['pos']== 0:
            #         self.Status[self.vtSymbol[0]]['orderId']=self.short(self.tickData[self.vtSymbol[0]]['lastPrice'], self.volume, self.vtSymbol[0])
            #         self.Status[self.vtSymbol[1]]['orderId']=self.buy(self.tickData[self.vtSymbol[1]]['lastPrice'], self.volume, self.vtSymbol[1])
            #         self.orderTracking = True
            #         self.startTime = tick.datetime
            #         self.Status[self.vtSymbol[0]]['profit']=EMPTY_FLOAT
            #         self.Status[self.vtSymbol[1]]['profit']=EMPTY_FLOAT
            #         self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_OPEN
            #         self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_OPEN
            # elif longCover and self.orderTracking == False:
            #     if self.Status[self.vtSymbol[0]]['pos'] > 0 and self.Status[self.vtSymbol[1]]['pos'] < 0:
            #         self.Status[self.vtSymbol[0]]['orderId']=self.sell(self.tickData[self.vtSymbol[0]]['lastPrice'], abs(self.Status[self.vtSymbol[0]]['pos']), self.vtSymbol[0])
            #         self.Status[self.vtSymbol[1]]['orderId']=self.cover(self.tickData[self.vtSymbol[1]]['lastPrice'], abs(self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
            #         self.orderTracking = True
            #         self.startTime = tick.datetime
            #         self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
            #         self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
            # elif shortCover and self.orderTracking == False:
            #     if self.Status[self.vtSymbol[0]]['pos'] < 0 and self.Status[self.vtSymbol[1]]['pos'] > 0:
            #         self.Status[self.vtSymbol[0]]['orderId']=self.cover(self.tickData[self.vtSymbol[0]]['lastPrice'], abs(self.Status[self.vtSymbol[0]]['pos']), self.vtSymbol[0])
            #         self.Status[self.vtSymbol[1]]['orderId']=self.sell(self.tickData[self.vtSymbol[1]]['lastPrice'], abs(self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
            #         self.orderTracking = True
            #         self.startTime = tick.datetime
            #         self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
            #         self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY

            # 挂单有效期内，价格出现趋势运动,撤单处理，只在开仓时进行防抖动处理
            if self.orderTracking == True and self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_NOTTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_NOTTRADED:
                
                # if self.res >= self.sMean-2*self.slip and self.res <= self.sMean+2*self.slip and \
                # self.Status[self.vtSymbol[0]]['orderOffset'] == OFFSET_OPEN and self.Status[self.vtSymbol[1]]['orderOffset'] == OFFSET_OPEN :
                #     self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
                #     self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
                #     self.writeCtaLog(u'开仓挂单有效期内，价差恢复，撤单！')
                
                if (abs(self.Status[self.vtSymbol[0]]['orderPrice']-self.tickData[self.vtSymbol[0]]['lastPrice'])>=self.loss or \
                abs(self.Status[self.vtSymbol[1]]['orderPrice']-self.tickData[self.vtSymbol[1]]['lastPrice'])>=self.loss) :
                    if self.Status[self.vtSymbol[0]]['orderOffset'] == OFFSET_OPEN and self.Status[self.vtSymbol[1]]['orderOffset'] == OFFSET_OPEN and \
                    self.res >= self.sMean-2*self.slip and self.res <= self.sMean+2*self.slip :
                        self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
                        self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
                        self.writeCtaLog(u'开仓挂单有效期内，任意标的价格变化过大，撤单！')
                    else:
                        self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
                        self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
                        self.writeCtaLog(u'平仓挂单有效期内，任意标的价格变化过大，撤单！')


            # 挂单有效期内，双边均未成交，1分钟到达后全部撤单
            if tick.datetime - self.startTime > timedelta(seconds=self.waitSeconds) and self.orderTracking == True and \
            self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_NOTTRADED and \
            self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_NOTTRADED:
                if self.paramChange == True:
                    print '1 minute cancel',tick.datetime,self.startTime,self.Status[self.vtSymbol[0]]['orderStatus'],self.Status[self.vtSymbol[1]]['orderStatus']
                    self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
                    self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
                    self.orderTracking == False
                    self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_UNKNOWN
                    self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_UNKNOWN

        # 策略暂停时间达到1小时后重新恢复策略交易
        if tick.datetime - self.startTime > timedelta(hours=self.waitHours) and self.waiting == True :
            self.waiting = False

        # 信号闪烁导致磨损引发的价差调整，盈利或者5分钟后重置
        if self.Status[self.vtSymbol[0]]['profit']+self.Status[self.vtSymbol[1]]['profit'] > 0 or tick.datetime - self.startAjTime > timedelta(seconds=self.waitSeconds*5):
            self.AjBeta = 0

        # 计算K线
        tickMinute = tick.datetime.minute
        if tickMinute != self.spreadMinute:
            self.spread.append(self.res)
            # 确保spread的长度始终为所需要的
            self.spread.pop(0)
            self.onBar(self.spread)
            self.spreadMinute = tickMinute


        # 发出状态更新事件
        self.putEvent()
    #----------------------------------------------------------------------
    def onBar(self, spread):
        """收到Bar推送（必须由用户继承实现）"""
        # 计算价差上下限
        sMeanTemp = np.round(np.mean(spread)/2.5)*2.5
        sStdTemp = np.max([np.round(np.std(spread)/2.5)*2.5,self.slip])
        if self.sMean != sMeanTemp or self.sStd != sStdTemp:
            self.sMean = sMeanTemp
            self.sStd = sStdTemp
            self.pth = self.sMean + self.beta1*self.sStd + self.beta2*self.slip + self.AjBeta*self.slip
            self.nth = self.sMean - self.beta1*self.sStd - self.beta2*self.slip - self.AjBeta*self.slip
            self.loss = self.beta1*self.sStd + self.beta2*self.slip - self.slip + self.AjBeta*self.slip
            self.paramChange =True
        else:
            self.paramChange =False

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        # print 'on order return!',order.vtSymbol, order.totalVolume, order.tradedVolume, order.direction, order.offset, order.status, order.orderID, order.vtOrderID, order.price

        # 将订单回报更新到本地变量
        if order.vtSymbol in self.vtSymbol:
            self.Status[order.vtSymbol]['orderId']=order.vtOrderID
            self.Status[order.vtSymbol]['orderStatus']=order.status
            self.Status[order.vtSymbol]['orderVolume']=order.totalVolume
            self.Status[order.vtSymbol]['tradedVolume']=order.tradedVolume
            self.Status[order.vtSymbol]['orderDirection']=order.direction
            self.Status[order.vtSymbol]['orderPrice']=order.price
            # self.Status[order.vtSymbol]['orderOffset']=order.offset

        # 单边成交后，将未成交挂单撤单
        if self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
        elif self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])

        elif self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_CANCELLED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
        elif self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_CANCELLED and self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])

        if self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_ALLTRADED:
            self.orderTracking = False
            self.atsCount = 0

        # 双边都撤单后，判断持仓量是否持平，若持平则修改订单追踪状态，否则将全部持仓平仓
        elif self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_CANCELLED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_CANCELLED:
            self.orderTracking = False
            self.atsCount = 0

        # 部分成交后，将所有未成交部分撤单，修改成交腿成交状态，修改未成交腿下单数量
        elif self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_PARTTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
            self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
            self.Status[self.vtSymbol[0]]['orderStatus'] = STATUS_ALLTRADED
            self.Status[self.vtSymbol[1]]['orderVolume'] = self.Status[self.vtSymbol[0]]['tradedVolume']
        elif self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_PARTTRADED and self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_NOTTRADED:
            self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
            self.cancelOrder(self.Status[self.vtSymbol[1]]['orderId'])
            self.Status[self.vtSymbol[1]]['orderStatus'] = STATUS_ALLTRADED
            self.Status[self.vtSymbol[0]]['orderVolume'] = self.Status[self.vtSymbol[1]]['tradedVolume']

        self.rebalancePos()

        self.writeCtaLog(u'下单回报，%s，%s，%s，下单：%s，成交：%s, 状态：%s' 
                         %(order.vtSymbol, order.direction, order.offset, order.totalVolume, order.tradedVolume, order.status))

    def afterTheSingle(self, vts):
        """根据传入的标的，按照本地记录的订单信息进行追单"""
        self.atsCount = self.atsCount+1 
        print 'after the single!',vts,self.Status[vts]['orderOffset'],self.Status[vts]['orderDirection']
        
        if self.atsCount > 5:
            self.writeCtaLog(u'持续追单失败,暂停交易,请检查!')
            print u'持续追单失败,暂停交易,请检查!'
            self.waiting = True
            self.startTime = datetime.now()
            self.closeAll(bias = 10)
            self.atsCount = 0


        # 按照对价进行追单，追单成功由onOrder保证，持续追单由整个事件循环过程保证
        if self.Status[vts]['orderOffset']==OFFSET_CLOSETODAY and self.Status[vts]['orderDirection']==DIRECTION_LONG:
            self.cover(self.tickData[vts]['askPrice1']+self.beta2*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_CLOSETODAY and self.Status[vts]['orderDirection']==DIRECTION_SHORT:
            self.sell(self.tickData[vts]['bidPrice1']-self.beta2*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_OPEN and self.Status[vts]['orderDirection']==DIRECTION_LONG:
            self.buy(self.tickData[vts]['askPrice1']+self.beta2*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_OPEN and self.Status[vts]['orderDirection']==DIRECTION_SHORT:
            self.short(self.tickData[vts]['bidPrice1']-self.beta2*self.slip, self.Status[vts]['orderVolume'], vts)

    def closeAll(self,bias):
        """平掉所有仓位"""
        for vts in self.vtSymbol:
            if self.Status[vts]['orderStatus'] == STATUS_NOTTRADED:
                self.cancelOrder(self.Status[vts]['orderId'])

            if self.Status[vts]['pos'] > 0:
                self.sell(self.tickData[vts]['askPrice1']-bias*self.slip, abs(self.Status[vts]['pos']), vts)
            elif self.Status[vts]['pos'] < 0:
                self.cover(self.tickData[vts]['bidPrice1']+bias*self.slip, abs(self.Status[vts]['pos']), vts)
            else:
                self.writeCtaLog(u'position clear!')
                if (datetime.now().hour == 14 and datetime.now().minute >= 55) or \
                (datetime.now().hour == 0 and datetime.now().minute >= 45):
                    self.trading = False

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        # 当前假定保单状态的成交改变和成交回报完全相同
        # print 'on trade return!',trade.vtSymbol, trade.volume, trade.price, trade.direction, trade.offset, trade.tradeID, trade.vtTradeID, trade.orderID, trade.vtOrderID
        # print 'on trade return! pos ',self.pos
        if trade.vtSymbol in self.vtSymbol:
            self.Status[trade.vtSymbol]['tradePrice']=trade.price
            self.Status[trade.vtSymbol]['offset']=trade.offset
            self.Status[trade.vtSymbol]['direction']=trade.direction
            self.Status[trade.vtSymbol]['tradeOrderId']=trade.orderID
            if self.Status[trade.vtSymbol]['offset'] == OFFSET_OPEN :
                self.Status[trade.vtSymbol]['entryPrice']=trade.price
            elif self.Status[trade.vtSymbol]['offset'] == OFFSET_CLOSETODAY :
                self.Status[trade.vtSymbol]['exitPrice']=trade.price
                if self.Status[trade.vtSymbol]['direction'] == DIRECTION_LONG :
                    self.Status[trade.vtSymbol]['profit']=self.Status[trade.vtSymbol]['entryPrice']-self.Status[trade.vtSymbol]['exitPrice']
                elif self.Status[trade.vtSymbol]['direction'] == DIRECTION_SHORT :
                    self.Status[trade.vtSymbol]['profit']=self.Status[trade.vtSymbol]['exitPrice']-self.Status[trade.vtSymbol]['entryPrice']

        self.pos_1 = self.Status[self.vtSymbol[0]]['pos']
        self.price_1 = self.Status[self.vtSymbol[0]]['tradePrice']
        self.pos_2 = self.Status[self.vtSymbol[1]]['pos']
        self.price_2 = self.Status[self.vtSymbol[1]]['tradePrice']

        # 亏损等于1跳，可能是由于价差机会消失，单边平仓所导致，因此不使程序进入等待状态
        if self.Status[self.vtSymbol[0]]['profit']+self.Status[self.vtSymbol[1]]['profit'] < 0 :
            self.waiting = True
            self.startTime = datetime.now()
            self.writeCtaLog(u'single profit，%s @ %s   ------   %s @ %s' 
                         %(self.vtSymbol[0], self.Status[self.vtSymbol[0]]['profit'],self.vtSymbol[1], self.Status[self.vtSymbol[1]]['profit']))   
            print self.vtSymbol[0], self.Status[self.vtSymbol[0]]['profit'],self.vtSymbol[1], self.Status[self.vtSymbol[1]]['profit'], self.waiting

        # 全部成交，且持仓为0，修改本地订单状态
        if self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_ALLTRADED:
            if self.Status[self.vtSymbol[0]]['pos'] == 0 and self.Status[self.vtSymbol[1]]['pos'] == 0:
                self.Status[self.vtSymbol[0]]['orderStatus']=STATUS_UNKNOWN
                self.Status[self.vtSymbol[1]]['orderStatus']=STATUS_UNKNOWN

        # 双边持仓都不为0，记录本地变量，开仓价差
        if self.Status[self.vtSymbol[0]]['pos'] != 0 and self.Status[self.vtSymbol[1]]['pos'] != 0:
            self.resOpen = self.Status[self.vtSymbol[0]]['entryPrice']-self.Status[self.vtSymbol[1]]['entryPrice']
        else:
            self.resOpen = self.res

        self.rebalancePos()

        self.writeCtaLog(u'成交回报，%s，%s，%s，%s @ %s' 
                         %(trade.vtSymbol, trade.direction, trade.offset, trade.volume, trade.price))

    def rebalancePos(self):
        """根据成交持仓状态对当前持仓进行再平衡操作"""

        ############### 保单状态更新，但是成交回报没有更新，因此将该部分判断移到成交回报处，跟持仓相关的判断，都移到成交回报
        # 双边都成交后，判断持仓量是否持平，若持平则修改订单追踪状态，否则将非平衡持仓平仓
        if self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_ALLTRADED and \
        self.Status[self.vtSymbol[0]]['tradeOrderId']==self.Status[self.vtSymbol[0]]['orderId'] and self.Status[self.vtSymbol[1]]['tradeOrderId']==self.Status[self.vtSymbol[1]]['orderId'] :
            # 订单ID和成交的订单ID一致，表明持仓已经更新过
            if self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos'] > 0:
                if self.Status[self.vtSymbol[0]]['pos'] > 0:
                    self.sell(self.tickData[self.vtSymbol[0]]['bidPrice1']-self.beta2*self.slip, self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos'], self.vtSymbol[0])
                elif self.Status[self.vtSymbol[1]]['pos'] > 0:
                    self.sell(self.tickData[self.vtSymbol[1]]['bidPrice1']-self.beta2*self.slip, self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos'], self.vtSymbol[1])

            elif self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos'] < 0:
                if self.Status[self.vtSymbol[0]]['pos'] < 0:
                    self.cover(self.tickData[self.vtSymbol[0]]['askPrice1']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[0])
                elif self.Status[self.vtSymbol[1]]['pos'] < 0:
                    self.cover(self.tickData[self.vtSymbol[1]]['askPrice1']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
            else:
                self.orderTracking = False
                self.atsCount = 0

        # 双边都撤单后，判断持仓量是否持平，若持平则修改订单追踪状态，否则将全部持仓平仓
        elif self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_CANCELLED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_CANCELLED:
            if self.Status[self.vtSymbol[0]]['pos'] + self.Status[self.vtSymbol[1]]['pos'] != 0:
                if self.Status[self.vtSymbol[0]]['pos'] > 0:
                    self.sell(self.tickData[self.vtSymbol[0]]['bidPrice1']-self.beta2*self.slip, self.Status[self.vtSymbol[0]]['pos'], self.vtSymbol[0])
                elif self.Status[self.vtSymbol[0]]['pos'] < 0:
                    self.cover(self.tickData[self.vtSymbol[0]]['askPrice1']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[0]]['pos']), self.vtSymbol[0])

                if self.Status[self.vtSymbol[1]]['pos'] > 0:
                    self.sell(self.tickData[self.vtSymbol[1]]['bidPrice1']-self.beta2*self.slip, self.Status[self.vtSymbol[1]]['pos'], self.vtSymbol[1])
                elif self.Status[self.vtSymbol[1]]['pos'] < 0:
                    self.cover(self.tickData[self.vtSymbol[1]]['askPrice1']+self.beta2*self.slip, abs(self.Status[self.vtSymbol[1]]['pos']), self.vtSymbol[1])
            else:
                self.orderTracking = False
                self.atsCount = 0

        # 一腿成交，另一腿撤单：在开仓条件下，判断交易信号是否存在，若存在则进行追单，不存在则修改相应订单状态，平掉成交持仓；在平仓条件下，继续追单平仓
        elif self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_CANCELLED:
            # 判断价差是否还存在，进行相应的追单或者平仓操作
            if self.Status[self.vtSymbol[0]]['orderOffset'] == OFFSET_OPEN and self.Status[self.vtSymbol[0]]['tradeOrderId']==self.Status[self.vtSymbol[0]]['orderId']:
                # 单边ID检测控制
                if self.Status[self.vtSymbol[0]]['orderDirection'] == DIRECTION_LONG:
                    # 防止信号闪烁，降低开仓要求
                    if self.Status[self.vtSymbol[0]]['tradePrice']-self.tickData[self.vtSymbol[1]]['bidPrice1'] < self.nth+self.AjBeta*self.slip and \
                    self.Status[self.vtSymbol[0]]['tradePrice']-self.tickData[self.vtSymbol[0]]['lastPrice'] < self.loss:
                        print 1
                        self.afterTheSingle(self.vtSymbol[1])
                    else :
                        self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[0]]['orderDirection']=DIRECTION_SHORT
                        self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[1]]['orderStatus'] = STATUS_ALLTRADED
                        print 2
                        self.afterTheSingle(self.vtSymbol[0])
                        self.AjBeta = self.AjBeta+1
                        self.startAjTime = datetime.now()
                        self.onBar(self.spread)

                elif self.Status[self.vtSymbol[0]]['orderDirection'] == DIRECTION_SHORT:
                    if self.Status[self.vtSymbol[0]]['tradePrice']-self.tickData[self.vtSymbol[1]]['askPrice1'] > self.pth-self.AjBeta*self.slip and \
                    self.tickData[self.vtSymbol[0]]['lastPrice']-self.Status[self.vtSymbol[0]]['tradePrice'] < self.loss:
                        print 3
                        self.afterTheSingle(self.vtSymbol[1])
                    else :
                        self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[0]]['orderDirection']=DIRECTION_LONG
                        self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[1]]['orderStatus'] = STATUS_ALLTRADED
                        print 4
                        self.afterTheSingle(self.vtSymbol[0])
                        self.AjBeta = self.AjBeta+1
                        self.startAjTime = datetime.now()
                        self.onBar(self.spread)
            else :
                print 5
                self.afterTheSingle(self.vtSymbol[1])
        elif self.Status[self.vtSymbol[1]]['orderStatus'] == STATUS_ALLTRADED and self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_CANCELLED:
            if self.Status[self.vtSymbol[1]]['orderOffset'] == OFFSET_OPEN and self.Status[self.vtSymbol[1]]['tradeOrderId']==self.Status[self.vtSymbol[1]]['orderId']:
                # 单边ID检测控制
                if self.Status[self.vtSymbol[1]]['orderDirection'] == DIRECTION_LONG:
                    if self.Status[self.vtSymbol[1]]['tradePrice']-self.tickData[self.vtSymbol[0]]['bidPrice1'] > self.pth-self.AjBeta*self.slip and \
                    self.Status[self.vtSymbol[1]]['tradePrice']-self.tickData[self.vtSymbol[1]]['lastPrice'] < self.loss:
                        print 6
                        self.afterTheSingle(self.vtSymbol[0])
                    else :
                        self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[1]]['orderDirection']=DIRECTION_SHORT
                        self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[0]]['orderStatus'] = STATUS_ALLTRADED
                        print 7
                        self.afterTheSingle(self.vtSymbol[1])
                        self.AjBeta = self.AjBeta+1
                        self.startAjTime = datetime.now()
                        self.onBar(self.spread)

                elif self.Status[self.vtSymbol[1]]['orderDirection'] == DIRECTION_SHORT:
                    if self.Status[self.vtSymbol[1]]['tradePrice']-self.tickData[self.vtSymbol[0]]['askPrice1'] < self.nth+self.AjBeta*self.slip and \
                    self.tickData[self.vtSymbol[1]]['lastPrice']-self.Status[self.vtSymbol[1]]['tradePrice'] < self.loss:
                        print 8
                        self.afterTheSingle(self.vtSymbol[0])
                    else :
                        self.Status[self.vtSymbol[1]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[1]]['orderDirection']=DIRECTION_LONG
                        self.Status[self.vtSymbol[0]]['orderOffset']=OFFSET_CLOSETODAY
                        self.Status[self.vtSymbol[0]]['orderStatus'] = STATUS_ALLTRADED
                        print 9
                        self.afterTheSingle(self.vtSymbol[1])
                        self.AjBeta = self.AjBeta+1
                        self.startAjTime = datetime.now()
                        self.onBar(self.spread)
            else :
                print 10
                self.afterTheSingle(self.vtSymbol[0])
