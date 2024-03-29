# look for board started, board completed,
# component rejected

import os
import time
import subprocess , threading
import paho.mqtt.client as mqtt

from inventree.stock import StockItem, StockLocation
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.build import Build

import control_conveyor

from inventree_parts_login import parts, reverse_parts, api

try:
    num_done_units = json.load(open("/git_repos/poly_erp/num_done_units.json"))
except:
    num_done_units = {"luke":{}, "leia": {}}


luke_pk = StockLocation.list(api, name="luke")[0].pk
leia_pk = StockLocation.list(api, name="leia")[0].pk
pks = {"luke": luke_pk, "leia": leia_pk}
pnp_name_to_part = {"josh1_audio_v9_2": "fv_audio_v9.2_assembled", "josh_touchpad_v5":"fv1_touchpad_v5_assembled", "josh_led_v5_panel": "fv1ledr4_assembled",
        "verbs_v1_1":"verbs_main_board"}
conveyor_count = 0
builds = {}
num_boards = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(r"pnp/luke", 2)
    client.subscribe(r"pnp/leia", 2)
    client.subscribe(r"pos1/1/Counter", 0)

# The callback for when a PUBLISH message is received from the server.
prev_message = ("", "")
def on_message(client, userdata, msg):
    global conveyor_count
    payload = str(msg.payload)#.decode("utf-16be")
    if msg.topic == "pos1/1/Counter":
        i_payload = int(msg.payload)
        if conveyor_count != i_payload:
            print("topic:", msg.topic, i_payload)
    else:
        print("topic:", msg.topic, payload)
        # pass
    machine_name = msg.topic.split("/")[1]
    # if "Component rejected" in payload:
    if "Event - 30161" in payload:
        # find the component id
        s = payload.find("Component: ")+len("Component: ")
        e = payload.find(". Reference ID:")
        component = payload[s:e]
        print("component rejected:", component, "on", machine_name)
        # decrement amount of component in inventree
        items = StockItem.list(api, IPN=component)
        # find which stock item is on the machine
        for stock_item in items:
            location_pk = stock_item.location
            sl = StockLocation(api, pk=location_pk)
            if sl.parent == pks[machine_name]:
                # this stock is on a feeder
                stock_item.removeStock(1)
                print("1 unit removed from", stock_item.pk, component)
    elif "Event - 30044" in payload: # started
        s = payload.find("Product: ")+len("Product: ")
        e = payload.find(".upf.  Barcode")
        board = payload[s:e]
        print("board started:", board, "on", machine_name)
        num_board = num_boards + 1
        # p = Part.list(api, IPN=pnp_name_to_part[board])[0]
        # if we haven't got a build order for today, start one
        # if board not in builds:
        #     builds[board] = Build.create(api, {'part':p.pk, 'title': "pnp build" + time.strftime("%d-%m-%Y"),
        #         "quantity":4, "reference": board+time.strftime("%d-%m-%Y")+"_"+str(num_boards) })

        # # start build output if we're luke
        # if machine_name == "luke":
        #     # auto allocate parts

    elif "Event - 30037" in payload: # complete
        s = payload.find("Product: ")+len("Product: ")
        e = payload.find(".upf.  Barcode")
        board = payload[s:e]
        print("board complete:", board, "on", machine_name)
        # c_n_d = num_done_units[machine_name].get(board, 0)
        # num_done_units[machine_name][board] =  c_n_d + 1
        # with open("/git_repos/poly_erp/num_done_units.json", "w") as f:
        #     json.dump(num_done_units, f)
        # print("num ", board, "done", c_n_d + 1)
        # complete build output if we're leia and it's something that needs leia
        # complete build output if we're leia and it's something that needs touch board that only needs luke
        p = Part.list(api, IPN=pnp_name_to_part[board])[0]
        # spawn_create_build_order(p.pk, 327, 4)
        create_build_order(p.pk, 327, 4)
    elif "Event - 30157" in payload: # feeder mounted, for easier debugging
        s = payload.find("Feeder mounted. ")+len("Feeder mounted. ")
        e = payload.find(r".</TD>")
        feeder_slot = payload[s:e]
        print("feeder loaded:", feeder_slot, "on", machine_name)
    elif msg.topic == "pos1/1/Counter":
        #from the posid blue thing
        # if the count has changed, toggle conveyor, it'll wait if it needs to
        payload = int(msg.payload)
        # print("before calling toggling conveyor", payload, conveyor_count)
        if conveyor_count != payload:
            # print("calling toggling conveyor")
            conveyor_count = payload
            x = threading.Thread(target=control_conveyor.toggle_conveyor, daemon=True)
            x.start()




# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
if __name__ == '__main__':
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("localhost", 1883, 60)
    client.loop_forever()
    # client.loop_start()
    # client.loop_stop()


    # "batch": "string",
    # "completion_date": "2019-08-24",
    # "destination": 0,
    # "parent": 0,
    # "sales_order": 0,
    # "target_date": "2019-08-24",
    # "take_from": 0,
    # "notes": "string",
    # "link": "http://example.com",
    # "issued_by": 0,
    # "responsible": 0,
    # "priority": 2147483647
# }

def spawn_create_build_order(part_id, output_location=327, num_units=1):
    x = threading.Thread(target=create_build_order, args=(part_id, output_location, num_units), daemon=True)
    x.start()

def create_build_order(part_id=195, output_location=327, num_units=1):
    data = {"search":None, "offset": 0, "limit": 1, "part_detail": True}
    response = api.get(f'{api.api_url}build/', data=data)[0]
    ref_pk = response["pk"]
    ref = "BO-{ref:04d}".format(ref=ref_pk+1)
    data = {
        "title": f"build {part_id} from pnp",
        "part": part_id,
        "reference": ref,
        "quantity": num_units,
        }
    response = api.post(f'{api.api_url}build/', data=data)
    build_pk = response["pk"]
    data = {
        "exclude_location": 291, # benches
        "interchangeable": True,
        "substitutes": True,
    }
    response = api.post(f'{api.api_url}build/{build_pk}/auto-allocate/', data=data)
    data = {
        "quantity": num_units,
    }
    p = Part(api, part_id)
    if p["trackable"]: # if it's a serialised one, we need serials, should check this...
        data["serial_numbers"] = f"~+{num_units}"

    response = api.post(f'{api.api_url}build/{build_pk}/create-output/', data=data)
    stock_items = StockItem.list(api, build=build_pk)
    build_outputs = [{"output":a["pk"]} for a in stock_items]
    data = {
        "outputs":build_outputs,
        "location": output_location,
        "status": 50,
    }
    response = api.post(f'{api.api_url}build/{build_pk}/complete/', data=data)
    data = {
        "accept_overallocated": "reject",
        "accept_unallocated": False,
        "accept_incomplete": False
    }
    response = api.post(f'{api.api_url}build/{build_pk}/finish/', data=data)

