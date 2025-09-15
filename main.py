from datetime import datetime
import time
import csv
import requests
from lxml import html
import os
from decimal import Decimal, getcontext, ROUND_HALF_EVEN


#to - do

# inflation rate
# editing past transactions: User will select what he/se wants to edit.
#duplicated code

def round_money(value: Decimal, places: int = 4) -> Decimal:
    quant = Decimal('1').scaleb(-places)  # 0.0001
    return value.quantize(quant, rounding=ROUND_HALF_EVEN)


def read_shares_csv(): #deneme
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        shares = {}
        for line in reader:
            shares[f"{line['share_name']}"] = float(f"{line['quantity']}")
        return shares #


def show_stocks():
    rows = []
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for share in reader:
            while True:
                try:
                    price = float(input(f"What is the current price of share of {share['share_name']} (eg. 19.5): "))
                    break
                except ValueError:
                    print("Invalid price, try again.")
            share['price'] = price
            rows.append(share)

    dollar = get_dollar()
    print('-' * 46)
    print(f"|Share Name|Quantity|Dollar Value|  TL Value  |")

    dollar_sum = 0.0
    for share in rows:
        qty = float(share['quantity'])
        country = share['country_name'].upper()
        price = float(share['price'])

        if country == 'US':
            usd_price = qty * price
            tr_price = usd_price * dollar
        elif country == 'TR':
            tr_price = qty * price
            usd_price = tr_price / dollar
        else:
            print('Unexpected country name has been detected.')
            usd_price = tr_price = 0.0

        print(f"|{share['share_name']:^10}|{qty:^8.1f}|{usd_price:^12.4f}|{tr_price:^12.4f}|")
        dollar_sum += usd_price

    print(f"|{'Total':^10}|{'----':^8}|{dollar_sum:^12.4f}|{(dollar_sum*dollar):^12.4f}|")


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_dollar():
    url = 'https://kur.doviz.com/serbest-piyasa/amerikan-dolari'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        tree = html.fromstring(response.content)
        value_strs = tree.xpath('//div[@class="text-xl font-semibold text-white"]/text()')
        if not value_strs:
            print("Exchange rate value not found. XPath result is empty.")
            return None
        value_str = value_strs[0]
        try:
            value_float = float(value_str.replace(",", "."))
        except ValueError:
            print(f"Exchange rate value could not be converted to float: '{value_str}'")
            return None
        return Decimal(str(value_float))
    except requests.Timeout:
        print("Timeout occurred while retrieving the exchange rate.")
        return None
    except requests.RequestException as e:
        print(f"An error occurred during the exchange rate request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def load_bar():
    for i in range(0):
        print("-", end="", flush=True)
        time.sleep(0.05)
    print()


def is_info_file_exist():
    try:
        with open("info.txt", mode='r'):
            return True
    except OSError:
        print("Welcome to the reel profit calculation.")
        return False


def create_info_file(usr_name: str):
    with open("info.txt", mode = 'w') as f:
        f.write(f"Name: {usr_name.strip().capitalize()}\n")
        f.write(f"Date: {datetime.today()}")
    print(f"{usr_name.capitalize()}, your account was created on {datetime.today()} ")


def get_usr_info():
    try:
        with open("info.txt", "r") as f:
            for line in f:
                if line.startswith("Name:"):
                    usr_name = line.split()[1]
                elif line.startswith("Date:"):
                    date = line.split()[1]
        return usr_name, date
    except OSError:
        if is_info_file_exist():
            print("Unexpected error")
        else:
            print("Info file couldn't be found.")
        return None, None


def create_files():
    if not os.path.exists("operations.csv"):
        with open("operations.csv", mode="w") as f:
            writer = csv.writer(f)
            writer.writerow(
                ['id','stock_name', 'country_name', 'transaction_type', 'share_price',
                 'number_of_shares', 'transaction_fee', 'exchange_rate', 'currency', 'date' ,'tl_price', 'usd_price']
            )
    if not os.path.exists("inflation.csv"):
        with open("inflation.csv", mode="w") as f:
            writer = csv.writer(f)
            writer.writerow(
                ['month', 'year', 'country', 'rate']
            )
    if not os.path.exists("shares.csv"):
        with open("shares.csv", mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                'share_name','country_name', 'quantity'
            ])


