from modules import *
import os

username = ''
password = ''

# a class handling with automatic option trading
class ibot:
    def __init__(self, fname="log/ibot"):
        self.pending_orders = []
        self.filled_orders = []
        self.failed_orders = []
        self.cancelled_orders = []
        self.unknown_orders = []
        self.pidfile = "/var/run/ibot.pid"
        self.earningfile = "/var/www/html/test/data/earnings.txt"
        self.holdingfile = "/var/www/html/test/data/holdings.txt"
        self.writePidFile()
        atexit.register(self.all_done)
        
        self.fname = fname + "_" + dt.datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d_%H:%M") + ".log"
        self.forders = fname + "_orders.log"
        self.fcsv = fname + "_transactions.csv"

        self.logger = r.setup_logger("ibot", self.fname)
        self.logger.info("Biu, your ibot is waking up")
        print("Biu, your ibot is waking up")
        

        self.logger.info("Checking if market is open today...")
        self.mytime = marketTime(self.fname)
        self.logger.info("Today, market open: {}, time now: {}".format(self.mytime.is_open,  self.mytime.time))

        self.logger.info("checking stocks and options we are currently holding ...")
        self.myaccount = loadAccount(self.fname)
        self.optionToSell = len(self.myaccount.stocks_avai100)
        if(self.optionToSell==0):
            self.logger.info("There's no enough shares as collateral at the moment.")
        else:
            self.logger.info("Viola, we have some available options to sell today:")
            for stk in self.myaccount.stocks_avai100:
                self.logger.info("Sym: {:4s}, quantity: {:2f}".format(stk["symbol"], stk["num_contracts"]))
        self.optionHeld = len(self.myaccount.option_positions)
        if(self.optionHeld==0):
            self.logger.info("Emm, we don't hold any open options at the moment")
        else:
            self.logger.info("Nice, we are holding some open option positions:")
            for opt in self.myaccount.option_positions:
                self.logger.info("sym: {:4s} , quantity: {:2f}, credits per contract: {:7.2f}, current value: {:5.2f}, exp date: {}, strike price: {:6.2f}".format(opt["symbol"], opt["quantity"], opt["trade_price"], opt["price"], opt["exp_date"], opt["strike_price"]))
            self.logger.info("ibot will monitor these options' price")

        self.mytransaction = transaction(self.fname)
        

    def __del__(self):
        r.close_logger(self.logger)

    def all_done(self):
        os.remove(self.pidfile)


    # Setup PID file
    def writePidFile(self):
        pid = str(os.getpid())
        with open(self.pidfile, "w") as f:
            f.write(pid)

    # function to write orders into files
    def cleanUp(self):
        self.logger.info("writing orders to file...")
        num = 0
        order_types = self.filled_orders + self.failed_orders + self.unknown_orders + self.cancelled_orders
        with open(self.forders, "a") as f:
