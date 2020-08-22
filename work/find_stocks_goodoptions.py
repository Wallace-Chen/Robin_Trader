import robin_stocks as r
import datetime as dt
import holidays
import pytz
import numpy as np
import os

'''
This is a script that will load all stocks and do some analysis
'''

#!!! Fill out username and password
username = '54chenyuan@gmail.com'
password = '54tianCAI!'
#!!!

login = r.login(username, password)

returnOptionFlag = True
submitOptionSell = False

#stks = r.find_instrument_data("")
stks = [
    {'symbol': 'PLAY', 'tradeable': True, 'type': 'stock'},
    {'symbol': 'CCL', 'tradeable': True, 'type': 'stock'},
    {'symbol': 'UAL', 'tradeable': True, 'type': 'stock'}
]

def sellCallOption(dic):
    sym = dic['symbol']
    exp_date = dic['exp_date'].strftime("%Y-%m-%d")
    strike_p = dic['strike_p']
    rlt = r.find_options_by_expiration_and_strike(sym, exp_date, strike_p, "call")
    if (not len(rlt) > 0 ) or (not rlt[0]["tradability"] == "tradable"):
        print("\nFAILED to submit a sell Call option: symbol {}, strike_p {}, exp_date {}\n".format(sym, strike_p ,exp_date))
        return False
    bid_p = float(rlt[0]["bid_price"])
    ask_p = float(rlt[0]["ask_price"])
    adjusted_p = round(bid_p+ask_p/2, 2)
    print("\nSubmiting a sell Call option: symbol {}, strike_p {}, exp_date {}, adjusted_price: {}\n".format(sym, strike_p ,exp_date, adjusted_p))
    try:
        ret = r.order_sell_option_limit("open", "credit", adjusted_p , sym, 1, exp_date, strike_p, "call")
        if ret:
            print(" Submitted, the order status is: {}".format(ret["state"]))
            return True
    except:
        print(" Failed!")
        return False

def returnRate(sym, price, date):
    opts = r.find_options_by_expiration(sym, date, "call")
    #print("we have {} options to check".format(len(opts)))
    dicts = []
    num = 0
    for rlt in opts:
        num = num + 1
#        if(num>100): break
        try:
            strike_p = float(rlt['strike_price'])
            bid_price = float(rlt['bid_price'])
            #print("bid_price: {}, strike_price: {}\n".format(bid_price, strike_p))
            if bid_price>0.01 and (strike_p-price)>2*bid_price and strike_p>=1.1*price:
                dic = {}
                dic["bid_price"] = bid_price
                dic["strike_price"] = strike_p
                #print("Appended")
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
def returnOption(sym, price, checkCand=True):
    us_holidays = holidays.US()
    today = dt.datetime.now(pytz.timezone('US/Eastern'))
    next_friday = today + dt.timedelta( (3-today.weekday()) % 7 + 1) # looking for the next Friday
    next_friday = next_friday
    if next_friday.strftime("%Y-%m-%d") in us_holidays: 
        date1 = next_friday - dt.timedelta(1)
    else: date1 = next_friday
    date2 = next_friday + dt.timedelta(7)
    if date2.strftime("%Y-%m-%d") in us_holidays: date2 = date2 - dt.timedelta(1)
    candle_date = next_friday + dt.timedelta(7*3)
    if candle_date.strftime("%Y-%m-%d") in us_holidays: candle_date = candle_date - dt.timedelta(1)
    ndays1 = np.busday_count(today.strftime("%Y-%m-%d"), date1.strftime("%Y-%m-%d"),  holidays=list(us_holidays)) + 1
    ndays2 = np.busday_count(today.strftime("%Y-%m-%d"), date2.strftime("%Y-%m-%d"), holidays=list(us_holidays)) + 1
    ncand = np.busday_count(today.strftime("%Y-%m-%d"), candle_date.strftime("%Y-%m-%d"), holidays=list(us_holidays)) + 1
    #print("ndays1: {}, ndays2:{}, ncand:{}\n".format(ndays1, ndays2, ncand))
    
    print("date1: {}, date2:{}, cand: {}".format(date1, date2, candle_date))
    try:
        (c_rate, c_bid_price, c_strike_p) = returnRate(sym, price, candle_date.strftime("%Y-%m-%d"))
        (p1_rate, p1_bid_price, p1_strike_p) = returnRate(sym, price, date1.strftime("%Y-%m-%d"))
        (p2_rate, p2_bid_price, p2_strike_p) = returnRate(sym, price, date2.strftime("%Y-%m-%d"))
        print("bid_price {}, date {}".format(c_bid_price, candle_date))
        print("bid_price {}, date {}".format(p1_bid_price, date1))
        print("bid_price {}, date {}".format(p2_bid_price, date2))
    except Exception as e:
        print(e)
        return None
    if(checkCand and p1_bid_price/ndays1<0.8*c_bid_price/ncand and p2_bid_price/ndays2<0.8*c_bid_price/ncand):
        print("\nStrange price found in the next two weeks compared to a month later\n")
        print("next friday date: {}, strike_price: {}, amortized day price: {}\n ".format(date1, p1_strike_p, p1_bid_price/ndays1/100))
        print("the next two friday date: {}, strike_price: {}, amortized day price: {}\n ".format(date2, p2_strike_p, p2_bid_price/ndays2/100))
        print("the next month date: {}, strike_price: {}, amortized day price: {}\n".format(candle_date, c_strike_p, c_bid_price/ncand/100))
