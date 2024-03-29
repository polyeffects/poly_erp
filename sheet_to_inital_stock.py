import os, csv
import time
import subprocess

from inventree.stock import StockItem, StockLocation
from inventree.api import InvenTreeAPI
from inventree.part import Part

from inventree_parts_login import parts, reverse_parts, api
luke_pk = StockLocation.list(api, name="luke")[0].pk
leia_pk = StockLocation.list(api, name="leia")[0].pk
pks = {"luke": luke_pk, "leia": leia_pk}


feeder_csv = csv.DictReader(open("/home/loki/shared/luke/audio_board_feeders.csv"), dialect="excel-tab")
for f in feeder_csv:
    print("processing", f)
    sl = StockLocation.list(api, parent=pks[f["machine"]], name="slot "+f["Slot"]+"  lane "+f["Track"])[0]
    part = Part.list(api, IPN=f["Component"])[0]
    stock_id = StockItem.create(api, { 'part': part.pk, 'quantity': 100, 'notes': 'initial on feeders', 'location': sl.pk, 'status':10 }) # 10 is ok
