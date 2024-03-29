from inventree.order import SalesOrder, SalesOrderLineItem

from numpy import busday_offset
import date


# so = SalesOrder.create(api, {
#     "target_date": np.busday_offset(date.today(), 1, roll='forward')
#     "description": "string",
#     "customer": 0,
# }

parts = {"Blue Beebo":195, "Flat V": 199, "Black Hector": 197, 'Seafoam Hector': 198,
        "Verbs": 249, "Pink Beebo": 196}
reverse_parts = {v:k for k, v in parts.items()}

for po in pos:
    print(po)
    c = Company.list(api, name=po["Dealer"])[0]
    sales_order = c.createSalesOrder(
        target_date=str(np.busday_offset(date.today(), float(-20), roll='forward')),
        description=po["Current Orders"],
        customer_reference=po["PO"]
            )
    for part, pk in parts.items():
        if po[part] != '' and int(po[part]) > 0:
            line = sales_order.addLineItem(part=pk, quantity=int(po[part]))
    if po["Tracking"] != '':
        freight_cost = 0
        if po["freight cost"] == "":
            freight_cost = 0
        else:
            frieght_cost = float(po["freight cost"])
        extraline = sales_order.addExtraLineItem(
                    quantity=1,
                    reference=f"Freight: tracking {po['Tracking']}",
                    notes=f"shipped date: {po['Shipped Date']}",
                    price=freight_cost, price_currency="AUD"
                )

def csv_to_inv():
    import csv
    k = ['order_date', 'dealer', 'po', 'beebo_pink', 'beebo_blue', 'hector_black', 'hector_seafoam', 'flat_v', 'total', 'pink_tops', 'notes', 'shipped_date', 'tracking', 'freight_cost']
    inv_csv = csv.DictReader(open("june_15_inv.csv"), dialect="excel-tab", fieldnames=k)

