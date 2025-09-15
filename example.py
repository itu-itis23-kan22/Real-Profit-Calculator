import requests
from lxml import html


URL = 'https://www.cnbc.com/quotes/NVDA'
#https://tr.tradingview.com/symbols/NASDAQ-NVDA/
response = requests.get(url= URL)
tree = html.fromstring(response.content)
value = tree.xpath('//div[contains(@class, "lastPriceStripContainer")]/text()')
print(value)