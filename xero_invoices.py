import os
import datetime
import subprocess
import requests
import json
from xero import Xero
from xero.auth import OAuth2PKCECredentials, OAuth2Credentials
from xero.constants import XeroScopes

from inventree.stock import StockItem, StockLocation
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.build import Build
from inventree.company import Company
from inventree.order import SalesOrder, SalesOrderLineItem

from inventree_parts_login import parts, reverse_parts, api, client_id, client_secret

token = json.load(open("/git_repos/poly_erp/token.json"))

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
credentials = OAuth2Credentials(client_id,
        token=token,
        client_secret=client_secret)

if credentials.expired():
    token = credentials.refresh()
    json.dump(token, open("/git_repos/poly_erp/token.json", "w"))

# credentials.logon()
credentials.set_default_tenant()
xero = Xero(credentials)


exchange_rates = {}


item_display_names = {"beebo_blue": "Beebo (blue)",
"beebo_pink": "Beebo (pink)",
"beebo_silver": "Beebo (silver)",
"hector_black": "Hector (black)",
"hector_seafoam": "Hector (seafoam)",
"flat_v": "Josh Smith Flat V",
        }

def get_exchange_rates():
    url = "https://api.frankfurter.app/latest?from=USD"
    response = requests.get(url)
    data = response.json()
    global exchange_rates
    exchange_rates = data['rates']

get_exchange_rates()

def generate_invoice(currency="USD", contact_name="Vintage king", po="", line_items=[]):
    print("generating invoice, contact ", contact_name, "currency", currency)
    contact = xero.contacts.filter(raw='Name.ToLower().Contains("'+contact_name.lower()+'")')
    themes = {"USD": 'cdf92f25-af1e-4869-aee1-e3cf8faafe6f',
            "GBP":'f313bc71-ca66-4bb4-8c21-e6bbbbb61efd',
            "EUR": 'd4b84e69-a863-49c7-a69f-c1b91b04b4d9',
            "CAD": '8d93b858-f565-4712-9541-205a059f6def',
            "AUD": '92c7996f-6aa0-4a65-a89b-73d1520df891'
            }
    current_theme = themes[currency]
    for l_i in line_items:
        l_i.update({'AccountCode': '200',  'TaxType': "EXEMPTEXPORT", 'Tracking' : []})
    print(line_items)
    xero.invoices.put({
      'BrandingThemeID': current_theme,
      'Contact': contact,
      'CurrencyCode': currency,
      'Date': datetime.datetime.now(),
      'DateString': datetime.date.today(),
      'DueDate': datetime.datetime.now(),
      'DueDateString': datetime.date.today(),
      'HasAttachments': False,
      'LineAmountTypes': 'Exclusive',
      'LineItems': line_items,
      'Reference': po,
      'Status': 'DRAFT', #'AUTHORISED',
      'Type': 'ACCREC'})


def convert_currency(amount, input_cur, output_cur):
    if input_cur != output_cur:
        if input_cur  == "USD":
            amount = amount * float(exchange_rates[output_cur])
        elif output_cur  == "USD":
            # convert currency to USD
            amount = amount / float(exchange_rates[input_cur])
        else:
            # neither is USD
            # convert line item to USD
            amount = amount / float(exchange_rates[input_cur])
            # then to invoice cur
            amount = amount * float(exchange_rates[output_cur])
    return amount


# find inventree sales orders that have been issued where description doesn't contain invoiced
so_s = SalesOrder.list(api, metadata={}, status=20) # need to filter this to ones that haven't been invoiced, check metadata
for so in so_s:
    if not (so.getMetadata().get("invoiced")) and so["customer"] != 10: # ignore directs
        # now find details and send invoice, we need to know the customer, line items and freight (extra line items)
        # l_line_items = [{ 'Description': 'Beebo (blue)',
        #     'Quantity': 2.0,
        #     'UnitAmount': 449.0 },
        #     { 'Description': 'Hector (black)',
        #         'Quantity': 4.0,
        #         'UnitAmount': 599.0 },
        #     { 'Description': 'Josh Smith Flat V',
        #         'Quantity': 4.0,
        #         'UnitAmount': 399.0 }
        #     ]

        company = Company(api, pk=so["customer"])
        cur = company["currency"]

        l_line_items = []
        lis = so.getLineItems()
        for li in lis:

            # if change is in different currency than invoice currency convert it 
            amount = float(li["sale_price"])
            li_currency = li["sale_price_currency"]
            print(f"amount {amount} company currency {cur} li_currency {li_currency}")
            amount = convert_currency(amount, li_currency, cur)

            l_line_items.append({ 'Description': reverse_parts[li["part"]],
                'Quantity': li["quantity"],
                'UnitAmount': li["sale_price"] })

        # freight, any other costs like payment fees
        lis = so.getExtraLineItems()
        for li in lis:
            # if change is in different currency than invoice currency convert it 
            amount = float(li["price"])
            li_currency = li["price_currency"]
            amount = convert_currency(amount, li_currency, cur)

            tracking_number = ""
            try:
                tracking_number = " FedEx Tracking: " + so.getShipments()[0]["tracking_number"]
            except:
                pass

            l_line_items.append({ 'Description': li["reference"] +  tracking_number,
                'Quantity': li["quantity"],
                'UnitAmount': amount })


        generate_invoice(currency=cur, contact_name=company["name"], po=so["customer_reference"], line_items=l_line_items)
        so.setMetadata({"invoiced": True})
        description = so["description"]
        so["description"] = description + " : invoiced"
        so.save()

