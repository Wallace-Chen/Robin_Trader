import robin_stocks as r
import pytz
import datetime as dt
import re
import holidays
import numpy as np

username = ''
password = ''
login = r.login(username, password)
#rlt = r.load_account_profile()
#rlt = r.load_portfolio_profile()
#rlt = r.get_all_option_positions() #Returns all option positions ever held for the account
#rlt = r.get_open_option_positions() # Returns all open option positions for the account.
#rlt = r.get_markets() # get market mic available "XANS" for nasdaq
#rlt = r.get_market_hours("XNAS", "2020-08-22")
#rlt = r.get_market_today_hours("XNAS")
#rlt = r.build_holdings()
#rlt = r.build_user_profile()
#rlt = r.get_all_positions()
#rlt = r.get_linked_bank_accounts() # bank id: 899c320a-0e80-4489-8b81-51535cd1992e
#rlt = r.get_bank_account_info("899c320a-0e80-4489-8b81-51535cd1992e")
#rlt = r.get_open_stock_positions() # get all open stock positions
#rlt = r.load_phoenix_account()
#rlt = r.get_all_open_option_orders()
#rlt = r.get_all_open_stock_orders()
#print(rlt)
#r.export_completed_option_orders("./", "test")

# a function to adjust the price given a min_ticks, min_ticks look like:
# {'above_tick': '0.05', 'below_tick': '0.01', 'cutoff_price': '3.00'} for example
def adjustPrice(instrument, price, roundup=False):
    if roundup:
        price = max(0.05, price)
    try:    
        if "min_ticks" in instrument: min_ticks = instrument["min_ticks"]
        else: return price
        if min_ticks==None or len(min_ticks)==0: return price
        cutoff = round(float(min_ticks["cutoff_price"]),2)
        above_tick = round(float(min_ticks["above_tick"]), 2)
        below_tick = round(float(min_ticks["below_tick"]), 2)
        if price>=cutoff: tick = above_tick
        elif price<cutoff: tick = below_tick
        if(price%tick == 0): return price
        if(roundup): return round((int(price/tick)) * tick,2)
        else: return round((int(price/tick)+1) * tick,2)
    except:
        return price

# class dealing with checking market open
class marketTime:
    def __init__(self, fname="log/market_time.log", verbose=True):
        self.verbose = verbose
        if self.verbose:
            self.logger = r.setup_logger("marketTime", fname)
            self.logger.info("Class marketTime initialized.")
    
        self.tz = pytz.timezone('US/Eastern')
        self.openTime = dt.time(hour = 9, minute = 30, second = 0)
        self.closeTime = dt.time(hour = 16, minute = 0, second = 0)
        self.stopTime = dt.time(hour = 15, minute = 55, second = 0)
        self.mic = "XNAS" # mic for NASDAQ
        self.is_open = False # open today ?
        self.open_now = False # open now ?
        self.next_open_date = ""
        self.opennow()

    def __del__(self):
#        self.logger.info("Class marketTime exited.")
        if self.verbose:
            r.close_logger(self.logger)
        else:
            pass
    
    # a function to check that if today is open or not.
    def opencheck(self):
        ret = r.get_market_today_hours(self.mic)
        self.is_open = ret["is_open"]
        match = re.search(r"\d+-\d+-\d+",  ret["next_open_hours"])
        if match:
            self.next_open_date = match.group()
        else:
            self.next_open_date = "date not found!"
        return self.is_open

    def checkdate(self, date):
        ret = r.get_market_hours(self.mic, date)
        return ret["is_open"]

    def now(self):
        self.time = dt.datetime.now(self.tz)
        return self.time

    # a function to check if market is open now
    def opennow(self):
        now = self.now()
        if(not self.opencheck()):
            self.open_now = False 
            return False
        if (now.time() >= self.openTime) and (now.time() < self.closeTime):
            self.open_now = True
        else:
            self.open_now = False
        return self.open_now

# class to load currently held stocks
class loadAccount:
    def __init__(self, fname="log/load_account.log"):
        self.logger = r.setup_logger("loadAccount", fname)
        self.logger.info("Class loadAccount initialized.")
        
        self.bankid = "899c320a-0e80-4489-8b81-51535cd1992e"

        self.stocks_held = [] # dictionaries, each dict for each stock, "symbol", "shares", "shares_avai", "num_contracts", "avai_contracts", "buy_price", "current_price"
        self.stocks_held100 = [] # stocks with shares greater than 100
        self.stocks_avai100 = [] # stocks with available shares greater than 100
        self.loadstocks()

        self.option_positions = [] # dictionaries, each dict for each open option positions, "symbol" "quantity" "trade_price" "option_id" "exp_date" "strike_price" "price"
        self.loadoptions()

        self.open_orders = [] # list of dictionaries, each dict for each open order, "order_id" "option_id" "quantity" "position_effect" "side" "type"
        self.loadorders()

    def __del__(self):
