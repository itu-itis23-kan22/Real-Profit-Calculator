from datetime import datetime
import time
import csv
import requests
from lxml import html
import os
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation


#to - do


# editing past transactions: User will select what he/se wants to edit. 
# duplicated code

def ask_price(country: str, symbol: str) -> Decimal | None:
    while True:
        choice = input("How do you want to get the price? Auto (A) / Manual (M) / Cancel (0): ").strip().upper()
        if choice == 'A':
            price = get_share_price(country, symbol)
            if price is not None:
                return price
            print("Failed to fetch automatically. Choose Manual (M) or try again.")
            continue
        elif choice == 'M':
            while True:
                raw = input("Enter the price: ").strip().replace(',', '.')
                try:
                    price = Decimal(raw)
                    if price > 0:
                        return price
                    print("Price must be greater than 0.")
                except (InvalidOperation, ValueError):
                    print("Invalid price. Please enter a valid number.")
        elif choice == '0':
            return None
        else:
            print("Invalid choice. Please enter A, M, or 0.")


def get_share_price_tr(name: str) -> Decimal | None:
    name = name.strip().upper()
    referer = f"https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={name}"
    one_endeks_url = f"https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/OneEndeks?endeks={name}"
    session = requests.Session()
    ua = "Mozilla/5.0"
    try:
        session.get(referer, headers={"User-Agent": ua}, timeout=10)
        headers = {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
        }
        resp = session.get(one_endeks_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    row = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else None)
    if not row or row.get("symbol") != name:
        return None
    last_value = row.get("last")
    if last_value is None:
        return None
    try:
        return Decimal(str(last_value).replace(',', '.'))
    except Exception:
        return None


def get_share_price_us(name: str) -> Decimal | None:
    name = name.strip().upper()
    base_url = 'https://www.cnbc.com/quotes/'
    url = base_url + name
    headers = { 'User-Agent': 'Mozilla/5.0' }
    try:
        response = requests.get(url=url, headers=headers, timeout=10)
        response.raise_for_status()
        tree = html.fromstring(response.content)
        value_list = tree.xpath('//span[@class="QuoteStrip-lastPrice"]/text()')
    except Exception:
        return None
    if not value_list:
        return None
    raw = value_list[0].strip()
    # Clean formats like "$ 123.45" or "," thousands
    cleaned = raw.replace(',', '')
    if cleaned.startswith('$'):
        cleaned = cleaned.lstrip('$').strip()
    try:
        return Decimal(cleaned)
    except Exception:
        # Fallback: handle TR-style comma decimal
        try:
            return Decimal(raw.replace('.', '').replace(',', '.'))
        except Exception:
            return None


def get_share_price(country: str, name: str) -> Decimal | None:
    if country == 'US':
        return get_share_price_us(name)
    elif country == 'TR':
        return get_share_price_tr(name)
    else:
        raise ValueError(f"Invalid country: {country}")


def round_money(value: Decimal, places: int = 4) -> Decimal:
    quant = Decimal('1').scaleb(-places)  # 0.0001
    return value.quantize(quant, rounding=ROUND_HALF_EVEN)


def read_shares_csv() -> dict[str, Decimal]:
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        shares = {}
        for line in reader:
            shares[f"{line['share_name']}"] = Decimal(line['quantity'])
        return shares # type: dict[str, Decimal]


