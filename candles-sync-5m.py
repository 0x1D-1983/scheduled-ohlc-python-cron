#!/usr/bin/python

import pandas as pd
import mplfinance as plt
import numpy as np
import time, math, numbers

from mplfinance.original_flavor import candlestick_ohlc
from datetime import *

from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy, DowngradingConsistencyRetryPolicy, ConsistencyLevel
from cassandra.query import dict_factory, tuple_factory, UNSET_VALUE, ValueSequence

profile = ExecutionProfile(
    load_balancing_policy=WhiteListRoundRobinPolicy(['127.0.0.1']),
    retry_policy=DowngradingConsistencyRetryPolicy(),
    consistency_level=ConsistencyLevel.LOCAL_QUORUM,
    serial_consistency_level=ConsistencyLevel.LOCAL_SERIAL,
    request_timeout=15,
    row_factory=dict_factory
)

cluster = Cluster(execution_profiles={EXEC_PROFILE_DEFAULT: profile})
session = cluster.connect('stock_data', wait_for_all_pools=True)

insert_query = session.prepare("INSERT INTO candlestick_data_5min(symbol, time, ask_open, ask_high, ask_low, ask_close, bid_open, bid_high, bid_low, bid_close, open_spread, high_spread, low_spread, close_spread, ask_volume, bid_volume) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")

now = datetime.now()
five_mins_ago = (now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
print(five_mins_ago)

select_query = "SELECT symbol, time, ask, bid FROM raw WHERE time > '" + five_mins_ago + "' ALLOW FILTERING"
select_prepared = session.prepare(select_query)

rows = session.execute(select_prepared)

def calculate_candlesticks():
    print(len(data))

    df = pd.DataFrame.from_dict(data)

    if (df.empty):
        print('No rows returned, exiting co-routine.')
        exit

    df = df.set_index(['time'])

    # set index of dataframe to the value in time column
    df.index = pd.to_datetime(df.index, unit='s')

    # need to cast decimals to float in dataframe
    data_types_dict = {'ask': float, 'bid': float}
    df = df.astype(data_types_dict)

    PipPosition = 4

    df['spread'] = (df['ask'] - df['bid']) * 10**PipPosition

    grouped = df.groupby('symbol')

    # resample
    ask_resample = grouped['ask'].resample('5Min')
    bid_resample = grouped['bid'].resample('5Min')

    # open, high, low, close
    ask_ohlc =  ask_resample.ohlc()
    bid_ohlc = bid_resample.ohlc()

    # volume
    ask_volume = ask_resample.count()
    bid_volume = bid_resample.count()

    df2 = pd.concat([ask_ohlc, bid_ohlc], axis=1, keys=['ask', 'bid'])

    Open_Ask = df2['ask']['open'].values
    Close_Ask = df2['ask']['close'].values
    High_Ask = df2['ask']['high'].values
    Low_Ask = df2['ask']['low'].values

    # Date = range(len(df2))
    Open_Bid = df2['bid']['open'].values
    Close_Bid = df2['bid']['close'].values
    High_Bid = df2['bid']['high'].values
    Low_Bid = df2['bid']['low'].values

    total_queries = len(df2)

    for i in range(0, total_queries):
        o_ask = Open_Ask[i]
        h_ask = High_Ask[i]
        l_ask = Low_Ask[i]
        c_ask = Close_Ask[i]

        if (math.isnan(Open_Ask[i])):
            o_ask = UNSET_VALUE

        if (math.isnan(High_Ask[i])):
            h_ask = UNSET_VALUE

        if (math.isnan(Low_Ask[i])):
            l_ask = UNSET_VALUE

        if (math.isnan(Close_Ask[i])):
            c_ask = UNSET_VALUE

        
        o_bid = Open_Bid[i]
        h_bid = High_Bid[i]
        l_bid = Low_Bid[i]
        c_bid = Close_Bid[i]

        if (math.isnan(Open_Bid[i])):
            o_bid = UNSET_VALUE

        if (math.isnan(High_Bid[i])):
            h_bid = UNSET_VALUE

        if (math.isnan(Low_Bid[i])):
            l_bid = UNSET_VALUE

        if (math.isnan(Close_Bid[i])):
            c_bid = UNSET_VALUE

        # spreads

        if (isinstance(o_ask, float) == True and isinstance(o_bid, float)):
            o_spread = o_ask - o_bid
        else:
            o_spread = UNSET_VALUE

        if (isinstance(h_ask, float) == True and isinstance(h_bid, float)):
            h_spread = h_ask - h_bid
        else:
            h_spread = UNSET_VALUE

        if (isinstance(l_ask, float) == True and isinstance(l_bid, float)):
            l_spread = l_ask - l_bid
        else:
            l_spread = UNSET_VALUE

        if (isinstance(c_ask, float) == True and isinstance(c_bid, float)):
            c_spread = c_ask - c_bid
        else:
            c_spread = UNSET_VALUE
        
        # build a list of futures
        session.execute(insert_query, [df2.index[i][0], df2.index[i][1], o_ask, h_ask, l_ask, c_ask, o_bid, h_bid, l_bid, c_bid, o_spread, h_spread, l_spread, c_spread, ask_volume[i], bid_volume[i]])


data = []
i = 0

for row in rows:
    data.append(row)
    i = i + 1
    if (i > 99999):
        calculate_candlesticks()
        data = []
        i = 0

calculate_candlesticks()

