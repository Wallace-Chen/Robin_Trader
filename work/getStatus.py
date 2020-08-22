import robin_stocks as r

username = ''
password = ''
login = r.login(username, password)
#rlt = r.load_account_profile()
#rlt = r.load_portfolio_profile()
#rlt = r.get_all_option_positions() #Returns all option positions ever held for the account
#rlt = r.get_open_option_positions() # Returns all open option positions for the account.
#rlt = r.get_markets() # get market mic available "XANS" for nasdaq
rlt = r.get_market_hours("XNAS", "2020-08-22")
print(rlt)