def show_stocks():
    rows = []
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for share in reader:
            price = ask_price(share['country_name'], share['share_name'])
            share['price'] = price
            if price is not None:
                rows.append(share)
            else:
                print("Failed to get the price. Thus, the share will be excluded from the list.")

    dollar = get_dollar() # type: get_dollar() -> Decimal
    if dollar is None:
        print("Failed to get the dollar value.")
        return

    print('_' * 46)
    print(f"|Share Name|Quantity|Dollar Value|  TL Value  |")

    dollar_sum = Decimal('0')
    for share in rows:
        qty = Decimal(str(share['quantity']))
        country = share['country_name'].upper()
        price = share['price']  # already Decimal

        if country == 'US':
            usd_price = round_money(qty * price)
            tr_price = round_money(usd_price * dollar)
        elif country == 'TR':
            tr_price = round_money(qty * price)
            usd_price = round_money(tr_price / dollar)
        else:
            print('Unexpected country name has been detected.')
            usd_price = tr_price = Decimal('0')

        print(f"|{share['share_name']:^10}|{qty:^8.4f}|{usd_price:^12.4f}|{tr_price:^12.4f}|")
        dollar_sum += usd_price

    print(f"|{'Total':^10}|{'----':^8}|{round_money(dollar_sum):^12.4f}|{round_money(dollar_sum*dollar):^12.4f}|")
    print('¯' * 46)
    while True:
        is_continue = input("If you want to continue, press Y. Press 0 to exit: ").upper()
        if is_continue == 'Y':
            router()
            return
        elif is_continue == '0':
            print('Exiting...')
            load_bar()
            return
        else:
            print('You can only enter Y or 0.')


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_dollar() -> Decimal:
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
            return Decimal(value_str.replace(",", "."))
        except Exception:
            print(f"Exchange rate value could not be parsed: '{value_str}'")
            return None
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
    for i in range(0): # 74 is the length of the load bar
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
                current_qty = Decimal(row['quantity'])
                new_qty = current_qty + qty
                row['quantity'] = str(new_qty)
                control = True
            rows.append(row)
    if not control:
        rows.append({
            'share_name': stock_name,
            'country_name': country_name,
            'quantity': str(qty)
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
    have_qty = shares[stock_name]
    if qty > have_qty:
        print(f"The number of shares you have is not enough. You have {have_qty} shares but you tried to sell {qty} shares.")
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
            f"{tl_price}",
            f"{usd_price}"
        ])

    # 2) Update shares.csv (decrease quantity and remove the row if it reaches 0)
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = []
        for row in reader:
            if row['share_name'] == stock_name:
                new_qty = Decimal(row['quantity']) - qty
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
                share_price = ask_price(country_name, stock_name)
                if share_price is None:
                    print('Operation cancelled.')
                    router()
                    return
                while True:
                    try:
                        number_of_shares = Decimal(input("Enter number of shares: ").strip().replace(',', '.'))
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid number. Try again.')
                while True:
                    try:
                        transaction_fee = Decimal(input("Enter transaction fee: ").strip().replace(',', '.'))
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid fee. Try again.')
                while True:
                    try:
                        ex_raw = input("Enter exchange rate, if you want to get it automatically enter 0: ").strip().replace(',', '.')
                        exchange_rate = Decimal(ex_raw)
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid rate. Try again.')
                if exchange_rate == Decimal('0'):
                    exchange_rate = get_dollar()
                    if exchange_rate is None:
                        print("Failed to get the dollar value.")
                        return
                while True:
                    currency = input("Enter currency: (tl, usd): ").upper()
                    if currency in ('TL', 'USD'):
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
                share_price = ask_price(country_name, stock_name)
                if share_price is None:
                    print('Operation cancelled.')
                    router()
                    return
                while True:
                    try:
                        number_of_shares = Decimal(input("Enter number of shares: ").strip().replace(',', '.'))
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid number. Try again.')
                while True:
                    try:
                        transaction_fee = Decimal(input("Enter transaction fee: ").strip().replace(',', '.'))
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid fee. Try again.')
                while True:
                    try:
                        ex_raw = input("Enter exchange rate, if you want to get it automatically enter 0: ").strip().replace(',', '.')
                        exchange_rate = Decimal(ex_raw)
                        break
                    except (InvalidOperation, ValueError):
                        print('Invalid rate. Try again.')
                if exchange_rate == Decimal('0'):
                    exchange_rate = get_dollar()
                    if exchange_rate is None:
                        print("Failed to get the dollar value.")
                        return
                while True:
                    currency = input("Enter currency: (tl, usd): ").upper()
                    if currency in ('TL', 'USD'):
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


def show_inflation_rates():
    print('_' * 34)
    print(f"|{'Month':^10}|{'Year':^6}|{'Country':^7}|{'Rate':^6}|")
    with open('inflation.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            month = ""
            month_num = int(row['month'])
            months = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December"
            }
            month = months.get(month_num, f"Month {month_num}")
            print(f"|{month:^10}|{row['year']:^6}|{row['country']:^7}|{row['rate']:^6}|")
    print('¯' * 34)
    router()