#        return None
    if(p1_bid_price/ndays1 <= 0.9*p2_bid_price/ndays2):
        return date2, p2_bid_price, p2_strike_p
    else:
        return date1, p1_bid_price, p1_strike_p

nums = len(stks)
counter = 0
print("{} stocks to be processed...".format(nums))
outs = []
for stk in stks:    
    counter = counter + 1
    if counter%(nums/100) == 0:
        print("\n {}\% finished\n".format(counter/(nums/100)))
    try:
        if not stk['tradeable']: continue
        if not stk['type'] == 'stock': continue
        sym = stk['symbol']
        price = float(r.get_stock_quote_by_symbol(sym)['last_trade_price'])
        if(price>200 or price<5): continue
    
        print("\n------------Getting option info for: {}-------------\n".format(sym))
        
        if returnOptionFlag:
            date, bid_price, strike_p = returnOption(sym, price, False)
            dic = {}
            dic['symbol'] = sym
            dic['profit'] = bid_price
            dic['exp_date'] = date
            dic['strike_p'] = strike_p
            dic['price'] = price
            outs.append(dic)
            if submitOptionSell: sellCallOption(dic)
        else:
            rate, profit, strike_p = returnRate(sym, price, "2020-08-28")
            if rate is not None:
                dic = {}
                dic['symbol'] = sym
                dic['returnRate'] = rate
                dic['profit'] = profit
                dic['strike_p'] = strike_p
                dic['price'] = price
                outs.append(dic)
    except Exception as e: 
        print(e)

if not returnOptionFlag:
    outs.sort(key=lambda x: x["returnRate"], reverse=True)

# write to a file:
folder = "outputs"
today = dt.datetime.now(pytz.timezone("Europe/Zurich"))
timestamp = today.strftime("%Y-%m-%d_%H:%M")
os.system('mkdir -p {}'.format(folder))
outf = "{}/stocks_{}.txt".format(folder, timestamp)
if returnOptionFlag: outf = "{}/options_{}.txt".format(folder, timestamp)
print("\nWe have {} stocks, writing data to the file: {}, a moment please...\n".format(len(outs), outf))

with open(outf, "w") as f:
    for stk in outs:
        print("  writing {}...".format(stk['symbol']))
        if returnOptionFlag:
            line = "SYMBOL: {:4s}, profits: {:6.1f}, expire date: {}, strike price: {:6.2f}, stock price: {:6.2f}".format(stk['symbol'],stk['profit'], stk['exp_date'].strftime("%Y-%m-%d"), stk['strike_p'],  stk['price'])
        else:
            line = "Return rate: {:5.3f}, profits per month: {:6.1f}, SYMBOL: {:4s}, strike price: {:6.2f}, stock price: {:6.2f}".format(stk['returnRate'], stk['profit'], stk['symbol'], stk['strike_p'], stk['price'])
        f.write(line)
        f.write('\n')
print("Done, please check the file.")
