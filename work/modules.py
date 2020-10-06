from utilities import *
from threadWrapper import *
import atexit

# a class monitoring open option prices and will close those low-value options
class priceMonitor(ThreadWithExc):
    def __init__(self, mytime, myaccount, mytransaction, pending_orders, fname="log/price_monitor.log"):
        threading.Thread.__init__(self)
        self.logger = r.setup_logger("priceMonitor", fname)
        self.logger.info("Class priceMonitor initialized.")

        self.mytime = mytime
        self.myaccount = myaccount
        self.mytransaction = mytransaction
        self.pending_orders = pending_orders
        
    def __del__(self):
        r.close_logger(self.logger)

    # function to update options price using loadoptions
    def updateOption(self):
        retry = 0 # use try - exception block in the case of busy network
        succeed = False
        try:
            self.myaccount.loadoptions()
            succeed = True
        except Exception as e:
            succeed = False
            self.logger.error("updating option error:{}".format(e))
        while retry<5 and not succeed:
            try:
                self.myaccount.loadoptions()
                succeed = True
            except Exception as e:
                succeed = False
                self.logger.error("updating option error:{}".format(e))
            time.sleep(30)
            retry += 1
        return succeed

    # check if dic has pending orders in open orders or pending orders
    def checkInstrument(self, dic):
        for order in self.myaccount.open_orders:
            if(order["option_id"]==dic["option_id"] and order["position_effect"]=="close" and order["side"]=="buy" and order["type"]=="call"):
                dic["quantity"] = max(0, dic["quantity"]-order["quantity"])
        for order in self.pending_orders:
            if(order["option_id"]==dic["option_id"] and order["position_effect"]=="close" and order["side"]=="buy" and order["type"]=="call"):
                dic["quantity"] = max(0, dic["quantity"]-order["quantity"])
        return dic["quantity"]>0

    # check option price and close low-value options
    def checkOption(self):
        if(len(self.myaccount.option_positions)>0):
            for opt in self.myaccount.option_positions:
                if(opt["price"]<=abs(opt["trade_price"])*0.01*0.1 or opt["price"]<=0.03): # low-value options
                    if(self.checkInstrument(opt)):
#                        if(self.mytime.tz.localize(dt.datetime.strptime(opt["exp_date"], "%Y-%m-%d")).date() == self.mytime.now().date()): continue # cannot trade options with exp_date equal to today
                        self.logger.info("found a low-value options, will close it, buy in price: {:6.2f}, current value: {:6.2f}".format(abs(opt["trade_price"])*0.01, opt["price"]))
                        order = self.mytransaction.buyCallOption(opt)
                        if not order==None:
                            self.pending_orders.append(order)
                            self.logger.info("order to buy option is submitted.")
                        else:
                            self.logger.error("cannot close the option position!")
        else:
            return
        

    def run(self):
        try:
            if(not self.mytime.opennow()):
                if(self.mytime.now().time() >= self.mytime.closeTime):
                    self.logger.info("The market has already been closed, thread will exit.")
                    raise SystemExit
                else:
                    time_to_wait = (self.mytime.tz.localize(dt.datetime.combine(dt.date.today() ,self.mytime.openTime)) - self.mytime.now() ).total_seconds()
                    self.logger.info("the market will be open in {} secs, so now sleep".format(int(time_to_wait)))
                    time.sleep(int(time_to_wait))
            while True:
                if(self.mytime.opennow()):
#                    self.logger.info("route: checking options")
                    if(self.updateOption()):
                        self.checkOption()
                time.sleep(300)

        except SystemExit:
            self.logger.info("exit signal received, terminating...")
        except Exception as e:
            self.logger.error("thread exited unexpecredly: {}".format(e))
        finally:
            self.logger.info("thread exited.")