#        self.logger.info("Class loadAccount exited.")
        r.close_logger(self.logger)
        
    def loadstocks(self):
        self.logger.info("loading stocks...")
        self.stocks_held = []
        self.stocks_held100 = []
        self.stocks_avai100 = []
        ret = r.get_open_stock_positions()
        for stk in ret:
            dic = {}
            dic["symbol"] =  r.get_instrument_by_url(stk["instrument"])["symbol"]
            dic["shares"] = round(float(stk["quantity"]), 3)
            dic["shares_avai"] = int(float(stk["shares_available_for_exercise"]))
            dic["avai_contracts"] = int(dic["shares_avai"]/100)
            dic["num_contracts"] = int(float( stk["shares_available_for_exercise"] )/100)
            dic["buy_price"] = round(float(stk["average_buy_price"]), 2)
            dic["current_price"] = round(float(r.get_stock_quote_by_symbol(dic["symbol"])['last_trade_price']), 2)
            dic["equity"] = round(dic["current_price"] * dic["shares"],2)
            if(dic["shares"]>=100):
                self.stocks_held100.append(dic)
                if dic["shares_avai"]>=100: self.stocks_avai100.append(dic)
            self.stocks_held.append(dic)

    # a function to get stock buy price given a symbol
    def getStockPrice(self, sym):
        if(len(self.stocks_held)>0):
            for stk in self.stocks_held:
                if stk["symbol"]==sym:
                    return stk["buy_price"]
            return -1
        else:
            return -1

    # function to load currently open options positions
    def loadoptions(self):
        self.logger.info("loading options...")
        self.option_positions = []
        ret = r.get_open_option_positions()
        for opt in ret:
            dic = {}
            dic["symbol"] = opt["chain_symbol"]
            dic["quantity"] = int(float(opt["quantity"]))
            dic["trade_price"] = round(float(opt["average_price"]), 2)
            if(dic["trade_price"] > 0): continue # only consider credits openning positions
            dic["option_id"] = opt["option"].split('/')[-2]
            instrument = r.get_option_instrument_data_by_id(dic["option_id"])
            dic["exp_date"] = instrument["expiration_date"]
            dic["strike_price"] = round(float(instrument["strike_price"]),2)
            quote = r.get_option_market_data_by_id(dic["option_id"])
            dic["price"] = round(float(quote["adjusted_mark_price"]),2)
            dic["stock_price"] = self.getStockPrice(dic["symbol"])
            
            self.option_positions.append(dic)

    # function to load currently pending orders
    def loadorders(self):
        self.logger.info("loading open orders...")
        self.open_orders = []
        ret = r.get_all_open_option_orders()
        for order in ret:
            dic = {}
            dic["order_id"] = order["id"]
            dic["option_id"] = order["legs"][0]["option"].split('/')[-2]
            dic["quantity"] = int(float(order["quantity"]))
            dic["position_effect"] = order["legs"][0]["position_effect"]
            dic["side"] = order["legs"][0]["side"]
            dic["type"] = "unknown"
            strategy = None
            if not order["opening_strategy"]==None: strategy = order["opening_strategy"]
            elif not order["closing_strategy"]==None: strategy = order["closing_strategy"]
            if (not strategy==None) and "call" in strategy: dic["type"] = "call"
            elif (not strategy==None) and "put" in strategy: dic["type"] = "put"

            self.open_orders.append(dic)


# class to get the optimal option to trade given the stock symbol
class findOption:
    def __init__(self, fname="log/findOption.log"):
        self.logger = r.setup_logger("findOption", fname)
        self.logger.info("Class findOption initialized.")

        self.us_holidays = holidays.US()
        self.today = dt.datetime.now(pytz.timezone('US/Eastern'))

    def __del__(self):
