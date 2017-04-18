# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''

from ctaBase import *
from vtConstant import *
import numpy as np
import pandas as pd
from datetime import datetime,timedelta
import json,csv,os
from dataRecorder.drEngine import DrEngine

########################################################################
class CtaTemplate(object):
    """CTA策略模板"""
    
    # 策略类的名称和作者
    className = 'CtaTemplate'
    author = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    
    # 策略的基本参数
    name = EMPTY_UNICODE           # 策略实例名称
    vtSymbol = EMPTY_STRING        # 交易的合约vt系统代码
    tradeparam={}
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）    
    # 策略的基本变量，由引擎管理
    inited = False                 # 是否进行了初始化
    trading = False                # 是否启动交易，由引擎管理
    pos = {}                        # 持仓情况
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine
        self.barTime = datetime.now()
        self.initedTime = datetime.now()
        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
                if key =='vtSymbol':
                    self.vtSymbol=setting[key]

        self.tradeCachePath = os.getcwd()+'/tradeCache'

        self.posTD={}
        self.posYD={}
        self.tickData={}
        self.Status={}
        # vtSymbol 交易合约代码
        for vts in self.vtSymbol :

            self.posTD[vts]={}
            self.posYD[vts]={}
            
            self.posTD[vts]['long']=EMPTY_INT
            self.posYD[vts]['long']=EMPTY_INT
            self.posTD[vts]['short']=EMPTY_INT
            self.posYD[vts]['short']=EMPTY_INT

            self.posTD[vts]['pos']=EMPTY_INT
            self.posYD[vts]['pos']=EMPTY_INT
   
            self.tickData[vts]={}
            self.tickData[vts]['lastPrice']=EMPTY_FLOAT
            self.tickData[vts]['bidPrice1']=EMPTY_FLOAT
            self.tickData[vts]['askPrice1']=EMPTY_FLOAT

            self.Status[vts]={}
            self.Status[vts]['orderId']=EMPTY_INT            
            self.Status[vts]['tradeOrderId']=EMPTY_INT
            self.Status[vts]['orderStatus']=STATUS_UNKNOWN
            self.Status[vts]['pos']=EMPTY_INT
            self.Status[vts]['orderPrice']=EMPTY_FLOAT
            self.Status[vts]['tradePrice']=EMPTY_FLOAT
            self.Status[vts]['offset']=OFFSET_NONE
            self.Status[vts]['direction']=DIRECTION_NONE
            self.Status[vts]['entryPrice']=EMPTY_FLOAT
            self.Status[vts]['exitPrice']=EMPTY_FLOAT
            self.Status[vts]['dayProfit']=[]
            
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

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

        # if self.Status[self.vtSymbol[0]]['orderStatus'] == STATUS_ALLTRADED :
        #     self.orderTracking = False
        # else:
        #     # 未对部分成交做特殊处理
        #     if datetime.now() - self.Status[self.vtSymbol[0]]['orderTime'] > timedelta(minutes = 1) :
        #         self.cancelOrder(self.Status[self.vtSymbol[0]]['orderId'])
        #         self.orderTracking = False
        
        self.writeCtaLog(u'下单回报,标的--%s,方向--%s,开平--%s,下单量--%s,成交量--%s,下单价--%s,状态--%s' 
                         %(order.vtSymbol, order.direction, order.offset, order.totalVolume, order.tradedVolume, order.price, order.status))
        return
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 当前假定保单状态的成交改变和成交回报完全相同
        # print 'on trade return!',trade.vtSymbol, trade.volume, trade.price, trade.direction, trade.offset, trade.tradeID, trade.vtTradeID, trade.orderID, trade.vtOrderID
        # print 'on trade return! pos ',self.pos
        if trade.vtSymbol in self.vtSymbol:
            # self.orderTracking = False
            
            if trade.offset == OFFSET_OPEN :
                if self.Status[trade.vtSymbol]['pos'] == 0:
                    self.Status[trade.vtSymbol]['entryPrice'] = trade.price
                else:
                    tempPos1 = self.Status[trade.vtSymbol]['pos']
                    tempPos2 = self.posYD[trade.vtSymbol]['pos']+self.posTD[trade.vtSymbol]['pos']
                    self.Status[trade.vtSymbol]['entryPrice'] = (self.Status[trade.vtSymbol]['entryPrice']*tempPos1 + trade.price*tempPos2)/(tempPos1+tempPos2)

                # print u'持仓均价',self.Status[trade.vtSymbol]['entryPrice'],type(self.Status[trade.vtSymbol]['entryPrice']),trade.price,type(trade.price)
                self.writeCtaLog(u'持仓均价--%s,最新建仓价--%s'
                     %(str(self.Status[trade.vtSymbol]['entryPrice']),trade.price))

                self.Status[trade.vtSymbol]['exitPrice'] = 0

            else:
                self.Status[trade.vtSymbol]['exitPrice'] = trade.price
                if trade.direction == DIRECTION_LONG :
                    self.Status[trade.vtSymbol]['dayProfit'].append((self.Status[trade.vtSymbol]['entryPrice']-trade.price)*trade.volume)
                else:
                    self.Status[trade.vtSymbol]['dayProfit'].append((trade.price-self.Status[trade.vtSymbol]['entryPrice'])*trade.volume)

                # print u'最新平仓价',self.Status[trade.vtSymbol]['exitPrice'],type(self.Status[trade.vtSymbol]['exitPrice']),self.Status[trade.vtSymbol]['dayProfit'][-1]
                self.writeCtaLog(u'最新平仓价--%s,单次平仓盈亏--%s'
                     %(str(self.Status[trade.vtSymbol]['exitPrice']),str(self.Status[trade.vtSymbol]['dayProfit'][-1])))

            self.Status[trade.vtSymbol]['tradePrice']=trade.price
            self.Status[trade.vtSymbol]['offset']=trade.offset
            self.Status[trade.vtSymbol]['direction']=trade.direction
            self.Status[trade.vtSymbol]['tradeOrderId']=trade.orderID
            self.Status[trade.vtSymbol]['pos'] = self.posYD[trade.vtSymbol]['pos']+self.posTD[trade.vtSymbol]['pos']

        self.writeCtaLog(u'成交回报,标的--%s,方向--%s,开平--%s,成交量--%s,成交价--%s' 
                         %(trade.vtSymbol, trade.direction, trade.offset, trade.volume, trade.price))
        return
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def buy(self, price, volume,vtsymbol, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume,vtsymbol, stop)
    
    #----------------------------------------------------------------------
    def sell(self, price, volume, vtsymbol,stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, vtsymbol,stop)

    #----------------------------------------------------------------------
    def short(self, price, volume,vtsymbol, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, vtsymbol,stop)
 
    #----------------------------------------------------------------------
    def cover(self, price, volume, vtsymbol,stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume,vtsymbol, stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, vtsymbol,stop=False):
        """发送委托"""

        if self.trading:
            # self.tradeparam['price']=price
            # self.tradeparam['volume']=volume
            # self.tradeparam['vtsymbol']=vtsymbol
            # self.tradeparam['orderType']=orderType
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(vtsymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(vtsymbol, orderType, price, volume, self)
            return vtOrderID
        else:
            return None        
        
    #----------------------------------------------------------------------
    def sendOrderOriginal(self, direction, offset, price, volume, vtsymbol):
        """发送委托"""

        if self.trading:
            # self.tradeparam['price']=price
            # self.tradeparam['volume']=volume
            # self.tradeparam['vtsymbol']=vtsymbol
            # self.tradeparam['orderType']=000 # 调用原始下单函数没有ordertype

            vtOrderID = self.ctaEngine.sendOrderOriginal(vtsymbol, direction, offset, price, volume, self)
            
            return vtOrderID
        else:
            return None        

    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        if STOPORDERPREFIX in vtOrderID:
            self.ctaEngine.cancelStopOrder(vtOrderID)
        else:
            self.ctaEngine.cancelOrder(vtOrderID)
            self.writeCtaLog(u'撤单委托,订单ID--%s' 
                         %(vtOrderID))

    #----------------------------------------------------------------------
    def insertTick(self,vtsymbol, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, vtsymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, vtsymbol, bar):
        """向数据库中插入bar数据"""
        # self.ctaEngine.insertData(self.barDbName, vtsymbol, bar)

        filename='d:/CsvData/'+datetime.now().strftime('%Y%m%d')+'/'+vtsymbol
        if not os.path.exists(filename):
            os.makedirs(filename)
        # print filename+'/01MS.csv'
        with open(filename+'/01MS.csv','ab') as f:
            a = csv.writer(f, delimiter=',')
            bar.insert(0,vtsymbol)
            a.writerows([bar])
            # print 'insert data',vtsymbol,datetime.now()
                
    #----------------------------------------------------------------------
    def loadTick(self, days,vtsymbol):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, vtsymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, vtsymbol, cycle, days):
        """读取bar数据"""
        # return self.ctaEngine.loadBar(self.barDbName, vtsymbol, days)
        # 修改ctaEngine的loadBar方法，当前设定为直接读取csv文件
        fileList = os.listdir(self.ctaEngine.drEngine.dataPath)
        fileList.sort(reverse=True)
        try:
            return self.ctaEngine.drEngine.loadBarData(fileList, vtsymbol, cycle, days)
        except Exception as e:
            print e
            self.writeCtaLog(u'初始化--读取历史'+str(self.cycle)+u'分钟数据失败!!!')

        
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    #----------------------------------------------------------------------
    def afterTheSingle(self, vtOrderID):
        """追单"""
        raise NotImplementedError
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)

    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.ctaEngine.engineType
    #----------------------------------------------------------------------
    # def onTradeTime(self, ticktime):
    #     #if  ticktime.hour ==10 or ticktime.hour ==13  or ticktime.hour ==21 or ticktime.hour ==22 \
    #     raise NotImplementedError                

    #----------------------------------------------------------------------
    def tradeCacheSave(self,writeData): 

        if datetime.now()>datetime.now().replace(hour=15,minute=17,second=0) and datetime.now()<datetime.now().replace(hour=20,minute=59,second=0):
            dayOff = True
        else:
            dayOff = False

        
        if dayOff is True: # 逻辑仍然存在漏洞，夜盘连续交易之后可能会出现今仓，夜盘不交易的话应该没有逻辑漏洞 
        # (self.initedTime < datetime.now() - timedelta(hours=20) and datetime.now().weekday()!=0)or  时间判断这部分对于节假日过于敏感，因此暂时删除
            for vts in self.vtSymbol:
                writeData[vts] = {}
                writeData[vts]['positionToday'] = EMPTY_INT
                writeData[vts]['positionYesterday'] = self.posYD[vts]['pos']+self.posTD[vts]['pos']
                writeData[vts]['positionTodayLong'] = EMPTY_INT
                writeData[vts]['positionYesterdayLong'] = self.posYD[vts]['long']+self.posTD[vts]['long']
                writeData[vts]['positionTodayShort'] = EMPTY_INT
                writeData[vts]['positionYesterdayShort'] = self.posYD[vts]['short']+self.posTD[vts]['short']
                writeData[vts]['entryPrice'] = self.Status[vts]['entryPrice']
                writeData[vts]['exitPrice'] = self.Status[vts]['exitPrice']
                writeData[vts]['lastPrice'] = self.tickData[vts]['lastPrice']
                # writeData[vts]['dayProfit'] = sum(self.Status[vts]['dayProfit'])+(self.tickData[vts]['lastPrice']-self.Status[vts]['entryPrice'])*(self.posTD[vts]['pos']+self.posYD[vts]['pos'])
                writeData[vts]['dayProfit'] = self.Status[vts]['dayProfit']
                if self.posTD[vts]['pos']+self.posYD[vts]['pos'] != 0:
                    writeData[vts]['dayProfit'].append((writeData[vts]['lastPrice']-writeData[vts]['entryPrice'])*(self.posTD[vts]['pos']+self.posYD[vts]['pos']))
                writeData[vts]['systemReserve'] = 'symbol'
                writeData[vts]['vtSymbol'] = vts
        else:
            for vts in self.vtSymbol:
                writeData[vts] = {}
                writeData[vts]['positionToday'] = self.posTD[vts]['pos']
                writeData[vts]['positionYesterday'] = self.posYD[vts]['pos']
                writeData[vts]['positionTodayLong'] = self.posTD[vts]['long']
                writeData[vts]['positionYesterdayLong'] = self.posYD[vts]['long']
                writeData[vts]['positionTodayShort'] = self.posTD[vts]['short']
                writeData[vts]['positionYesterdayShort'] = self.posYD[vts]['short']
                writeData[vts]['entryPrice'] = self.Status[vts]['entryPrice']
                writeData[vts]['exitPrice'] = self.Status[vts]['exitPrice']
                writeData[vts]['lastPrice'] = self.tickData[vts]['lastPrice']
                # writeData[vts]['dayProfit'] = sum(self.Status[vts]['dayProfit'])+(self.tickData[vts]['lastPrice']-self.Status[vts]['entryPrice'])*(self.posTD[vts]['pos']+self.posYD[vts]['pos'])
                writeData[vts]['dayProfit'] = self.Status[vts]['dayProfit']
                if self.posTD[vts]['pos']+self.posYD[vts]['pos'] != 0:
                    writeData[vts]['dayProfit'].append((writeData[vts]['lastPrice']-writeData[vts]['entryPrice'])*(self.posTD[vts]['pos']+self.posYD[vts]['pos']))
                writeData[vts]['systemReserve'] = 'symbol'
                writeData[vts]['vtSymbol'] = vts

        writeData['writeTime'] = datetime.strftime(datetime.now(),'%Y%m%d%H%M%S')

        d1 = json.dumps(writeData,sort_keys=True,indent=4)
        with open(self.tradeCachePath+'/'+self.name+'_dataExchange.json','w') as f:
            f.write(d1)
        if not os.path.exists(self.tradeCachePath+'/hisTradeCache/'+self.name) :
            os.makedirs(self.tradeCachePath+'/hisTradeCache/'+self.name)
        with open(self.tradeCachePath+'/hisTradeCache/'+self.name+'/'+self.name+'_dataExchange_'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json','w') as f:
            f.write(d1)
            
    #----------------------------------------------------------------------
    def tradeCacheLoad(self):


        try:    
            with open(self.tradeCachePath+'/'+self.name+'_dataExchange.json','r') as f:
                readData = json.load(f)
        except Exception, e:
            self.writeCtaLog(u'载入配置出错--%s' %e)
            return

        writeTime = datetime.strptime(readData['writeTime'],'%Y%m%d%H%M%S')

        for vts in self.vtSymbol:
            if (datetime.now().hour > 15 and datetime.now().hour < 21) or \
            writeTime < datetime.now() - timedelta(hours=20) :

                self.posTD[vts]['pos'] = EMPTY_INT
                self.posYD[vts]['pos'] = readData[vts]['positionYesterday']+readData[vts]['positionToday']
                self.posTD[vts]['long'] = EMPTY_INT
                self.posYD[vts]['long'] = readData[vts]['positionYesterdayLong']+readData[vts]['positionTodayLong']
                self.posTD[vts]['short'] = EMPTY_INT
                self.posYD[vts]['short'] = readData[vts]['positionYesterdayShort']+readData[vts]['positionTodayShort']

            else:

                self.posTD[vts]['pos'] = readData[vts]['positionToday']
                self.posYD[vts]['pos'] = readData[vts]['positionYesterday']
                self.posTD[vts]['long'] = readData[vts]['positionTodayLong']
                self.posYD[vts]['long'] = readData[vts]['positionYesterdayLong']
                self.posTD[vts]['short'] = readData[vts]['positionTodayShort']
                self.posYD[vts]['short'] = readData[vts]['positionYesterdayShort']

            self.Status[vts]['pos'] = self.posYD[vts]['pos']+self.posTD[vts]['pos']
            if self.posTD[vts]['long'] == 0 and self.posYD[vts]['long'] == 0 and self.posTD[vts]['short'] == 0 and self.posYD[vts]['short'] == 0 :
                pass
            else:
                self.Status[vts]['entryPrice'] = readData[vts]['entryPrice']

            if any([[self.posTD[vts]['long'],self.posYD[vts]['long'],self.posTD[vts]['short'],self.posYD[vts]['short']]<0]):
                self.writeCtaLog(u'载入配置出错,单向持仓信息包含负数!')

            # del readData[vts]

        # del readData['writeTime']

        print self.posTD[vts]['pos'],self.posYD[vts]['pos'],self.posTD[vts]['long'],self.posYD[vts]['long'],self.posTD[vts]['short'],self.posYD[vts]['short']

        return readData

    def afterTheSingle(self, vts):
        """根据传入的标的，按照本地记录的订单信息进行追单"""
        self.atsCount = self.atsCount+1 
        print 'after the single!',vts,self.Status[vts]['orderOffset'],self.Status[vts]['orderDirection']
        
        if self.atsCount > 5:
            self.writeCtaLog(u'持续追单失败--暂停交易--请检查!!!')
            self.waiting = True
            self.startTime = datetime.now()
            self.closeAll(bias = 10)
            self.atsCount = 0

        # 按照对价进行追单，追单成功由onOrder保证，持续追单由整个事件循环过程保证
        if self.Status[vts]['orderOffset']==OFFSET_CLOSETODAY and self.Status[vts]['orderDirection']==DIRECTION_LONG:
            self.cover(self.tickData[vts]['askPrice1']+self.beta1*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_CLOSETODAY and self.Status[vts]['orderDirection']==DIRECTION_SHORT:
            self.sell(self.tickData[vts]['bidPrice1']-self.beta1*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_OPEN and self.Status[vts]['orderDirection']==DIRECTION_LONG:
            self.buy(self.tickData[vts]['askPrice1']+self.beta1*self.slip, self.Status[vts]['orderVolume'], vts)
        elif self.Status[vts]['orderOffset']==OFFSET_OPEN and self.Status[vts]['orderDirection']==DIRECTION_SHORT:
            self.short(self.tickData[vts]['bidPrice1']-self.beta1*self.slip, self.Status[vts]['orderVolume'], vts)

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


