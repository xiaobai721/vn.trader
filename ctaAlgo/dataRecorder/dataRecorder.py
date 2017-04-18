# encoding: UTF-8

"""
套利策略，记录数据用
"""

from ctaBase import *
from ctaTemplate import CtaTemplate
import numpy as np
import time, json
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

        self.tickTime=datetime.now()
        self.symbol=[]
        self.exchange=[]
        self.openPrice=[]
        self.highPrice=[]
        self.lowPrice=[]
        self.lastPrice=[]
        self.volume=[]
        self.turnover=[]
        self.openInterest=[]
        self.date=[]
        self.time=[]
        self.datetime=[]
        self.bidPrice1=[]
        self.bidVolume1=[]
        self.askPrice1=[]
        self.askVolume1=[]

        # self.createContract()
        # print 'createContract'

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

        self.symbol.append(tick.symbol)
        self.exchange.append(tick.exchange)

        self.openPrice.append(tick.openPrice)
        self.highPrice.append(tick.highPrice)
        self.lowPrice.append(tick.lowPrice)
        self.lastPrice.append(tick.lastPrice)

        self.volume.append(tick.volume)
        self.turnover.append(tick.turnover)
        
        self.openInterest.append(tick.openInterest)
        self.date.append(tick.date)
        self.time.append(tick.time)
        self.datetime.append(tick.datetime)
        self.bidPrice1.append(tick.bidPrice1)
        self.bidVolume1.append(tick.bidVolume1)
        self.askPrice1.append(tick.askPrice1)
        self.askVolume1.append(tick.askVolume1) 

        if tick.datetime -self.tickTime > timedelta(seconds=60):    # 如果分钟变了，则把旧的K线插入数据库，并生成新的K线
            # self.tickTime = tick.datetime
            self.tickTime = datetime.now()

            self.insertBar(self.symbol,self.date,self.time,self.datetime,
                self.openPrice,self.highPrice,self.lowPrice,self.lastPrice,
                self.volume,self.turnover,self.openInterest,
                self.bidPrice1,self.bidVolume1,self.askPrice1,self.askVolume1)

            self.symbol=[]
            self.exchange=[]
            self.openPrice=[]
            self.highPrice=[]
            self.lowPrice=[]
            self.lastPrice=[]
            self.volume=[]
            self.turnover=[]
            self.openInterest=[]
            self.date=[]
            self.time=[]
            self.datetime=[]
            self.bidPrice1=[]
            self.bidVolume1=[]
            self.askPrice1=[]
            self.askVolume1=[]

    #----------------------------------------------------------------------
    def insertBar(self,symbol,date,time,datetime1,
                openPrice,highPrice,lowPrice,lastPrice,
                volume,turnover,openInterest,
                bidPrice1,bidVolume1,askPrice1,askVolume1):
        """向数据库中插入bar数据"""
        # self.ctaEngine.insertData(self.barDbName, vtsymbol, bar)
        # dateInsert = datetime.now().strftime('%Y%m%d')
        dateInsert = max(date)
        dateFile = self.tickTime.strftime('%Y%m%d%H%M%S')
        filename='c:/AllCsvData/'+dateInsert

        if not os.path.exists(filename):
            os.makedirs(filename)
        # print filename+'/01MS.csv'
        # try:  
        with open(filename+'/'+dateFile,'ab') as f:
            a = csv.writer(f, delimiter=',')
            a.writerows(np.array([symbol,date,time,datetime1,
                openPrice,highPrice,lowPrice,lastPrice,
                volume,turnover,openInterest,
                bidPrice1,bidVolume1,askPrice1,askVolume1]).T)
                # print 'insert data',vtsymbol,datetime.now()
            # self.writeCtaLog(u'数据记录工具正常!')
        # except Exception,e:  
        #     print Exception,":",e
        #     self.writeCtaLog(u'数据记录工具错误!!!!!!'+str(Exception)+':'+str(e))
        
        print 'insertData',self.tickTime

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

    #----------------------------------------------------------------------
    def createContract(self):
        """创建遍历合约"""
        symbolList = []
        cList = ['IF','IH','IC','TF','T','a','ag','al','au','b','bb','bu','c','cf','cs','cu','fb','fg','fu','hc','i','j',
        'jd','jm','jr','l','lr','m','ma','ni','oi','p','pb','pm','pp','rb','ri','rm','rs','ru','sf','sm','sn','sr','ta',
        'tc','v','wh','wr','y','zn']
        mList = ['01','02','03','04','05','06','07','08','09','10','11','12']
        yNow = datetime.now().year
        mNow = datetime.now().month
        if mNow < 10:
            mCut = '0'+str(mNow)
        else:
            mCut = str(mNow)

        # for cI in cList:
        #     for mI in mList:
        #         if mI > mCut:
        #             symbolList.append(cI+str(yNow)[2:4]+mI)
        #         elif mI < mCut:
        #             symbolList.append(cI+str(yNow+1)[2:4]+mI)
        #         elif mI == mCut:
        #             symbolList.append(cI+str(yNow+1)[2:4]+mI)
        #             symbolList.append(cI+str(yNow)[2:4]+mI)

        # cI = 'cu'
        # for mI in mList:
        #     if mI > mCut:
        #         symbolList.append(cI+str(yNow)[2:4]+mI)
        #     elif mI < mCut:
        #         symbolList.append(cI+str(yNow+1)[2:4]+mI)
        #     elif mI == mCut:
        #         symbolList.append(cI+str(yNow+1)[2:4]+mI)
        #         symbolList.append(cI+str(yNow)[2:4]+mI)


        recordCList = [
        {"name": "DataRecorderAll",
        "className": "DataRecorder",
        "vtSymbol": symbolList}
        ]

        with open ('C:/vnpy/vn.trader/ctaAlgo/CTA_setting.json','w') as f:
            f.write(json.dumps(recordCList))
