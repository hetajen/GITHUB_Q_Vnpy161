# encoding: UTF-8

"""
本模块中主要包含：
1. 从通联数据下载历史行情的引擎
2. 用来把MultiCharts导出的历史数据载入到MongoDB中用的函数
3. 增加从通达信导出的历史数据载入到MongoDB中的函数

History
<id>            <author>        <description>
2017050301      hetajen         DB[CtaTemplate增加日线bar数据获取接口][Mongo不保存Tick数据][新增数据来源Sina]
2017052500      hetajen         DB[增加：5分钟Bar数据的记录、存储和获取]
"""

'''2017052500 Add by hetajen begin'''
import os
import datetime
import time
import pymongo
'''2017052500 Add by hetajen end'''
from multiprocessing.pool import ThreadPool

from ctaBase import *
from vtConstant import *
from vtFunction import loadMongoSetting
from datayesClient import DatayesClient
'''2017050301 Add by hetajen begin'''
import json
import urllib
'''2017050301 Add by hetajen end'''

# 以下为vn.trader和通联数据规定的交易所代码映射 
VT_TO_DATAYES_EXCHANGE = {}
VT_TO_DATAYES_EXCHANGE[EXCHANGE_CFFEX] = 'CCFX'     # 中金所
VT_TO_DATAYES_EXCHANGE[EXCHANGE_SHFE] = 'XSGE'      # 上期所 
VT_TO_DATAYES_EXCHANGE[EXCHANGE_CZCE] = 'XZCE'       # 郑商所
VT_TO_DATAYES_EXCHANGE[EXCHANGE_DCE] = 'XDCE'       # 大商所
DATAYES_TO_VT_EXCHANGE = {v:k for k,v in VT_TO_DATAYES_EXCHANGE.items()}


