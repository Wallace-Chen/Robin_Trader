import robin_stocks as r
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np

from matplotlib.dates import num2date
from matplotlib.ticker import Formatter
'''
This is example code that gets the past 30 days of opening and closing prices
for a specific option call or put. As far as I know, there is no way to view
past prices for options, so this is a very useful piece of code. This code also
plots the data using matplotlib, but the data is contained in the
historicalData list and you are free to do whatever you want with it.

NOTE: closing prices are plotted in red and opening prices plotted in blue.
Matplotlib also has a candlestick option that you can use.
'''

#!!! Fill out username and password
username = ''
password = ''
#!!!

login = r.login(username,password)

#!!! fill out the specific option information
symbol = 'AAPL'
expirationDate = '2020-07-17' # format is YYYY-MM-DD.
strike = 395
#symbol = 'WORK'
#expirationDate = '2020-08-21' # format is YYYY-MM-DD.
#strike = 40
optionType = 'call' # available options are 'call' or 'put' or None.
interval = '5minute' # available options are '5minute', '10minute', 'hour', 'day', and 'week'.
span = 'week' # available options are 'day', 'week', 'year', and '5year'.
bounds = 'regular' # available options are 'regular', 'trading', and 'extended'.
days_back = 1
period_sma_20m = 4
period_sma_30m = 6
period_sma_1h = 12
info = None
symbol_name = r.get_name_by_symbol(symbol)
#!!!

class MyFormatter(Formatter):
    def __init__(self, dates, fmt='%Y-%m-%d'):
        self.dates = dates
        self.fmt = fmt
	
    def __call__(self, x, pos=0):
        'Return the label for time x at position pos'
        ind = int(np.round(x))
        if ind >= len(self.dates) or ind < 0:
            return ''
        return self.dates[ind].strftime(self.fmt)

now = dt.datetime.utcnow() - dt.timedelta(days=days_back-1)
day = int(now.strftime("%d"))
month = int(now.strftime("%m"))
year = int(now.strftime("%Y"))
timecut = dt.datetime(year, month, day)

historicalData = r.get_option_historicals(symbol, expirationDate, strike, optionType, interval, span, bounds, info)
stocksData = r.get_stock_historicals(symbol, interval, span, bounds, info)

dates = []
closingPrices = []
openPrices = []

stock_dates = []
stock_closingPrices = []
stock_openPrices = []

for data_point in historicalData:
    if(dt.datetime.strptime(data_point['begins_at'],'%Y-%m-%dT%H:%M:%SZ') < timecut): continue
    dates.append(data_point['begins_at'])
    closingPrices.append(float(data_point['close_price']))
    openPrices.append(float(data_point['open_price']))
    print("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price'])))
for stock_point in stocksData:
    if(dt.datetime.strptime(stock_point['begins_at'],'%Y-%m-%dT%H:%M:%SZ') < timecut): continue
    stock_dates.append(stock_point['begins_at'])
    stock_closingPrices.append(float(stock_point['close_price']))
    stock_openPrices.append(float(stock_point['open_price']))

fig, ax1 = plt.subplots()
# change the dates into a format that matplotlib can recognize.
x = [dt.datetime.strptime(d,'%Y-%m-%dT%H:%M:%SZ') for d in dates]
stock_x = [dt.datetime.strptime(d,'%Y-%m-%dT%H:%M:%SZ') for d in stock_dates]

# plot the data.
formatter = MyFormatter(stock_x, '%Y-%m-%dT%H:%M:%SZ')
ax1.xaxis.set_major_formatter(formatter)
#ax1.plot(stock_x, stock_closingPrices, '-go', label="stock closing price")
ax1.plot(np.arange(len(stock_x)), stock_closingPrices, '-g', label="stock closing price")
ax1.plot(np.arange(period_sma_1h-1,len(stock_x)), r.expo_ma(stock_closingPrices, period_sma_1h), ':g', label="stock 1 hour ema price")
ax1.plot(np.arange(period_sma_30m-1,len(stock_x)), r.expo_ma(stock_closingPrices, period_sma_30m), '-.g', label="stock 30 mins ema price")
ax1.plot(np.arange(period_sma_20m-1,len(stock_x)), r.expo_ma(stock_closingPrices, period_sma_20m), '--g', label="stock 20 mins ema price")
ax1.set_ylabel("Stock price", color='green')
ax1.tick_params(axis='y', labelcolor="green")
ax2 = ax1.twinx()
#ax2.plot(x, closingPrices, '-bo', label="option closing price")
ax2.plot(np.arange(len(x)), closingPrices, '-b', label="option closing price")
ax2.plot(np.arange(period_sma_1h-1,len(x)), r.expo_ma(closingPrices, period_sma_1h), ':b', label="option 1 hour ema price")
ax2.plot(np.arange(period_sma_30m-1,len(x)), r.expo_ma(closingPrices, period_sma_30m), '-.b', label="option 30 mins ema price")
ax2.plot(np.arange(period_sma_20m-1,len(x)), r.expo_ma(closingPrices, period_sma_20m), '--b', label="option 20 mins ema price")
plt.title("Option & stock price for {} over time".format(symbol_name))
ax2.set_xlabel("Dates")
ax2.set_ylabel("Option price", color="blue")
ax2.tick_params(axis='y', labelcolor="blue")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")
##fig.tight_layout()  # otherwise the right y-label is slightly clipped
##plt.gcf().autofmt_xdate()
ax1.xaxis.grid()
ax1.yaxis.grid()
fig.autofmt_xdate()
plt.show()

