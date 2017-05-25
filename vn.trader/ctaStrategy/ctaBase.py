# encoding: UTF-8

'''
本文件中包含了CTA模块中用到的一些基础设置、类和常量等。

History
<id>            <author>        <description>
2017050301      hetajen         DB[CtaTemplate增加日线bar数据获取接口][Mongo不保存Tick数据][新增数据来源Sina]
2017051500      hetajen         夜盘tick|bar数据增加tradingDay字段，用于指明夜盘tick|bar数据的真实交易日
2017052500      hetajen         DB[增加：5分钟Bar数据的记录、存储和获取]
'''

from __future__ import division


# 把vn.trader根目录添加到python环境变量中
import sys
sys.path.append('..')


# 常量定义
# CTA引擎中涉及到的交易方向类型
CTAORDER_BUY = u'买开'
CTAORDER_SELL = u'卖平'
CTAORDER_SHORT = u'卖开'
CTAORDER_COVER = u'买平'

# 本地停止单状态
STOPORDER_WAITING = u'等待中'
STOPORDER_CANCELLED = u'已撤销'
STOPORDER_TRIGGERED = u'已触发'

# 本地停止单前缀
STOPORDERPREFIX = 'CtaStopOrder.'

# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
POSITION_DB_NAME = 'VnTrader_Position_Db'

TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'
'''2017052500 Add by hetajen begin'''
MINUTE5_DB_NAME = 'VnTrader_5Min_Db'
'''2017052500 Add by hetajen end'''

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# CTA引擎中涉及的数据类定义
from vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

'''2017050301 Add by hetajen begin'''
URL_SINA_HIST_D   = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol='
URL_SINA_HIST_M1  = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine1m?symbol='
URL_SINA_HIST_M5  = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine5m?symbol='
URL_SINA_REALTIME = 'http://hq.sinajs.cn/list='
SINA_DATE = 0
# open
SINA_O = 1
# high
SINA_H = 2
# low
SINA_L = 3
# close
SINA_C = 4
SINA_VOL = 5
'''2017050301 Add by hetajen end'''

########################################################################
class StopOrder(object):
    """本地停止单"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT
        
        self.strategy = None             # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号 
        self.status = EMPTY_STRING       # 停止单状态


########################################################################
class CtaBarData(object):
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
        '''2017051500 Add by hetajen begin'''
        self.tradingDay = EMPTY_STRING      # 交易日：上期所、中金所、大商所夜盘为下一日，郑商所夜盘为当日
        self.actionDay = EMPTY_STRING       # 业务发生日：上期所、中金所夜盘为当日，大商所同交易日，郑商所为当日
        '''2017051500 Add by hetajen end'''
        
        self.volume = EMPTY_INT             # 成交量
        self.openInterest = EMPTY_INT       # 持仓量


########################################################################
class CtaTickData(object):
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
        self.openInterest = EMPTY_INT           # 持仓量
        
        self.upperLimit = EMPTY_FLOAT           # 涨停价
        self.lowerLimit = EMPTY_FLOAT           # 跌停价
        
        # tick的时间
        self.date = EMPTY_STRING            # 日期
        self.time = EMPTY_STRING            # 时间
        self.datetime = None                # python的datetime时间对象
        '''2017051500 Add by hetajen begin'''
        self.tradingDay = EMPTY_STRING      # 交易日：上期所、中金所、大商所夜盘为下一日，郑商所夜盘为当日
        self.actionDay = EMPTY_STRING       # 业务发生日：上期所、中金所夜盘为当日，大商所同交易日，郑商所为当日
        '''2017051500 Add by hetajen end'''
        
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