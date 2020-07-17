"""Contains implementation of trading strategies: like common indicators, SMA, EMA, MACD, etc."""
import numpy as np
import datetime as dt
import pytz
import logging

#logging.basicConfig(filename='log/log_analyzer_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d"), filemode='a', format='%(asctime)s - %(name)s , %(levelname)s : %(message)s',level=logging.INFO)
logfile_analyzer = filename='log/log_analyzer_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d")

def setup_logger(name, log_file, level=logging.INFO):
	""" return a logger with log_file """
	logger = logging.getLogger(name)
	fh = logging.FileHandler(log_file, mode='a')
	fh.setLevel(level)
	fh.setFormatter(logging.Formatter( '%(asctime)s - %(name)s , %(levelname)s : %(message)s' ))
	logger.addHandler(fh)
	logger.propagate = False

	return logger

def close_logger(logger):
	handlers = logger.handlers[:]
	for handler in handlers:
		handler.close()
		logger.removeHandler(handler)

def simple_ma(data, period):
	""" input a list of data points and return SMA with period points averaged

	:param data: the list of data points
	:type data: list
	:param period: averaged over past period data points
	:param period: int
	:return a list of SMA with period points averaged

	"""
	if period > len(data):
#		print("Error in simple_ma function: the length of data points is too short!")
		return []
	ret = np.cumsum(data,dtype=float)
	ret[period:] = ret[period:] - ret[:-period]
	return list(ret[period-1:]/period)

def sma_update(sma,price, period): 
	if len(sma) == 0: sma = simple_ma(price, period)
	else:
	    sma.append((price[-1] - price[-1-period])/period + sma[-1])
	return sma


def expo_ma(data, period):
	""" input a list of data points and return EMA with period points averaged

	:param data: the list of data points
	:type data: list
	:param period: averaged over past period data points
	:param period: int
	:return a list of EMA with period points averaged

	"""
	if period > len(data):
#		print("Error in expo_ma function: the length of data points is too short!")
		return []
	ret = [None] * (len(data)-period+1)
	# initialize the first element in the EMA series to the SMA of first period data points
	ret[0] = sum(data[:period])/period
	# set smoothing factor to be 2/(period+1)
	factor = float(2/(period+1))
	# calculate the rest of series by the formula: factor * P(t) + (1-factor) * EXP(t-1)
	for i in range(1, len(data)-period+1):
		ret[i] = factor*data[period+i-1] + (1-factor)*ret[i-1]
	return list(ret)

def ema_update(ema, price, period):
	if len(ema) == 0: ema = expo_ma(price, period)
	else:
	    factor = float(2/(period+1))
	    ema.append(factor*price[-1] + (1-factor)*ema[-1])
	return ema

def update_status(stk):
	""" 
		a function to update derivatives for price and ema lines and line position
	"""
	nPoints = len(stk.time)
	if len(stk.price) > 1: stk.price_dvt.append((stk.price[-1] - stk.price[-2])/stk.price[-2] )
	else: stk.price_dvt.append(None)
	if len(stk.ema1) > 1: stk.ema1_dvt.append((stk.ema1[-1] - stk.ema1[-2])/stk.ema1[-2] )
	else: stk.ema1_dvt.append(None)
	if len(stk.ema2) > 1: stk.ema2_dvt.append((stk.ema2[-1] - stk.ema2[-2])/stk.ema2[-2] )
	else: stk.ema2_dvt.append(None)
	if len(stk.ema3) > 1: stk.ema3_dvt.append((stk.ema3[-1] - stk.ema3[-2])/stk.ema3[-2] )
	else: stk.ema3_dvt.append(None)
	if (len(stk.price)==0 or len(stk.ema1)==0  or len(stk.ema2)==0 or len(stk.ema3)==0): stk.status.append([0,0,0,0]) # indicate a invalid line position status
	else:
		tmp = [stk.price[-1], stk.ema1[-1], stk.ema2[-1], stk.ema3[-1]]
		tmp.sort()
		stk.status.append([1<<tmp.index(stk.price[-1]), 1<<tmp.index(stk.ema1[-1]), 1<<tmp.index(stk.ema2[-1]), 1<<tmp.index(stk.ema3[-1])])