########################################################################
class HistoryDataEngine(object):
    """CTA模块用的历史数据引擎"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        host, port, logging = loadMongoSetting()
        
        self.dbClient = pymongo.MongoClient(host, port)
        self.datayesClient = DatayesClient()
        
    #----------------------------------------------------------------------
    def lastTradeDate(self):
        """获取最近交易日（只考虑工作日，无法检查国内假期）"""
        '''2017052500 Add by hetajen begin'''
        today = datetime.datetime.now()
        oneday = datetime.timedelta(1)
        '''2017052500 Add by hetajen end'''
        
        if today.weekday() == 5:
            today = today - oneday
        elif today.weekday() == 6:
            today = today - oneday*2        
        
        return today.strftime('%Y%m%d')

    # ----------------------------------------------------------------------
    '''2017052500 Add by hetajen begin'''
    def loadTradeCal(self):
        print u'Trade Calendar load from csv, BEGIN'

        '''数据库'''
        dbName = SETTING_DB_NAME
        collectionName = TRADECAL_CL_NAME
        collection = self.dbClient[dbName][collectionName]
        collection.ensure_index([('calendarDate', pymongo.ASCENDING)], unique=True) # 创建索引
        # 查询数据库中已有数据的最后日期
        cx = collection.find(sort=[('calendarDate', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0][u'calendarDate']
        else:
            last = datetime.datetime(1990, 12, 31, 23, 59, 59)

        '''数据源'''
        import csv
        fileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), u'strategy\\tradeCal.csv')
        reader = csv.reader(file(fileName, 'r'))

        '''数据解析&持久化'''
        calendarsTmp = []
        calendars = []
        filterHeaders = True # 过滤表头
        nextTradeDate = None
        for d in reader:
            if filterHeaders:
                filterHeaders = False
                continue

            calendarDict = {}
            calendarDict['calendarDate'] = datetime.datetime.strptime(d[1].replace('/', ''), '%Y%m%d')
            if calendarDict['calendarDate'] < last:
                continue

            calendarDict['exchangeCD'] = d[0]
            calendarDict['isOpen'] = d[2]
            if (d[3] != ''):
                calendarDict['prevTradeDate'] = datetime.datetime.strptime(d[3].replace('/', ''), '%Y%m%d')
            else:
                calendarDict['prevTradeDate'] = None
            calendarDict['isWeekEnd'] = d[4]
            calendarDict['isMonthEnd'] = d[5]
            calendarDict['isQuarterEnd'] = d[6]
            calendarDict['isYearEnd'] = d[7]
            calendarsTmp.append(calendarDict)
        calendarsTmp.reverse()

        for calendarDict in calendarsTmp:
            calendarDict['nextTradeDate'] = nextTradeDate
            calendars.append(calendarDict)
            if calendarDict['isOpen'] == '1':
                nextTradeDate = calendarDict['calendarDate']
        # calendars.reverse()

        for calendarDict in calendars:
            flt = {'calendarDate': calendarDict['calendarDate']}
            collection.update_one(flt, {'$set': calendarDict}, upsert=True)

        print u'Trade Calendar load from csv, End'

    def downloadTradeCal(self):
        print u'Trade Calendar download from datayes, BEGIN'

        '''数据库'''
        dbName = SETTING_DB_NAME
        collectionName = TRADECAL_CL_NAME
        collection = self.dbClient[dbName][collectionName]
        collection.ensure_index([('calendarDate', pymongo.ASCENDING)], unique=True) # 创建索引
        # 查询数据库中已有数据的最后日期
        cx = collection.find(sort=[('calendarDate', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0][u'calendarDate']
        else:
            last = datetime.datetime(1990, 12, 31, 23, 59, 59)

        '''数据源'''
        path = 'api/master/getTradeCal.json'
        params = {}
        # params['field'] = ''
        params['exchangeCD'] = 'XSGE'
        params['beginDate'] = unicode(last.date())
        data = self.datayesClient.downloadData(path, params)

        '''数据解析&持久化'''
        if data:
            for d in data:
                calendarDict = {}
                calendarDict['exchangeCD'] = d['exchangeCD']
                calendarDict['calendarDate'] = d['calendarDate']
                calendarDict['isOpen'] = d['isOpen']
                calendarDict['prevTradeDate'] = d['prevTradeDate']
                calendarDict['isWeekEnd'] = d['isWeekEnd']
                calendarDict['isMonthEnd'] = d['isMonthEnd']
                calendarDict['isQuarterEnd'] = d['isQuarterEnd']
                calendarDict['isYearEnd'] = d['isYearEnd']
                flt = {'calendarDate': d['calendarDate']}
                collection.update_one(flt, {'$set': calendarDict}, upsert=True)
            print u'Trade Calendar download from datayes, END'
        else:
            print u'Trade Calendar download from datayes, Wrong'
    '''2017052500 Add by hetajen end'''
    
    #----------------------------------------------------------------------
    def readFuturesProductSymbol(self):
        """查询所有期货产品代码"""
        cx = self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].find()
        return set([d['productSymbol'] for d in cx])    # 这里返回的是集合（因为会重复）
    
    #----------------------------------------------------------------------
    def readFuturesSymbol(self):
        """查询所有期货合约代码"""
        cx = self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].find()
        return [d['symbol'] for d in cx]    # 这里返回的是列表
        
    #----------------------------------------------------------------------
    def downloadFuturesSymbol(self, tradeDate=''):
        """下载所有期货的代码"""
        if not tradeDate:
            tradeDate = self.lastTradeDate()
        
        self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].ensure_index([('symbol', pymongo.ASCENDING)], 
                                                                       unique=True)
        

        path = 'api/market/getMktMFutd.json'
        
        params = {}
        params['tradeDate'] = tradeDate
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            for d in data:
                symbolDict = {}
                symbolDict['symbol'] = d['ticker']
                symbolDict['productSymbol'] = d['contractObject']
                flt = {'symbol': d['ticker']}
                
                self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].update_one(flt, {'$set':symbolDict}, 
                                                                           upsert=True)
            print u'期货合约代码下载完成'
        else:
            print u'期货合约代码下载失败'
        
    #----------------------------------------------------------------------
    def downloadFuturesDailyBar(self, symbol):
        """
        下载期货合约的日行情，symbol是合约代码，
        若最后四位为0000（如IF0000），代表下载连续合约。
        """
        print u'开始下载%s日行情' %symbol
        
        # 查询数据库中已有数据的最后日期
        cl = self.dbClient[DAILY_DB_NAME][symbol]
        cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0]
        else:
            last = ''
        
        # 主力合约
        if '0000' in symbol:
            path = 'api/market/getMktMFutd.json'
            
            params = {}
            params['contractObject'] = symbol.replace('0000', '')
            params['mainCon'] = 1
            if last:
                params['startDate'] = last['date']
        # 交易合约
        else:
            path = 'api/market/getMktFutd.json'
            
            params = {}
            params['ticker'] = symbol
            if last:
                params['startDate'] = last['date']
        
        # 开始下载数据
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            # 创建datetime索引
            self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                      unique=True)                

            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d.get('openPrice', 0)
                    bar.high = d.get('highestPrice', 0)
                    bar.low = d.get('lowestPrice', 0)
                    bar.close = d.get('closePrice', 0)
                    bar.date = d.get('tradeDate', '').replace('-', '')
                    bar.time = ''
                    '''2017052500 Add by hetajen begin'''
                    bar.datetime = datetime.datetime.strptime(bar.date, '%Y%m%d')
                    '''2017052500 Add by hetajen end'''
                    bar.volume = d.get('turnoverVol', 0)
                    bar.openInterest = d.get('openInt', 0)
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
                print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol
            
    #----------------------------------------------------------------------
    def downloadAllFuturesDailyBar(self):
        """下载所有期货的主力合约日行情"""
        '''2017052500 Add by hetajen begin'''
        start = time.time()
        '''2017052500 Add by hetajen end'''
        print u'开始下载所有期货的主力合约日行情'
        
        productSymbolSet = self.readFuturesProductSymbol()
        
        print u'代码列表读取成功，产品代码：%s' %productSymbolSet
        
        # 这里也测试了线程池，但可能由于下载函数中涉及较多的数据格
        # 式转换，CPU开销较大，多线程效率并无显著改变。
        #p = ThreadPool(10)
        #p.map(self.downloadFuturesDailyBar, productSymbolSet)
        #p.close()
        #p.join()
        
        for productSymbol in productSymbolSet:
            self.downloadFuturesDailyBar(productSymbol+'0000')

        '''2017052500 Add by hetajen begin'''
        print u'所有期货的主力合约日行情已经全部下载完成, 耗时%s秒' %(time.time()-start)
        '''2017052500 Add by hetajen end'''
        
    #----------------------------------------------------------------------
    def downloadFuturesIntradayBar(self, symbol):
        """下载期货的日内分钟行情"""
        print u'开始下载%s日内分钟行情' %symbol
                
        # 日内分钟行情只有具体合约
        path = 'api/market/getFutureBarRTIntraDay.json'
        
        params = {}
        params['instrumentID'] = symbol
        params['unit'] = 1
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            '''2017052500 Add by hetajen begin'''
            today = datetime.datetime.now().strftime('%Y%m%d')
            '''2017052500 Add by hetajen end'''
            
            # 创建datetime索引
            self.dbClient[MINUTE_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                      unique=True)                

            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d.get('openPrice', 0)
                    bar.high = d.get('highestPrice', 0)
                    bar.low = d.get('lowestPrice', 0)
                    bar.close = d.get('closePrice', 0)
                    bar.date = today
                    bar.time = d.get('barTime', '')
                    '''2017052500 Add by hetajen begin'''
                    bar.datetime = datetime.datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M')
                    '''2017052500 Add by hetajen end'''
                    bar.volume = d.get('totalVolume', 0)
                    bar.openInterest = 0
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[MINUTE_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
            print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol   

    #----------------------------------------------------------------------
    def downloadEquitySymbol(self, tradeDate=''):
        """下载所有股票的代码"""
        if not tradeDate:
            tradeDate = self.lastTradeDate()
        
        self.dbClient[SETTING_DB_NAME]['EquitySymbol'].ensure_index([('symbol', pymongo.ASCENDING)], 
                                                                       unique=True)
        

        path = 'api/market/getMktEqud.json'
        
        params = {}
        params['tradeDate'] = tradeDate
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            for d in data:
                symbolDict = {}
                symbolDict['symbol'] = d['ticker']
                flt = {'symbol': d['ticker']}
                
                self.dbClient[SETTING_DB_NAME]['EquitySymbol'].update_one(flt, {'$set':symbolDict}, 
                                                                           upsert=True)
            print u'股票代码下载完成'
        else:
            print u'股票代码下载失败'
        
    #----------------------------------------------------------------------
    def downloadEquityDailyBar(self, symbol):
        """
        下载股票的日行情，symbol是股票代码
        """
        print u'开始下载%s日行情' %symbol
        
        # 查询数据库中已有数据的最后日期
        cl = self.dbClient[DAILY_DB_NAME][symbol]
        cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0]
        else:
            last = ''
        
        # 开始下载数据
        path = 'api/market/getMktEqud.json'
            
        params = {}
        params['ticker'] = symbol
        if last:
            params['beginDate'] = last['date']
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            # 创建datetime索引
            self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                unique=True)                

            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d.get('openPrice', 0)
                    bar.high = d.get('highestPrice', 0)
                    bar.low = d.get('lowestPrice', 0)
                    bar.close = d.get('closePrice', 0)
                    bar.date = d.get('tradeDate', '').replace('-', '')
                    bar.time = ''
                    '''2017052500 Add by hetajen begin'''
                    bar.datetime = datetime.datetime.strptime(bar.date, '%Y%m%d')
                    '''2017052500 Add by hetajen end'''
                    bar.volume = d.get('turnoverVol', 0)
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
            print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol    
        


#----------------------------------------------------------------------
'''2017050301 Add by hetajen begin'''
class XH_HistoryDataEngine(object):
    """CTA模块用的历史数据引擎"""
    def __init__(self):
        """Constructor"""
        host, port, logging = loadMongoSetting()
        self.dbClient = pymongo.MongoClient(host, port)

    '''2017052500 Add by hetajen begin'''
    def downloadFutures5MinBarSina(self, symbol):
        print u'5minBar download from sina, BEGIN - %s' %symbol

        '''数据库'''
        dbName = MINUTE5_DB_NAME
        collectionName = symbol
        collection = self.dbClient[dbName][collectionName]
        collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True) # 创建datetime索引
        # 查询数据库中已有数据的最后日期
        cx = collection.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0][u'datetime']
        else:
            last = datetime.datetime(1990, 12, 31, 23, 59, 59)

        '''数据源'''
        if '888' in symbol: # 主力合约
            url = '%s%s' % (URL_SINA_HIST_M5, symbol.replace('888', '0'))
        else:               # 交易合约
            url = '%s%s' % (URL_SINA_HIST_M5, symbol)
        html = urllib.urlopen(url).read().decode('gb2312')
        data = json.loads(html)
        data.reverse() # 按时间递增顺序在collection中appand Bar数据（Sina接口获取的5min线数据为减序，故需要reverse）

        '''数据解析&持久化'''
        if data:
            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.datetime = datetime.datetime.strptime(d[SINA_DATE], '%Y-%m-%d %H:%M:%S')
                    bar.datetime = bar.datetime - datetime.timedelta(minutes=5)  # Sina接口的数据有误，So要对5分钟Bar的时间数据进行清洗
                    if bar.datetime < last:
                        continue

                    # bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d[SINA_O]
                    bar.high = d[SINA_H]
                    bar.low = d[SINA_L]
                    bar.close = d[SINA_C]

                    bar.date = bar.datetime.strftime('%Y%m%d')
                    bar.time = bar.datetime.strftime('%H:%M:%S')
                    bar.actionDay = bar.date
                    if bar.datetime.time() > datetime.time(hour=20, minute=0):
                        '''数据库'''
                        cl = self.dbClient[SETTING_DB_NAME][TRADECAL_CL_NAME]
                        calendarDict = cl.find_one({'calendarDate':datetime.datetime.strptime(bar.date, '%Y%m%d')})
                        if calendarDict != None:
                            bar.tradingDay = calendarDict['nextTradeDate'].strftime('%Y%m%d')
                        else:
                            bar.tradingDay = bar.date
                    else:
                        bar.tradingDay = bar.date

                    # bar.volume = d[SINA_VOL]
                    # bar.openInterest = d.get('openInt', 0)
                except KeyError:
                    print d

                flt = {'datetime': bar.datetime}
                collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)

            print u'5minBar download from sina, END - %s' %symbol
        else:
            print u'5minBar download from sina, Wrong - %s' %symbol

    def downloadFuturesDailyBarSina(self, symbol):
        print u'DailyBar download from sina, BEGIN - %s' %symbol

        '''数据库'''
        dbName = DAILY_DB_NAME
        collectionName = symbol
        collection = self.dbClient[dbName][collectionName]
        collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True) # 创建datetime索引
        # 查询数据库中已有数据的最后日期
        cx = collection.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0][u'datetime']
        else:
            last = datetime.datetime(1990, 12, 31, 23, 59, 59)

        '''数据源'''
        if '888' in symbol: # 主力合约
            url = '%s%s' % (URL_SINA_HIST_D, symbol.replace('888', '0'))
        else:               # 交易合约
            url = '%s%s' % (URL_SINA_HIST_D, symbol)
        html = urllib.urlopen(url).read().decode('gb2312')
        data = json.loads(html)
        # data.reverse() # 按时间递增顺序在collection中appand Bar数据（Sina接口获取的日线数据即为增序）

        '''数据解析&持久化'''
        if data:
            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    '''2017052500 Add by hetajen begin'''
                    bar.datetime = datetime.datetime.strptime(d[SINA_DATE], '%Y-%m-%d')
                    if bar.datetime < last:
                        continue
                    '''2017052500 Add by hetajen end'''

                    # bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d[SINA_O]
                    bar.high = d[SINA_H]
                    bar.low = d[SINA_L]
                    bar.close = d[SINA_C]

                    bar.date = bar.datetime.strftime('%Y%m%d')
                    bar.time = bar.datetime.strftime('%H:%M:%S')
                    bar.actionDay = bar.date
                    bar.tradingDay = bar.date

                    # bar.volume = d[SINA_VOL]
                    # bar.openInterest = d.get('openInt', 0)
                except KeyError:
                    print d

                flt = {'datetime': bar.datetime}
                collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)
            print u'DailyBar download from sina, End - %s' %symbol
        else:
            print u'DailyBar download from sina, Wrong - %s' %symbol
    '''2017052500 Add by hetajen end'''
'''2017050301 Add by hetajen end'''


#----------------------------------------------------------------------
def downloadEquityDailyBarts(self, symbol):
        """
        下载股票的日行情，symbol是股票代码
        """
        print u'开始下载%s日行情' %symbol
        
        # 查询数据库中已有数据的最后日期
        cl = self.dbClient[DAILY_DB_NAME][symbol]
        cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0]
        else:
            last = ''
        # 开始下载数据
        import tushare as ts
        
        if last:
            start = last['date'][:4]+'-'+last['date'][4:6]+'-'+last['date'][6:]
            
        data = ts.get_k_data(symbol,start)
        
        if not data.empty:
            # 创建datetime索引
            self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                unique=True)                
            
            for index, d in data.iterrows():
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.open = d.get('open')
                    bar.high = d.get('high')
                    bar.low = d.get('low')
                    bar.close = d.get('close')
                    bar.date = d.get('date').replace('-', '')
                    bar.time = ''
                    '''2017052500 Add by hetajen begin'''
                    bar.datetime = datetime.datetime.strptime(bar.date, '%Y%m%d')
                    '''2017052500 Add by hetajen end'''
                    bar.volume = d.get('volume')
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
            print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol
#----------------------------------------------------------------------
def loadMcCsv(fileName, dbName, symbol):
    """将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
    import csv
    
    '''2017052500 Add by hetajen begin'''
    start = time.time()
    '''2017052500 Add by hetajen end'''
    print u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol)
    
    # 锁定集合，并创建索引
    host, port, logging = loadMongoSetting()
    
    client = pymongo.MongoClient(host, port)    
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   
    
    # 读取数据和插入到数据库
    reader = csv.DictReader(file(fileName, 'r'))
    for d in reader:
        bar = CtaBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = float(d['Open'])
        bar.high = float(d['High'])
        bar.low = float(d['Low'])
        bar.close = float(d['Close'])
        '''2017052500 Add by hetajen begin'''
        bar.date = datetime.datetime.strptime(d['Date'], '%Y-%m-%d').strftime('%Y%m%d')
        bar.time = d['Time']
        bar.datetime = datetime.datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        '''2017052500 Add by hetajen end'''
        bar.volume = d['TotalVolume']

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
        print bar.date, bar.time
    
    '''2017052500 Add by hetajen begin'''
    print u'插入完毕，耗时：%s' % (time.time()-start)
    '''2017052500 Add by hetajen end'''