#        self.logger.info("Class transaction exited.")
        r.close_logger(self.logger)

    # give a type of option, find optimal strike price 
    def returnRate(self, sym, price, date, buyin_price):
        opts = r.find_options_by_expiration(sym, date, "call")
        dicts = []
        for rlt in opts:
            try:
                strike_p = float(rlt['strike_price'])
                bid_price = float(rlt['bid_price'])
                if bid_price>0.01 and (strike_p-price)>2*bid_price and strike_p>1.1*price and strike_p>buyin_price:
                    dic = {}
                    dic["bid_price"] = bid_price
                    dic["strike_price"] = strike_p
                    dicts.append(dic)
            except Exception as e: 
                print(e)
                pass
        dicts.sort(key=lambda x: x["bid_price"], reverse=True)
        if(len(dicts)>0):
            rate = dicts[0]['bid_price']/price
            return rate,dicts[0]['bid_price']*100,dicts[0]['strike_price']
        else:
            return None
    
    # a function to return a best call option to sell given a stock
    def returnOption(self, sym, buyin_price=-1, nextFriday=False):
        self.logger.info("looking for a call option to sell for {} ...".format(sym))
        price = float(r.get_stock_quote_by_symbol(sym)['last_trade_price'])
        next_friday = self.today + dt.timedelta( (3 - self.today.weekday()) % 7 + 1) # looking for the next Friday
        next_friday = next_friday
        if next_friday.strftime("%Y-%m-%d") in self.us_holidays: 
            date1 = next_friday - dt.timedelta(1)
        else: date1 = next_friday
        date2 = next_friday + dt.timedelta(7)
        if date2.strftime("%Y-%m-%d") in self.us_holidays: date2 = date2 - dt.timedelta(1)
        ndays1 = np.busday_count(self.today.strftime("%Y-%m-%d"), date1.strftime("%Y-%m-%d"),  holidays=list(self.us_holidays)) + 1
        ndays2 = np.busday_count(self.today.strftime("%Y-%m-%d"), date2.strftime("%Y-%m-%d"), holidays=list(self.us_holidays)) + 1
        
        try:
            (p1_rate, p1_bid_price, p1_strike_p) = self.returnRate(sym, price, date1.strftime("%Y-%m-%d"), buyin_price)
            (p2_rate, p2_bid_price, p2_strike_p) = self.returnRate(sym, price, date2.strftime("%Y-%m-%d"), buyin_price)
            print("bid_price {}, date {}".format(p1_bid_price, date1))
            print("bid_price {}, date {}".format(p2_bid_price, date2))
        except Exception as e:
            self.logger.warning("ReturnOption: Fetching option failed: {}".format(e))
            print(e)
            return None
        if (not nextFriday) and (p1_bid_price/ndays1 <= 0.7*p2_bid_price/ndays2):
            return date2, p2_bid_price, p2_strike_p, price
        else:
            return date1, p1_bid_price, p1_strike_p, price

# class to handle with option tranctions
class transaction:
    def __init__(self, fname="log/transaction.log"):
        self.logger = r.setup_logger("transaction", fname)
        self.logger.info("Class transaction initialized.")

        self.us_holidays = holidays.US()
        self.today = dt.datetime.now(pytz.timezone('US/Eastern'))

    def __del__(self):
#        self.logger.info("Class transaction exited.")
        r.close_logger(self.logger)

    
    # submit a sell call option given a dict, the dictionary should contain:
    # "sym" "exp_date" "strike_p" "quantity" "current_price"
    # after, the dictionary will contain:
    # "adjusted_price" "status" "order_id" "option_id" "position_effect" "side" "type" "adjusted_price"
    # Note: this is a OPEN effect with credits
    def sellCallOption(self,dic):
        sym = dic['symbol']
        exp_date = dic['exp_date'].strftime("%Y-%m-%d")
        strike_p = dic['strike_p']
        quant = dic["quantity"]
        price = dic["current_price"]
        self.logger.info("prepare to submit the sell call order, symbol:{}, exp_date:{}, strike_price:{}, quantity: {}, current price:{}".format(sym, exp_date, strike_p, quant, price))
        rlt = r.find_options_by_expiration_and_strike(sym, exp_date, strike_p, "call")
        if (not len(rlt) > 0 ) or (not rlt[0]["tradability"] == "tradable"):
            print("\nFAILED to submit a sell Call option: symbol {}, strike_p {}, exp_date {}\n".format(sym, strike_p ,exp_date))
            self.logger.warning("cannot find available option!")
            dic["adjusted_price"] = -1
            dic["status"] = "Failed"
            return False
        bid_p = float(rlt[0]["bid_price"])
        ask_p = float(rlt[0]["ask_price"])
        adjusted_p = round((bid_p+ask_p)/2, 2)
        # here is the price limit check, the average month return rate should be at least 0.03, that is the amortized day return rate is 0.0015
        ndays = np.busday_count(self.today.strftime("%Y-%m-%d"), exp_date,  holidays=list(self.us_holidays)) + 1
        if(adjusted_p/ndays/price<0.0015):
            new_price = round((price*0.0015*ndays+adjusted_p)/2, 2)
            self.logger.warning("the adjusted price is too low {}, has been re-adjusted to {}".format(adjusted_p, new_price))
            adjusted_p = new_price
        instrument = r.get_option_instrument_data(sym, exp_date, strike_p, "call")
