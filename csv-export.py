from __future__ import print_function
from Robinhood import Robinhood
from login_data import collect_login_data
from profit_extractor import profit_extractor
import getpass
import collections
import argparse
import ast
from dotenv import load_dotenv, find_dotenv
import os
import csv

logged_in = False

parser = argparse.ArgumentParser(
    description='Export Robinhood trades to a CSV file')
parser.add_argument(
    '--debug', action='store_true', help='store raw JSON output to debug.json')
parser.add_argument(
    '--username', default='', help='your Robinhood username')
parser.add_argument(
    '--password', default='', help='your Robinhood password')
parser.add_argument(
    '--mfa_code', help='your Robinhood mfa_code')
parser.add_argument(
    '--device_token', help='your device token')
parser.add_argument(
    '--auth_token', help='your oauth2 token')
parser.add_argument(
    '--profit', action='store_true', help='calculate profit for each sale')
parser.add_argument(
    '--dividends', action='store_true', help='export dividend payments')
parser.add_argument(
    '--crypto', action='store_true', help='export crypto')
args = parser.parse_args()
username = args.username
password = args.password
mfa_code = args.mfa_code
device_token = args.device_token
auth_token = args.auth_token

load_dotenv(find_dotenv())

robinhood = Robinhood()

# login to Robinhood
if args.auth_token:
    robinhood.use_token(args.auth_token)
    logged_in = True
else:
    logged_in = collect_login_data(robinhood_obj=robinhood, username=username, password=password, device_token=device_token, mfa_code=mfa_code)

print("Pulling trades. Please wait...")

fields = collections.defaultdict(dict)
trade_count = 0
queued_count = 0

#holds instrument['symbols'] to reduce API ovehead {instrument_url:symbol}
cached_instruments = {}

# fetch order history and related metadata from the Robinhood API
orders = robinhood.get_endpoint('orders')

# load a debug file
# raw_json = open('debug.txt','rU').read()
# orders = ast.literal_eval(raw_json)

# store debug
if args.debug:
    # save the CSV
    try:
        with open("debug.txt", "w+") as outfile:
            outfile.write(str(orders))
            print("Debug infomation written to debug.txt")
    except IOError:
        print('Oops.  Unable to write file to debug.txt')

# do/while for pagination
paginated = True
page = 0
while paginated:
    for i, order in enumerate(orders['results']):
        executions = order['executions']

        symbol = cached_instruments.get(order['instrument'], False)
        if not symbol:
            symbol = robinhood.get_custom_endpoint(order['instrument'])['symbol']
            cached_instruments[order['instrument']] = symbol

        fields[i + (page * 100)]['symbol'] = symbol

        for key, value in enumerate(order):
            if value != "executions":
                fields[i + (page * 100)][value] = order[value]

        fields[i + (page * 100)]['num_of_executions'] = len(executions)
        fields[i + (page * 100)]['execution_state'] = order['state']

        if len(executions) > 0:
            trade_count += 1
            fields[i + (page * 100)]['execution_state'] = ("completed", "partially filled")[order['cumulative_quantity'] < order['quantity']]
            fields[i + (page * 100)]['first_execution_at'] = executions[0]['timestamp']
            fields[i + (page * 100)]['settlement_date'] = executions[0]['settlement_date']
        elif order['state'] == "queued":
            queued_count += 1
    # paginate
    if orders['next'] is not None:
        page = page + 1
        orders = robinhood.get_custom_endpoint(str(orders['next']))
    else:
        paginated = False

# for i in fields:
#   print fields[i]
#   print "-------"

# check we have trade data to export
if trade_count > 0 or queued_count > 0:
    print("%d queued trade%s and %d executed trade%s found in your account." %
          (queued_count, "s" [queued_count == 1:], trade_count,
           "s" [trade_count == 1:]))
    # print str(queued_count) + " queded trade(s) and " + str(trade_count) + " executed trade(s) found in your account."
else:
    print("No trade history found in your account.")
    quit()

# CSV headers
keys = fields[0].keys()
keys = sorted(keys)

# choose a filename to save to
print("Choose a filename or press enter to save to `robinhood.csv`:")
try:
    input = raw_input
except NameError:
    pass
filename = input().strip()
if filename == '':
    filename = "robinhood.csv"

