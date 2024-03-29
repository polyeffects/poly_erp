import product_labels

from inventree.stock import StockItem, StockLocation
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.build import Build
from inventree.company import Company
from inventree.order import SalesOrder, SalesOrderLineItem

from inventree_parts_login import parts, reverse_parts, api

# [product_labels.print_label(product_labels.label_template("beebo", "blue")) for i in range(10)]
barcode_actions = { "print_product":  product_labels.gen_and_print_label}

# start shipment, units scanned after this are allocated to this shipment
# add unit to current shipment
def add_unit_to_current_shipment(part_pk, unit_serial):
    # get stock item, find part
    stock_item = StockItem.list(api, part=part_pk, serial=unit_serial)[0]
    unit_pk = stock_item["pk"]
    # get shipments
    so_s = SalesOrder.list(api, status=15) # status 10 Pending
    shipments = [s.getShipments() for s in so_s if s.getShipments() != []][0]
    shipment = [s for s in shipments if s["shipment_date"] is None][0] # pending shipments
    so = shipment.getOrder()
    part_lis = [(li["part"], li["pk"]) for li in so.getLineItems()]
    # find the line item
    for part, li_pk in part_lis:
        if part == part_pk:
            items = [{
               "line_item": li_pk,
               "quantity": 1,
               "stock_item": unit_pk
            }]
            shipment.allocateItems(items)
            return

# find which line item this unit is, add this unit to shipment
# finish shipment
