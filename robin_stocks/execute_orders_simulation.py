"""Contains implementation of functions to query and execute orders"""
"""This file is for simulation, no real order actions!"""
from observer import *

logging.basicConfig(filename='log/log_executing_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d"), filemode='a', format='%(asctime)s - %(name)s , %(levelname)s : %(message)s',level=logging.INFO)
logfile_execution = 'log/log_executing_%s.txt'%dt.datetime.now().strftime("%Y-%m-%d")
def optionBuy(opt, logger):
	logger.info("Try to place buy option")
	if opt.type == "": 
		logger.warning("Empty option, returned!")
		return False
	# first check if option is available to trade
	#rlt = r.find_options_by_expiration_and_strike(opt.symbol, opt.expr_date, opt.strike_price, opt.type)
	#if (not len(rlt) > 0 ) or (not rlt[0]["tradability"] == "tradable"): return False
	#ret = r.order_buy_option_limit("open", "debit", float(rlt[0]["adjusted_mark_price"]) , opt.symbol, 1, opt.expr_date, opt.strike_price, opt.type)
	ret = {"quantity": 3, "state": "unconfirmed"} 
	if ret:
#		opt.buy_price = float(rlt[0]["adjusted_mark_price"])
		opt.buy_price = opt.price[-1] 
		opt.sell_price = round(0.9*opt.buy_price, 2)
		opt.quantity = int(ret["quantity"])
#		opt.buy_order_id = ret["id"]
		opt.buy_state = ret["state"]
		opt.direction = "buy"
		logger.info("Order placed: symbol {}, strike_price {}, expr_date {}, type {}, quant {}, buy_price {}".format(opt.symbol, opt.strike_price, opt.expr_date, opt.type, 1, opt.buy_price))
		print("sell price: ", opt.sell_price)
		return True
	else:
		return False

def optionSell(opt, logger, close_market = False): # set close_market to True if you want to sell the option at a market price now
	logger.info("Try to place sell option")
	if not opt:
		logger.warning("Empty option, returned!")
		return False
	# first check if option is filled before selling it
#	buy_rlt = r.get_option_order_info(opt.buy_order_id) 
#	if (not buy_rlt["state"] == "filled") or (not buy_rlt["state"] == "completed"): return False
#	quant = int(buy_rlt["quantity"])
	quant = 1
	if close_market:
		#rlt = r.find_options_by_expiration_and_strike(opt.symbol, opt.expr_date, opt.strike_price, opt.type)
		#price = float(rlt[0]["adjusted_mark_price"])
		price = opt.price[-1]
	else:
		price = opt.sell_price
#	ret = r.order_sell_option_limit("close", "credit", price, opt.symbol, quant, opt.expr_date, opt.strike_price, opt.type)
	ret = {"state": "unconfirmed"}
	if ret:
		print(ret)
		opt.quantity = quant
#		opt.sell_order_id = ret["id"]
		opt.sell_state = ret["state"]
		opt.direction = "sell"
		logger.info("Order placed: symbol {}, strike_price {}, expr_date {}, type {}, quant {}, sell_price {}".format(opt.symbol, opt.strike_price, opt.expr_date, opt.type, quant, opt.sell_price))
		return True
	else:
		return False

def optionCancel(opt, logger, diretion="buy"): # only can cancel a option if it's in 'unconfirmed' or 'queued' state
	if opt.type == "": 
		logger.warning("Empty option, returned!")
		return False
	logger.info("cancel the option: symbol {}, strike_price {}, expr_date {}, type {}, sell_price {}".format(opt.symbol, opt.strike_price, opt.expr_date, opt.type, opt.sell_price))
	if diretion=="buy":
		if opt.buy_order_id=="": return False
		# first check the state of a option state
		rlt = r.get_option_order_info(opt.buy_order_id)
		if rlt["state"]=="queued" or rlt["state"]=="unconfirmed":
			ret = r.cancel_option_order(opt.buy_order_id)
			opt.buy_state = "canceled"
			return True
		else: return False
	elif direction=="sell":
		if opt.sell_order_id=="": return False
		# first check the state of a option state
		rlt = r.get_option_order_info(opt.sell_order_id)
		if rlt["state"]=="queued" or rlt["state"]=="unconfirmed":
			ret = r.cancel_option_order(opt.sell_order_id)
			opt.sell_state = "canceled"
			return True
		else: return False

def optionReplace(opt, logger, direction="buy"): # replace a sell order or buy order
	logger.info("Replacing the option:")
#	ret = optionCancel(opt, direction)
	ret = True 
	if ret:
		if direction=="sell": rlt = optionSell(opt, logger)
		elif direction=="buy": rlt = optionBuy(opt, logger)
		if rlt:
			return True
		else:
			return False
	else:
		return False

class optionChecker(threading.Thread):
	def __init__(self, stk, opt, refreshing_rate, direction="buy"):
		threading.Thread.__init__(self)
		self.stk = stk
		self.opt = opt
		self.refresh_rate = refreshing_rate

		self.logger = r.setup_logger("optionChecker", logfile_execution)
		self.logger.info("class optionChecker started...")

	def __del__(self):
		r.close_logger(self.logger)

	def run(self):
		valid_call = len(self.stk.signal) > 2 and ( "buy" in self.stk.signal[-3:] and self.opt.type == "call")
		valid_put = len(self.stk.signal) > 2 and ( "sell" in self.stk.signal[-3:] and self.opt.type == "put")
		valid_close = len(self.opt.signal) > 0 and (self.opt.signal[-1] == "close" or self.opt.signal[-1] == "")
		self.logger.info("waiting for {} option completed or canceled!".format(self.opt.direction))
		while valid_call or valid_put or valid_close:
			if self.opt.direction=="buy":
				#rlt = r.get_option_order_info(self.opt.buy_order_id)
				self.opt.buy_state = "filled"
				state = self.opt.buy_state
				print("checker!!!!!!!!!simulation: option bought at price: {}".format(self.opt.buy_price))
			elif self.opt.direction=="sell":
				#rlt = r.get_option_order_info(self.opt.sell_order_id)
				#rlt = r.find_options_by_expiration_and_strike(opt.symbol, opt.expr_date, opt.strike_price, opt.type)
				rlt = {"adjust_market_price": self.opt.price[-1]}
				if float(rlt["adjust_market_price"]) <= self.opt.sell_price:
					self.opt.close_price = float(rlt["adjust_market_price"])
					self.opt.sell_state = "completed"
				state = self.opt.sell_state
				print("checker!!!!!!!!!simulation: option sold at price: {}".format(self.opt.close_price))
			if state == "canceled" or state == "filled" or state == "completed":
				self.logger.info("{} option {}!".format(self.opt.direction, state))
				return True
			time.sleep(1)
			valid_call = len(self.stk.signal) > 2 and ( "buy" in self.stk.signal[-3:] and self.opt.type == "call")
			valid_put = len(self.stk.signal) > 2 and ( "sell" in self.stk.signal[-3:] == "sell" and self.opt.type == "put")
			valid_close = len(self.opt.signal) > 0 and (self.opt.signal[-1] == "close" or self.opt.signal[-1] == "")
		if (not valid_call) or (not valid_put) or (not valid_close):
			self.logger.info("signal has changed while the option order has not been filled. Thus this order will be canceled!")
			print("signal has changed while the option order has not been filled. Thus this order will be canceled!")
#			rlt = optionCancel(self.opt, direction)
			print("Error: tried to canceled the order but failed, pls check it, status: {}".format(state))
			print("expr_date:{}, strike_price:{}, option_type:{}".format(self.opt.expr_date, self.opt.strike_price, self.opt.type))

class orderExecution(threading.Thread):
	def __init__(self, stk, opt, period_ma1, period_ma2, period_ma3, refreshing_rate, limitPrice=100): # limitPrice: the maximum price to buy one option
		threading.Thread.__init__(self)
		self.stk = stk
		self.opt = opt
		self.limit_price = limitPrice
		self.period_ma1 = period_ma1
		self.period_ma2 = period_ma2
		self.period_ma3 = period_ma3
		self.refresh_rate = refreshing_rate

		self.logger = r.setup_logger("optionExecution", logfile_execution)
		self.logger.info("class optionExecution started...")
	
	def __del__(self):
		r.close_logger(self.logger)
	
	def run(self):
		while True:
			time.sleep(self.refresh_rate)
			warningTime = dt.time(hour = 15, minute = 40, second = 0)
			now = dt.datetime.now(tz)
#			if (self.opt.type=="") and now.time()> warningTime:
#				self.logger.info("Market is about to close in 15 minutes, won't trade option today, bye")
#				print("Market it about to close in 15 minutes, won't trade option today, bye")
#				return True
			if len(self.stk.signal)>1 and ("buy" in self.stk.signal[-2:] or "sell" in self.stk.signal[-2:]):
				self.logger.info("signal trigged, look for available options to buy...")
				print("signal trigged, look for available options to buy...")
				self.optionCandidate(self.opt, self.logger)
				print(self.opt)
				if not self.opt == None: 
					if len(self.opt.price) == 0: continue
					rlt = optionBuy(self.opt, self.logger)
					self.logger.info("Option order placed, waiting to be filled...")
					print("Option order placed, waiting to be filled...")
					thread_buychecker = optionChecker(self.stk, self.opt, self.refresh_rate, "buy")
					thread_buychecker.start()
					thread_buychecker.join()
					del thread_buychecker
					if self.opt.buy_state == "filled" or self.opt.buy_state == "completed": 
						print("Order confirmed, setting sell option order ...")
						self.logger.info("Order confirmed with buy_price {}, setting sell option order ...".format(self.opt.buy_price))
						optionSell(self.opt, self.logger) # immediately sell this option after buy to restrict the risk
						break
					elif self.opt.buy_state == "canceled":
						self.logger.info("Order has been canceled!")
						continue
					else:
						self.logger.error("Error, the order status is {}, orderExecution class will be returned.".format(opt.buy_state))
						print("Error, the order status is {}, orderExecution class will be returned.".format(self.opt.buy_state))
						return False
				else:
					self.logger.warning("Cannot find a available options to buy, check your accoun balance or market is not open!")
					print("Cannot find a available options to buy, check your accoun balance or market is not open!")

		while self.opt.direction == "sell": # since option is filled, will need to wait for closing this option
			if len(self.opt.signal)>0 and self.opt.signal[-1] == "close": # a signal to close the option immediately anyway
				self.logger.info("Close the option now, order will be placed!")
				print("Close the option now, order placed!")
				rlt = optionSell(self.opt, self.logger, True)
				# has to wait the sell action is completed
				thread_sellchecker = optionChecker(self.stk, self.opt, self.refresh_rate, "sell")
				thread_sellchecker.start()
				thread_sellchecker.join()
				del thread_sellchecker
			elif len(self.opt.signal)>0 and self.opt.signal[-1] == "": # here just to replace orders
#				rlt = r.get_option_order_info(self.opt.sell_order_id)
#				self.opt.sell_state = rlt["state"]
#				if (abs(self.opt.sell_price - float(ret["price"])) > 0):
#				print("Selling price changed,replacing the option order")
				rlt = optionReplace(self.opt, self.logger, "sell")
				#rlt = r.find_options_by_expiration_and_strike(opt.symbol, opt.expr_date, opt.strike_price, opt.type)
				rlt = {"adjust_market_price": float(self.opt.price[-1])}
				if float(rlt["adjust_market_price"]) <= self.opt.sell_price:
					self.opt.sell_state = "completed"
					self.opt.close_price = float(rlt["adjust_market_price"])
			if rlt:
				if self.opt.sell_state == "filled" or self.opt.sell_state == "completed": # sell orders completed --> finished
					self.logger.info("selling orders completed with sell_price {}".format(self.opt.close_price))
					print("hit!!!!!!!!!simulation: option sold at price: {}".format(self.opt.close_price))
					print("selling orders completed.")
					break
				elif self.opt.sell_state == "unconfirmed" or self.opt.sell_state == "queued": # meaning replacing orders done
					self.logger.info("selling orders unconfirmed or queued, waiting for close or replace")
					print("selling orders unconfirmed or queued.")
				else:
					self.logger.error("Error, the order status is {}, orderExecution class will be returned.".format(self.opt.sell_state))
					print("Error, the order status is {}, orderExecution class will be returned.".format(self.opt.sell_state))
					return False
			else:
				self.logger.info("Error, cannot selling or replacing options!")
				print("Error, cannot selling or replacing options!")
				print(self.opt)

			time.sleep(1)

		self.logger.info("A cycle of option actions has been completed today!")
		print("A cycle of option actions has been completed today!")
		return True

	def optionCandidate(self, opt, logger):
		logger.info("Looking for valid option to buy")
		if not opt.buy_state == "":
			opt.time = []
			opt.price = []
			opt.price_dvt = []
			opt.ema1 = []
			opt.ema2 = []
			opt.ema3 = []
			opt.sma1 = []
			opt.sma2 = []
			opt.sma3 = []
			opt.ema1_dvt = []
			opt.ema2_dvt = []
			opt.ema3_dvt = []
			opt.tmp_trend = []
			opt.trend = []
			opt.signal = []
			opt.status = []

#		if afterHours():
#			print("Market is closed now.")
#			return None
#		portfolio = r.load_portfolio_profile()
#		balance = (float(portfolio["extended_hours_equity"]) - float(portfolio["extended_hours_market_value"]))
#		if(balance < self.limit_price):
#			print("Your account balance is less than {}, will use the balance {} to buy options!".format(self.limit_price, balance))
#			self.limit_price = balance
#		us_holidays = holidays.US()
#		today = dt.datetime.now(pytz.timezone('US/Eastern'))
#		expr_date = today + dt.timedelta( (3-today.weekday()) % 7 + 1) # looking for the next Friday
#		while expr_date.strftime("%Y-%m-%d") in us_holidays:
#			expr_date = expr_date - t.timedelta(1)
#			if not expr_date >  today:
#				print("Cannot find a valid expiration date for options!")
#				return None # cannot find a valid expiration date
		if self.stk.signal[-1] == "buy": 
			option_type = "call"
		elif self.stk.signal[-1] == "sell": 
			option_type = "put"
		else: return None
		price = int(self.stk.price[-1]/5)*5
#		rlts = r.find_options_by_expiration(self.stk.symbol, expr_date.strftime("%Y-%m-%d"), option_type)
#		opts = []
#		for opt in rlts:
#			if float(opt["adjusted_mark_price"]) < self.limit_price*0.95/100 and float(opt["adjusted_mark_price"]) > 0.01:
#				dic = {}
#				dic["adjusted_mark_price"] = float(opt["adjusted_mark_price"])
#				dic["strike_price"] = float(opt["strike_price"])
#				dic["gamma"] = float(opt["gamma"])
#				opts.append(dic)
#		if len(opts) == 0: return None
#		opts.sort(key=lambda x: x["gamma"], reverse=True)
#		print("expr_date:{}, strike_price:{}, option_type:{}".format(expr_date.strftime("%Y-%m-%d"), opts[0]["strike_price"], option_type))
#		print("option price: {}, gamma: {}".format(opts[0]["adjusted_mark_price"], opts[0]["gamma"]))
#		return option(self.stk.symbol, expr_date.strftime("%Y-%m-%d"), opts[0]["strike_price"], option_type, self.period_ma1, self.period_ma2, self.period_ma3)
		opt.type = option_type
		opt.expr_date = "2020-07-17"
		opt.strike_price = price
		print("price: ", opt.strike_price)
		print("type: ", opt.type)
		print("time: ", opt.expr_date)
		logger.info("expr_date:{}, strike_price:{}, option_type:{}".format(opt.expr_date, opt.strike_price, option_type))
		return option(self.stk.symbol, "2020-07-17", price, option_type, self.period_ma1, self.period_ma2, self.period_ma3)



#login = r.login("","") 
#mystock = stock("AAPL", 10,20,50)
#mystock.signal.append("sell")
#order = orderExecution(mystock, 10, 20, 50, 5, 200)
##myoption = option("AAPL", "2020-07-17", 375, "put", 10, 20, 50)
##myoption.state = "unconfirmed"
##myoption.quantity = 1
##myoption.order_id = "3307ace1-ade8-4325-aaa8-86a89013dbd4"
#optionCancel(myoption)
#order.run()

