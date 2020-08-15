"""Contains implementation of class to monitor price of stocks/options"""

import robin_stocks as r
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np
import time
import logging
import pytz, holidays

import threading
import multiprocessing as mp

from matplotlib.dates import num2date
from matplotlib.ticker import Formatter

ENDFLAG = False

#logging.basicConfig(filename='log_loadingData_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d"), filemode='a', format='%(asctime)s - %(name)s , %(levelname)s : %(message)s',level=logging.INFO)
logfile_loadingData = 'log/log_loadingData_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d")

tz = pytz.timezone('US/Eastern')
us_holidays = holidays.US()
def afterHours():
	now = dt.datetime.now(tz)
	openTime = dt.time(hour = 9, minute = 30, second = 0)
	closeTime = dt.time(hour = 16, minute = 0, second = 0)
	# If a holiday
	if now.strftime('%Y-%m-%d') in us_holidays:
		return True
	# If before 0930 or after 1600
	if (now.time() < openTime) or (now.time() > closeTime):
		return True
	# If it's a weekend
	if now.date().weekday() > 4:
		return True
	return False

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

class stock:
	def __init__(self, symbol, period_ma1, period_ma2, period_ma3):
		self.symbol = symbol
		self.price = []
		self.price_dvt = []
		self.top_price = -1
		self.time = []
		self.trend = [] # "up" or "down"
		self.tmp_trend = [] # "up" or "down"
		self.signal = [] # "buy": signal for going up, "sell": signal for going down
		self.status = []
		self.period_ma1 = period_ma1
		self.period_ma2 = period_ma2
		self.period_ma3 = period_ma3
		self.ema1_dvt = []
		self.ema2_dvt = []
		self.ema3_dvt = []
		self.ema1 = []
		self.ema2 = []
		self.ema3 = []
		self.sma1 = []
		self.sma2 = []
		self.sma3 = []
		
		self.buy_price = -1
		self.quantity = 0
		self.buy_order_id = ""
		self.sell_order_id = ""
		self.sell_price = -1 # a price pending to close the option
		self.close_price = -1 # a price which closed the option
		self.direction = "" # indicate the status means a buy action or a sell action
		self.buy_state = ""
		self.sell_state = ""
	def updatePrice(self, t, p):
		self.time.append(t)
		self.price.append(p)
#		if (not self.buy_order_id == "") and (self.buy_state=="filled" or self.buy_state=="completed"  ):
#		print("updating price, buy_price: {}, buy_state: {}".format(self.buy_price, self.buy_state))
		if  (self.buy_state=="filled" or self.buy_state=="completed"  ):
			if(self.price[-1]>self.top_price): self.top_price = self.price[-1]
		self.sma1 = r.sma_update(self.sma1, self.price, self.period_ma1)
		self.sma2 = r.sma_update(self.sma2, self.price, self.period_ma2)
		self.sma3 = r.sma_update(self.sma3, self.price, self.period_ma3)
		self.ema1 = r.ema_update(self.ema1, self.price, self.period_ma1)
		self.ema2 = r.ema_update(self.ema2, self.price, self.period_ma2)
		self.ema3 = r.ema_update(self.ema3, self.price, self.period_ma3)
		r.update_status(self)


class option(stock):
	def __init__(self, symbol, expirationDate, strikePrice, optionType, period_ma1, period_ma2, period_ma3):
		stock.__init__(self, symbol, period_ma1, period_ma2, period_ma3)
		self.expr_date = expirationDate
		self.strike_price = strikePrice
		self.type = optionType

