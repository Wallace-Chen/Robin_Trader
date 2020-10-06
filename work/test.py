import robin_stocks as r
import re
import datetime as dt
import pytz 
from modules import *

username = '54chenyuan@gmail.com'
password = '54tianCAI!'
#login = r.login(username, password)
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
#rlt = rlt["next_open_hours"]
#match = re.search(r"\d+-\d+-\d+", rlt)
#print(match.group())
#rlt = r.get_option_instrument_data_by_id("e09f9300-2c3b-4298-a36f-9d5e621d6b3f")
#rlt = r.get_instrument_by_url("https://api.robinhood.com/instruments/3324b13c-dc23-40e8-8807-76d87fdb09ed/")
#rlt = r.find_options_by_expiration_and_strike("AAPL", "2020-08-28", 500, "call")
#rlt = r.get_all_option_orders()
#rlt = r.get_option_order_info("7278a81b-ba84-43a7-a3fb-b2d0f25d15f8")
#rlt = r.helper.request_get("https://api.robinhood.com/options/instruments/6d316f71-c529-40e4-a56d-e1e59811a9f2/")
#rlt = r.get_option_market_data_by_id("e09f9300-2c3b-4298-a36f-9d5e621d6b3f")
#rlt = "https://api.robinhood.com/options/instruments/e09f9300-2c3b-4298-a36f-9d5e621d6b3f/".split('/')
#tz = pytz.timezone("US/Eastern")
#time = tz.localize(dt.datetime.strptime(rlt["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ"))
#now = dt.datetime.now(tz)
#print(now.date())
#print(time.date())
#print(time.date()==now.date())
#print(rlt["legs"][0]["executions"][0]["price"])
#l = []
#d1={"name": "li", "age": 2}
#d2={"name": "wang", "age": 3}
#d3={"name": "zhang", "age": 3}
#l.append(d1)
#l.append(d2)
#l.append(d3)
#for d in l:
#    print(d)
#    if(d["age"]==3): l.remove(d)
#print(rlt)
#print(rlt["margin_balances"]["day_trade_buying_power"])

#print(dt.datetime.now(pytz.timezone('US/Eastern')).strftime("%Y-%m-%d_%H:%M:%S"))

mytime = marketTime("test", False)
print(mytime.is_open)
