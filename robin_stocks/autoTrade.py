from observer import *
from execute_orders import *

class tradingStrategy(realTimeShow):
	def __init__(self, symbol, refreshingRate = 5, period_sma1 = 0.1, period_sma2 = 0.2, period_sma3 = 0.5,showPlot=False):
		realTimeShow.__init__(self, symbol, refreshingRate, period_sma1, period_sma2, period_sma3, showPlot)
		print("initialize the tradingStrategy class")
#		self.myOption = None
		self.send_pipe_opt, self.recv_pipe_opt = mp.Pipe()
		self.plotterOption = showPrice()

	class analyze(threading.Thread):
		def __init__(self, stk, opt, refreshingRate, send_pipe, plotterOption, recv_pipe_opt, send_pipe_opt, fetchingPriceOption, showPlot=True):
			threading.Thread.__init__(self)
			self.refresh_rate = refreshingRate
			self.stk = stk
			self.opt = opt
			self.send_pipe = send_pipe
			self.plotterOption = plotterOption
			self.recv_pipe_opt = recv_pipe_opt
			self.send_pipe_opt = send_pipe_opt
			self.showPlot = showPlot
			self.fetchingPriceOption = fetchingPriceOption

		def run(self):
			plotshown = False
			initOpt = False
			while True:
				time.sleep(self.refresh_rate)
				r.strategy_ema(self.stk, self.opt, self.send_pipe, self.send_pipe_opt)
				
				if((not initOpt) and (not self.opt.type == "") and len(self.opt.price)==0):
					print("option will be initialized!") 
					initOpt = True
					initializeOption(self.opt)

					thread_fetchPriceOption = self.fetchingPriceOption(self.opt, self.refresh_rate)
					thread_fetchPriceOption.start()
				if (not plotshown) and self.showPlot and (not self.opt.type == ""):
					plotshown = True
					process_plotOptionPrice = mp.Process(target=self.plotterOption, args=(self.opt, self.recv_pipe_opt,self.refresh_rate,), daemon=True)
					process_plotOptionPrice.start()

	def run(self):
		thread_fetchPrice = self.fetchingPrice(self.myStock, self.refresh_rate)
		#thread_fetchPrice = self.fetchingPrice_simulation(self.myStock, self.refresh_rate) # for simulation
		thread_analyze = self.analyze(self.myStock, self.myOption, self.refresh_rate, self.send_pipe, self.plotterOption, self.recv_pipe_opt, self.send_pipe_opt, self.fetchingPriceOption)
		#thread_analyze = self.analyze(self.myStock, self.myOption, self.refresh_rate, self.send_pipe, self.plotterOption, self.recv_pipe_opt, self.send_pipe_opt, self.fetchingPriceOption_simulation) # for simulation
		thread_execute = orderExecution(self.myStock,  self.myOption, self.myStock.period_ma1, self.myStock.period_ma2, self.myStock.period_ma3, self.refresh_rate, 200)
		thread_fetchPrice.start()
		thread_analyze.start()
		thread_execute.start()
		if self.showplot:
			process_plotPrice = mp.Process(target=self.plotter, args=(self.myStock,self.recv_pipe,self.refresh_rate,), daemon=True)
			process_plotPrice.start()


		thread_fetchPrice.join()
		thread_analyze.join()
		thread_execute.join()

#		time.sleep(10)
#		global ENDFLAG
#		ENDFLAG = True
#		thread_fetchPrice.join()


if __name__ == '__main__':
	mp.set_start_method("forkserver") 
	myStrategy = tradingStrategy("AAPL",30, 12, 26, 60, True)
	myStrategy.run()