def initializeOption(opt):
	if not opt: return False
	if not len(opt.price) == 0: return False
	logger = r.setup_logger("initializeOption", logfile_loadingData)
	historicalData = r.get_option_historicals(opt.symbol, opt.expr_date, opt.strike_price, opt.type, "5minute", "day", "trading")
	for data_point in historicalData:
		opt.updatePrice(data_point['begins_at'], float(data_point['close_price']))
		logger.info("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price']) ))
	r.close_logger(logger)

def initializeOption_simulation(stk, opt):
	if (not opt) or (not stk): return False
	if not len(opt.price) == 0: return False
	logger = r.setup_logger("initializeOption_simulation", logfile_loadingData)
	historicalData = r.get_option_historicals(opt.symbol, opt.expr_date, opt.strike_price, opt.type, "5minute", "week", "regular")
	for data_point in historicalData:
		if data_point['begins_at']  in stk.time:
			opt.updatePrice(data_point['begins_at'], float(data_point['close_price']))
			logger.info("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price']) ))
#			print("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price'])))
	r.close_logger(logger)

class showPrice(object):	
	def __init__(self):
		self.plotting_rate = 2000 # 1000 ms
		self.refreshing_rate = 5 # 1000 ms
		self.ema = True # show SMA by default, set it to True to show EMA
		self.legendShow = False
		
#		self.logger = logging.getLogger('showPrice') 
#		self.logger.info("showPrice class has been initialized: EMA: %d, refreshing rate: %d ms"%(self.ema, self.plotting_rate))

	def terminate(self):
		plt.close('all')

	def call_back(self):
		while self.pipe.poll():
			if len(self.stk.price) > 0: print("refreshing plot: ", self.stk.price[-1])
			try:
				command = self.pipe.recv()
			except:
				return
			self.stk = command
			xdata = [dt.datetime.strptime(d,'%Y-%m-%dT%H:%M:%SZ') for d in self.stk.time]
			formatter = MyFormatter(xdata, '%Y-%m-%dT%H:%M:%SZ')
			self.ax.xaxis.set_major_formatter(formatter)
			self.ax.plot(np.arange(len(self.stk.time)), self.stk.price, 'b-', label="price" if self.legendShow == False else "")
			self.legendShow = True
			if len(self.stk.trend)>0:
				print("tmp_trend: {}, ".format(self.stk.tmp_trend[-1]))
				print("trend: {}, ".format(self.stk.trend[-1]))
				print("signal: {}\n".format(self.stk.signal[-1]))
			if len(self.stk.trend)>0 and self.stk.trend[-1] == "up":
				self.ax.arrow(len(self.stk.trend), self.stk.price[-1], 0, 0.8, length_includes_head=True, head_width=0.1)
			if len(self.stk.trend)>0 and self.stk.trend[-1] == "down":
				self.ax.arrow(len(self.stk.trend), self.stk.price[-1], 0, -0.8, length_includes_head=True, head_width=0.1)
			if len(self.stk.signal)>0 and self.stk.signal[-1] == "buy":
				self.ax.arrow(len(self.stk.trend), self.stk.price[-1], 0, 0.8, length_includes_head=True, head_width=0.3, head_length=0.3, color='green')
			if len(self.stk.signal)>0 and self.stk.signal[-1] == "sell":
				self.ax.arrow(len(self.stk.trend), self.stk.price[-1], 0, -0.8, length_includes_head=True, head_width=0.3,head_length=0.3, color='red')
			if (len(self.stk.signal)>0 and self.stk.signal[-1] == "close") or self.stk.sell_state=="completed":
				self.ax.arrow(len(self.stk.trend), self.stk.price[-1], 0, -0.8, length_includes_head=True, head_width=0.5,head_length=0.5, color='yellow')

			if self.ema:
				if self.stk.period_ma1 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma1-1, len(self.stk.time)), self.stk.ema1, 'b:', label="{}-min ema price".format(self.stk.period_ma1*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma1 else "")
				if self.stk.period_ma2 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma2-1, len(self.stk.time)), self.stk.ema2, 'b-.', label="{}-min ema price".format(self.stk.period_ma2*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma2 else "")
				if self.stk.period_ma3 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma3-1, len(self.stk.time)), self.stk.ema3, 'b--', label="{}-min ema price".format(self.stk.period_ma3*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma3 else "")
			else:
				if self.stk.period_ma1 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma1-1, len(self.stk.time)), self.stk.sma1, 'b:', label="{}-min sma price".format(self.stk.period_ma1*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma1 else "")
				if self.stk.period_ma2 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma2-1, len(self.stk.time)), self.stk.sma2, 'b-.', label= "{}-min sma price".format(self.stk.period_ma2*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma2 else "")
				if self.stk.period_ma3 <= len(self.stk.time): self.ax.plot(np.arange(self.stk.period_ma3-1, len(self.stk.time)), self.stk.sma3, 'b--', label= "{}-min sma price".format(self.stk.period_ma3*self.refreshing_rate/60) if len(self.stk.time) == self.stk.period_ma3 else "")
			self.ax.legend(loc="upper left")
			self.fig.canvas.draw()
#			self.logger.info("refreshing new curves.")

	def __call__(self, stk, pipe, refreshingRate):
		self.pipe = pipe
		self.fig, self.ax = plt.subplots()
		timer = self.fig.canvas.new_timer(interval=self.plotting_rate)
		timer.add_callback(self.call_back)
		timer.start()

		self.refreshing_rate = refreshingRate
		self.stk = stk
		self.ax.set_ylabel("Stock price", color='blue')
		self.ax.tick_params(axis='y', labelcolor="blue") 
		self.fig.autofmt_xdate()
		plt.title("Price for {} real time".format(self.stk.symbol)) 
		self.ax.xaxis.grid()
		self.ax.yaxis.grid()
		plt.show()