#----------------------------------------------------------------------
def loadTdxCsv(fileName, dbName, symbol):
    """将通达信导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    import csv
    
    '''2017052500 Add by hetajen begin'''
    start = time.time()
    '''2017052500 Add by hetajen end'''
    print u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol)
    
    # 锁定集合，并创建索引
    host, port, logging = loadMongoSetting()
    
    client = pymongo.MongoClient(host, port)    
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   
    
    # 读取数据和插入到数据库
    reader = csv.reader(file(fileName, 'r'))
    for d in reader:
        bar = CtaBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.open = float(d[2])
        bar.high = float(d[3])
        bar.low = float(d[4])
        bar.close = float(d[5])
        '''2017052500 Add by hetajen begin'''
        bar.date = datetime.datetime.strptime(d[0], '%Y/%m/%d').strftime('%Y%m%d')
        bar.time = d[1][:2]+':'+d[1][2:4]+':00'
        bar.datetime = datetime.datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        '''2017052500 Add by hetajen end'''
        bar.volume = d[6]
        bar.openInterest = d[7]

        flt = {'datetime': bar.datetime}
        collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
        print bar.date, bar.time
    
    '''2017052500 Add by hetajen begin'''
    print u'插入完毕，耗时：%s' % (time.time()-start)
    '''2017052500 Add by hetajen end'''
    
#----------------------------------------------------------------------
def loadTBCsv(fileName, dbName, symbol):
    """将TradeBlazer导出的csv格式的历史数据插入到Mongo数据库中
        数据样本：
        //时间,开盘价,最高价,最低价,收盘价,成交量,持仓量
        2017/04/05 09:00,3200,3240,3173,3187,312690,2453850
    """
    import csv
    
    '''2017052500 Add by hetajen begin'''
    start = time.time()
    '''2017052500 Add by hetajen end'''
    print u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol)
    
    # 锁定集合，并创建索引
    host, port, logging = loadMongoSetting()
    
    client = pymongo.MongoClient(host, port)    
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)
    
    # 读取数据和插入到数据库
    reader = csv.reader(file(fileName, 'r'))
    for d in reader:
        if len(d[0]) > 10:
            bar = CtaBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            
            '''2017052500 Add by hetajen begin'''
            bar.datetime = datetime.datetime.strptime(d[0], '%Y/%m/%d %H:%M')
            '''2017052500 Add by hetajen end'''
            bar.date = bar.datetime.date().strftime('%Y%m%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')
            
            bar.open = float(d[1])
            bar.high = float(d[2])
            bar.low = float(d[3])
            bar.close = float(d[4])
            
            bar.volume = float(d[5])
            bar.openInterest = float(d[6])

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)
            print '%s \t %s' % (bar.date, bar.time)
    
    '''2017052500 Add by hetajen begin'''
    print u'插入完毕，耗时：%s' % (time.time()-start)
    '''2017052500 Add by hetajen end'''
    
    
if __name__ == '__main__':
    ## 简单的测试脚本可以写在这里
    #from time import sleep
    #e = HistoryDataEngine()
    #sleep(1)
    #e.downloadEquityDailyBar('000001')
    #e.downloadEquityDailyBarts('000001')
    
    # 这里将项目中包含的股指日内分钟线csv导入MongoDB，作者电脑耗时大约3分钟
    loadMcCsv('IF0000_1min.csv', MINUTE_DB_NAME, 'IF0000')
    #导入通达信历史分钟数据
    #loadTdxCsv('CL8.csv', MINUTE_DB_NAME, 'c0000')
