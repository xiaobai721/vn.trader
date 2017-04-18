# encoding: UTF-8

'''
本文件中包含的数据格式和CTA模块通用，用户有必要可以自行添加格式。
'''

from __future__ import division


# 把vn.trader根目录添加到python环境变量中
import numpy as np
import sys
sys.path.append('..')


# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'


# CTA引擎中涉及的数据类定义
from vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT


########################################################################
class DrBarData(object):
    """K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
    
        self.open = EMPTY_FLOAT             # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT
        
        self.date = EMPTY_STRING            # bar开始的时间，日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        self.volume = EMPTY_INT             # 成交量
        self.turnover = EMPTY_INT             # 成交量
        self.openInterest = EMPTY_INT       # 持仓量


########################################################################
class DrTickData(object):
    """Tick数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""       
        self.vtSymbol = EMPTY_STRING            # vt系统代码
        self.symbol = EMPTY_STRING              # 合约代码
        self.exchange = EMPTY_STRING            # 交易所代码

        # 成交数据
        self.lastPrice = EMPTY_FLOAT            # 最新成交价
        self.volume = EMPTY_INT                 # 最新成交量
        self.turnover = EMPTY_INT 
        self.openInterest = EMPTY_INT           # 持仓量
        
        self.upperLimit = EMPTY_FLOAT           # 涨停价
        self.lowerLimit = EMPTY_FLOAT           # 跌停价
        
        # tick的时间
        self.date = EMPTY_STRING            # 日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        
        # 五档行情
        self.bidPrice1 = EMPTY_FLOAT
        self.bidPrice2 = EMPTY_FLOAT
        self.bidPrice3 = EMPTY_FLOAT
        self.bidPrice4 = EMPTY_FLOAT
        self.bidPrice5 = EMPTY_FLOAT
        
        self.askPrice1 = EMPTY_FLOAT
        self.askPrice2 = EMPTY_FLOAT
        self.askPrice3 = EMPTY_FLOAT
        self.askPrice4 = EMPTY_FLOAT
        self.askPrice5 = EMPTY_FLOAT        
        
        self.bidVolume1 = EMPTY_INT
        self.bidVolume2 = EMPTY_INT
        self.bidVolume3 = EMPTY_INT
        self.bidVolume4 = EMPTY_INT
        self.bidVolume5 = EMPTY_INT
        
        self.askVolume1 = EMPTY_INT
        self.askVolume2 = EMPTY_INT
        self.askVolume3 = EMPTY_INT
        self.askVolume4 = EMPTY_INT
        self.askVolume5 = EMPTY_INT    


class BarDataRam(object):
    """内存中的K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所
        self.lastVolume = EMPTY_FLOAT        # K线聚合的最后一个tick
        self.lastTurnover = EMPTY_FLOAT

        self.barData = EMPTY_INT
    
        # self.open = []             # OHLC
        # self.high = []
        # self.low = []
        # self.close = []
        
        # self.date = []            # bar开始的时间，日期
        # self.time = []            # 时间
        # self.datetime = []                # python的datetime时间对象
        
        # self.volume = []             # 成交量
        # self.turnover = []             # 成交量
        # self.openInterest = []       # 持仓量

class lastBarData(object):
    """K线数据"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING        # vt系统代码
        self.symbol = EMPTY_STRING          # 代码
        self.exchange = EMPTY_STRING        # 交易所

        self.lastBarData = np.zeros([1,10])
    
        # self.open = EMPTY_FLOAT             # OHLC
        # self.high = EMPTY_FLOAT
        # self.low = EMPTY_FLOAT
        # self.close = EMPTY_FLOAT
        
        # self.date = EMPTY_STRING            # bar开始的时间，日期
        # self.time = EMPTY_STRING            # 时间
        # self.datetime = None                # python的datetime时间对象
        
        # self.volume = EMPTY_INT             # 成交量
        # self.turnover = EMPTY_INT             # 成交量
        # self.openInterest = EMPTY_INT       # 持仓量