class realTimeShow:
	def __init__(self, symbol, refreshingRate, period_sma1=20, period_sma2=30, period_sma3=60, showPlot=False, expirationDate='', strikePrice='', optionType=''):
		self.logger = r.setup_logger("realTimeShow", logfile_loadingData)
		username = ''
		password = ''
		login = r.login(username,password)

		self.refresh_rate = refreshingRate
		self.myStock = stock(symbol, int(period_sma1*60/refreshingRate), int(period_sma2*60/refreshingRate), int(period_sma3*60/refreshingRate))
		self.myOption = option(symbol, expirationDate, strikePrice, optionType, int(period_sma1*60/refreshingRate), int(period_sma2*60/refreshingRate), int(period_sma3*60/refreshingRate))
		self.showplot = showPlot
		self.name = r.get_name_by_symbol(symbol)
		quotes = r.get_stock_quote_by_symbol(self.myStock.symbol)
		if not self.name:
			self.logger.error('the input symbol does not exist: {}!'.format(symbol))
			raise ValueError("the input symbol does not exist!")
		self.logger.info("realTimeshow class has been initialized for the stock {}".format(self.name))
		print("Initializing realTimeshow class for the stock : %s"%(self.name))
		self.send_pipe, self.recv_pipe = mp.Pipe()
		self.plotter = showPrice()
	
	def __del__(self):
		r.close_logger(self.logger)

# real time price fetcher	
	class fetchingPrice(threading.Thread):
		def __init__(self, stk, refreshingRate):
			threading.Thread.__init__(self)
			self.stk = stk
			self.refresh_rate = refreshingRate
#			self.send_pipe = send_pipe
			self.logger = r.setup_logger("fetchingPrice", logfile_loadingData)
			self.logger.info("fetchingPrice starting now...")
		
		def __del__(self):
			r.close_logger(self.logger)
		
		def run(self):
			global ENDFLAG
			while True:
				if ENDFLAG: break
				retry = 0
				try:
					quotes = r.get_stock_quote_by_symbol(self.stk.symbol)
				except: quotes = None
				while retry < 10 and quotes == None:
					try:
						retry += 1
						time.sleep(6)
						quotes = r.get_stock_quote_by_symbol(self.stk.symbol)
					except:
						quotes = None
						continue
				if quotes == None:
					print("Error in fetchingPrice: cannot get data from server!")
					self.logger.info("Error: cannot get data from server!")
					return
				if quotes["updated_at"] not in self.stk.time:
					if afterHours(): self.stk.updatePrice(quotes["updated_at"], float(quotes["last_extended_hours_trade_price"]))
					else: self.stk.updatePrice(quotes["updated_at"], float(quotes["last_trade_price"])) 
#					self.send_pipe.send( self.stk )
					self.logger.info("{}: add new data points {} and send it to pipe!".format(dt.datetime.now(), self.stk.price[-1]))
					print("{}: add new data points {} and send it to pipe!".format(dt.datetime.now(), self.stk.price[-1]))
				time.sleep(self.refresh_rate)

# real time price fetcher for option, be careful the timestamp is not from RobinHood server, instead is from the time when running this function !!! So time is only meaningful when option is open to trading
	class fetchingPriceOption(threading.Thread):
		def __init__(self, opt, refreshingRate):
			threading.Thread.__init__(self)
			self.opt = opt
			self.refresh_rate = refreshingRate
#			self.send_pipe = send_pipe
			self.file = "option_price_{}_{}_{}_{}.txt".format(self.opt.symbol, self.opt.expr_date, self.opt.strike_price, self.opt.type)

			self.logger = r.setup_logger("fetchingPriceOption", logfile_loadingData)	
			self.logger.info("fetchingPriceOption starting now...")

		def __del__(self):
			r.close_logger(self.logger)

		def run(self):
#			global ENDFLAG
			while True:
				if ENDFLAG: break
				retry = 0
				try:
					quotes = r.get_option_market_data(self.opt.symbol, self.opt.expr_date, self.opt.strike_price, self.opt.type)[0]
				except: quotes = None
				while retry < 10 and quotes == None:
					try:
						retry += 1
						time.sleep(6)
						quotes = r.get_option_market_data(self.opt.symbol, self.opt.expr_date, self.opt.strike_price, self.opt.type)[0]
					except:
						quotes = None
						continue
				if quotes == None:
					print("Error in fetchingPrice: cannot get data from server!")
					self.logger.info("Error: cannot get data from server!")
					return
				timestamp = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
				if timestamp not in self.opt.time:
					self.opt.updatePrice(timestamp, float(quotes["adjusted_mark_price"]))
