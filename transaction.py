class Transaction:
    def __init__(self, stock_name,country_name,transaction_type,share_price,number_of_shares,transaction_fee,exchange_rate,currency,date,tl_price,usd_price):
        self.stock_name = stock_name
        self.country_name = country_name
        self.transaction_type = transaction_type
        self.share_price = share_price
        self.number_of_shares = number_of_shares
        self.transaction_fee = transaction_fee
        self.exchange_rate =exchange_rate
        self.currency = currency
        self.date= date
        self.tl_price = tl_price
        self.usd_price = usd_price