#            for tp in order_types:
            for order in order_types:
                line = "[{:11s}]: {:4s}, {:4s}, {:4s}, {:5s}, {}, strike price: {:6.2f}, adjusted price: {:5.2f}, quantity: {:2f}".format(order["status"], order["symbol"], order["side"], order["type"], order["position_effect"], order["exp_date"], order["strike_p"], order["adjusted_price"], order["quantity"])
                f.write(line)
                f.write('\n')
                num += 1
        self.logger.info("done, wrote {} records".format(num))

        # updating earnings and stocks holdings
        self.logger.info("writing earning file and stock holdings")
        earning = 0
        for order in self.filled_orders:
            ret = r.get_option_order_info(order["order_id"])
            amount = round(float(ret["legs"][0]["executions"][0]["price"])*100, 2)
            if ret["direction"] == "credit": earning += amount
            elif ret["direction"] == "debit": earning -= amount
        with open(self.earningfile, "a") as f:
            now = self.mytime.now()
            f.write("{},{},{},{}\n".format(now.year, now.month, now.day, earning))
        
        # only dump stocks with equity larger than $100
        stocks = self.myaccount.stocks_held
        stocks.sort(key=lambda x: x["equity"], reverse=True)
        with open(self.holdingfile, "w") as f:
            for stk in stocks:
                if(stk["equity"]>=100):
                    f.write("{},{}\n".format(stk["symbol"], stk["shares"]))
        self.logger.info("Clean up finished.")
                
    def run(self):

        if(self.mytime.now().time() >= self.mytime.closeTime):
            self.logger.warning("market is closed, ibot will exit and sleep!")
            return
        
        if( not self.mytime.opencheck() ):
            self.logger.warning("market is not open today, ibot will exit and sleep!")
            return
        
        self.logger.info("ibot start monitoring prices and selling available options")
        print("ibot start monitoring prices and selling available options")
        
        thread_priceMonitor = priceMonitor(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.fname)
        thread_openOptionPosition = openOptionPosition(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.fname)
        thread_checkPengingOrder = checkPengingOrder(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.filled_orders, self.failed_orders, self.cancelled_orders, self.unknown_orders, self.fname)
        thread_portfolioValue = portfolioValue(self.mytime, self.myaccount, self.holdingfile, self.fname)
        thread_portfolioValue.start()
        thread_priceMonitor.start()
        thread_openOptionPosition.start()
        thread_checkPengingOrder.start()

        while(self.mytime.now().time() < self.mytime.stopTime):
            time_to_wait = (self.mytime.tz.localize(dt.datetime.combine(dt.date.today() ,self.mytime.stopTime)) - self.mytime.now() ).total_seconds() 
            try:
                self.mytime.opennow()
            except Exception as e:
                self.logger.warning("Error occurs when trying get open information on the market, try re login")
                login = r.login(username, password)
            if(not thread_portfolioValue.is_alive()):
                thread_portfolioValue = None
                self.logger.warning("detect thread portfolioValue is dead! restarting...")
                thread_portfolioValue = portfolioValue(self.mytime, self.myaccount, self.holdingfile, self.fname)
                thread_portfolioValue.start()
            if(not thread_priceMonitor.is_alive()):
                thread_priceMonitor = None
                self.logger.warning("detect thread thread_priceMonitor is dead! restarting...")
                thread_priceMonitor = priceMonitor(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.fname)
                thread_priceMonitor.start()
            if(not thread_openOptionPosition.is_alive()):
                thread_openOptionPosition = None
                self.logger.warning("detect thread thread_openOptionPosition is dead! restarting...")
                thread_openOptionPosition = openOptionPosition(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.fname)
                thread_openOptionPosition.start()
            if(not thread_checkPengingOrder.is_alive()):
                thread_checkPengingOrder = None
                self.logger.warning("detect thread thread_checkPengingOrder is dead! restarting...")
                thread_checkPengingOrder = checkPengingOrder(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.filled_orders, self.failed_orders, self.cancelled_orders, self.unknown_orders, self.fname)
                thread_checkPengingOrder.start()

            self.logger.info("market will close in {} secs! now sleep a bit and check later.".format(int(time_to_wait)+1))
            time.sleep(min(300, int(time_to_wait)+1))
        
        """
        time.sleep(5)
        print("simulate: stop pricemonitor")
        thread_priceMonitor.stop()
        time.sleep(5)
        print("simulate: restart it")
        thread_priceMonitor = priceMonitor(self.mytime, self.myaccount, self.mytransaction, self.pending_orders, self.fname)
        thread_priceMonitor.start()
        time.sleep(5)
        """

        self.logger.info("market close soon, stop all threads...")
        print("market close soon, stop all threads...")
        try:
            thread_priceMonitor.stop()
            thread_openOptionPosition.stop()
            thread_checkPengingOrder.stop()
            thread_portfolioValue.stop()
            thread_priceMonitor.join()
            thread_openOptionPosition.join()
            thread_checkPengingOrder.join()
            thread_portfolioValue.join()
        except Exception as e:
            self.logger.info("Error occurs when trying to close threads: {}".format(e))

        try:
            self.cleanUp()
        except Exception as e:
            self.logger.info("Error occurs when cleaning up threads: {}".format(e))
        #self.logger.info("ibot finished all tasks, it's time to sleep and see you in {}".format((self.mytime.next_open_date - self.mytime.now())))
        self.logger.info("ibot finished all tasks, it's time to sleep !")

if __name__ == '__main__':
    mybot = ibot()
    mybot.run()

#    mybot = ibot("log/text.txt")
#    mybot.run()

