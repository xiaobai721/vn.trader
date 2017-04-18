# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。
'''

import json
import csv,os
import copy
import numpy as np
from collections import OrderedDict
from datetime import datetime, timedelta

from eventEngine import *
from vtGateway import VtSubscribeReq, VtLogData
from drBase import *


########################################################################
class DrEngine(object):
    """数据记录引擎"""
    
    settingFileName = 'CTA_setting.json'
    settingFileName = os.getcwd() + '/configFiles/' + settingFileName

    Standard1ms = 'Standard1ms'
    Standard1ms = os.getcwd() + '/configFiles/' + Standard1ms

    dataPath = os.getcwd() + '/KCsvData/'
    dataPath1 = os.getcwd() + '/configFiles/'

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}
        
        # Tick对象字典
        self.tickDict = {}
        
        # K线对象字典
        self.barDict = {}
        
        # 载入设置，订阅行情
        self.loadSetting()

        self.newBar = np.zeros([1,7])
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入设置"""
        with open(self.settingFileName) as f:
            setting = json.load(f)

        lastVT = {}
        persontype = np.dtype({'names':['symbol', 'v', 't'],
            'formats':['S32','f', 'f']})

        try:
            with open(self.dataPath1+'lastVT/'+'lastVT.csv') as f:
                lastVT1  = np.genfromtxt(f,delimiter=',',dtype = persontype)
                # print lastVT1[0]
                for line in lastVT1:
                    lastVT[line[0]] = [line[1],line[2]]
                # print line
        # for k in lastVT.keys():
        #     print k,lastVT[k]
        except Exception as e:
            print e
            pass
 
        # 日盘、夜盘时段读取不同的1ms序列
        if datetime.now().hour >= 16 :
            with open(self.Standard1ms+'Night.json','r') as f:
                dictStandard1ms = json.load(f)    
        else:
            with open(self.Standard1ms+'Day.json','r') as f:
                dictStandard1ms = json.load(f)    

        self.barDict = {}
        self.splitDict = {}
        lastBar = DrBarData()
        barDataRam = BarDataRam()
        for strIns in setting:
            for symbol in strIns['vtSymbol']:
                if symbol not in self.barDict.keys():

                    self.splitDict[symbol] = {}

                    self.barDict[symbol] = {}
                    self.barDict[symbol][1] = {}
                    self.barDict[symbol][1]['data'] = copy.copy(barDataRam)
                    self.barDict[symbol][1]['lastData'] = copy.copy(lastBar)
                    # self.barDict[symbol][1]['lastTickVolume'] = 0
                    # self.barDict[symbol][1]['lastTickTurnover'] = 0
                    self.barDict[symbol][1]['initial1ms'] = False
                    # self.barDict[symbol][1]['break1msTime'] = []

                    strList = dictStandard1ms[filter(lambda ch: ch not in '0123456789', symbol).lower()]

                    timesList = self.timeSeries(strList)

                    # print temp1

                    timesList.append(timesList[-1]+timedelta(minutes=1))
                    self.splitDict[symbol][1] = copy.copy(timesList)

                    # print timesList
                # print strIns.keys()

                if u'cycle' in strIns.keys():
                    if strIns['cycle'] == 1:
                        continue

                    if strIns['cycle'] not in self.barDict[symbol]:
                        # 针对郑商所的合约代码可能要进行额外的处理
                        temp2 = dictStandard1ms[filter(lambda ch: ch not in '0123456789', symbol).lower()][-1]
                        strList = dictStandard1ms[filter(lambda ch: ch not in '0123456789', symbol).lower()][::strIns['cycle']]

                        # temp.pop(0)

                        timesList = self.timeSeries(strList)

                        # 使用正的偏差还是负的偏差尚未确定
                        if len(timesList)>1:
                            timesList.append(datetime.strptime(str(int(temp2)),'%Y%m%d%H%M%S').replace(year=timesList[-1].year,month=timesList[-1].month,day=timesList[-1].day)+timedelta(minutes=2))
                        else:
                            timesList.append(datetime.strptime(str(int(temp2)),'%Y%m%d%H%M%S').replace(year=datetime.now().year,month=datetime.now().month,day=datetime.now().day)+timedelta(minutes=2))
                        

                        self.splitDict[symbol][strIns['cycle']] = copy.copy(timesList)

                        # print symbol,strIns['cycle'],timesList

                        self.barDict[symbol][strIns['cycle']] = {}
                        self.barDict[symbol][strIns['cycle']]['data'] = copy.copy(barDataRam)
                        self.barDict[symbol][strIns['cycle']]['lastData'] = copy.copy(lastBar)
                        self.barDict[symbol][strIns['cycle']]['updateTime'] = datetime.now() + timedelta(hours = 3)

                if vars().has_key('lastVT'):
                    if symbol not in lastVT.keys():
                        self.barDict[symbol][1]['data'].lastVolume = 0
                        self.barDict[symbol][1]['data'].lastTurnover = 0
                    else:
                        self.barDict[symbol][1]['data'].lastVolume = lastVT[symbol][0]
                        self.barDict[symbol][1]['data'].lastTurnover = lastVT[symbol][1]
                self.barDict[symbol][1]['data'].lastTick = 0
                    
        gatewayName = "CTP"
            
        for symbol in self.barDict.keys():
            # bar = DrBarData()
            # self.barDict[symbol] = bar
            
            req = VtSubscribeReq()
            req.symbol = symbol
            self.mainEngine.subscribe(req, gatewayName)      
                
        self.registerEvent()   

    #----------------------------------------------------------------------
    def timeSeries(self, strList):
        timesList = []
        if datetime.now().hour >= 16 :

            for i in range(0,len(strList)):
                if datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').hour <16 and datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').hour>4   :
                    continue
                timesList.append(datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').replace(year=datetime.now().year,month=datetime.now().month,day=datetime.now().day))
                if timesList[-1].hour < 16 :
                    timesList[-1] = timesList[-1] + timedelta(days=1)
        elif datetime.now().hour < 4 :

            for i in range(0,len(strList)):
                if datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').hour >4 :
                    continue
                timesList.append(datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').replace(year=datetime.now().year,month=datetime.now().month,day=datetime.now().day))
        elif datetime.now().hour < 16 and datetime.now().hour > 4:

            for i in range(0,len(strList)):
                if datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').hour >16 or datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').hour<4 :
                    continue
                timesList.append(datetime.strptime(str(int(strList[i])),'%Y%m%d%H%M%S').replace(year=datetime.now().year,month=datetime.now().month,day=datetime.now().day))

        iTemp = 0
        for i in range(1,len(timesList)):
            if timesList[i-1] < datetime.now() and timesList[i] > datetime.now():
                iTemp = i-1
            else:
                if i == len(timesList):
                    iTemp = i
                pass

        timesList = timesList[iTemp:]     

        return timesList

    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol
        # print tick.date
        test = datetime.now()
        todayDate = test.strftime('%Y%m%d')

        # 转化Tick格式
        drTick = DrTickData()
        d = drTick.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = tick.__getattribute__(key)
        drTick.datetime = datetime.strptime(' '.join([todayDate, tick.time]), '%Y%m%d %H:%M:%S.%f')      

        if (drTick.datetime.hour <9 and drTick.datetime.hour >3) or (drTick.datetime.hour <21 and drTick.datetime.hour >16):
            # if drTick.datetime.hour <3 and drTick.datetime.hour >10:
            #     self.barDict[vtSymbol][1]['lastTickVolume'] = copy.deepcopy(drTick.volume)
            #     self.barDict[vtSymbol][1]['lastTickTurnover'] = copy.deepcopy(drTick.turnover)
            return        
        self.barDict[vtSymbol][1]['data'].lastTick = drTick.lastPrice
        # 更新分钟线数据
        if vtSymbol in self.barDict.keys():
            # print 1,vtSymbol
            if len(self.splitDict[vtSymbol][1]) > 1 :
                # 如果第一个TICK或者新的一分钟
                if not self.barDict[vtSymbol][1]['lastData'].datetime or drTick.datetime >= self.splitDict[vtSymbol][1][1]: 

                    tempTime = copy.copy(self.splitDict[vtSymbol][1][0])
                    self.splitDict[vtSymbol][1].pop(0)

                    if self.barDict[vtSymbol][1]['lastData'].vtSymbol :
                        tempList = [tempTime]
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].open)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].high)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].low)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].close)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].volume-self.barDict[vtSymbol][1]['data'].lastVolume)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].turnover-self.barDict[vtSymbol][1]['data'].lastTurnover)
                        tempList.append(self.barDict[vtSymbol][1]['lastData'].openInterest)

                        self.barDict[vtSymbol][1]['data'].lastVolume = self.barDict[vtSymbol][1]['lastData'].volume
                        self.barDict[vtSymbol][1]['data'].lastTurnover = self.barDict[vtSymbol][1]['lastData'].turnover

                        if isinstance(self.barDict[vtSymbol][1]['data'].barData,(int,float)):
                            self.barDict[vtSymbol][1]['data'].barData = [tempList]
                        else:
                            self.barDict[vtSymbol][1]['data'].barData.append(tempList)

                        # self.barDict[vtSymbol][1]['data'].lastEndTick.append()
                        self.barDict[vtSymbol][1]['updateTime'] = drTick.datetime

                        wPath = self.dataPath+tick.date+'/'+tick.vtSymbol
                        if not os.path.exists(wPath):
                            os.makedirs(wPath)

                        with open(wPath+'/'+str(1)+'MS.csv','ab') as f:
                            a = csv.writer(f, delimiter=',')
                            a.writerows([tempList])
                        # if isinstance(self.barDict[vtSymbol][1]['data'].barData,(int,float)):
                        #     self.barDict[vtSymbol][1]['data'].barData =  copy.copy(self.newBar)
                        #     self.barDict[vtSymbol][1]['data'].datetime.append(tempTime)
                        #     self.barDict[vtSymbol][1]['updateTime'] = drTick.datetime
                        # else:
                        #     self.barDict[vtSymbol][1]['data'].barData = np.append(self.barDict[vtSymbol][1]['data'].barData, self.newBar, axis = 0)
                        #     self.barDict[vtSymbol][1]['data'].datetime.append(tempTime)
                        #     self.barDict[vtSymbol][1]['updateTime'] = drTick.datetime

                        # wPath = 'c:/KCsvData/'+tick.date+'/'+tick.vtSymbol
                        # if not os.path.exists(wPath):
                        #     os.makedirs(wPath)

                        # with open(wPath+'/'+str(1)+'MS.csv','ab') as f:
                        #     a = csv.writer(f, delimiter=',')
                        #     a.writerows([[tempTime]+self.newBar.tolist()[0]])
                        # print u'写入1ms:',vtSymbol,self.barDict[vtSymbol][1]['lastData'].datetime ,drTick.datetime

                        self.barDict[vtSymbol][1]['initial1ms'] = False

                        if len(self.splitDict[vtSymbol][1]) == 1:
                            with open(self.dataPath1+'lastVT/'+'lastVT.csv','ab') as f:
                                a = csv.writer(f, delimiter=',')
                                if datetime.now().hour>=15 and datetime.now().hour<=20:
                                    a.writerows([[vtSymbol,0,0]])
                                else:
                                    a.writerows([[vtSymbol,self.barDict[vtSymbol][1]['data'].lastVolume,self.barDict[vtSymbol][1]['data'].lastTurnover]])

                    self.barDict[vtSymbol][1]['lastData'].date = copy.deepcopy(drTick.date)
                    self.barDict[vtSymbol][1]['lastData'].time = copy.deepcopy(drTick.time)
                    self.barDict[vtSymbol][1]['lastData'].datetime = copy.deepcopy(drTick.datetime)
                    self.barDict[vtSymbol][1]['lastData'].vtSymbol = copy.deepcopy(drTick.vtSymbol)
                    self.barDict[vtSymbol][1]['lastData'].volume = copy.deepcopy(drTick.volume)
                    self.barDict[vtSymbol][1]['lastData'].turnover = copy.deepcopy(drTick.turnover)
                    self.barDict[vtSymbol][1]['lastData'].openInterest = copy.deepcopy(drTick.openInterest)
                    
                if self.barDict[vtSymbol][1]['initial1ms'] == False :
                    # if not self.barDict[vtSymbol][1]['lastData'].datetime:
                    #     self.barDict[vtSymbol][1]['lastData'].date = copy.deepcopy(drTick.date)
                    #     self.barDict[vtSymbol][1]['lastData'].time = copy.deepcopy(drTick.time)
                    #     self.barDict[vtSymbol][1]['lastData'].datetime = copy.deepcopy(drTick.datetime)
                    #     self.barDict[vtSymbol][1]['lastData'].vtSymbol = copy.deepcopy(drTick.vtSymbol)

                    if drTick.volume != 0 or drTick.turnover != 0:
                        self.barDict[vtSymbol][1]['lastData'].open = copy.deepcopy(drTick.lastPrice)
                        self.barDict[vtSymbol][1]['lastData'].high = copy.deepcopy(drTick.lastPrice)
                        self.barDict[vtSymbol][1]['lastData'].low = copy.deepcopy(drTick.lastPrice)
                        self.barDict[vtSymbol][1]['lastData'].close = copy.deepcopy(drTick.lastPrice)
                    # try:
                    # self.barDict[vtSymbol][1]['lastData'].volume = copy.deepcopy(drTick.volume)-self.barDict[symbol][1]['lastTickVolume']
                    # self.barDict[vtSymbol][1]['lastData'].turnover = copy.deepcopy(drTick.turnover)-self.barDict[symbol][1]['lastTickTurnover']
                    # except Exception as e:
                    #     self.barDict[vtSymbol][1]['lastData'].volume = 0
                    #     self.barDict[vtSymbol][1]['lastData'].turnover = 0
                    # self.barDict[vtSymbol][1]['lastData'].volume = copy.deepcopy(drTick.volume)
                    # self.barDict[vtSymbol][1]['lastData'].turnover = copy.deepcopy(drTick.turnover)
                    # 丢失了第一个tick的成交量和成交额                    
                    # self.barDict[vtSymbol][1]['lastData'].openInterest = copy.deepcopy(drTick.openInterest)
                        self.barDict[vtSymbol][1]['initial1ms'] = True
                    else:
                        pass

                        # print u'初始化1ms:',vtSymbol
     
                # 否则继续累加新的K线
                else:  
                    self.barDict[vtSymbol][1]['lastData'].high = max(self.barDict[vtSymbol][1]['lastData'].high, drTick.lastPrice)
                    self.barDict[vtSymbol][1]['lastData'].low = min(self.barDict[vtSymbol][1]['lastData'].low, drTick.lastPrice)
                    self.barDict[vtSymbol][1]['lastData'].close = copy.deepcopy(drTick.lastPrice)
                    # self.barDict[vtSymbol][1]['lastData'].volume = self.barDict[vtSymbol][1]['lastData'].volume + drTick.volume - self.barDict[vtSymbol][1]['lastTickVolume']
                    # self.barDict[vtSymbol][1]['lastData'].turnover = self.barDict[vtSymbol][1]['lastData'].turnover + drTick.turnover - self.barDict[vtSymbol][1]['lastTickTurnover']
                    self.barDict[vtSymbol][1]['lastData'].volume = copy.deepcopy(drTick.volume)
                    self.barDict[vtSymbol][1]['lastData'].turnover = copy.deepcopy(drTick.turnover)
                    self.barDict[vtSymbol][1]['lastData'].openInterest = copy.deepcopy(drTick.openInterest)

                # print 'after',vtSymbol,self.barDict[vtSymbol][1]['lastData'].open,self.barDict[vtSymbol][1]['lastData'].high,self.barDict[vtSymbol][1]['lastData'].low,self.barDict[vtSymbol][1]['lastData'].close  
            
            for cycle in self.barDict[vtSymbol].keys():
                # print 1
                if cycle == 1 or cycle >= 999:
                    continue
                elif len(self.splitDict[vtSymbol][cycle])>1:
                    # print cycle,self.splitDict[vtSymbol][cycle][0]
                    # print drTick.datetime , self.splitDict[vtSymbol][cycle][0],drTick.datetime >= self.splitDict[vtSymbol][cycle][0]
                    if drTick.datetime >= self.splitDict[vtSymbol][cycle][1]:
                        # print vtSymbol,drTick.datetime , self.splitDict[vtSymbol][cycle][0]
                        # 两套系统，一套用于提供正常运转时的数据内存读写，另一套用于文件实时写入以保证意外情况数据恢复

                        tempTime = copy.copy(self.splitDict[vtSymbol][cycle][0])

                        self.splitDict[vtSymbol][cycle].pop(0)

                        self.barDict[vtSymbol][cycle]['data'].vtSymbol = drTick.vtSymbol
                        self.barDict[vtSymbol][cycle]['data'].symbol = drTick.symbol
                        self.barDict[vtSymbol][cycle]['data'].exchange = drTick.exchange

                        # if isinstance(self.barDict[vtSymbol][1]['data'].barData,(int,float)):
                        #     continue
                        try:
                            tempN = len(self.barDict[vtSymbol][1]['data'].barData)
                            tempBar = np.array(self.barDict[vtSymbol][1]['data'].barData[tempN-min(tempN,cycle):tempN])
                        except Exception as e:
                            print "not enough 1ms data."
                            continue

                        tempList = [tempTime]
                        tempList.append(tempBar[0,1])
                        tempList.append(max(tempBar[:,2]))
                        tempList.append(min(tempBar[:,3]))
                        tempList.append(tempBar[-1,4])
                        tempList.append(sum(tempBar[:,5]))
                        tempList.append(sum(tempBar[:,6]))
                        tempList.append(tempBar[-1,7])

                        # self.newBar[0, 0] = tempBar[0,0]
                        # self.newBar[0, 1] = max(tempBar[:,1])
                        # self.newBar[0, 2] = min(tempBar[:,2])
                        # self.newBar[0, 3] = tempBar[-1,3]
                        # self.newBar[0, 4] = tempBar[-1,4]
                        # self.newBar[0, 5] = tempBar[-1,5]
                        # self.newBar[0, 6] = tempBar[-1,6]

                        # tempTime1 = self.barDict[vtSymbol][1]['data'].datetime[len(self.barDict[vtSymbol][1]['data'].datetime)-cycle]
                        # if len(self.splitDict[vtSymbol][cycle])==0:
                        #     tempTime2 = self.barDict[vtSymbol][cycle]['data'].datetime[-1]+timedelta(minutes=cycle)
                        # else:
                        #     tempTime2 = min(tempTime-timedelta(minutes=cycle),self.barDict[vtSymbol][cycle]['data'].datetime[-1]+timedelta(minutes=cycle))

                        tempTime2 = tempTime

                        # if len(self.barDict[vtSymbol][cycle]['data'].datetime)==0:
                        #     tempTime2 = tempTime-timedelta(minutes=cycle)
                        # else:
                        #     tempTime2 = self.barDict[vtSymbol][cycle]['data'].datetime[-1]-timedelta(minutes=cycle)
                        if isinstance(self.barDict[vtSymbol][cycle]['data'].barData,(int,float)):
                            self.barDict[vtSymbol][cycle]['data'].barData = [tempList]
                        else:
                            self.barDict[vtSymbol][cycle]['data'].barData.append(tempList)

                        self.barDict[vtSymbol][cycle]['updateTime'] = drTick.datetime

                        wPath = self.dataPath+tick.date+'/'+tick.vtSymbol
                        if not os.path.exists(wPath):
                            os.makedirs(wPath)

                        with open(wPath+'/'+str(cycle)+'MS.csv','ab') as f:
                            a = csv.writer(f, delimiter=',')
                            a.writerows([tempList])

                        # if isinstance(self.barDict[vtSymbol][cycle]['data'].barData,(int,float)):
                        #     self.barDict[vtSymbol][cycle]['data'].barData =  copy.copy(self.newBar)
                        #     self.barDict[vtSymbol][cycle]['data'].datetime.append(tempTime2)
                        #     self.barDict[vtSymbol][cycle]['updateTime'] = drTick.datetime
                        # else:
                        #     self.barDict[vtSymbol][cycle]['data'].barData = np.append(self.barDict[vtSymbol][cycle]['data'].barData, self.newBar, axis = 0)
                        #     self.barDict[vtSymbol][cycle]['data'].datetime.append(tempTime2)
                        #     self.barDict[vtSymbol][cycle]['updateTime'] = drTick.datetime

                        # wPath = 'c:/KCsvData/'+tick.date+'/'+tick.vtSymbol
                        # if not os.path.exists(wPath):
                        #     os.makedirs(wPath)

                        # with open(wPath+'/'+str(cycle)+'MS.csv','ab') as f:
                        #     a = csv.writer(f, delimiter=',')
                        #     a.writerows([[tempTime2]+self.newBar.tolist()[0]])
                        # if self.barDict[vtSymbol][cycle]['dataLength']:

                        
                        # print u'写入cycle:',vtSymbol,tempTime2,self.newBar[0, 0],self.newBar[0, 1],self.newBar[0, 2],self.newBar[0, 3]
                        #     n = self.barDict[vtSymbol][cycle]['data'].shape[0] - self.barDict[vtSymbol][cycle]['dataLength'] - 1
    
                # self.barDict[vtSymbol][1]['lastTickVolume'] = copy.deepcopy(drTick.volume)
                # self.barDict[vtSymbol][1]['lastTickTurnover'] = copy.deepcopy(drTick.turnover)        

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)
        self.eventEngine.register(EVENT_TIMER, self.fakeTick)        

    def fakeTick(self,event):

        for vts in self.splitDict.keys():
            if len(self.splitDict[vts][1])<=2 and len(self.splitDict[vts][1])>=0 and datetime.now()>self.splitDict[vts][1][-1]+timedelta(minutes=2):

                tick = DrTickData()

                tick.vtSymbol = vts            # vt系统代码
                tick.symbol = vts              # 合约代码
                # 成交数据
                tick.lastPrice = self.barDict[vts][1]['data'].lastTick            # 最新成交价
                tick.volume = EMPTY_INT                 # 最新成交量
                tick.turnover = EMPTY_INT 
                tick.openInterest = EMPTY_INT           # 持仓量        
                # tick的时间
                tick.date = datetime.now().strftime('%Y%m%d')            # 日期
                tick.time = (datetime.now()+timedelta(minutes=5)).strftime('%H:%M:%S.%f')            # 时间
                tick.datetime = None                # python的datetime时间对象
                
                # 五档行情
                tick.bidPrice1 = self.barDict[vts][1]['data'].lastTick
                tick.askPrice1 = self.barDict[vts][1]['data'].lastTick       
                tick.bidVolume1 = EMPTY_INT
                tick.askVolume1 = EMPTY_INT   

                # print 'fake tick event',vts,datetime.now(),self.splitDict[vts][1]
                event1 = Event(type_=EVENT_TICK)
                event1.dict_['data'] = tick
                self.procecssTickEvent(event1)

 
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)

    #----------------------------------------------------------------------
    def loadBarData(self, fileList, vtSymbol, cycle, days):
        """加载历史K线，生成初始内存数据"""

        cycleName = str(cycle)

        for i in reversed(range(0,min([days+1,len(fileList)]))):
            filename=self.dataPath+fileList[i]+'/'+vtSymbol+'/'+cycleName+'MS.csv'
            # (self.barTime-timedelta(days)).strftime('%Y%m%d')
            try:
                with open(filename) as f:

                    historyData = np.genfromtxt(f, delimiter=',', dtype=None)

                    for i in range(0,historyData.shape[0]):
                        # 如果有毫秒信息，则修正为：datetime.strptime(historyData[i][0].split('.')[0], "%Y-%m-%d %H:%M:%S")
                        tempList = [datetime.strptime(historyData[i][0], "%Y-%m-%d %H:%M:%S")]
                        for j in range(1,len(historyData[i])):
                            tempList.append(historyData[i][j])

                        # self.newBar[0, 0] = datetime.strptime(historyData[i][0], "%Y-%m-%d %H:%M:%S") 
                        # self.newBar[0, 0] = historyData[i][1]
                        # self.newBar[0, 1] = historyData[i][2]
                        # self.newBar[0, 2] = historyData[i][3]
                        # self.newBar[0, 3] = historyData[i][4]
                        # self.newBar[0, 4] = historyData[i][5]
                        # self.newBar[0, 5] = historyData[i][6]
                        # self.newBar[0, 6] = historyData[i][7]

                        if isinstance(self.barDict[vtSymbol][cycle]['data'].barData,(int,float)):
                            self.barDict[vtSymbol][cycle]['data'].barData = [tempList]
                            # self.barDict[vtSymbol][cycle]['data'].barData =  self.newBar
                            # self.barDict[vtSymbol][cycle]['data'].datetime.append(datetime.strptime(historyData[i][0].split('.')[0], "%Y-%m-%d %H:%M:%S"))
                        else:
                            self.barDict[vtSymbol][cycle]['data'].barData.append(tempList)
                            # self.barDict[vtSymbol][cycle]['data'].barData = np.append(self.barDict[vtSymbol][cycle]['data'].barData, self.newBar, axis = 0)
                            # self.barDict[vtSymbol][cycle]['data'].datetime.append(datetime.strptime(historyData[i][0].split('.')[0], "%Y-%m-%d %H:%M:%S"))

                    self.barDict[vtSymbol][cycle]['updateTime'] = datetime.now()
                print fileList[i]
            except Exception, e:
                self.writeDrLog(fileList[i]+u'日,数据加载未成功!')
                print e
        
    #----------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_CTA_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    