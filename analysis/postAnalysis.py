# encoding: UTF-8

'''
log拆分和部分盘后计算功能
'''

import json,pyexcel_xls,copy,csv,re
import os
import logging
import logging.handlers
import numpy as np
import matplotlib.pyplot as plt
import calendar
from collections import OrderedDict
from datetime import datetime, timedelta
from pyexcel_xls import get_data

from eventEngine import *
from vtFunction import *
from vtGateway import *

from postConstant import *
from vtConstant import *

##########################################################################
class PostAnalysis(object):
    """日志拆分分析"""

    ctaEngineLogFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\ctaLogFile\\temp'
    ctaEngineTradeCacheFile = os.getcwd() + '/tradeCache'
    ctaSettingFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\algoConfig'

    ctaCurrPosFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir,os.pardir)) + 'vn.trader\\ctaLogFile\\ctaPosFile'
    ctaHisPosFile = ctaCurrPosFile + '\\' + 'hisPosFile'
    # statementFile = os.getcwd() + '/statement'

    #---------------------------------------------------------------------
    def __init__(self):
        """初始化"""
        # startTime = '20170419'
        # endTime = '20170419'
        # 当前日期
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # 单策略log字典
        self.singleStrategyLog = {}
        # # 分析起始时间
        # self.startTime = endTime+'-210000'
        # 分析结束时间
        # self.endTime = endTime+'-090000'
        # self.startTime = self.endTime
        # 捕捉字符串
        self.str1 = u'成交回报'
        self.str2 = u'标的'
        self.str3 = u'非系统'
        # 交易记录
        self.tradeList = OrderedDict()
        self.statement = OrderedDict()
        # 有效实例
        self.validateSi = []

        self.symbolInformation = {}

        # log 配置
        if not os.path.exists(self.ctaEngineLogFile):
            os.makedirs(self.ctaEngineLogFile)
        with open(self.ctaEngineLogFile+'/ctaLog','ab') as f:
            pass

        self.logger1 = logging.getLogger('statementLogger')
        self.logger1.setLevel(logging.DEBUG)
        fh = logging.handlers.RotatingFileHandler(self.statementFile+'/statementLog', mode='a', maxBytes=1024*1024)
        ch = logging.StreamHandler()
        self.logger1.addHandler(fh)
        self.logger1.addHandler(ch)

        self.loadSymbolInformation()

    #---------------------------------------------------------------------
    def loadSymbolInformation(self):
        """加载品种信息"""
        persontype = np.dtype({'names':['symbol', 'market', 'minimove', 'size', 'marginRate', 'tradecost', 'slip'],
            'formats':['S32','S32', 'f4', 'd', 'f4', 'f8', 'd']})
        with open(os.getcwd() + '/configFiles/BasicInformation.csv') as f:
            temp = np.genfromtxt(f,delimiter=',',dtype = persontype)

        for line in temp:
            line = list(line)
            self.symbolInformation[line[0]] = line[1:]

    #---------------------------------------------------------------------
    def loadLog(self,dirname):
        """加载log文件"""
        # dateList = os.listdir(self.ctaEngineLogFile)
        # self.endTime = endTime + '-090000'
        # self.startTime = self.endTime
        # startStr = self.startTime
        # endStr = self.endTime
        d = dirname
        self.tradeList = OrderedDict()
        self.endTime = dirname
        self.sLogdir = ['\AccountInstanceLog','\ContractInstanceLog']
        self.sTradedir = ['\AccountInstanceTradeList','\ContractInstanceTradeList']
        self.sCtaFile = ['\ctaLog2','\ctaLog2']
        for i in range(2):
            # for d in dateList:
                # if d >= startStr and d <= endStr:
                    # 创建策略实例log存储文件夹
            sLogPath = self.ctaEngineLogFile+'\\'+d+self.sLogdir[i]
            if not os.path.exists(sLogPath):
                os.makedirs(sLogPath)
            # 创建策略实例交易记录文件夹
            sTradePath = self.ctaEngineLogFile+'\\'+d+self.sTradedir[i]
            if not os.path.exists(sTradePath):
                os.makedirs(sTradePath)

            with open(self.ctaEngineLogFile+'\\'+d+self.sCtaFile[i]) as f:
                nt = 0
                for line in f:
                    try:
                        # 加入AccountName
                        si = line.split(':')[4]
                        an = line.split(':')[3]
                    except Exception as e:
                        continue

                    if '_' in si and 'Dummy' not in si:
                            self.writeStrategyLog(line,d+self.sLogdir[i],si,'ab')
                    else:
                        self.writeStrategyLog(line,d,'system','ab')

                    line = unicode(line,"utf-8")
                    si = line.split(':')[4]

                    if si and u'Dummy' not in si:
                        if si not in self.singleStrategyLog.keys():
                            self.singleStrategyLog[si] = {}
                            self.singleStrategyLog[si]['log'] = []
                            self.singleStrategyLog[si]['longPosition'] = []
                            self.singleStrategyLog[si]['shortPosition'] = []
                            self.singleStrategyLog[si]['longPrice'] = []
                            self.singleStrategyLog[si]['shortPrice'] = []
                            self.singleStrategyLog[si]['longProfit'] = []
                            self.singleStrategyLog[si]['shortProfit'] = []

                        self.singleStrategyLog[si]['log'].append(line)

                        # 成交回报
                        if self.str1 in line and self.str3 not in line:
                            nt = nt + 1
                            if nt == 1:
                                self.tradeList[self.sLogdir[i][1:]] = [
                                    [u'时间', u'账户', u'策略实例', u'策略类', u'标的', u'方向', u'开平', u'成交量', u'成交价']]
                            temp = []
                            for strc in line.split(','):
                                if self.str1 in strc:
                                    temp.append(strc[:19]) #strc[:8]
                                    temp.extend([strc.split(':')[j] for j in range(3,5)])
                                    temp.append(temp[2].split('_', 1)[0])
                                else:
                                    temp.append(strc.split('--')[-1].strip())
                            self.writeCsv(sTradePath+'/'+si,temp,'ab')
                            self.tradeList[self.sLogdir[i][1:]].append(temp)
                    else:
                        pass
            # self.writePosFile(d,self.tradeList)
            self.writeTradeList(d,self.tradeList) #ctaTradeList.xls
    #----------------------------------------------------------------------
    def writePosFile(self,date,posHolding):
        # for line in range(len(posHolding)):
        posPath =  self.ctaEngineLogFile + '/ctaPosFile' + '//' + posHolding[0] + '.txt'
        try:
            with open(posPath,'a') as f:
                s = ','.join([str(x) for x in posHolding])
                f.write( s + '\n')
        except Exception as e:
            print e

    #----------------------------------------------------------------------
    def writeCsv(self,filePath,data2Write,mode):
        """写csv"""
        temp = filePath.split('/')[-1]
        temp1 = filePath.replace(temp,'')
        if not os.path.exists(temp1):
            os.makedirs(temp1)
        with open (filePath,mode) as f:
            tw = csv.writer(f, delimiter=',')
            tw.writerows([data2Write])

    #----------------------------------------------------------------------
    def writeTradeList(self,date,data2Write):
        """写入交易记录
        加入账户和策略实例,分为3个sheet,策略实例、账户实例、账户合约"""

        if not os.path.exists(self.ctaEngineLogFile+'/'+date):
            os.makedirs(self.ctaEngineLogFile+'/'+date)

        try:
            with open (self.ctaEngineLogFile+'/'+date+'/'+'ctaTradeList.xls','wb') as f:
                pyexcel_xls.save_data(f,data2Write)
        except Exception as e:
            print e

    #----------------------------------------------------------------------
    def writeStrategyLog(self,logList,date,si,mode):
        """保存策略单独log"""

        try:
            with open(self.ctaEngineLogFile+'/'+date+'/'+'ctalog_'+si,mode) as f:
                f.write(logList)
        except Exception as e:
            # print logList
            return

    # ----------------------------------------------------------------------
    # def clearPosHisFile(self,id):
    #     """清理标的历史持仓信息"""
    #     d1 = datetime(2017,4,1)
    #     d2 = datetime(2017,4,10)
    #     posPath = self.ctaEngineLogFile + '/ctaPosFile' + '//' + id + '.txt'
    #     personaltype = np.dtype({'names': ['id', 'date', 'TLong', 'TShort', 'YLong', 'YShort'],
    #                              'formats': ['S40', 'S20', 'f', 'f', 'f', 'f']})
    #     curr_day = d1
    #     data = []
    #     if os.path.exists(posPath):
    #         with open(posPath,'r') as f:
    #             OFile = np.loadtxt(f,dtype = personaltype,delimiter=",")
    #             if OFile.shape:
    #                 OFile = OFile.tolist()
    #                 while (d2 - curr_day).days > 0:
    #                     for line in OFile:
    #                         if line[1][:9] == curr_day.strftime('%Y%m%d'):
    #                             OFile.remove(line)
    #                     curr_day = curr_day + timedelta(days = 1)
    #             # data_OFile = OFile
    #         for i in range(len(OFile)):
    #             s = ','.join([str(x) for x in OFile[i]])
    #             data.append(s)
    #         with open(posPath, 'w') as f:
    #             # data = [line + '\n' for line in data]
    #             f.writelines(data)

    # ----------------------------------------------------------------------
    def loadPosHolding(self,id):
        """载入当前id的前一日持仓信息"""
        personaltype = np.dtype({'names': ['id','date', 'Long', 'Short','lastPrice','profit'],
                               'formats': ['S40','S20','f', 'f','f','f']})

        if not os.path.exists(self.ctaEngineLogFile+'\ctaPosFile'):
            os.makedirs(self.ctaEngineLogFile+'\ctaPosFile')
        try:
            with open(self.ctaEngineLogFile+'\ctaPosFile' + '\''+id + '.txt','rb') as f:
                POSFile = np.loadtxt(f, dtype=personaltype, delimiter=",")
                f.close()
        except Exception as e:
            POSFile = np.array([[id,'0', 0.0, 0.0, 0.0, 0.0]])

        try:
            POSFile = POSFile[-1].tolist()
        except:
            POSFile = POSFile.tolist()
        return POSFile
    #----------------------------------------------------------------------
    def loadTradeHolding(self,lastPrice):
        """读取交易记录"""
        LTKdata = list(lastPrice)
        try:
            tradeData = pyexcel_xls.get_data(self.ctaEngineLogFile+'/'+self.endTime+'/'+'ctaTradeList.xls')
            ail = tradeData['AccountInstanceLog']

        except Exception as e:
            print e

        for n in range(len(ail)):
            if n > 0:
                ail[n].append(ail[n][1] + '_' + ail[n][2])
        ail = ail[1:]
        posHolding = [] #记录所有标的持仓信息
        IDList = []
        prePrice = {} #记录标的前一日价格
        for line in range(len(ail)):
            if ail[line][-1] not in IDList:
                ypos = self.loadPosHolding(ail[line][-1])
                prePrice[ypos[0]] = float(ypos[-2])
                ypos = ypos[:4]
                IDList.append(ail[line][-1])
            else:
                for idx, val in enumerate(posHolding):
                    if ail[line][-1] in val[0]:
                        ypos = val[:4]
                        del posHolding[idx]

            temp = []
            temp.extend(ypos)
            temp[1] = self.endTime[:8] #修改日期

            if unicode('多',"utf8") in ail[line][5]:
                if unicode('开仓',"utf8") in ail[line][6]:
                    temp[2] = float(temp[2]) + float(ail[line][7])
                elif unicode('平',"utf8") in ail[line][6]:
                    continue
                    # temp[2] = float(temp[2]) - float(ail[line][7])

            elif unicode('空',"utf8") in ail[line][5]:
                if unicode('开仓',"utf8") in ail[line][6]:
                    temp[3] = float(temp[3]) + float(ail[line][7])
                elif unicode('平',"utf8") in ail[line][6]:
                    continue
                    # temp[3] = float(temp[3]) - float(ail[line][7])

            symbol = ''.join(re.findall(r'[a-z]', ail[line][4].lower()))
            lastPriceData = self.qryLastTick(LTKdata,symbol)
            temp.append(lastPriceData)
            temp.append(0.0)
            posHolding.append(temp)
        for i in posHolding:
            trade = self.initTradeList()
            symbol = i[0].split('_',2)[2]
            TProfit = self.calculateSingeldayCapital(float(i[2]),float(i[3]),trade,prePrice[i[0]],i[4],symbol)
            i[5] = TProfit
            self.writePosFile(self.endTime,i)
    # ----------------------------------------------------------------------
    def qryLastTick(self,pricedata,conid):
        try:
            for i in pricedata:
                if i['vtSymbol'] == unicode('a00',"utf8"):  #a00为测试vt，后期根据需要修改
                    return float(i['lastPrice'])
                else:
                    continue
        except:
            return 0.0
    # ----------------------------------------------------------------------
    def initTradeList(self):
        tradeList = []
        for line in self.tradeList['AccountInstanceLog'][1:]:
            tradeList.append(TempTradeData(line[8],line[7],line[6],line[5],line[0],line[4]))
        return tradeList
    # ----------------------------------------------------------------------
    def calculateSingeldayCapital(self, longPos, shortPos, tradeList, previousPrice, currentPrice,symbolO):
        """计算单个标的,单日资产权益"""

        # symbol = ''.join(re.findall(r'[a-z]', symbolO.lower()))
        tempCaptial = []
        symbol = ''.join(re.findall(r'[a-z]', symbolO.lower()))
        cSymbolInfo = self.symbolInformation[symbol]
        size = cSymbolInfo[2]
        rate = cSymbolInfo[4]

        if tradeList:
            
            for trade in tradeList:
                if rate > 0.1:
                    tradeCost = -trade.volume*rate
                else:
                    tradeCost = -trade.price*size*trade.volume*rate
                if trade.offset == OFFSET_CLOSE or trade.offset == OFFSET_CLOSEYESTERDAY or trade.offset == OFFSET_CLOSETODAY:
                    if trade.direction == DIRECTION_LONG and shortPos > 0:
                        tempC = (previousPrice - trade.price)*trade.volume*size + tradeCost
                        tempCaptial.append(tempC)
                        shortPos = shortPos - trade.volume
                    elif trade.direction == DIRECTION_SHORT and longPos > 0:
                        tempC = (trade.price - previousPrice)*trade.volume*size + tradeCost
                        tempCaptial.append(tempC)
                        longPos = longPos - trade.volume
                    else:
                        # print DIRECTION_LONG, DIRECTION_SHORT, trade.direction, trade.direction == DIRECTION_SHORT,longPos > 0
                        self.writeCtaLogFile(OFFSET_CLOSE+' wrong:'+trade.tradeTime)
                        pass
                elif trade.offset == OFFSET_OPEN:
                    if trade.direction == DIRECTION_LONG:
                        previousPrice = (previousPrice*longPos + trade.price*trade.volume) /(longPos+trade.volume)
                        longPos = longPos + trade.volume
                        tempCaptial.append(tradeCost)
                    elif trade.direction == DIRECTION_SHORT:
                        previousPrice = (previousPrice*shortPos + trade.price*trade.volume) / (shortPos+trade.volume)
                        shortPos = shortPos + trade.volume
                        tempCaptial.append(tradeCost)
                    else:
                        self.writeCtaLogFile(OFFSET_OPEN+' wrong:'+trade.tradeTime)
                        pass
                else:
                    # print trade.offset, OFFSET_OPEN, OFFSET_CLOSE
                    self.writeCtaLogFile('wrong:'+trade.tradeTime)#
                    pass

        if longPos > 0:
            tempC = (currentPrice - previousPrice) * longPos * size
            tempCaptial.append(tempC)
        elif shortPos > 0:
            tempC = (previousPrice - currentPrice) * shortPos * size
            tempCaptial.append(tempC)
        else:
            pass

        return sum(tempCaptial)

    # ----------------------------------------------------------------------
    def backupHisPos(self):
        if not os.path.exists(self.ctaHisPosFile):
            os.makedirs(self.ctaHisPosFile)
        valList = self.loadCTASetting()
        for i in os.walk(self.ctaCurrPosFile):
            if len(i[-1]) > 0 and 'txt' in i[-1][0]:
                for j in i[-1] :
                    if j.split('_', 1)[-1][:-4] in valList:
                        os.rename(i[0] + '/' + j, i[0] + '/his/' + j)

    # ---------------------------------------------------------------------
    def loadCTASetting(self):
        try:
            with open(self.ctaSettingFile + '\\' + 'CTA_SETTING.json') as f:
                d = json.load(f)
                self.validateSi.append([d[i]['name'] for i in d.keys()])
                return self.validateSi
        except Exception as e:
            print e
            return []

    #----------------------------------------------------------------------
    def calculateNetCurve(self,netDict,initC):
        """计算所需的各种净值相关数据"""
        dateList = []
        netList = []
        outCome = {}
        for k in netDict.keys():
            dateList.append(k)
        dateList.sort()
        for date in dateList:
            netList.append(netDict[date])

        diffRet = []
        for net in netList:
            diffRet.append(net/1.0/initC)

        tempCaptial = np.cumsum(netList)

        e = self.evaluatingNetCurve(diffRet)
        e['terminalNet'] = tempCaptial[-1]
        e['terminalRet'] = tempCaptial[-1]/initC

        showN = 20
        n = len(dateList)

        fig = plt.figure(figsize=(8,4))
        plt.plot(range(n),tempCaptial,label="netCurve",color="red",linewidth=2,linestyle="-", marker="o")
        ax = plt.gca()
        if n < showN:
            ax.set_xticks(np.linspace(0,n-1,n))
            ax.set_xticklabels(dateList)
        else:
            ax.set_xticks(np.linspace(0,n-1,showN))
            index = list(np.linspace(0,n-1,showN))
            for i in range(len(index)):
                index[i] = int(index[i])
            index = list(set(index))
            if index[-1] < n-1:
                index.append(n-1)
            dateList1 = []
            for i in index:
                dateList1.append(dateList[i])
            ax.set_xticklabels(dateList1)

        xlabels = ax.get_xticklabels()
        for xl in xlabels:
            xl.set_rotation(90)
        plt.xlabel("Date")
        plt.ylabel("Net")
        plt.title("Selected Net Curve")
        plt.grid()
        # plt.ylim(min(tempCaptial)-10,max(tempCaptial)+10)
        plt.show()

        return e
    #----------------------------------------------------------------------
    def evaluatingNetCurve(self,diffRet):
        risklessR = 0
        annualDays = 240
        e = {}
        e['annualRet'] = round(np.mean(diffRet)*annualDays, 3)*100
        e['sharp'] = round(np.mean(diffRet)/np.std(diffRet)*np.sqrt(annualDays), 3)
        RetNeg = [pow(x-risklessR/annualDays, 2) for x in diffRet if x < 0]
        DDneg = sum(RetNeg) / (len(diffRet) - 1)
        e['sortino'] = round((np.mean(diffRet) * 240 - risklessR) / np.sqrt(DDneg * 240), 3)
        cumRet = np.cumsum(diffRet)
        drawdown = []
        drawdownDay = []
        drawdown.append(0)
        drawdownDay.append(0)
        for i in range(1,len(cumRet)):
            temp = cumRet[i] - max(cumRet[:i+1])
            drawdown.append(temp)
            if temp < 0:
                drawdownDay.append(drawdownDay[-1]+1)
            else:
                drawdownDay.append(0)
        e['maxDrawdown'] = min(drawdown)*-100
        e['meanDrawdown'] = np.mean(drawdown)*-100
        e['maxDrawdownDay'] = max(drawdownDay)
        e['meanDrawdownDay'] = np.mean(drawdownDay)
        # e['totalHoldingDay'] = len([x for x in self.dayCapital if x != 0])/len(self.dayCapital)

        return e

    #----------------------------------------------------------------------
    # def genNetData(self,path):
    #     """生成净值曲线数据"""
    #     if os.path.isfile(path):
    #         netDict = self.sumNet([path])
    #     else:
    #         netDict = self.sumNet(self.pathIter(path))
    #     return netDict  # netDict以日期为key，净值为value的字典，不包含任何策略信息

    #----------------------------------------------------------------------
    # def pathIter(self,path):
    #     """文件查询迭代函数"""
    #     pathList = []
    #     path1 = os.listdir(path)
    #     for p in path1:
    #         if os.path.isfile(path+'/'+p):
    #             pathList.append(path+'/'+p)
    #         else:
    #             pathList = pathList + self.pathIter(path+'/'+p)
    #     return list(set(pathList))

    #----------------------------------------------------------------------
    def sumNet(self,filePathList,sum_sign):
        """加总曲线净值"""
        netDict = {}
        dateList = []
        for netf in filePathList:
            netDict[netf] = {}
            with open(netf,'rb') as f:
                temp = f.readlines()
                for line in temp:
                    netDict[netf][line.split(',')[0]] = float(line.split(',')[4].strip())
                    dateList.append(line.split(',')[0])
        dateList = list(set(dateList))
        dateList.sort()
        netOut = {}
        for d in dateList:
            temp = []
            for v in netDict.values():
                try:
                    temp.append(v[d])
                except Exception as e:
                    temp.append(0)

            netOut[d] = sum(temp) if sum_sign else temp

        return netOut

    #----------------------------------------------------------------------
    def writeCtaLogFile(self, content):
        """快速发出CTA模块日志事件"""
        content = '\t'.join([str(datetime.now()), content])
        # print content
        self.logger1.info(content)


class TempTradeData(object):
    def __init__(self,price,volume,offset,direction,tradeTime,symbol):
        self.symbol = symbol
        self.price = float(price.encode('utf-8'))
        self.volume = float(volume.encode('utf-8'))
        self.offset = offset
        self.direction = direction
        self.tradeTime = tradeTime

def main():
    endStr = datetime.now().strftime('%Y%m%d')
    startStr = (datetime.now()-timedelta(days=1)).strftime('%Y%m%d')
    test = PostAnalysis()
    test.loadLog()
    # test.tradeCacheLoad()
    # test.writeStatement()



if __name__ == '__main__':
    main()