def is_sorted(l, descend=True, validCheck=True):
	# first check if the status code is valid, return False if not
	if validCheck and all([l[i] == 0 for i in range(len(l))]): return False
	if descend:
		return all([l[i] >= l[i+1] for i in range(len(l)-1)])
	else:
		return all([l[i] <= l[i+1] for i in range(len(l)-1)])

def update_trend(stk, pos): # update trend variables at the position @ pos
	if len(stk.tmp_trend) < pos-1: update_trend(stk, pos-1)
	elif len(stk.tmp_trend) == pos-1:
		if (len(stk.price_dvt)==0 or len(stk.ema1_dvt)==0 or len(stk.ema2_dvt)==0 or len(stk.ema3_dvt)==0 or (len(set(stk.status[pos-1]))==1 and stk.status[pos-1][0]==0) or stk.ema3_dvt[pos-1]==None):
			stk.tmp_trend.append("undefined")
			stk.trend.append("undefined")
			stk.signal.append("")
		elif is_sorted(stk.status[pos-1], True): # ok, now lines postions are in order, but needs to check derivatives are pointing up
			#if stk.price_dvt[pos-1]>0 and stk.ema1_dvt[pos-1]>0 and stk.ema2_dvt[pos-1]>0 and stk.ema3_dvt[pos-1]>0:
			if  stk.ema1_dvt[pos-1]>0 and stk.ema2_dvt[pos-1]>0 and stk.ema3_dvt[pos-1]>0:
				stk.tmp_trend.append("up")
				stk.trend.append("")
				stk.signal.append("")
			else:
				stk.tmp_trend.append("out of order")
				stk.trend.append("")
				stk.signal.append("")
		elif is_sorted(stk.status[pos-1], False): # ok, now lines postions are in order, but needs to check derivatives are pointing down
			#if stk.price_dvt[pos-1]<0 and stk.ema1_dvt[pos-1]<0 and stk.ema2_dvt[pos-1]<0 and stk.ema3_dvt[pos-1]<0:
			if  stk.ema1_dvt[pos-1]<0 and stk.ema2_dvt[pos-1]<0 and stk.ema3_dvt[pos-1]<0:
				stk.tmp_trend.append("down")
				stk.trend.append("")
				stk.signal.append("")
			else:
				stk.tmp_trend.append("out of order")
				stk.trend.append("")
				stk.signal.append("")
		else:
			stk.tmp_trend.append("out of order")
			stk.trend.append("")
			stk.signal.append("")

		if((stk.tmp_trend[-1]=="up" or stk.tmp_trend[-1]=="down") and len(stk.trend)>1): stk.trend[-1] = stk.trend[-2]
		
		if(len(stk.trend)>1 and (stk.trend[-2]=="up" or stk.trend[-2]=="down")):
			if(stk.trend[-2]=="up" and is_sorted(stk.status[-1][-3:], True) and stk.ema2_dvt[pos-1]>0 and stk.ema3_dvt[pos-1]>0): # if trend is "up" at the previous time, even if the price hits the ema1 or ema2 , and as long as all ema lines are in order and pointing up, it's ok to keep the same trend, but price cannot hit the sma3 line
				if all([stk.status[-i][0]<stk.status[-i][1] for i in range(1, int(stk.period_ma1/4))]): stk.trend[-1] = "" # if price line below ema1/2 lines for a while, terminate "up" trend
				elif stk.status[-1][0]<=min(stk.status[-1][-3:]): stk.trend[-1] = "" # if price hits the ema3 line, terminate the "up" trend
				else: stk.trend[-1] = stk.trend[-2] 
			elif(stk.trend[-2]=="down" and is_sorted(stk.status[-1][-3:], False) and stk.ema2_dvt[pos-1]<0 and stk.ema3_dvt[pos-1]<0):
				if all([stk.status[-i][0]>stk.status[-i][1] for i in range(1, int(stk.period_ma1/4))]): stk.trend[-1] = ""
				elif stk.status[-1][0]>=max(stk.status[-1][-3:]): stk.trend[-1] = ""
				else: stk.trend[-1] = stk.trend[-2]
			else: stk.trend[-1] = "" # or ema lines are either not in order or have wrong sign of derivatives, teminate the previous trend
		else:
#			print(stk.tmp_trend)
#			print(len(set(stk.tmp_trend[-int(stk.period_ma1/2):]))==1)
#			print(stk.tmp_trend[-1])
			if len(set(stk.tmp_trend[-int(stk.period_ma1/1):]))==1 and stk.tmp_trend[-1] == "up": stk.trend[-1] = "up" # if tmp_trend variables has been "up" for a while, then decides now trend is "up"
			if len(set(stk.tmp_trend[-int(stk.period_ma1/1):]))==1 and stk.tmp_trend[-1] == "down": stk.trend[-1] = "down" # if tmp_trend variables has been "down" for a while, then decides now trend is "down"
#			print(stk.trend[-1])
			
	
		if len(stk.signal)>2 and stk.signal[-2] == "close": stk.signal[-1] = "close"

def check_signal(stk): # a function to check if a "buy" or "sell" signal should be triggered
	logger = setup_logger("check_signal", logfile_analyzer)
	if len(stk.ema1) <= int(stk.period_ma1/4) + 1: return # ema3 line is too short to trigger signal 
	if is_sorted(stk.status[-1], True): # for a buy, the lines must be in order
		#if stk.price_dvt[-1]>0 and stk.ema1_dvt[-1]>0 and stk.ema2_dvt[-1]>0 and stk.ema3_dvt[-1]>0: # second, the derivatives must be pointing up
		if  (not stk.ema3_dvt[-1] == None) and stk.ema1_dvt[-1]>0 and stk.ema2_dvt[-1]>0 and stk.ema3_dvt[-1]>0: # second, the derivatives must be pointing up
			crossed = False
			converge = False
			for i in range(2, 2+int(stk.period_ma1/3)): # third, need to check if ema lines are reversed in order within the past short time
				if is_sorted(stk.status[-i][-3:], False):
					crossed = True
				if is_sorted(stk.status[-i][:2], False):
					converge = True
				if crossed and converge: break
			if crossed and converge:
				logger.info("a buy signal is triggered! status, ema1_dvt, ema2_dvt, ema3_dvt")
				logger.info(stk.status)
				logger.info(stk.ema1_dvt)
				logger.info(stk.ema2_dvt)
				logger.info(stk.ema3_dvt)
				stk.signal[-1] = "buy"
				stk.trend[-1] = "up"
	if is_sorted(stk.status[-1], False): # for a sell, the lines must be in order
		#if stk.price_dvt[-1]<0 and stk.ema1_dvt[-1]<0 and stk.ema2_dvt[-1]<0 and stk.ema3_dvt[-1]<0: # second, the derivatives must be pointing down
		if (not stk.ema3_dvt[-1] == None) and stk.ema1_dvt[-1]<0 and stk.ema2_dvt[-1]<0 and stk.ema3_dvt[-1]<0: # second, the derivatives must be pointing down
			crossed = False
			converge = False
			for i in range(2, 2+int(stk.period_ma1/3)): # third, need to check if ema lines are reversed in order within the past short time
				if is_sorted(stk.status[-i][-3:], True):
					crossed = True
				if is_sorted(stk.status[-i][:2], True):
					converge = True
				if crossed and converge: break
			if crossed and converge:
				logger.info("a sell signal is triggered! status, ema1_dvt, ema2_dvt, ema3_dvt")
				logger.info(stk.status)
				logger.info(stk.ema1_dvt)
				logger.info(stk.ema2_dvt)
				logger.info(stk.ema3_dvt)
				stk.signal[-1] = "sell"
				stk.trend[-1] = "down"
	close_logger(logger)

