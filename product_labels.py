import socket
import template_images
import json
import requests

from inventree.stock import StockItem, StockLocation
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.build import Build
from inventree.company import Company
from inventree.order import SalesOrder, SalesOrderLineItem

from inventree_parts_login import parts, reverse_parts, api

try:
    serials = json.load(open("/git_repos/poly_erp/serials.json"))
except:
    serials = {"beebo": 2938, "flat_v": 308, "hector": 758, 'verbs': 1}

def print_label(raw_zpl):

    # Get settings
    zpl_host = "192.168.20.14"

    try:
        zpl_port = int(9100)
    except:
        zpl_port = 9100
        print("ZPL: WARNING: PORT config option is invalid; defaulting to 9100")

    try:
        zpl_timeout = int(15)
    except:
        zpl_timeout = 15
        print("ZPL: WARNING: TIMEOUT config option is invalid; defaulting to 15")

    # templ_path = self.get_setting('TEMPLATE_PATH')

    # object_to_print = kwargs['label_instance'].object_to_print

    # if kwargs['label_instance'].SUBDIR == 'part':
    #     tpart = object_to_print
    # elif kwargs['label_instance'].SUBDIR == 'stockitem':
    #     tpart = object_to_print.part
    # else:
    #     print(f"!! Unsupported item type: {object_to_print.SUBDIR}")
    #     return

    # try:
    #     with open(templ_path) as f:
    #         template = Template(f.read())
    # except Exception as e:
    #     print(f"ZPL: ERROR: failed to read template from file: {templ_path}")
    #     raise(e)

    # fields = {
    #     'name': tpart.name,
    #     'description': tpart.description,
    #     'ipn': tpart.IPN,
    #     'pk': tpart.pk,
    #     'params': tpart.parameters_map(),
    #     'category': tpart.category.name,
    #     'category_path': tpart.category.pathstring
    # }

    # # Give template access to the full part object + preprocessed fields
    # raw_zpl = template.render(part=tpart, **fields).encode('utf-8')

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(zpl_timeout)
        sock.connect((zpl_host, zpl_port))
        sock.send(raw_zpl)
    except Exception as e:
        print(f"ZPL: ERROR: Failed to connect to host {zpl_host}:{zpl_port}")
        raise(e)

    sock.close()
    print("ZPL: Spooled label to printer {zpl_host} successfully")
    json.dump(serials, open("/git_repos/poly_erp/serials.json", "w"))

def create_build_order(part_name="Blue Beebo", serial_num=0, part_id=195, output_location=331, num_units=1):
    data = {"search":None, "offset": 0, "limit": 1, "part_detail": True}
    response = api.get(f'{api.api_url}build/', data=data)[0]
    ref_pk = response["pk"]
    ref = "BO-{ref:04d}".format(ref=ref_pk+1)
    data = {
        "title": f"build {part_name} from label",
        "part": part_id,
        "reference": ref,
        "quantity": num_units,
        }
    response = api.post(f'{api.api_url}build/', data=data)
    build_pk = response["pk"]
    data = {
        # "exclude_location": 0, # benches
        "interchangeable": True,
        "substitutes": True,
    }
    response = api.post(f'{api.api_url}build/{build_pk}/auto-allocate/', data=data)
    data = {
        "quantity": num_units,
        "serial_numbers": serial_num,
    }
    response = api.post(f'{api.api_url}build/{build_pk}/create-output/', data=data)
    stock_items = StockItem.list(api, build=build_pk)
    build_outputs = [{"output":a["pk"]} for a in stock_items]
    if part_name == "Verbs":
        # need to install tracked parts
        main_board = StockItem.list(api, IPN="verbs_main_board", status=10, installed=False)[0]["pk"]
        get_data = {'build': build_pk, 'bom_item': 220, 'search': None, 'offset': 0, 'limit': 1}
        response = api.get(f'{api.api_url}build/line/', params=get_data)
        build_line = response["results"][0]["pk"]
        data = {"items":[{"build_line":build_line, "stock_item":main_board,"quantity":"1","output":stock_items[0]["pk"]}]}
        response = api.post(f'{api.api_url}build/{build_pk}/allocate/', data=data)
        # and install
        stock_item_pk = stock_items[0]["pk"]
        data = {'stock_item': main_board}
        response = api.post(f'{api.api_url}stock/{stock_item_pk}/install/', data=data)

    data = {
        "outputs":build_outputs,
        "location": output_location,
        "status": 10,
    }
    response = api.post(f'{api.api_url}build/{build_pk}/complete/', data=data)
    data = {
        "accept_overallocated": "reject",
        "accept_unallocated": False,
        "accept_incomplete": False
    }
    # if "Hector" in part_name:
    #     data["accept_unallocated"] = True
    response = api.post(f'{api.api_url}build/{build_pk}/finish/', data=data)


def label_template(unit, colour, s_n = None):
    f = open("label_template.zpl")
    # if s_n is not none were reprinting
    is_reprint = False
    if s_n is None:
        s_n = serials[unit] + 1
        serials[unit] = s_n
        json.dump(serials, open("/git_repos/poly_erp/serials.json", "w"))
    else:
        is_reprint = True
    a = f.read()

    name_map = {"beebo_blue": "Blue Beebo", "beebo_silver": "Silver Beebo", "beebo_pink" : "Pink Beebo",
            "hector_seafoam": "Seafoam Hector", "hector_black": "Black Hector",
            "flat_v_silver": "Flat V", 'verbs_mint':"Verbs"}

    part_name = name_map[unit+"_"+colour]
    images = {"beebo": template_images.beebo_image, "hector": template_images.hector_image, "flat_v": template_images.flat_v_image, 'verbs':template_images.verbs_image}
    eans = {"beebo_blue": "0721782396210", "beebo_silver": "0721782396203", "beebo_pink" : "0721782396203", "hector_seafoam": "0721782396227", "hector_black": "0721782396227",
            "flat_v_silver": "0721782396234", 'verbs_mint':"0780627449047"}

    filled_t = a.format(data_matrix="PA:"+str(parts[part_name])+":"+str(s_n), colour=colour.upper(), serial_number=str(s_n), ean=eans[unit+"_"+colour], image=images[unit])
    # print(filled_t)
    # create build order, add output with serial number, complete build order
    if not is_reprint:
        create_build_order(part_name=part_name, serial_num=s_n, part_id=parts[part_name], output_location=331, num_units=1)
    return bytes(filled_t, "utf8")

def print_action_label(display_name, action_data):
    f = open("action_label_template.zpl")
    a = f.read()
    filled_t = a.format(action_data=action_data, display_name=display_name)
    # print(filled_t)
    print_label(bytes(filled_t, "utf8"))


def gen_and_print_label(action_data):
    # action data is from the scanned label
    if "colour" not in action_data or "unit" not in action_data:
        return
    l = label_template(action_data["unit"], action_data["colour"])
    if action_data["unit"] == "hector":
        print_label(l)
    else:
        print_label(l)
        print_label(l)