#					self.send_pipe.send(self.opt )
					with open(self.file, 'a') as f:
						if afterHours():
							f.write("!unofficial time! %s : %f\n"%(self.opt.time[-1], self.opt.price[-1]))
						else:
							f.write("%s : %f\n"%(self.opt.time[-1], self.opt.price[-1]))
					self.logger.info("{}: add new data points {} and send it to pipe!".format(dt.datetime.now(), self.opt.price[-1]))
					print("{}: add new data points {} and send it to pipe!".format(dt.datetime.now(), self.opt.price[-1]))
				time.sleep(self.refresh_rate)
# pseudo price fetcher, mimic fetching price from the history
	class fetchingPriceOption_simulation(threading.Thread):
		def __init__(self, opt, refreshingRate):
			threading.Thread.__init__(self)
			self.opt = opt
			self.refresh_rate = refreshingRate
#			self.send_pipe = send_pipe
			self.file = "option_price_{}_{}_{}_{}.txt".format(self.opt.symbol, self.opt.expr_date, self.opt.strike_price, self.opt.type)

			self.logger = r.setup_logger("fetchingPriceOption_simulation", logfile_loadingData)
			self.logger.info("fetchingPriceOption_simulation starting now...")

		def __del__(self):
			r.close_logger(self.logger)

		def run(self):
#			global ENDFLAG
			while True:
				historicalData = r.get_option_historicals(self.opt.symbol, self.opt.expr_date, self.opt.strike_price, self.opt.type, "5minute", "week", "regular")
				start = False
				for data_point in historicalData:
#					global ENDFLAG
#					if ENDFLAG: break
					if data_point['begins_at'] not in self.opt.time:
						self.opt.updatePrice(data_point['begins_at'], float(data_point['close_price']))
						start = True
						self.logger.info("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price'])))
						print("{}: add new data points {}!".format( data_point['begins_at'], float(data_point['close_price'])))
					if start:
						time.sleep(1)

# pseudo price fetcher, mimic fetching price from the history
	class fetchingPrice_simulation(threading.Thread):
		def __init__(self, stk, refreshingRate):
			threading.Thread.__init__(self)
			self.stk = stk
			self.refresh_rate = refreshingRate
#			self.send_pipe = send_pipe
			self.logger = r.setup_logger("fetchingPrice_simulation", logfile_loadingData)
			self.logger.info("fetchingPrice_simulation starting now...")
	
		def __del__(self):
			r.close_logger(self.logger)

		def run(self):
			stocksData = r.get_stock_historicals(self.stk.symbol, '5minute', 'week', 'regular', None)
			for stock_point in stocksData:
				global ENDFLAG
				if ENDFLAG:
					break
				if stock_point['begins_at'] not in self.stk.time:
					self.stk.updatePrice(stock_point['begins_at'], float(stock_point['close_price']))
					self.logger.info("{}: add new data points {}!".format(stock_point['begins_at'], self.stk.price[-1]))
					print("{}: add new data points {}!".format(dt.datetime.now(), self.stk.price[-1]))
				time.sleep(1)
					
	def run(self):
		self.logger.info("running start.")
		thread_fetchPrice = self.fetchingPrice(self.myStock, self.refresh_rate)
		thread_fetchPrice.start()
		if self.showplot:
			process_plotPrice = mp.Process(target=self.plotter, args=(self.myStock,self.recv_pipe,self.refresh_rate), daemon=True)
			process_plotPrice.start()
		
		time.sleep(20)
		global ENDFLAG
#		ENDFLAG = True
		thread_fetchPrice.join()
		self.logger.info("running finished.")
		input()

	def runOption(self):
		thread_fetchPrice = self.fetchingPriceOption(self.myOption, self.refresh_rate)
		thread_fetchPrice.start()
		if self.showplot:
			process_plotPrice = mp.Process(target=self.plotter, args=(self.myOption, self.recv_pipe, self.refresh_rate), daemon=True)
			process_plotPrice.start()

		time.sleep(5)
		global ENDFLAG
#		ENDFLAG = True
		thread_fetchPrice.join()

if __name__ == '__main__':
    mp.set_start_method("forkserver") 
    myShow = realTimeShow("AAPL",5,1,2,3,True,"2020-07-17",385, "call")
    myShow.run()
#    myShow.runOption()