try:
    with open(filename, "w+") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(keys)
        writer.writerows(([row.get(key) for key in keys] for row in fields.values()))
except IOError:
    print("Oops.  Unable to write file to ", filename)


if args.dividends:
    fields=collections.defaultdict(dict)
    dividend_count = 0
    queued_dividends = 0

    # fetch order history and related metadata from the Robinhood API
    dividends = robinhood.get_endpoint('dividends')


    paginated = True
    page = 0
    while paginated:
        for i, dividend in enumerate(dividends['results']):
            symbol = cached_instruments.get(dividend['instrument'], False)
            if not symbol:
                symbol = robinhood.get_custom_endpoint(dividend['instrument'])['symbol']
                cached_instruments[dividend['instrument']] = symbol

            fields[i + (page * 100)]['symbol'] = symbol

            for key, value in enumerate(dividend):
                if value != "executions":
                    fields[i + (page * 100)][value] = dividend[value]

            fields[i + (page * 100)]['execution_state'] = order['state']

            if dividend['state'] == "pending":
                queued_dividends += 1
            elif dividend['state'] == "paid":
                dividend_count += 1
        # paginate
        if dividends['next'] is not None:
            page = page + 1
            orders = robinhood.get_custom_endpoint(str(dividends['next']))
        else:
            paginated = False

    # for i in fields:
    #   print fields[i]
    #   print "-------"

    # check we have trade data to export
    if dividend_count > 0 or queued_dividends > 0:
        print("%d queued dividend%s and %d executed dividend%s found in your account." %
              (queued_dividends, "s" [queued_count == 1:], dividend_count,
               "s" [trade_count == 1:]))
        # print str(queued_count) + " queded trade(s) and " + str(trade_count) + " executed trade(s) found in your account."
    else:
        print("No dividend history found in your account.")
        quit()

    # CSV headers

    keys = fields[0].keys()
    keys = sorted(keys)

    # choose a filename to save to
    print("Choose a filename or press enter to save to `dividends.csv`:")
    try:
        input = raw_input
    except NameError:
        pass
    filename = input().strip()
    if filename == '':
        filename = "dividends.csv"

    # save the CSV
    try:
        with open(filename, "w+") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(keys)
            writer.writerows(([row.get(key) for key in keys] for row in fields.values()))
    except IOError:
        print("Oops.  Unable to write file to ", filename)

if args.crypto:
    paginated = True
    results = []
    currency_pair_ids = set()
    is_first = True
    next_url = None
    while is_first or next_url:
        if is_first:
            response = robinhood.get_endpoint('crypto_orders')
        else:
            response = robinhood.get_custom_endpoint(next_url)
        is_first = False
        next_url = response['next']
        results += response['results']
        currency_pair_ids.update((order["currency_pair_id"] for order in results))

    # dict from currency_pair_id to dict e.g. {"symbol": "BTC-USD", "asset_currency": {"code": "BTC", …}, …}
    cached_currency_pairs = {}
    is_first = True
    next_url = None
    while len(currency_pair_ids) > 0 and (is_first or next_url):
        if is_first:
            response = robinhood.get_currency_pairs(currency_pair_ids)
        else:
            response = robinhood.get_custom_endpoint(next_url)
        is_first = False
        next_url = response['next']
        for result in response['results']:
            cached_currency_pairs[result['id']] = result

    for result in results:
        currency_pair = cached_currency_pairs[result['currency_pair_id']]
        result['currency_pair_symbol'] = currency_pair['symbol']
        result['asset_currency_code'] = currency_pair['asset_currency']['code']

    # CSV headers
    keys = sorted(list(set(key for order in results for key in order.keys())))

    # choose a filename to save to
    print("Choose a filename or press enter to save to `crypto.csv`:")
    try:
        input = raw_input
    except NameError:
        pass
    filename = input().strip()
    if filename == '':
        filename = "crypto.csv"

    # save the CSV
    try:
        with open(filename, "w+") as outfile:
            writer = csv.writer(outfile)
            writer.writerow(keys)
            writer.writerows(([row.get(key) for key in keys] for row in results))
    except IOError:
        print("Oops.  Unable to write file to ", filename)

if args.profit:
    profit_csv = profit_extractor(csv, filename)
