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
from collections import OrderedDict, defaultdict
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

    ctaSettingFile = os.path.abspath(os.path.join(os.path.dirname('ctaLogFile'), os.pardir, os.pardir)) + 'vn.trader\\algoConfig'
    #---------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """初始化"""
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # 单策略log字典
        self.singleStrategyLog = {}

        self.str1 = u'成交回报'
        self.str2 = u'标的'
        self.str3 = u'非系统'
        # 交易记录
        self.tradeList = OrderedDict()
        self.statement = OrderedDict()
        # 有效实例
        self.validateSi = []

        self.symbolInformation = {}

        self.logger1 = logging.getLogger('statementLogger')
        self.logger1.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
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
    def loadLog(self,dirname, LogFile):
        """加载log文件"""
        d = dirname
        self.ctaEngineLogFile = LogFile
        if not os.path.exists(self.ctaEngineLogFile):
            os.makedirs(self.ctaEngineLogFile)									 
											  
        self.tradeList = OrderedDict()
        self.endTime = dirname
        self.sLogdir = ['\AccountInstanceLog','\ContractInstanceLog']
        self.sTradedir = ['\AccountInstanceTradeList','\ContractInstanceTradeList']
        self.sCtaFile = ['\ctaLog2','\ctaLog2']
        for i in range(2):
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
            self.writeTradeList(d,self.tradeList) #ctaTradeList.xls
    #----------------------------------------------------------------------
    def writePosFile(self,date,posHolding):

        Conid = posHolding[1]
        posPath =  self.ctaEngineLogFile + '/ctaPosFile' + '//' + posHolding[0] + '//' + Conid + '.txt'
        truncateSign = False
        if os.path.exists(posPath):
            with open(posPath, 'rb') as f:
                POS = f.readline()
                if POS:
                    if not self.compare_dateTime(posHolding[2], POS.split(',')[1]):
                        truncateSign = True

        try:
            with open(posPath,'a') as f:
                if truncateSign:
                    f.truncate()
                s = ','.join([str(x) for x in posHolding[1:]])
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
    def loadPosHolding(self,id,conid):
        """载入当前id的前一日持仓信息"""
        personaltype = np.dtype({'names': ['id', 'date', 'Long', 'Short', 'lastPrice', 'profit'],
                                 'formats': ['S40', 'S20', 'f', 'f', 'f', 'f']})
        filePath = self.ctaEngineLogFile + '\ctaPosFile' + '\\' + str(id)
        if not os.path.exists(filePath):
            os.makedirs(filePath)
        try:
            with open(filePath + '\\' + str(conid) + '.txt', 'rb') as f:
                POSFile = np.loadtxt(f, dtype=personaltype, delimiter=",")
                f.close()
        except Exception as e:
            POSFile = np.array([[conid, '0', 0.0, 0.0, 0.0, 0.0]])

        try:
            for i in range(1, len(POSFile)+1):
                if not self.compare_dateTime(self.endTime[:8], POSFile[-i][1]):
                    continue
                else:
                    POSFile = POSFile[-i].tolist()
        except:
            POSFile = POSFile.tolist()
        return POSFile

    #----------------------------------------------------------------------
    def loadTradeHolding(self,lastPrice):
        """读取交易记录"""
        LTKdata = list(lastPrice)
        try:
            tradeData = pyexcel_xls.get_data(self.ctaEngineLogFile+'/'+self.endTime+'/'+'ctaTradeList_1.xls')
            ail = tradeData['AccountInstanceLog']

        except Exception as e:
            print e

        for n in range(len(ail)):
            if n > 0:
                ail[n].append(ail[n][1] + '_' + ail[n][2])
        ail = ail[1:]
        posHolding = [] #记录所有标的持仓信息[InstID,ConID,date,long,short,lastprice,profit]
        IDList = [] #InstID + Conid 作为ID标志
        ypos = {} #记录标的前一日posholding
        for line in range(len(ail)):
            InstID = ail[line][-1]
            ConID = ail[line][4]
            ypos1 = []
            if str(InstID) + '_' + str(ConID) not in IDList:
                if not ypos.has_key(InstID):
                    ypos[InstID] = {}
                ypos[InstID][ConID] = self.loadPosHolding(InstID, ConID)
                ypos1.append(InstID)
                ypos1.extend(ypos[InstID][ConID][:4])
                IDList.append(str(InstID) + '_' + str(ConID))
            else:
                for idx, val in enumerate(posHolding):
                    if InstID in val[0] and ConID in val[1]:
                        ypos1 = val[:5]
                        del posHolding[idx]

            temp = []
            temp.extend(ypos1)
            temp[2] = self.endTime[:8] #修改日期

            if unicode('多',"utf8") in ail[line][5]:
                if unicode('开仓',"utf8") in ail[line][6]:
                    temp[3] = float(temp[3]) + float(ail[line][7])
                elif unicode('平',"utf8") in ail[line][6]:
                    # continue
                    temp[3] = float(temp[3]) - float(ail[line][7])

            elif unicode('空',"utf8") in ail[line][5]:
                if unicode('开仓',"utf8") in ail[line][6]:
                    temp[4] = float(temp[4]) + float(ail[line][7])
                elif unicode('平',"utf8") in ail[line][6]:
                    # continue
                    temp[4] = float(temp[4]) - float(ail[line][7])

            lastPriceData = self.qryLastTick(LTKdata,ConID)
            temp.append(lastPriceData)
            temp.append(0.0)
            posHolding.append(temp)
        for i in posHolding:
            trade = self.initTradeList(i[0], i[1], ail)
            TProfit = self.calculateSingeldayCapital(float(ypos[i[0]][i[1]][2]),float(ypos[i[0]][i[1]][3]),trade,float(ypos[i[0]][i[1]][4]),i[5],i[1])
            i[6] = TProfit
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
    def initTradeList(self,id,conid,ail):
        tradeList = []
        for line in ail:
            if line[1] + '_' + line[2] == id and line[4] == conid:
                tradeList.append(TempTradeData(line[8],line[7],line[6],line[5],line[0],line[4]))
        return tradeList
    # ----------------------------------------------------------------------
    def calculateSingeldayCapital(self, longPos, shortPos, tradeList, previousPrice, currentPrice,symbolO):
        """计算单个标的,单日资产权益"""

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
        self.ctaHisPosFile = self.ctaEngineLogFile + '/' + 'his'
        if not os.path.exists(self.ctaHisPosFile):
            os.makedirs(self.ctaHisPosFile)
        valList = self.loadCTASetting()
        for i in os.walk(self.ctaHisPosFile + '/' + 'ctaPosFile'):
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
    def calculateNetCurve(self,netDict,initC,sign_sum):
        """计算所需的各种净值相关数据"""
        dateList = []
        tree = lambda:defaultdict(tree)

        for id in netDict.values():
            for date in id.keys():
                if date not in dateList:
                    dateList.append(date)

        netList = tree()
        diffRet = tree()
        tempCapital = tree()
        # temp = tree()
        e = tree()
        for id in netDict.keys():
            for date in dateList:
                if netDict[id].has_key(date):
                    netList[id][date] = netDict[id][date]
                else:
                    netList[id][date] = 0.0

                if sign_sum:
                    if netList['sum'][date] == {}:
                        netList['sum'][date] = 0.0
                    netList['sum'][date] += netList[id][date]

        for id in netList.keys():
            diffRet[id] = []
            tempCapital[id] = []
            for net in netList[id].values():
                diffRet[id].append(float(net)/1.0/initC)
            x = np.cumsum(diffRet[id])
            for i in x:
                tempCapital[id].append(i)

        # n = len(dateList)
        for id in diffRet.keys():
            e[id] = self.evaluatingNetCurve(diffRet[id])
            e[id]['terminalNet'] = tempCapital[id][-1]
            e[id]['terminalRet'] = tempCapital[id][-1]/initC
        return dateList, tempCapital, e
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
        return e
    #----------------------------------------------------------------------
    def sumNet(self,filePathList):
        """加总曲线净值"""
        #针对单策略实例多标的的情况，取sum作为实例net
        netDict = {}
        for netf in filePathList:
            InstID = netf.split('\\')[-1]
            netDict[InstID] = {}
            files = os.listdir(netf)
            for file in files:
                with open(netf + '\\' + file,'rb') as f:
                    temp = f.readlines()
                    for line in temp:
                        if not netDict[InstID].has_key(line.split(',')[1]):
                            netDict[InstID][line.split(',')[1]] = float(line.split(',')[5].strip())
                        else:
                            netDict[InstID][line.split(',')[1]] += float(line.split(',')[5].strip())


        return netDict

    #----------------------------------------------------------------------
    def writeCtaLogFile(self, content):
        """快速发出CTA模块日志事件"""
        content = '\t'.join([str(datetime.now()), content])
        # print content
        self.logger1.info(content)

    def string_toDatetime(self, string):
        """把字符串转成datetime"""
        return datetime.strptime(string, "%Y%m%d")

    def compare_dateTime(self, dateStr1, dateStr2):
        """两个日期的比较"""
        date1 = self.string_toDatetime(dateStr1)
        date2 = self.string_toDatetime(dateStr2)
        return date1.date() > date2.date()

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