#        min_ticks = instrument["min_ticks"]
        adjusted_p = adjustPrice(instrument, adjusted_p, True)
        print("\nSubmiting a sell Call option: symbol {}, strike_p {}, exp_date {}, adjusted_price: {}\n".format(sym, strike_p ,exp_date, adjusted_p))
        dic["adjusted_price"] = adjusted_p
        try:
            self.logger.info("submitting the required order with adjusted price: {}".format(adjusted_p))
            ret = r.order_sell_option_limit("open", "credit", adjusted_p , sym, quant, exp_date, strike_p, "call")
            if ret:
                self.logger.info("Order submitted, the status is: {}".format(ret["state"]))
                print(" Submitted, the order status is: {}".format(ret["state"]))
                dic["status"] = ret["state"]
                dic["order_id"] = ret["id"]
                dic["option_id"] = rlt[0]["id"]
                dic["position_effect"] = "open"
                dic["side"] = "sell"
                dic["type"] = "call"
                dic["adjusted_price"] = adjusted_p
                return True
        except Exception as e:
            print(" Failed: {}".format(e))
            self.logger.error("Submission failed: {}".format(e))
            dic["status"] = "Failed"
            return False

    # submit a buy call option to close the option position given a dict, the dictionary should contain:
    # "symbol", "quantity" "strike_price" "exp_date" "option_id"
    # after, a new order dictionary will be returned
    # Note: this is a CLOSE effect with debits
    def buyCallOption(self,dic):
        try:
            quote = r.get_option_market_data_by_id(dic["option_id"])
            instrument = r.get_option_instrument_data_by_id(dic["option_id"])
#            min_ticks = instrument["min_ticks"]
            price = round(float(quote["adjusted_mark_price"]), 2)
            price = adjustPrice(instrument, price)
            # check if enough funds available
            profile = r.load_account_profile()
            #balance = round(float(profile["cash"]), 2)
            balance = round(float(profile["margin_balances"]["day_trade_buying_power"]), 2)
            if price*100 < balance:
                self.logger.info("Submitting to buy a option to close, sym:{}, quant:{}, exp_date:{}, strike_price:{}, price:{}".format(dic["symbol"], dic["quantity"], dic["exp_date"],  dic["strike_price"],price))
                ret = r.order_buy_option_limit("close", "debit", price, dic["symbol"], dic["quantity"], dic["exp_date"],  dic["strike_price"], "call")
                if ret:
                    opt = {}
                    opt["symbol"] = dic["symbol"]
                    opt["quantity"] = dic["quantity"]
                    opt["exp_date"] = dic["exp_date"]
                    opt["strike_p"] = dic["strike_price"]
                    opt["option_id"] = dic["option_id"]
                    opt["side"] = "buy"
                    opt["type"] = "call"
                    opt["position_effect"] = "close"
                    opt["order_id"] = ret["id"]
                    opt["status"] = ret["state"]
                    opt["adjusted_price"] = price
                    self.logger.info("Buy option order has been submiited, order id: {}, status: {}".format(opt["order_id"], opt["status"]))
                    return opt
                else:
                    self.logger.warning("failed to buy a option!")
                    return None
            else:
                self.logger.warning("trying to buy option but not enough funds, balance:{}, price:{}".format(balance, price*100))
                return None
        except Exception as e:
            self.logger.error(" error occured when trying to close the option: {}".format(e))
            return None

    # function to cancel a option order, the dictionary should contain the "order_id" and the status should be "unconfirmed" or "queued"
    def cancelOrder(self, dic):
        if "order_id" not in dic:
            self.logger.warning("cancelOrder: cannot find order_id, returned!")
            return False
        order_id = dic["order_id"]
        ret = r.get_option_order_info(order_id)
        if ret:
            if ret["state"]=="queued" or ret["state"]=="unconfirmed" or ret["state"]=="confirmed":
                rlt = r.cancel_option_order(order_id)
                self.logger.info("cancel option order  request submitted.")
                dic["status"] = "cancelled" 
                return True
            else:
                self.logger.warning("cannot cancel this order: {}, since the status is: {}".format(order_id, ret["state"]))
                return False
        else:
            self.logger.warning("cancelOrder: cannot get the info about this order, seems order id is not correct: {}".format(order_id))
            return False

if __name__ == '__main__':
#    myaccount = loadAccount()
#    print(myaccount.open_orders)
    mytransaction = transaction()
    dic={"order_id": "a4a06a12-df44-4d58-915d-21e724dc6fed" }
    ret = mytransaction.cancelOrder(dic)
    print(ret)