# a class to sell options 
class openOptionPosition(ThreadWithExc):
    def __init__(self, mytime, myaccount, mytransaction, pending_orders, fname="log/open_optionposition.log"):
        threading.Thread.__init__(self)
        self.logger = r.setup_logger("openOptionPosition", fname)
        self.logger.info("Class openOptionPosition initialized.")

        self.mytime = mytime
        self.myaccount = myaccount
        self.mytransaction = mytransaction
        self.pending_orders = pending_orders

        self.myfindoption = findOption(fname)

    def __del__(self):
        r.close_logger(self.logger)

    # function to update stocks holdings
    def updateStocks(self):
        retry = 0
        succeed = False
        try:
            self.myaccount.loadstocks()
            succeed = True
        except Exception as e:
            succeed = False
            self.logger.info("updating stocks error: {}".format(e))
        while retry < 5 and not succeed:
            try:
                self.myaccount.loadstocks()
                succeed = True
            except Exception as e:
                succeed = False
                self.logger.info("updating stocks error: {}".format(e))
            finally:
                retry += 1
                time.sleep(30)
        return succeed

    # function to find option given a stock and then try to sell it.
    def openSellOption(self, stk):
        self.logger.info("trying to open the call option: {}".format(stk))
        try:
            date, bid_price, strike_p, price = self.myfindoption.returnOption(stk["symbol"], stk["buy_price"])
            # prepare opt to be submitted
            self.logger.info("preparing to submit the sell option, sym:{:4s}, quantity: {:2f}, stock price: {:6.2f}, exp date:{}, strike price:{:6.2f}".format(stk["symbol"], stk["num_contracts"], price, date,strike_p))
            opt = {"symbol": stk["symbol"], "quantity": stk["num_contracts"], "current_price": price, "exp_date": date, "strike_p": strike_p}
            ret = self.mytransaction.sellCallOption(opt)
            if ret:
                self.logger.info("order submitted.")
                self.pending_orders.append(opt)
            else:
                self.logger.info("failed to submit order.")
        except Exception as e:
            self.logger.info("selling option failed: {}".format(e))

    def run(self):
        try:
            if(not self.mytime.opennow()):
                if(self.mytime.now().time() >= self.mytime.closeTime):
                    self.logger.info("The market has already been closed, thread will exit.")
                    raise SystemExit
                else:
                    time_to_wait = (self.mytime.tz.localize(dt.datetime.combine(dt.date.today() ,self.mytime.openTime)) - self.mytime.now() ).total_seconds()
                    self.logger.info("the market will be open in {} secs, so now sleep".format(int(time_to_wait)))
                    time.sleep(int(time_to_wait))
            while True:
                if(self.mytime.opennow()):
#                    self.logger.info("route: checking stocks")
                    if(self.updateStocks() and len(self.myaccount.stocks_avai100)>0): # means we have available option to sell
#                    dic = {"symbol": "CCL", "buy_price": 17.00, "num_contracts": 1}
#                    self.myaccount.stocks_avai100.append(dic)
#                    if( len(self.myaccount.stocks_avai100)>0): # means we have available option to sell
                        for stk in self.myaccount.stocks_avai100:
                            self.openSellOption(stk)
                            
                time.sleep(600)

        except SystemExit:
            self.logger.info("exit signal received, terminating...")
        except Exception as e:
            self.logger.error("thread exited unexpecredly: {}".format(e))
        finally:
            self.logger.info("thread exited.")