def share_purchase(stock_name,country_name,transaction_type,share_price,number_of_shares,transaction_fee,exchange_rate,currency,date):
    price = Decimal(str(share_price))
    qty = Decimal(str(number_of_shares))
    fee = Decimal(str(transaction_fee))
    rate = Decimal(str(exchange_rate))
    if currency == 'TL':
        tl_price = round_money(price * qty)
        usd_price = round_money(tl_price / rate)
    else:  # USD
        usd_price = round_money(price * qty)
        tl_price = round_money(usd_price * rate)
        # total_cost =  will be added later
    new_id = 0
    with open('operations.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            new_id = max(new_id, int(row['id']))
        new_id +=1
    with open('operations.csv', mode = 'a', newline='') as f:
        writer = csv.writer(f)

        writer.writerow([new_id,stock_name,country_name, transaction_type,share_price,
                         number_of_shares,transaction_fee,exchange_rate,currency,date, f'{tl_price}', f'{usd_price}'
        ])

    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        control = False
        rows = []
        for row in reader:
            if stock_name == row['share_name']:
                row['quantity'] = str(float(row['quantity']) + float(number_of_shares))
                control = True
            rows.append(row)
    if not control:
        rows.append({
            'share_name': stock_name,
            'country_name': country_name,
            'quantity': str(number_of_shares)
        })
    with open('shares.csv', mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


    print('Successfully saved.')


def share_sale(stock_name,country_name,transaction_type,share_price,number_of_shares,transaction_fee,exchange_rate,currency,date):
    

    price = Decimal(str(share_price))
    qty = Decimal(str(number_of_shares))
    fee = Decimal(str(transaction_fee))
    rate = Decimal(str(exchange_rate))
    
    # Calculate TL and USD equivalents for the sale
    if currency == 'TL':
        tl_price = round_money(price * qty)
        usd_price = round_money(tl_price / rate)
    else:
        usd_price = round_money(price * qty)
        tl_price = round_money(usd_price * rate)
    # Read current shares as a dict: {share_name: quantity}
    
    shares = read_shares_csv()

    # Existence & quantity checks
    if stock_name not in shares:
        print(f"You don't have this share: {stock_name}")
        return
    if float(number_of_shares) > float(shares[stock_name]):
        print(f"The number of shares you have is not enough. You have {shares[stock_name]} shares but you tried to sell {number_of_shares} shares.")
        return

    new_id = 0
    with open('operations.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            new_id = max(new_id, int(row['id']))
        new_id += 1

    # 1) Append this sale into operations.csv (log the transaction)
    with open('operations.csv', mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            new_id,
            stock_name,
            country_name,
            transaction_type,
            share_price,
            number_of_shares,
            transaction_fee,
            exchange_rate,
            currency,
            date,
            f"{tl_price:.4f}",
            f"{usd_price:.4f}"
        ])

    # 2) Update shares.csv (decrease quantity and remove the row if it reaches 0)
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = []
        for row in reader:
            if row['share_name'] == stock_name:
                new_qty = float(row['quantity']) - float(number_of_shares)
                if new_qty > 0:
                    row['quantity'] = str(new_qty)
                    rows.append(row)
                else:
                    # Quantity drops to zero; omit the row to "remove" the position
                    pass
            else:
                rows.append(row)

    with open('shares.csv', mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print('Sale saved and positions updated successfully.')


def opr(country_name: str):
    create_files()
    print()
    print('1. Share Purchase')
    print('2. Share Sale')
    print('3. Edit past transactions.')
    print('0. Return to the previous page.')
    try:
        choice = int(input('Please select the action you wish to perform from the options above: '))
    except ValueError:
        print('You can only enter a number between 0-3.')
        opr(country_name)
    else:
        if choice == 0:
            router()
        elif choice == 1:
            try:

                stock_name = input("Enter stock name: ").upper()
                share_price = float(input("Enter share price: "))
                number_of_shares = float(input("Enter number of shares: "))
                transaction_fee = float(input("Enter transaction fee: "))
                exchange_rate = float(input("Enter exchange rate, if you want to get it automatically enter 0: "))
                if exchange_rate == 0:
                    exchange_rate = get_dollar()
                while True:
                    currency = input("Enter currency: (tl, usd): ").upper()
                    if currency == 'TL' or currency == 'USD':
                        break
                    else:
                        print('You can only enter TL or USD')
                while True:
                    date = input("Enter date (YYYY-MM-DD), if you want to get it automatically enter 0: ")
                    if  date == '0':
                        date = str(datetime.today()).split()[0]
                        break
                    elif is_valid_date(date):
                        break
                    else:
                        print('You need to enter a valid date. (Ex: 2025-12-19)')
                share_purchase(stock_name=stock_name, country_name= country_name, transaction_type='purchase',
                               share_price=share_price, number_of_shares=number_of_shares,
                               transaction_fee=transaction_fee, exchange_rate=exchange_rate,
                               currency=currency, date=date)
            except ValueError as e:
                print(f'Invalid input detected. {e}')
                print('You are being redirected to the previous page.')
                load_bar()
                opr(country_name)
            else:
                router()

        elif choice == 2:
            read_shares_csv()


            try:
                stock_name = input("Enter stock name: ").upper()
                share_price = float(input("Enter share price: "))
                number_of_shares = float(input("Enter number of shares: "))
                transaction_fee = float(input("Enter transaction fee: "))
                exchange_rate = float(input("Enter exchange rate, if you want to get it automatically enter 0: "))
                if exchange_rate == 0:
                    exchange_rate = get_dollar()
                while True:
                    currency = input("Enter currency: (tl, usd): ").upper()
                    if currency == 'TL' or currency == 'USD':
                        break
                    else:
                        print('You can only enter TL or USD')
                while True:
                    date = input("Enter date (YYYY-MM-DD), if you want to get it automatically enter 0: ")
                    if  date == '0':
                        date = str(datetime.today()).split()[0]
                        break
                    elif is_valid_date(date):
                        break
                    else:
                        print('You need to enter a valid date. (Ex: 2025-12-19)')
                share_sale(stock_name=stock_name, country_name= country_name, transaction_type='sale',
                               share_price=share_price, number_of_shares=number_of_shares,
                               transaction_fee=transaction_fee, exchange_rate=exchange_rate,
                               currency=currency, date=date)
            except ValueError as e:
                print(f'Invalid input detected. {e}')
                print('You are being redirected to the previous page.')
                load_bar()
                opr(country_name)
            else:
                router()

        elif choice == 3: # Edit past transactions.
            operations =[]
            with open('operations.csv', mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for operation in reader:
                    operations.append(operation)

            if not operations:
                print('There has been no transaction yet. First, you need to make a transaction.')

            usr_share_name = input('Please enter the name of the share you want to edit (eg. NVDA): ').strip().upper()
            matched_transactions = {}
            count = 0
            id_edit = 0
            for share in operations:
                if share['stock_name'] == usr_share_name:
                    matched_transactions[count] = share
                    if count == 0:
                        print(
                            f"| {'Number':^6} | {'Stock Name':^12} | {'Country Name':^14} | {'Transaction Type':^18} | {'Share Price':^13} | {'Number Of Shares':^18} | {'Transaction Fee':^15} | {'Exchange Rate':^14} | {'Currency':^8} | {'Date':^10} | {'TL Price':^10} | {'USD Price':^10} |")
                    count += 1

                    print(
                        f"| {count:^6} | {share['stock_name']:^12} | {share['country_name']:^14} | {share['transaction_type']:^18} | {share['share_price']:^13} | {share['number_of_shares']:^18} | {share['transaction_fee']:^15} | {share['exchange_rate']:^14} | {share['currency']:^8} | {share['date']:^10} | {share['tl_price']:^10} | {share['usd_price']:^10} |")
            if not matched_transactions:
                print('There has been no transaction executed for this share.')
                router()
            while True:
                try:
                    choice = int(input('Please enter the number of transaction you want to edit: '))
                except ValueError:
                    print('You can only enter a number.')
                else:
                    if 0<= choice <= count:

                        break
                    else:
                        print(f'You can only enter a number between 0-{count} (Enter 0 to exit)')

            print('This function has not yet been completed.')



        else:
            print('Please enter a number within the valid range.')
            opr(country_name)


def edit_inflation_rates():
    create_files()
def calculate_reel_profit():
    print("Calculating...")
    load_bar()

def router():
    print()
    print("1. US Stock Operations")
    print("2. TR Stock Operations")
    print("3. Edit Inflation Rates")
    print("4. Calculate my reel profit")
    print("5. Show my stock summary")
    print("0. Exit")

    try:
        choice = int(input("Please enter the number which indicates the operation you want to do: "))
    except ValueError:
        print("Please enter a number.")
        router()
    else:
        if choice == 1:
            print('\nYour country has been selected as US.')
            opr('US')
        elif choice == 2:
            print('\nYour country has been selected as TR.')
            opr('TR')
        elif choice == 3:
            edit_inflation_rates()
        elif choice == 4:
            calculate_reel_profit()
        elif choice == 5:
            show_stocks()
        elif choice == 0:
            print("Exiting...")
            load_bar()

        else:
            print("Please enter a valid number. (0- 4)")
            router()

if __name__ == '__main__':
    print('-' * 20 + "Welcome to Reel Profit Application" + '-' * 20) #74
    load_bar()
    if not is_info_file_exist():
        name = input("Please enter your name: ")
        create_info_file(name)
    else:
        usr_info = get_usr_info()
        print(f"Hello {usr_info[0]}")
        print("You can operate what you want.")
    router()
