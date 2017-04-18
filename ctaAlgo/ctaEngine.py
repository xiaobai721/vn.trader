# encoding: UTF-8

'''
本文件中实现了CTA策略引擎，针对CTA类型的策略，抽象简化了部分底层接口的功能。
'''

import json
import os
import logging
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta

from ctaBase import *
from ctaSetting import STRATEGY_CLASS
from eventEngine import *
from vtConstant import *
from vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData, VtErrorData
from dataRecorder.drEngine import DrEngine


########################################################################
class CtaEngine(object):
    """CTA策略引擎"""
    settingFileName = 'CTA_setting.json'
    settingFileName = os.getcwd() + '/configFiles/' + settingFileName
    if datetime.now().hour>4 and datetime.now().hour<20:
        ctaEngineLogFile =os.getcwd() + '/ctaLogFile/' + datetime.now().replace(hour = 9,minute=0,second=0).strftime('%Y%m%d-%H%M%S')
    else:
        ctaEngineLogFile =os.getcwd() + '/ctaLogFile/' + datetime.now().replace(hour = 21,minute=0,second=0).strftime('%Y%m%d-%H%M%S')

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        self.drEngine = DrEngine(mainEngine, eventEngine)
        
        # 当前日期
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 保存策略实例的字典
        # key为策略名称，value为策略实例，注意策略名称不允许重复
        self.strategyDict = {}
        
        # 保存vtSymbol和策略实例映射的字典（用于推送tick数据）
        # 由于可能多个strategy交易同一个vtSymbol，因此key为vtSymbol
        # value为包含所有相关strategy对象的list
        self.tickStrategyDict = {}
        
        # 保存vtOrderID和strategy对象映射的字典（用于推送order和trade数据）
        # key为vtOrderID，value为strategy对象
        self.orderStrategyDict = {}     

        # tradeID记录，防止系统重复返回
        self.tradIDList = []
        
        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)
        
        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}      # 停止单撤销后会从本字典中删除
        
        # 持仓缓存字典
        # key为vtSymbol，value为PositionBuffer对象
        self.posBufferDict = {}

        # 引擎类型为实盘
        self.engineType = ENGINETYPE_TRADING
        
        # 注册事件监听
        self.registerEvent()
        
        # log 配置
        if not os.path.exists(self.ctaEngineLogFile):
            os.makedirs(self.ctaEngineLogFile)
        with open(self.ctaEngineLogFile+'/ctaLog','ab') as f:
            pass

        self.logger1 = logging.getLogger('ctaLogger')
        self.logger1.setLevel(logging.DEBUG)
        fh = logging.handlers.RotatingFileHandler(self.ctaEngineLogFile+'/ctaLog', mode='a', maxBytes=1024*1024)
        ch = logging.StreamHandler()
        self.logger1.addHandler(fh)
        self.logger1.addHandler(ch)
 
    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        contract = self.mainEngine.getContract(vtSymbol)
        
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange
        req.price = price
        req.volume = volume
        
        req.productClass = strategy.productClass
        req.currency = strategy.currency   
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = PRICETYPE_LIMITPRICE   


        # CTA委托类型映射
        if contract.exchange != EXCHANGE_SHFE:
            if orderType == CTAORDER_BUY:
                req.direction = DIRECTION_LONG
                req.offset = OFFSET_OPEN
            elif orderType == CTAORDER_SHORT:
                req.direction = DIRECTION_SHORT
                req.offset = OFFSET_OPEN
            elif orderType == CTAORDER_SELL:
                req.direction = DIRECTION_SHORT
                req.offset = OFFSET_CLOSE
            elif orderType == CTAORDER_COVER:
                req.direction = DIRECTION_LONG
                req.offset = OFFSET_CLOSE

            return self.SubsendOrder(req,strategy,contract.gatewayName)

        # 针对可能发生的平昨、平今进行订单拆分
        else:
            if orderType == CTAORDER_BUY:
                req.direction = DIRECTION_LONG
                req.offset = OFFSET_OPEN

                return self.SubsendOrder(req,strategy,contract.gatewayName)

            elif orderType == CTAORDER_SHORT:
                req.direction = DIRECTION_SHORT
                req.offset = OFFSET_OPEN

                return self.SubsendOrder(req,strategy,contract.gatewayName)

            elif orderType == CTAORDER_SELL:
                req.direction = DIRECTION_SHORT

                if strategy.posTD[vtSymbol]['long'] > 0 :
                    if volume <= strategy.posTD[vtSymbol]['long']:
                        req.offset = OFFSET_CLOSETODAY

                        return self.SubsendOrder(req,strategy,contract.gatewayName)

                    else:
                        req.volume = strategy.posTD[vtSymbol]['long']
                        req.offset = OFFSET_CLOSETODAY
                        vtOrderID1 = self.SubsendOrder(req,strategy,contract.gatewayName)
                        req.volume = volume - strategy.posTD[vtSymbol]['long']
                        req.offset = OFFSET_CLOSE
                        vtOrderID2 = self.SubsendOrder(req,strategy,contract.gatewayName)

                        return [vtOrderID1,vtOrderID2]
                elif strategy.posYD[vtSymbol]['long'] > 0 :
                    req.volume = volume
                    req.offset = OFFSET_CLOSE
                    return self.SubsendOrder(req,strategy,contract.gatewayName)
                else :
                    self.writeCtaLog(u'%s:下单委托,报单与当前持仓不匹配!' 
                         %(strategy.name))

            elif orderType == CTAORDER_COVER:
                req.direction = DIRECTION_LONG

                if strategy.posTD[vtSymbol]['short'] > 0:
                    if volume <= strategy.posTD[vtSymbol]['short']:
                        req.offset = OFFSET_CLOSETODAY

                        return self.SubsendOrder(req,strategy,contract.gatewayName)

                    else:
                        req.volume = strategy.posTD[vtSymbol]['short']
                        req.offset = OFFSET_CLOSETODAY
                        vtOrderID1 = self.SubsendOrder(req,strategy,contract.gatewayName)
                        req.volume = volume - strategy.posTD[vtSymbol]['short']
                        req.offset = OFFSET_CLOSE
                        vtOrderID2 = self.SubsendOrder(req,strategy,contract.gatewayName)

                        return [vtOrderID1,vtOrderID2]
                elif strategy.posYD[vtSymbol]['short'] > 0:
                    req.volume = volume
                    req.offset = OFFSET_CLOSE
                    return self.SubsendOrder(req,strategy,contract.gatewayName)
                else:
                    self.writeCtaLog(u'%s:下单委托,报单与当前持仓不匹配!' 
                         %(strategy.name))
        
    def SubsendOrder(self,req,strategy,contractgatewayName):
        # 下单函数子函数，无实际意义，只为了便于重复使用
        vtOrderID = self.mainEngine.sendOrder(req, contractgatewayName)    # 发单
        self.orderStrategyDict[vtOrderID] = strategy        # 保存vtOrderID和策略的映射关系
        self.writeCtaLog(u'%s:下单委托,标的--%s,方向--%s,开平--%s,下单量--%s,下单价--%s' 
                         %(strategy.name, req.symbol, req.direction, req.offset, req.volume, req.price))
        return vtOrderID
    
    #----------------------------------------------------------------------
    def sendOrderOriginal(self, vtSymbol, direction, offset, price, volume, strategy):
        """CTP原始发单"""
        contract = self.mainEngine.getContract(vtSymbol)
        
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange
        req.price = price
        req.volume = volume
        req.direction = direction
        req.offset = offset
        
        req.productClass = strategy.productClass
        req.currency = strategy.currency   
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = PRICETYPE_LIMITPRICE                 
        
        vtOrderID = self.mainEngine.sendOrder(req, contract.gatewayName)    # 发单

        if __name__ == '__main__':
            self.orderStrategyDict[vtOrderID] = strategy        # 保存vtOrderID和策略的映射关系
        #     这样做之后，收到的委托回报和成交回报就可以正确的提交到对应的策略，不至于乱套.

        self.writeCtaLog(u'%s:下单委托,标的--%s,方向--%s,开平--%s,下单量--%s,下单价--%s' 
                         %(strategy.name, vtSymbol, req.direction, req.offset, req.volume, req.price))
 
        return vtOrderID

    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 查询报单对象
        order = self.mainEngine.getOrder(vtOrderID)
        
        # 如果查询成功
        if order:
            # 检查是否报单还有效，只有有效时才发出撤单指令
            orderFinished = (order.status==STATUS_ALLTRADED or order.status==STATUS_CANCELLED)
            if not orderFinished:
                req = VtCancelOrderReq()
                req.symbol = order.symbol
                req.exchange = order.exchange
                req.frontID = order.frontID
                req.sessionID = order.sessionID
                req.orderID = order.orderID
                self.mainEngine.cancelOrder(req, order.gatewayName)
                

    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.orderType = orderType
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        
        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE           
        
        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so
        
        return stopOrderID
    
    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]

    #----------------------------------------------------------------------
    def processStopOrder(self, tick):
        """收到行情后处理本地停止单（检查是否要立即发出）"""
        vtSymbol = tick.vtSymbol
        
        # 首先检查是否有策略交易该合约
        if vtSymbol in self.tickStrategyDict:
            # 遍历等待中的停止单，检查是否会被触发
            for so in self.workingStopOrderDict.values():
                if so.vtSymbol == vtSymbol:
                    longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice>=so.price        # 多头停止单被触发
                    shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice<=so.price     # 空头停止单被触发
                    
                    if longTriggered or shortTriggered:
                        # 买入和卖出分别以涨停跌停价发单（模拟市价单）
                        if so.direction==DIRECTION_LONG:
                            price = tick.upperLimit
                        else:
                            price = tick.lowerLimit
                        
                        so.status = STOPORDER_TRIGGERED
                        self.sendOrder(so.vtSymbol, so.orderType, price, so.volume, so.strategy)
                        del self.workingStopOrderDict[so.stopOrderID]

    #----------------------------------------------------------------------
    def processTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
        self.processStopOrder(tick)
        
        # 推送tick到对应的策略实例进行处理
        if tick.vtSymbol in self.tickStrategyDict:
            # 将vtTickData数据转化为ctaTickData
            ctaTick = CtaTickData()
            d = ctaTick.__dict__
            for key in d.keys():
                if key != 'datetime':
                    d[key] = tick.__getattribute__(key)
            # 添加datetime字段
            ctaTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')

            # 逐个推送到策略实例中
            l = self.tickStrategyDict[tick.vtSymbol]
            for strategy in l:
                self.callStrategyFunc(strategy, strategy.onTick, ctaTick)
    
    #----------------------------------------------------------------------
    def processOrderEvent(self, event):
        """处理委托推送"""
        order = event.dict_['data']
        
        if order.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[order.vtOrderID]            
            self.callStrategyFunc(strategy, strategy.onOrder, order)
    
    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """处理成交推送"""
        trade = event.dict_['data']

        contract = self.mainEngine.getContract(trade.vtSymbol)

        # 防止系统重复发出成交回报
        if trade.tradeID not in self.tradIDList:
            self.tradIDList.append(trade.tradeID)
        else:
            return

        if trade.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[trade.vtOrderID]
            
            # 计算策略持仓
            # if trade.vtSymbol not in strategy.pos.keys():  #by hw
            #         strategy.pos[trade.vtSymbol]=0

            if contract.exchange != EXCHANGE_SHFE:

                if trade.offset == OFFSET_OPEN:
                    if trade.direction == DIRECTION_LONG:
                        strategy.posYD[trade.vtSymbol]['long'] += trade.volume
                        strategy.posYD[trade.vtSymbol]['pos'] += trade.volume
                    elif trade.direction == DIRECTION_SHORT:
                        strategy.posYD[trade.vtSymbol]['short'] += trade.volume
                        strategy.posYD[trade.vtSymbol]['pos'] -= trade.volume
                    else:
                        self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                             %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))
                elif trade.offset == OFFSET_CLOSE:
                    if trade.direction == DIRECTION_LONG:
                        strategy.posYD[trade.vtSymbol]['short'] -= trade.volume
                        strategy.posYD[trade.vtSymbol]['pos'] += trade.volume
                    elif trade.direction == DIRECTION_SHORT:
                        strategy.posYD[trade.vtSymbol]['long'] -= trade.volume
                        strategy.posYD[trade.vtSymbol]['pos'] -= trade.volume
                    else:
                        self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                             %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))
                else:
                    self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                         %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))

            else:

                if trade.offset == OFFSET_OPEN:
                
                    if trade.direction == DIRECTION_LONG:
                        strategy.posTD[trade.vtSymbol]['pos'] += trade.volume
                        strategy.posTD[trade.vtSymbol]['long'] += trade.volume
                    elif trade.direction == DIRECTION_SHORT:
                        strategy.posTD[trade.vtSymbol]['pos'] -= trade.volume
                        strategy.posTD[trade.vtSymbol]['short'] += trade.volume
                    else:
                        self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                             %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))
                        
                elif trade.offset == OFFSET_CLOSETODAY:
                
                    if trade.direction == DIRECTION_LONG:
                        strategy.posTD[trade.vtSymbol]['pos'] += trade.volume
                        strategy.posTD[trade.vtSymbol]['short'] -= trade.volume
                    elif trade.direction == DIRECTION_SHORT:
                        strategy.posTD[trade.vtSymbol]['pos'] -= trade.volume
                        strategy.posTD[trade.vtSymbol]['long'] -= trade.volume
                    else:
                        self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                             %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))

                elif trade.offset == OFFSET_CLOSEYESTERDAY:

                    if trade.direction == DIRECTION_LONG:
                        strategy.posYD[trade.vtSymbol]['pos'] += trade.volume
                        strategy.posYD[trade.vtSymbol]['short'] -= trade.volume
                    elif trade.direction == DIRECTION_SHORT:
                        strategy.posYD[trade.vtSymbol]['pos'] -= trade.volume
                        strategy.posYD[trade.vtSymbol]['long'] -= trade.volume
                    else:
                        self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                             %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))
                else:
                    self.writeCtaLog(u'%s:收到异常成交回报,异常回报值: 开平--%s,多空--%s,成交量--%s,成交价--%s' 
                         %(strategy.name, trade.offset, trade.direction, trade.volume, trade.price))

            self.callStrategyFunc(strategy, strategy.onTrade, trade)
            # 
            # del self.orderStrategyDict[trade.vtOrderID]
        else:
            self.writeCtaLog(u'非系统运行策略自动操作:'+u'成交回报,标的--%s,方向--%s,开平--%s,成交量--%s,成交价--%s' 
                         %(trade.vtSymbol, trade.direction, trade.offset, trade.volume, trade.price))

        # 更新持仓缓存数据
        if trade.vtSymbol in self.tickStrategyDict:
            posBuffer = self.posBufferDict.get(trade.vtSymbol, None)
            if not posBuffer:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = trade.vtSymbol
                self.posBufferDict[trade.vtSymbol] = posBuffer
            posBuffer.updateTradeData(trade)            
            
    #----------------------------------------------------------------------
    def processPositionEvent(self, event):
        """处理持仓推送"""
        pos = event.dict_['data']
        
        # 更新持仓缓存数据
        if pos.vtSymbol in self.tickStrategyDict:
            posBuffer = self.posBufferDict.get(pos.vtSymbol, None)
            if not posBuffer:
                posBuffer = PositionBuffer()
                posBuffer.vtSymbol = pos.vtSymbol
                self.posBufferDict[pos.vtSymbol] = posBuffer
            posBuffer.updatePositionData(pos)

    # #----------------------------------------------------------------------
    # def procecssBarEvent(self, event):
    #     """处理K线行情推送"""
    #     Bar = event.dict_['data']
    #     # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
    #     self.processStopOrder(tick)
        
    #     # 推送tick到对应的策略实例进行处理
    #     if tick.vtSymbol in self.tickStrategyDict:
    #         # 将vtTickData数据转化为ctaTickData
    #         ctaTick = CtaTickData()
    #         d = ctaTick.__dict__
    #         for key in d.keys():
    #             if key != 'datetime':
    #                 d[key] = tick.__getattribute__(key)
    #         # 添加datetime字段
    #         ctaTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')

    #         # 逐个推送到策略实例中
    #         l = self.tickStrategyDict[tick.vtSymbol]
    #         for strategy in l:
    #             strategy.onTick(ctaTick)
     
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_POSITION, self.processPositionEvent)
        self.eventEngine.register(EVENT_CTA_LOG, self.writeCtaLogFile)
        self.eventEngine.register(EVENT_ERROR, self.writeCtaLogFile)
 
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)
    
    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        cursor = self.mainEngine.dbQuery(dbName, collectionName, d)
        
        l = []
        if cursor:
            for d in cursor:
                bar = CtaBarData()
                bar.__dict__ = d
                l.append(bar)
            
        return l
   
    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        cursor = self.mainEngine.dbQuery(dbName, collectionName, d)
        
        l = []
        if cursor:
            for d in cursor:
                tick = CtaTickData()
                tick.__dict__ = d
                l.append(tick)
        
        return l    
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """快速发出CTA模块日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_CTA_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   

    #----------------------------------------------------------------------
    def writeCtaLogFile(self, event):
        """快速发出CTA模块日志事件"""
        log = event.dict_['data']
        try:
            content = '\t'.join([log.logTime, log.logContent])
            self.logger1.info(content)
        except Exception as e:
            if isinstance(log, VtErrorData):
                content = '\t'.join([log.errorTime, str(log.errorID), log.errorMsg, log.additionalInfo])
                self.logger1.info(content)
            else:
                print e
        
    #----------------------------------------------------------------------
    def loadStrategy(self, setting):
        """载入策略"""
        try:
            name = setting['name']
            className = setting['className']
        except Exception, e:
            self.writeCtaLog(u'载入策略出错：%s' %e)
            return
        
        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        if not strategyClass:
            self.writeCtaLog(u'找不到策略类：%s' %className)
            return
        
        # 防止策略重名
        if name in self.strategyDict:
            self.writeCtaLog(u'策略实例重名：%s' %name)
        else:
            # 创建策略实例
            strategy = strategyClass(self, setting)  
            self.strategyDict[name] = strategy
            strategy.name = name
            
            # 保存Tick映射关系
            # 增加循环，用于单策略订阅多个合约
            vtSymbolList=strategy.vtSymbol
            for vtSymbol in vtSymbolList:
                if vtSymbol in self.tickStrategyDict:
                    # key为vtSymbol，value为包含所有相关strategy对象的list
                    l = self.tickStrategyDict[vtSymbol]
                else:
                    l = []
                    self.tickStrategyDict[vtSymbol] = l
                l.append(strategy)
                
                # 订阅合约
                contract = self.mainEngine.getContract(vtSymbol)
                # 获取合约的最小变动价位、合约乘数等相关信息----------------------------------------------------------------------------
                if contract:
                    req = VtSubscribeReq()
                    req.symbol = contract.symbol
                    req.exchange = contract.exchange
                    self.mainEngine.subscribe(req, contract.gatewayName)
                else:
                    self.writeCtaLog(u'%s的交易合约%s无法找到' %(name, vtSymbol))


    #----------------------------------------------------------------------
    def initStrategy(self, name):
        """初始化策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]

            if not strategy.inited:
                strategy.inited = True
                self.callStrategyFunc(strategy, strategy.onInit)
            else:
                self.writeCtaLog(u'请勿重复初始化策略实例：%s' %name)
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)        

    #---------------------------------------------------------------------
    def startStrategy(self, name):
        """启动策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.inited and not strategy.trading:
                strategy.trading = True
                self.callStrategyFunc(strategy, strategy.onStart)
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)
    
    #----------------------------------------------------------------------
    def stopStrategy(self, name):
        """停止策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.trading:
                strategy.trading = False
            
                # 对该策略发出的所有限价单进行撤单
                for vtOrderID, s in self.orderStrategyDict.items():
                    if s is strategy:
                        self.cancelOrder(vtOrderID)
                
                # 对该策略发出的所有本地停止单撤单
                for stopOrderID, so in self.workingStopOrderDict.items():
                    if so.strategy is strategy:
                        self.cancelStopOrder(stopOrderID)   
                        
            self.callStrategyFunc(strategy, strategy.onStop)
                
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)        
    
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存策略配置"""
        with open(self.settingFileName, 'w') as f:
            l = []
            
            for strategy in self.strategyDict.values():
                setting = {}
                for param in strategy.paramList:
                    setting[param] = strategy.__getattribute__(param)
                l.append(setting)
            
            jsonL = json.dumps(l, indent=4)
            f.write(jsonL)
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingFileName) as f:
            l = json.load(f)
            
            for setting in l:
                self.loadStrategy(setting)
    
    #----------------------------------------------------------------------
    def getStrategyVar(self, name):
        """获取策略当前的变量字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            varDict = OrderedDict()
            
            for key in strategy.varList:
                varDict[key] = strategy.__getattribute__(key)
            
            return varDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None
    
    #----------------------------------------------------------------------
    def getStrategyParam(self, name):
        """获取策略的参数字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            paramDict = OrderedDict()
            
            for key in strategy.paramList:  
                paramDict[key] = strategy.__getattribute__(key)
            
            return paramDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None   
        
    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """触发策略状态变化事件（通常用于通知GUI更新）"""
        event = Event(EVENT_CTA_STRATEGY+name)
        self.eventEngine.put(event)

    #----------------------------------------------------------------------
    def callStrategyFunc(self, strategy, func, params=None):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            # 停止策略，修改状态为未初始化
            strategy.trading = False
            strategy.inited = False
            
            # 发出日志
            content = '\n'.join([u'策略%s触发异常已停止' %strategy.name,
                                traceback.format_exc()])
            self.writeCtaLog(content)


########################################################################
class PositionBuffer(object):
    """持仓缓存信息（本地维护的持仓数据）"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        
        # 多头
        self.longPosition = EMPTY_INT
        self.longToday = EMPTY_INT
        self.longYd = EMPTY_INT
        
        # 空头
        self.shortPosition = EMPTY_INT
        self.shortToday = EMPTY_INT
        self.shortYd = EMPTY_INT
        
    #----------------------------------------------------------------------
    def updatePositionData(self, pos):
        """更新持仓数据"""
        if pos.direction == DIRECTION_LONG:
            self.longPosition = pos.position
            self.longYd = pos.ydPosition
            self.longToday = self.longPosition - self.longYd
        else:
            self.shortPosition = pos.position
            self.shortYd = pos.ydPosition
            self.shortToday = self.shortPosition - self.shortYd
    
    #----------------------------------------------------------------------
    def updateTradeData(self, trade):
        """更新成交数据"""
        if trade.direction == DIRECTION_LONG:
            # 多方开仓，则对应多头的持仓和今仓增加
            if trade.offset == OFFSET_OPEN:
                self.longPosition += trade.volume
                self.longToday += trade.volume
            # 多方平今，对应空头的持仓和今仓减少
            elif trade.offset == OFFSET_CLOSETODAY:
                self.shortPosition -= trade.volume
                self.shortToday -= trade.volume
            # 多方平昨，对应空头的持仓和昨仓减少
            else:
                self.shortPosition -= trade.volume
                self.shortYd -= trade.volume
        else:
            # 空头和多头相同
            if trade.offset == OFFSET_OPEN:
                self.shortPosition += trade.volume
                self.shortToday += trade.volume
            elif trade.offset == OFFSET_CLOSETODAY:
                self.longPosition -= trade.volume
                self.longToday -= trade.volume
            else:
                self.longPosition -= trade.volume
                self.longYd -= trade.volume