# a class to check pending orders and clean up filled, failed, cancelled orders
class checkPengingOrder(ThreadWithExc):
    def __init__(self, mytime, myaccount, mytransaction, pending_orders, filled_orders, failed_orders, cancelled_orders, unknown_orders, fname="log/check_pendingorder.log"):
        threading.Thread.__init__(self)
        self.logger = r.setup_logger("checkPengingOrder", fname)
        self.logger.info("Class checkPengingOrder initialized.")

        self.expire_time = 1800 # after expire_time, still pending orders will be cancelled.
        self.refresh_time = 600
        self.quick_refresh = 5

        self.mytime = mytime
        self.myaccount = myaccount
        self.mytransaction = mytransaction
        self.pending_orders = pending_orders
        self.filled_orders = filled_orders
        self.failed_orders = failed_orders
        self.cancelled_orders = cancelled_orders
        self.unknown_orders = unknown_orders

    def __del__(self):
        r.close_logger(self.logger)

    def checkOrders(self, stop=False):
        tmp = []
        cancelled = False
        for order in self.pending_orders:
            ret = r.get_option_order_info(order["order_id"])
            status = ret["state"]
            order["status"] = status
            if(status=="cancelled"):
                self.logger.info("moving a cancelled order from pending list, id: {}".format(order["order_id"]))
                self.cancelled_orders.append(order)
            elif(status=="failed"):
                self.logger.info("moving a failed order from pending list, id:{}".format(order["order_id"]))
                self.failed_orders.append(order)
            elif(status=="filled"):
                self.logger.info("moving a filled order from pending list, id:{}".format(order["order_id"]))
                self.filled_orders.append(order)
            elif( status=="queued" or status=="confirmed" or status=="unconfirmed"):
                tmp.append(order)
                creation_time = self.mytime.tz.localize(dt.datetime.strptime(ret["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"))
                if stop or ((self.mytime.now()-creation_time).total_seconds() >= self.expire_time): # this pending orders will be cancelled
                    if stop:
                        self.logger.info("stop signal received, will cancel the order: {}".format(order["order_id"]))
                    else:
                        self.logger.info("this pending order lasts for {} secs, will cancel it, order id: {}".format(self.expire_time,order["order_id"]))
                    cancelled = True
                    try:
                        rlt = self.mytransaction.cancelOrder(order)
                        if rlt: self.logger.info("cancel request submitted.")
                        else: self.logger.info("cancel order failed.")
                    except Exception as e:
                        self.logger.error("error occured when canceling order: {}".format(e))
                        pass
                else:
                    self.logger.info("{} order is pending.".format(order["order_id"]))
                
            else:
                self.logger.error("cannot recognize the status of this order: {}, id: {}".format(status, order["order_id"]))
                self.unknown_orders.append(order)
            self.pending_orders[:] = tmp
            return cancelled

    # function to cancel all pending orders
    def cleanUp(self):
        self.logger.info("clean up all pending orders...")
        self.checkOrders(True)
        time.sleep(5)
        self.checkOrders(True)
        if(len(self.pending_orders)>0):
            self.logger.error("still find pending orders:")
            for order in self.pending_orders:
                ret = r.get_option_order_info(order["order_id"])
                self.logger.info("order id: {}, status: {}".format(order["order_id"], ret["state"]))
        self.logger.info("clean up finished, exit...") 


    def run(self):
        waiting_time = self.refresh_time
        try:
            if(not self.mytime.opennow()):
                if(self.mytime.now().time() >= self.mytime.closeTime):
                    self.logger.info("The market has already been closed, thread will exit.")
                    raise SystemExit
                else:
                    time_to_wait = (self.mytime.tz.localize(dt.datetime.combine(dt.date.today() ,self.mytime.openTime)) - self.mytime.now() ).total_seconds()
                    self.logger.info("the market will be open in {} secs, so now sleep".format(int(time_to_wait)))
                    time.sleep(int(time_to_wait))
            while True:
                if(self.mytime.opennow()):
                    self.logger.info("route: checking pending orders")
                    if( len(self.pending_orders)>0 ):
                        self.logger.info("have pending orders")
                        ret = self.checkOrders()
                        if ret: waiting_time = self.quick_refresh
                        else: waiting_time = self.refresh_time
                            
                time.sleep(waiting_time)

        except SystemExit:
            self.logger.info("exit signal received, terminating...")
        except Exception as e:
            self.logger.error("thread exited unexpecredly: {}".format(e))
        finally:
            if( len(self.pending_orders)>0 ): self.cleanUp()
            self.logger.info("thread exited.")

# a class to update portfolio value
class portfolioValue(ThreadWithExc):
    def __init__(self, mytime, myaccount, holdingfile ,fname="log/portfolio_value.log"):
        threading.Thread.__init__(self)
        self.logger = r.setup_logger("portfolioValue", fname)
        self.logger.info("Class portfolioValue initialized.")

        self.refresh_time = 1800
        self.outf = "/var/www/html/test/data/data.txt"

        self.mytime = mytime
        self.myaccount = myaccount
        self.holdingfile = holdingfile
    
    def __del__(self):
        r.close_logger(self.logger)

    def run(self):
        try:
            while True:
                # writing portfolio value
                profile = r.load_portfolio_profile() 
                if self.mytime.opennow(): balance = round(float(profile["equity"]), 2)
                else:  balance = round(float(profile["extended_hours_equity"]), 2)
                now = self.mytime.now()
                with open(self.outf, "a") as f:
                    f.write("{},{},{},{},{},{}\n".format(now.year, now.month, now.day, now.hour, now.minute, balance))

                # stocks holdings
                self.logger.info("stock holdings")
        
                # only dump stocks with equity larger than $100
                stocks = self.myaccount.stocks_held
                stocks.sort(key=lambda x: x["equity"], reverse=True)
                with open(self.holdingfile, "w") as f:
                    for stk in stocks:
                        if(stk["equity"]>=100):
                            f.write("{},{}\n".format(stk["symbol"], stk["shares"]))
                time.sleep(self.refresh_time)

        except SystemExit:
            self.logger.info("exit signal received, terminating...")
        except Exception as e:
            self.logger.error("thread exited unexpecredly: {}".format(e))
        finally:
            self.logger.info("thread exited.")

if __name__ == '__main__':
   mytime = marketTime("",False)
   myaccount = loadAccount("log/test.txt")
   mytransaction = transaction("log/test.txt")
   pending_orders = []

   dic = {"symbol": "CCL", "buy_price": 17.00, "num_contracts": 1}
   myaccount.stocks_avai100.append(dic)
   thread_openOptionPosition = openOptionPosition(mytime, myaccount, mytransaction, pending_orders, "log/test.txt")
   print(pending_orders)
   thread_openOptionPosition.start()
   time.sleep(10)
   print("stoping threads.")
   thread_openOptionPosition.stop()
   thread_openOptionPosition.join()
   print(" new length {}".format(len(pending_orders)))
   print(pending_orders)