def check_exit(opt): # check exit signal and set proper sell price
	"""
		when top price below buy_price*1.1, set sell_price = 0.9*price
		when top above but below 1.3*price, we lock the profit: 0.4
		when top above 1.3x but below 1.5x, lock the profit: 0.5
		when top above 1.5x but below 2x, lock the profit: 0.6
		when top above, lock the profit 0.8
	"""
	logger = setup_logger("check_exit", logfile_analyzer)
	# here check if price hits the ema2 line, or break ema1 line for a while, then trigger a close action
	logger.info("buy_price:{}, top_price:{}, state: {}".format(opt.buy_price, opt.top_price, opt.buy_state))
	if not (opt.buy_state == "filled" or opt.buy_state == "completed"): return False	
	if opt.top_price<0: return False	
	if opt.sell_state=="filled" or opt.sell_state=="completed": return False

	tz = pytz.timezone('US/Eastern')
	now = dt.datetime.now(tz)
	warningTime = dt.time(hour = 15, minute = 50, second = 0)
	if (not opt.signal[-1] == "close") and now.time()> warningTime:
		print("Market is about to close, now trying to close the option!")
		logger.info("Market is about to close, now trying to close the option!")
		opt.signal[-1] = "close"

	if opt.top_price < 1.1*opt.buy_price:
		opt.sell_price = round(0.9*opt.buy_price, 2)
	elif opt.top_price < 1.3*opt.buy_price:
		opt.sell_price = opt.buy_price+ round(0.4*(opt.top_price-opt.buy_price), 2)
	elif opt.top_price < 1.5*opt.buy_price:
		opt.sell_price = opt.buy_price+ round(0.5*(opt.top_price-opt.buy_price), 2)
	elif opt.top_price < 1.5*opt.buy_price:
		opt.sell_price = opt.buy_price+ round(0.6*(opt.top_price-opt.buy_price), 2)
	else:
		opt.sell_price = opt.buy_price+ round(0.8*(opt.top_price-opt.buy_price), 2)
	print("check_exit: ", opt.sell_price)
	logger.info("buy_price:{}, top_price:{}, check_exit: {}".format(opt.buy_price, opt.top_price, opt.sell_price))
	
	if len(opt.time) == 0: return False
	if opt.type == "call":
		if opt.price[-1] <= opt.ema2[-1]: 
			logger.info("call option: a close signal is triggered: price hit the ema2 line, price, ema1, ema2, ema3")
			logger.info(opt.price)
			logger.info(opt.ema1)
			logger.info(opt.ema2)
			logger.info(opt.ema3)
			
			opt.signal[-1] = "close"
		if all([i<j for i,j in zip(opt.price[-int(opt.period_ma1/3):], opt.ema1[-int(opt.period_ma1/3):])]):
			logger.info("call option: a close signal is triggered: price hit the ema1 line for {} minutes, price, ema1, ema2, ema3".format(int(opt.period_ma1/3)))
			logger.info(opt.price)
			logger.info(opt.ema1)
			logger.info(opt.ema2)
			logger.info(opt.ema3)
			
			opt.signal[-1] = "close"
	elif opt.type == "put":
		if opt.price[-1] <= opt.ema2[-1]:
			logger.info("put option: a close signal is triggered: price hit the ema2 line, price, ema1, ema2, ema3")
			logger.info(opt.price)
			logger.info(opt.ema1)
			logger.info(opt.ema2)
			logger.info(opt.ema3)

			opt.signal[-1] = "close"
		if all([i<j for i,j in zip(opt.price[-int(opt.period_ma1/3):], opt.ema1[-int(opt.period_ma1/3):])]):
			logger.info("put option: a close signal is triggered: price hit the ema1 line for {} minutes, price, ema1, ema2, ema3".format(int(opt.period_ma1/3)))
			logger.info(opt.price)
			logger.info(opt.ema1)
			logger.info(opt.ema2)
			logger.info(opt.ema3)

			opt.signal[-1] = "close"
	
	close_logger(logger)		
	

def strategy_ema(stock, opt, send_pipe, send_pipe_opt): # a function checking entry point or exit point at each iteration 
	logger = setup_logger("strategy_ema", logfile_analyzer) 
	logger.info("analyze stock data with strategy_ema")
	while len(stock.tmp_trend) < len(stock.time)-1:
		update_trend(stock, len(stock.time)-1)
	check_signal(stock)
	send_pipe.send(stock)
	# send a fake signal for simulation:
#	if len(stock.signal)>=10:
#		stock.signal[-1] = "buy"

	if not opt.type == "":
		logger.info("analyze option data with strategy_ema")
		while len(opt.tmp_trend) < len(opt.time)-1:
			update_trend(opt, len(opt.time)-1)
		check_exit(opt)
		send_pipe_opt.send(opt)
		print("sell price: ", opt.sell_price)
	close_logger(logger)	
	
	