def edit_inflation_rates():
    create_files()
    print()
    print('1. Add a new inflation rate')
    print('2. Edit an existing inflation rate')
    print('3. Delete an existing inflation rate')
    print('4. Show all inflation rates')
    print('0. Return to the previous page.')
    choice = input("Please enter the action you wish to perform from the options above: ")
    if choice == '1': # Add a new inflation rate
        try:
            month = int(input("Enter the month: (eg. 12 for December): "))
            year = int(input("Enter the year: (eg. 2025): "))
            country = input("Enter the country: (eg. TR): ").strip().upper()
            rate_input = input("Enter the rate: (eg. 1.5): ").strip().replace(',', '.')
            rate = Decimal(rate_input)
        except ValueError:
            print("Please enter a valid number.")
            edit_inflation_rates()
            return

        if country not in {'TR', 'US'}:
            print("Please enter a valid country.")
            edit_inflation_rates()
            return
        elif not (1 <= month <= 12):
            print("Please enter a valid month.")
            edit_inflation_rates()
            return
        elif not (2000 <= year <= 2100):
            print("Please enter a valid year.")
            edit_inflation_rates()
            return
        else:
            # Duplicate check
            exists = False
            with open('inflation.csv', mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['month'] == str(month) and row['year'] == str(year) and row['country'] == country:
                        exists = True
                        break
            if exists:
                print('A record for the same (month, year, country) already exists. Use edit option.')
                return
            with open('inflation.csv', mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([month, year, country, str(rate)])
            print('Inflation rate saved successfully.')

    elif choice == '2': # Edit an existing inflation rate
        rows = []
        with open('inflation.csv', mode='r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
                print(row)
            try:
                month = int(input("Enter the month you want to edit: (eg. 12 for December): "))
                year = int(input("Enter the year you want to edit: (eg. 2025): "))
                country = input("Enter the country you want to edit: (eg. TR): ").strip().upper()
                rate_input = input("Enter the new rate: (eg. 1.5): ").strip().replace(',', '.')
                rate = Decimal(rate_input)
            except ValueError:
                print("Please enter a valid number.")
                edit_inflation_rates()
                return

            if country not in {'TR', 'US'}:
                print("Please enter a valid country.")
                edit_inflation_rates()
                return
            elif month < 1 or month > 12:
                print("Please enter a valid month.")
                edit_inflation_rates()
                return
            elif year < 2000 or year > 2100:
                print("Please enter a valid year.")
                edit_inflation_rates()
                return
            else:
                with open('inflation.csv', mode='w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    found = False
                    for row in rows:
                        if row['month'] == str(month) and row['year'] == str(year) and row['country'] == country:
                            row['rate'] = str(rate)
                            found = True
                        writer.writerow(row)
                if found:
                    print('Inflation rate saved successfully.')
                else:
                    print('No matching record found to edit.')

    elif choice == '3': # Delete an existing inflation rate
        rows = []
        with open('inflation.csv', mode='r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                rows.append(row)
                print(row)
            try:
                month = int(input("Enter the month you want to delete: (eg. 12 for December): "))
                year = int(input("Enter the year you want to delete: (eg. 2025): "))
                country = input("Enter the country you want to delete: (eg. TR): ").strip().upper()
            except ValueError:
                print("Please enter a valid number.")
                edit_inflation_rates()
                return

            if country != 'TR' and country != 'US':
                print("Please enter a valid country.")
                edit_inflation_rates()
                return
            elif month < 1 or month > 12:
                print("Please enter a valid month.")
                edit_inflation_rates()
                return
            elif year < 2000 or year > 2100:
                print("Please enter a valid year.")
                edit_inflation_rates()
                return
            else:
                new_rows = []
                removed = 0
                for row in rows:
                    if row['month'] == str(month) and row['year'] == str(year) and row['country'] == country:
                        removed += 1
                        continue
                    new_rows.append(row)
                with open('inflation.csv', mode='w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(new_rows)
                if removed:
                    print('Inflation rate deleted successfully.')
                else:
                    print('No matching record found to delete.')

    elif choice == '4': # Show all inflation rates
        show_inflation_rates()

    elif choice == '0':
        pass
    else:
        print('Please enter a valid number.')
        edit_inflation_rates()
    router()


def parse_year_month(date_str: str) -> tuple[int, int]:
    parts = date_str.strip().split("-")
    return int(parts[0]), int(parts[1])


def next_year_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def iter_year_months(start_year: int, start_month: int, end_year: int, end_month: int):
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        year, month = next_year_month(year, month)


def load_inflation_rates_by_country(country: str) -> dict[tuple[int, int], Decimal]:
    rates: dict[tuple[int, int], Decimal] = {}
    with open('inflation.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['country'].strip().upper() != country:
                continue
            y = int(row['year'])
            m = int(row['month'])
            r = Decimal(str(row['rate']).replace(',', '.'))
            rates[(y, m)] = r
    return rates


def build_deflators(country: str, base_year: int, base_month: int, needed_months: list[tuple[int, int]]):
    rates = load_inflation_rates_by_country(country)
    if not rates:
        return None, {m for m in needed_months}

    min_needed = min(needed_months)
    max_needed = max(needed_months)

    # Ensure base is included
    all_months = list(iter_year_months(base_year, base_month, max_needed[0], max_needed[1]))

    # Check missing months (excluding base which can be treated as index=1)
    missing = set()
    for (y, m) in all_months:
        if (y, m) == (base_year, base_month):
            continue
        if (y, m) not in rates:
            missing.add((y, m))

    if missing:
        return None, missing

    # Build CPI index with base = 1.0
    index: dict[tuple[int, int], Decimal] = {}
    index[(base_year, base_month)] = Decimal('1')
    prev_y, prev_m = base_year, base_month
    for (y, m) in iter_year_months(base_year, base_month, max_needed[0], max_needed[1]):
        if (y, m) == (base_year, base_month):
            continue
        prev_index = index[(prev_y, prev_m)]
        monthly_rate = rates[(y, m)]  # percent per month
        growth = (Decimal('1') + (monthly_rate / Decimal('100')))
        index[(y, m)] = (prev_index * growth)
        prev_y, prev_m = y, m

    # Deflator D(t) = 1 / I(t)
    deflators = {ym: (Decimal('1') / idx) for ym, idx in index.items()}
    return deflators, None


def get_current_dollar_rate_interactive() -> Decimal | None:
    rate = get_dollar()
    if rate is None:
        try:
            manual = input("Failed to fetch USD/TRY. Enter rate manually (e.g., 41.50) or 0 to cancel: ").strip()
            if manual == '0':
                return None
            return Decimal(manual.replace(',', '.'))
        except Exception:
            return None
    return rate


def prompt_current_prices_for_shares(reference_country: str) -> tuple[list[dict] | None, Decimal | None]:
    rows = []
    with open('shares.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for share in reader:
            rows.append(share)

    if not rows:
        return [], None

    usdtry = None
    current_prices = []
    for share in rows:
        share_name = share['share_name']
        native_country = share['country_name'].strip().upper()
        qty = Decimal(str(share['quantity']))
        price = ask_price(native_country, share_name)
        if price is None:
            return None, None
        current_prices.append({
            'share_name': share_name,
            'native_country': native_country,
            'quantity': qty,
            'native_price': price
        })

    if reference_country == 'TR':
        if any(p['native_country'] == 'US' for p in current_prices):
            usdtry = get_current_dollar_rate_interactive()
            if usdtry is None:
                return None, None
    else:
        if any(p['native_country'] == 'TR' for p in current_prices):
            usdtry = get_current_dollar_rate_interactive()
            if usdtry is None:
                return None, None

    for p in current_prices:
        if reference_country == 'TR':
            if p['native_country'] == 'US':
                p['price_in_ref'] = round_money(p['native_price'] * usdtry)
            else:
                p['price_in_ref'] = round_money(p['native_price'])
        else:
            if p['native_country'] == 'TR':
                p['price_in_ref'] = round_money(p['native_price'] / usdtry)
            else:
                p['price_in_ref'] = round_money(p['native_price'])
    return current_prices, usdtry


def calculate_reel_profit():
    # 1) Ask reference inflation country
    while True:
        ref_country = input("Reference inflation (TR or US): ").strip().upper()
        if ref_country in {'TR', 'US'}:
            break
        print("Please enter TR or US.")

    ref_ccy = 'TL' if ref_country == 'TR' else 'USD'

    # 2) Read operations and determine base month
    operations = []
    with open('operations.csv', mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            operations.append(row)

    if not operations:
        print('There has been no transaction yet. First, you need to make a transaction.')
        router()
        return

    tx_months = [] # type: list[tuple[int, int]]: year, month
    for op in operations:
        y, m = parse_year_month(op['date'])
        tx_months.append((y, m))
    
    base_year, base_month = min(tx_months)

    # 3) Needed months include all tx months and current month
    today = datetime.today()
    curr_year, curr_month = today.year, today.month
    needed = sorted(set(tx_months + [(curr_year, curr_month)]))

    # 4) Build deflators
    deflators, missing = build_deflators(ref_country, base_year, base_month, needed)
    if missing is not None:
        missing_str = ", ".join([f"{y}-{m:02d}" for (y, m) in sorted(missing)])
        print(f"Missing inflation data for: {missing_str}. Please add rates and try again.")
        router()
        return

    # Convenience to get deflator for a month (base month uses 1)
    def get_deflator(y: int, m: int) -> Decimal:
        if (y, m) == (base_year, base_month):
            return Decimal('1')
        return deflators[(y, m)]

    # 5) Aggregate deflated cash flows in reference currency
    total_real_cashflows = Decimal('0')
    invested_real_abs = Decimal('0')
    for op in operations:
        y, m = parse_year_month(op['date'])
        amount_ref = Decimal(op['tl_price']) if ref_ccy == 'TL' else Decimal(op['usd_price'])
        if op['transaction_type'].strip().lower() == 'purchase':
            amount_ref = -amount_ref
        elif op['transaction_type'].strip().lower() == 'sale':
            pass
        else:
            # Unknown type, skip
            continue
        deflator = get_deflator(y, m)
        real_amount = round_money(amount_ref * deflator)
        total_real_cashflows += real_amount
        if real_amount < 0:
            invested_real_abs += (-real_amount)

        # Include transaction fee as an additional negative cash flow
        try:
            fee_native = Decimal(str(op['transaction_fee']).strip())
        except Exception:
            fee_native = Decimal('0')
        if fee_native != 0:
            op_ccy = op['currency'].strip().upper()
            try:
                rate = Decimal(str(op['exchange_rate']).strip())
            except Exception:
                rate = None

            # Convert fee to reference currency
            if op_ccy == ref_ccy:
                fee_ref = fee_native
            elif op_ccy == 'USD' and ref_ccy == 'TL' and rate is not None and rate != 0:
                fee_ref = round_money(fee_native * rate)
            elif op_ccy == 'TL' and ref_ccy == 'USD' and rate is not None and rate != 0:
                fee_ref = round_money(fee_native / rate)
            else:
                # Fallback: if rate missing, skip fee conversion for safety
                fee_ref = None

            if fee_ref is not None:
                fee_real = round_money((-fee_ref) * deflator)
                total_real_cashflows += fee_real
                if fee_real < 0:
                    invested_real_abs += (-fee_real)

    # 6) Current portfolio nominal value in reference currency
    current_prices, usdtry = prompt_current_prices_for_shares(ref_country)
    if current_prices is None:
        print('Operation cancelled.')
        router()
        return

    portfolio_nominal_ref = Decimal('0')
    for p in current_prices:
        portfolio_nominal_ref += round_money(p['price_in_ref'] * p['quantity'])

    # 7) Deflate current value to base
    curr_deflator = get_deflator(curr_year, curr_month)
    portfolio_real = round_money(portfolio_nominal_ref * curr_deflator)

    # 8) Real gain and ROI
    real_gain = round_money(portfolio_real + total_real_cashflows)
    if invested_real_abs > 0:
        real_roi = (real_gain / invested_real_abs) * Decimal('100')
    else:
        real_roi = None

    # Inflation over the period (index at current)
    curr_index = (Decimal('1') / curr_deflator)
    inflation_over_period_pct = (curr_index - Decimal('1')) * Decimal('100')

    # 9) Report
    print('_' * 64)
    print(f"Reference: {ref_country} / {ref_ccy}")
    print(f"Base: {base_year}-{base_month:02d}  Current: {curr_year}-{curr_month:02d}")
    print(f"Period CPI change: {inflation_over_period_pct:.2f}%")
    print('-' * 64)
    print(f"Real cash flows sum: {total_real_cashflows:.4f} {ref_ccy}")
    print(f"Current portfolio (nominal): {portfolio_nominal_ref:.4f} {ref_ccy}")
    print(f"Current portfolio (real): {portfolio_real:.4f} {ref_ccy}")
    print(f"Real net gain: {real_gain:.4f} {ref_ccy}")
    if real_roi is not None:
        print(f"Real ROI: {real_roi:.2f}%  (on invested real capital {invested_real_abs:.4f} {ref_ccy})")
    else:
        print("Real ROI: N/A (no invested capital detected)")
    print('¯' * 64)
    router()
 
    

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
            print("Please enter a valid number. (0-5)")
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
