import tkinter as tk
# import ttkbootstrap as ttk
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

import time
from Logger import logger
import traceback
import re
import xmltodict
import uuid
import textwrap
import uu
from collections import defaultdict
import xml.dom.minidom

text_box = None
result_box = None
sct_box = None
lines = []
detached_items = []
items = []
received_rpcs = []
message_id_without_counterpart = []
oran_steps = []
VERSION = "v0.9"
cells_found=set()
ENORMOUS_RPC_SIZE = 20000


def wrap(string, length=100):
    return '\n'.join(textwrap.wrap(string, length))


def json_tree(parent, dictionary, tags, depth=0, box=None, xml=""):
    if box is None:
        box = result_box
    for key in dictionary:
        uid = uuid.uuid4()
        if isinstance(dictionary[key], dict):
            box.insert(parent, 'end', uid, text='', values=(
                "", "", "", "\t" * depth + key, "", xml), tags=tags)
            json_tree(uid, dictionary[key], tags, depth + 1, box=box, xml=xml)
        elif isinstance(dictionary[key], list):
            json_tree(parent,
                      dict([(key + (" " * i), x) for i, x in enumerate(dictionary[key])]), tags, depth + 1, box=box, xml=xml)
        else:
            value = dictionary[key]
            key_without_ns = key.split(':')[-1]
            if value is None:
                value = ""
            vl = value.split("\n")
            vl_wrapped = []
            for v in vl:
                for x in textwrap.wrap(v, 100):
                    vl_wrapped.append(x)
            vl = vl_wrapped
            if len(vl) > 1:
                for i, v in enumerate(vl):
                    uid = uuid.uuid4()
                    box.insert(parent, 'end', uid, text='', values=(
                        "", "", "", "\t" * depth + str(key_without_ns) if i == 0 else "", wrap(v), xml), tags=tags)
            else:
                box.insert(parent, 'end', uid, text='', values=(
                "", "", "", "\t" * depth + str(key_without_ns), wrap(value), xml), tags=tags)

def get_value_if_exists_recurse(dic, key):
    for (k,v) in dic.items():
        if k == key:
            return v
        elif isinstance(v, dict):
            val = get_value_if_exists_recurse(v, key)
            if val is not None:
                return val
    return None

def get_all_values_for_key_recurse(dic, key, values = []):
    for (k,v) in dic.items():
        if k == key:
            values.append(v)
        elif isinstance(v, dict):
            get_all_values_for_key_recurse(v, key, values)
    return values

def check_value_if_exists_recurse(dic, value):
    for (k,v) in dic.items():
        if v == value:
            return True
        elif isinstance(v, dict):
            return check_value_if_exists_recurse(v, value)
    return False


def display_list_tech(l):
    if type(l) is not list:
        l = [l]
    return " + ".join([str(x) for x in l])


def compute_cell_id(dn):
    pattern = ".*?\.[A-Za-z]+(\d+).*"
    match = re.match(pattern, dn)
    if match:
        return int(match.group(1))
    return None

def analyze_rpc_for_oran(dic, message_type, d, message_id):
    global oran_steps
    tags = "success"
    if message_type == "hello" and d == '<-':
        analysis_box.insert("", "end", text="", values=(f"{message_id}", "RU", "✅", "Netconf Client Connected"), tags= "success")
    elif message_type == "rpc-reply":
        if "rpc-error" in dic:
            analysis_box.insert("", "end", text="", values=(f"{message_id}", "RU", "❎", f"RPC Error for message-id {message_id}"), tags="failure")

        elif get_value_if_exists_recurse(dic, "supported-mplane-version") is not None:
            analysis_box.insert("", "end", text="", values=(f"{message_id}", "RU", "✅", f"Supported MPLANE version: {get_value_if_exists_recurse(dic, 'supported-mplane-version')}"), tags=tags)
        elif check_value_if_exists_recurse(dic, "o-ran-hw:O-RAN-RADIO"):
            mfg_name = get_value_if_exists_recurse(dic, "mfg-name")
            product_code = get_value_if_exists_recurse(dic, "product-code")
            serial_num = get_value_if_exists_recurse(dic, "serial-num")
            o_ran_name = get_value_if_exists_recurse(dic, "o-ran-name")
            if o_ran_name is None or mfg_name is None or product_code is None or serial_num is None:
                return
            dict_to_display = {
                "Detected Hardware": {
                    "mfg-name": mfg_name,
                    "product-code": product_code,
                    "serial-num": serial_num,
                    "o-ran-name": o_ran_name
                }
            }
            parent = analysis_box.insert('', 'end', text='', values=(
                f"{message_id}", "RU", "✅", f"O-DU Detects Hardware ", ""), tags=tags)
            json_tree(parent, dict_to_display, tags, box=analysis_box)
        elif get_value_if_exists_recurse(dic, "module-capability") is not None:
            bands = get_all_values_for_key_recurse(dic, "band-capabilities", []) #band-capabilities is already a list
            if len(bands) > 0 and type(bands[0]) is not list:
                bands = [bands]
            if bands:
                dict_to_display = {
                    "Bands Supported": [
                        {
                            "band-number": band["band-number"],
                            "supported-technology-dl": display_list_tech(band["supported-technology-dl"]) if "supported-technology-dl" in band else "",
                            "supported-technology-ul": display_list_tech(band["supported-technology-ul"]) if "supported-technology-ul" in band else ""
                        }
                    for band in bands[0]]
                }
                tags = "success"
                parent = analysis_box.insert('', 'end', text='', values=(
                    f"{message_id}", "RU", "✅", f"O-DU Gets Module Capabilities", ""), tags=tags)
                json_tree(parent, dict_to_display, tags, box=analysis_box)
        elif get_value_if_exists_recurse(dic, "user-plane-configuration") is not None:
            tx_arrays = get_all_values_for_key_recurse(dic, "tx-arrays", [])
            rx_arrays = get_all_values_for_key_recurse(dic, "rx-arrays", [])
            def get_supported_techs(array, direction):
                try:
                    return display_list_tech(array["capabilities"][f"supported-technology-{direction}"])
                except:
                    return ""
            if tx_arrays:
                dict_to_display = {
                    "User Plane Configuration": {
                        "tx-arrays": [
                            {
                                "tx-array" : tx_array["name"],
                                "band-number": tx_array["band-number"],
                                "supported-technology-dl": get_supported_techs(tx_array, "dl"),
                            }
                        for tx_array in tx_arrays[0]]
                    }
                }
                parent = analysis_box.insert('', 'end', text='', values=(
                    f"{message_id}", "RU", "✅", f"O-DU Gets Tx-Arrays list", ""), tags=tags)
                json_tree(parent, dict_to_display, tags, box=analysis_box)
            if rx_arrays:
                dict_to_display = {
                    "User Plane Configuration": {
                        "rx-array": [
                            {
                                "name" : rx_array["name"],
                                "band-number": rx_array["band-number"],
                                "supported-technology-ul": get_supported_techs(rx_array, "ul"),
                            }
                        for rx_array in rx_arrays[0]]
                    }
                }
                parent = analysis_box.insert('', 'end', text='', values=(
                    f"{message_id}", "RU", "✅", f"O-DU Gets Rx-Arrays list", ""), tags=tags)
                json_tree(parent, dict_to_display, tags, box=analysis_box)

    elif message_type == "rpc":
        if "edit-config" in dic:
            if get_value_if_exists_recurse(dic, "user-plane-configuration") is not None:
                low_level_rx_endpoints = get_all_values_for_key_recurse(dic, "low-level-rx-endpoints", [])
                low_level_tx_endpoints = get_all_values_for_key_recurse(dic, "low-level-tx-endpoints", [])
                rx_array_carriers = get_all_values_for_key_recurse(dic, "rx-array-carriers", [])
                tx_array_carriers = get_all_values_for_key_recurse(dic, "tx-array-carriers", [])
                low_level_rx_links = get_all_values_for_key_recurse(dic, "low-level-rx-links", [])
                low_level_tx_links = get_all_values_for_key_recurse(dic, "low-level-tx-links", [])

                def get_type_from_endpoint(scs, dir):
                    if dir == "ul":
                        if scs == "KHZ_1_25":
                            return "PRACH"
                        return "DATA"
                    else:
                        if scs == "KHZ_240":
                            return "SSB"
                        return "DATA"

                if low_level_rx_endpoints:
                    if get_value_if_exists_recurse(low_level_rx_endpoints[0][0], "eaxc-id") is None:
                        mode = "Deletion"
                    else:
                        mode = "Creation"
                    if mode == "Creation":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-rx-endpoints": [
                                    {
                                        "name": rx_endpoint["name"],
                                        "eaxc-id": get_value_if_exists_recurse(rx_endpoint, "eaxc-id"),
                                        "type": get_type_from_endpoint(get_value_if_exists_recurse(rx_endpoint, "scs"), "ul")
                                    }
                                for rx_endpoint in low_level_rx_endpoints[0]]
                            }
                        }
                    else:
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-rx-endpoints": [
                                    {
                                        "name": rx_endpoint["name"]
                                    }
                                    for rx_endpoint in low_level_rx_endpoints[0]]
                            }
                        }
                    operation = "Creates" if mode == "Creation" else "Deletes"
                    if mode == "Creation":
                        types_d = defaultdict(lambda : 0)
                        for endpoint in dict_to_display["User Plane Configuration"]["low-level-rx-endpoints"]:
                            types_d[endpoint["type"]] += 1
                        types = ", " + ' '.join([f"{v} {k}" for k, v in types_d.items()])
                    else:
                        types = ""
                    number_of_endpoints = len(dict_to_display["User Plane Configuration"]["low-level-rx-endpoints"])

                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", "Cell", "✅", f"O-DU {operation} {number_of_endpoints} Low Level Rx-Endpoints {types}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
                if low_level_tx_endpoints:
                    if get_value_if_exists_recurse(low_level_tx_endpoints[0][0], "eaxc-id") is None:
                        mode = "Deletion"
                    else:
                        mode = "Creation"
                    if mode == "Creation":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-tx-endpoints": [
                                    {
                                        "name": tx_endpoint["name"],
                                        "eaxc-id": get_value_if_exists_recurse(tx_endpoint, "eaxc-id"),
                                        "type": get_type_from_endpoint(get_value_if_exists_recurse(tx_endpoint, "scs"), "dl")
                                    }
                                for tx_endpoint in low_level_tx_endpoints[0]]
                            }
                        }
                    else:
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-tx-endpoints": [
                                    {
                                        "name": tx_endpoint["name"]
                                    }
                                    for tx_endpoint in low_level_tx_endpoints[0]]
                            }
                        }

                    operation = "Creates" if mode == "Creation" else "Deletes"
                    if mode == "Creation":
                        types_d = defaultdict(lambda : 0)
                        for endpoint in dict_to_display["User Plane Configuration"]["low-level-tx-endpoints"]:
                            types_d[endpoint["type"]] += 1
                        types = ", " + ' '.join([f"{v} {k}" for k, v in types_d.items()])
                    else:
                        types = ""

                    number_of_endpoints = len(dict_to_display["User Plane Configuration"]["low-level-tx-endpoints"])

                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", "Cell", "✅", f"O-DU {operation} {number_of_endpoints} Low Level Tx-Endpoints {types}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
                if low_level_rx_links:
                    if type(low_level_rx_links[0]) is list:
                        low_level_rx_links = low_level_rx_links[0]
                    if "rx-array-carrier" not in low_level_rx_links[0]:
                        mode = "Deletion"
                    else:
                        mode = "Creation"
                    if mode == "Creation":
                        dict_to_display = {
                        "User Plane Configuration": {
                            "low-level-rx-links": [
                                {
                                    "name": rx_link["name"],
                                    "rx-array-carrier": rx_link["rx-array-carrier"],
                                    "low-level-rx-endpoint": rx_link["low-level-rx-endpoint"],
                                    "cell_id": str(compute_cell_id(rx_link["name"]))
                                }
                            for rx_link in low_level_rx_links]
                        }
                    }
                    else:
                        dict_to_display = {
                        "User Plane Configuration": {
                            "low-level-rx-links": [
                                {
                                    "name": rx_link["name"],
                                    "cell_id": str(compute_cell_id(rx_link["name"]))
                                }
                                for rx_link in low_level_rx_links]
                        }
                    }
                    cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["User Plane Configuration"]["low-level-rx-links"]]))
                    tags = f"cell_{cell_id}"
                    cells_found.add(cell_id)
                    number_low_level_rx_links = len(dict_to_display["User Plane Configuration"]["low-level-rx-links"])
                    operation = "Creates" if mode == "Creation" else "Deletes"
                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", f"Cell {cell_id}", "✅", f"O-DU {operation} {number_low_level_rx_links} Low Level Rx Links for cell {cell_id}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
                if low_level_tx_links:
                    if type(low_level_tx_links[0]) is list:
                        low_level_tx_links = low_level_tx_links[0]
                    if "tx-array-carrier" not in low_level_tx_links[0]:
                        mode = "Deletion"
                    else:
                        mode = "Creation"

                    if mode == "Creation":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-tx-links": [
                                    {
                                        "name": tx_link["name"],
                                        "tx-array-carrier": tx_link["tx-array-carrier"],
                                        "low-level-tx-endpoint": tx_link["low-level-tx-endpoint"],
                                        "cell_id": str(compute_cell_id(tx_link["name"]))
                                    }
                                for tx_link in low_level_tx_links]
                            }
                        }
                    else:
                        dict_to_display = {
                            "User Plane Configuration": {
                                "low-level-tx-links": [
                                    {
                                        "name": tx_link["name"],
                                        "cell_id": str(compute_cell_id(tx_link["name"]))
                                    }
                                    for tx_link in low_level_tx_links]
                            }
                        }
                    cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["User Plane Configuration"]["low-level-tx-links"]]))
                    tags = f"cell_{cell_id}"
                    cells_found.add(cell_id)
                    number_low_level_tx_links = len(dict_to_display["User Plane Configuration"]["low-level-tx-links"])
                    operation = "Creates" if mode == "Creation" else "Deletes"
                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", f"Cell {cell_id}", "✅", f"O-DU {operation} {number_low_level_tx_links} Low Level Tx Links for cell {cell_id}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
                if rx_array_carriers:
                    if type(rx_array_carriers[0]) is list:
                        rx_array_carriers = rx_array_carriers[0]

                    if get_value_if_exists_recurse(rx_array_carriers[0], "active") == "ACTIVE":
                        mode = "Activation"
                    elif get_value_if_exists_recurse(rx_array_carriers[0], "type") is not None or get_value_if_exists_recurse(rx_array_carriers[0], "channel-bandwidth") is not None:
                        mode = "Creation"
                    elif get_value_if_exists_recurse(rx_array_carriers[0], "active") == "INACTIVE":
                        mode = "Deactivation"
                    elif get_value_if_exists_recurse(rx_array_carriers[0], "n-ta-offset") is not None:
                        mode = "Update"
                        #no need to display this one
                        return
                    else:
                        mode = "Deletion"
                    if mode == "Creation":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "rx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "active": get_value_if_exists_recurse(array_carrier, "active"),
                                        "type": "N/A" if get_value_if_exists_recurse(array_carrier, "type") is None else get_value_if_exists_recurse(array_carrier, "type"),
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in rx_array_carriers]
                            }
                        }
                    elif mode == "Deletion":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "rx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in rx_array_carriers]
                            }
                        }
                    else:
                        dict_to_display = {
                            "User Plane Configuration": {
                                "rx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "active": get_value_if_exists_recurse(array_carrier, "active"),
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in rx_array_carriers]
                            }
                        }
                    cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["User Plane Configuration"]["rx-array-carriers"]]))
                    number_rx_array_carriers = len(dict_to_display["User Plane Configuration"]["rx-array-carriers"])
                    type_cell = None
                    tags = f"cell_{cell_id}"
                    cells_found.add(cell_id)
                    if mode == "Creation":
                        type_cell = ' + '.join(set([ll["type"] for ll in dict_to_display["User Plane Configuration"]["rx-array-carriers"]])) + ' '
                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", f"Cell {cell_id}", "✅", f"O-DU Sends {mode} of {number_rx_array_carriers} Rx Array Carriers for {type_cell if type_cell else '' }cell {cell_id}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
                if tx_array_carriers:
                    if type(tx_array_carriers[0]) is list:
                        tx_array_carriers = tx_array_carriers[0]

                    if get_value_if_exists_recurse(tx_array_carriers[0], "active") == "ACTIVE":
                        mode = "Activation"
                    elif get_value_if_exists_recurse(tx_array_carriers[0], "type") is not None or get_value_if_exists_recurse(tx_array_carriers[0], "channel-bandwidth") is not None:
                        mode = "Creation"
                    elif get_value_if_exists_recurse(tx_array_carriers[0], "active") == "INACTIVE":
                        mode = "Deactivation"
                    elif get_value_if_exists_recurse(tx_array_carriers[0], "gain") is not None:
                        mode = "Update"
                        #no need to display this one
                        return
                    else:
                        mode = "Deletion"
                    if mode == "Creation":

                        dict_to_display = {
                            "User Plane Configuration": {
                                "tx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "active": get_value_if_exists_recurse(array_carrier, "active"),
                                        "type": "N/A" if get_value_if_exists_recurse(array_carrier, "type") is None else get_value_if_exists_recurse(array_carrier, "type"),
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in tx_array_carriers]
                            }
                        }
                    elif mode == "Deletion":
                        dict_to_display = {
                            "User Plane Configuration": {
                                "tx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in tx_array_carriers]
                            }
                        }
                    else:
                        dict_to_display = {
                            "User Plane Configuration": {
                                "tx-array-carriers": [
                                    {
                                        "name": array_carrier["name"],
                                        "active": get_value_if_exists_recurse(array_carrier, "active"),
                                        "cell_id": str(compute_cell_id(array_carrier["name"]))
                                    }
                                    for array_carrier in tx_array_carriers]
                            }
                        }
                    cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["User Plane Configuration"]["tx-array-carriers"]]))
                    number_tx_array_carriers = len(dict_to_display["User Plane Configuration"]["tx-array-carriers"])
                    type_cell = None
                    tags = f"cell_{cell_id}"
                    cells_found.add(cell_id)
                    if mode == "Creation":
                        type_cell = ' + '.join(set([ll["type"] for ll in dict_to_display["User Plane Configuration"]["tx-array-carriers"]])) + ' '
                    parent = analysis_box.insert('', 'end', text='', values=(
                        f"{message_id}", f"Cell {cell_id}", "✅", f"O-DU Sends {mode} of {number_tx_array_carriers} Tx Array Carriers for {type_cell if type_cell else '' }cell {cell_id}", ""), tags=tags)
                    json_tree(parent, dict_to_display, tags, box=analysis_box)
    elif message_type == "notification":
        if "tx-array-carriers-state-change" in dic:
            tx_array_carriers = get_value_if_exists_recurse(dic, "tx-array-carriers")
            if type(tx_array_carriers) is dict:
                tx_array_carriers = [tx_array_carriers]
            dict_to_display = {
                "Tx Array Carrier State Change": {
                    "tx-array-carriers": [
                        {
                            "name": array_carrier["name"],
                            "state": get_value_if_exists_recurse(array_carrier, "state"),
                            "cell_id": str(compute_cell_id(array_carrier["name"]))
                        }
                        for array_carrier in tx_array_carriers]
                }
            }
            cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["Tx Array Carrier State Change"]["tx-array-carriers"]]))
            tags = f"cell_{cell_id}"
            cells_found.add(cell_id)
            number_tx_array_carriers = len(dict_to_display["Tx Array Carrier State Change"]["tx-array-carriers"])
            states = ', '.join(set([ll["state"] for ll in dict_to_display["Tx Array Carrier State Change"]["tx-array-carriers"]]))
            parent = analysis_box.insert('', 'end', text='', values=(
                f"{message_id}", f"Cell {cell_id}", "✅", f"O-RU Notifies Tx Array Carrier State Change of {number_tx_array_carriers} Tx Array Carriers to {states} for cell {cell_id}", ""), tags=tags)
            json_tree(parent, dict_to_display, tags, box=analysis_box)
        if "rx-array-carriers-state-change" in dic:
            rx_array_carriers = get_value_if_exists_recurse(dic, "rx-array-carriers")
            if type(rx_array_carriers) is dict:
                rx_array_carriers = [rx_array_carriers]
            dict_to_display = {
                "Rx Array Carrier State Change": {
                    "rx-array-carriers": [
                        {
                            "name": array_carrier["name"],
                            "state": get_value_if_exists_recurse(array_carrier, "state"),
                            "cell_id": str(compute_cell_id(array_carrier["name"]))
                        }
                        for array_carrier in rx_array_carriers]
                }
            }
            cell_id = ', '.join(set([ll["cell_id"] for ll in dict_to_display["Rx Array Carrier State Change"]["rx-array-carriers"]]))
            tags = f"cell_{cell_id}"
            cells_found.add(cell_id)
            number_rx_array_carriers = len(dict_to_display["Rx Array Carrier State Change"]["rx-array-carriers"])
            states = ', '.join(set([ll["state"] for ll in dict_to_display["Rx Array Carrier State Change"]["rx-array-carriers"]]))
            parent = analysis_box.insert('', 'end', text='', values=(
                f"{message_id}", f"Cell {cell_id}", "✅", f"O-RU Notifies Rx Array Carrier State Change of {number_rx_array_carriers} Rx Array Carriers to {states} for cell {cell_id}", ""), tags=tags)
            json_tree(parent, dict_to_display, tags, box=analysis_box)


def parse_file(full_lines):
    global message_id_without_counterpart
    #Check if there is the log file will contain unwanted lines between messages
    if "830 for SSH connections" in full_lines:
        lines_filtered = [line for line in full_lines.split("\n") if ">" in line or "<" in line]
        full_lines = "\n".join(lines_filtered)
    if "Session 0: Sending message" in full_lines:
        # full_lines = re.sub(r".* Session \d: Sending message:", "", full_lines)
        full_lines = re.sub(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z Dbg: .*? Session \d+: (?:Sending|Received) message:",
            "",
            full_lines)
    else:
        full_lines = re.sub(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{7} INF (?:Sending|Received) message: ",
            "",
            full_lines)

    reg = r'<rpc .*? message-id=.(\d+).>(.*?)</rpc>|' \
          r'<rpc-reply .*? message-id=.(\d+).>(.*?)</rpc-reply>|' \
          r'<notification .*?/eventTime>(.*?)</notification>|'\
          r'<hello xmlns=\".*?\">(.*?)</hello>'

    all_matches = re.findall(reg, full_lines, re.MULTILINE|re.DOTALL)
    hello_req = False

    for i,element in enumerate(all_matches):
        pb['value'] = int(i/len(all_matches)*100)

        if pb['value'] < 25:
            label_step['text'] = "... Starting ..."
        elif pb['value'] < 50:
            label_step['text'] = "... Not Giving Up ..."
        elif pb['value'] < 75:
            label_step['text'] = "... Running Full Speed ..."
        else:
            label_step['text'] = "... Almost There ..."

        label_pb['text'] = f"{pb['value']}%"
        message_summary = ""
        #Hello case
        if element[5] != "":
            data = element[5]
            message_type = "hello"
            message_id = "0"
            raw_data = f'<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{element[5]}</hello>'
            data = element[5]
            d = "->" if not hello_req else "<-"
            tags = "hello"
            hello_req = not hello_req
            data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)
            data = re.sub(r'<session-id.*/session-id>', '', data)
        elif element[0] != "": #rpc case
            message_type = "rpc"
            message_id = element[0]
            raw_data = f'<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{element[1]}</rpc>'
            data = element[1]
            d = "->"
            tags = "req"
            if "get-schema" not in data:
                message_id_without_counterpart.append(int(message_id))
            else:
                message_type = "get-schema"
                tags = "schema"
            data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)
            data = re.sub('\n', '', data)

        elif element[2] != "": #rpc-reply case
            message_type = "rpc-reply"
            message_id = element[2]
            data = element[3]
            raw_data = f'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{element[3]}</rpc-reply>'
            d = "<-"
            if len(data) < 10000 and "rpc-error" in data:
                data = f"<rpc-error>{data}</rpc-error>"
                tags = "rpc-error"
            else:
                data = f"<rpc-reply>{data}</rpc-reply>"
                tags = "resp"
            if int(message_id) in message_id_without_counterpart:
                message_id_without_counterpart.remove(int(message_id))
            data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)
            data = re.sub(r'^.*?<', '<', data, flags=re.DOTALL)
            data = re.sub(r'>[^>]*?$', '>', data, flags=re.DOTALL)
        elif element[4] != "": #notification case
            message_type = "notification"
            message_id = "N/A"
            data = element[4]
            raw_data = f'<notification xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{element[4]}</notification>'
            d = "<-"
            if "netconf-config-change" in data:
                tags = "config-change"
            else:
                tags = "notif"
            data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)

        try:
            raw_data = re.sub(r'} {', '', raw_data, flags=re.DOTALL)
            raw_data = re.sub(r'\n', '', raw_data, flags=re.DOTALL)
            data = re.sub(r'} {', '', data, flags=re.DOTALL)
            data = re.sub(r'\n', '', data, flags=re.DOTALL)
            xml = raw_data
            dic = xmltodict.parse(data)
            if tags == "req":
                if "get" in dic:
                    try:
                        message_summary = f"get {'|'.join(dic['get']['filter'].keys())}"
                    except:
                        message_summary = "get"
                elif "edit-config" in dic:
                    try:
                        message_summary = f"edit-config {''.join(dic['edit-config']['config'].keys())}"
                    except:
                        message_summary = "edit-config"
                else:
                    message_summary = f"rpc {''.join(dic.keys())}"
            elif tags == "notif":
                message_summary = f"notification {''.join(dic.keys())}"
            elif tags == "hello":
                capas = set()
                capabilities = list(dic["capabilities"].values())
                if type(capabilities[0]) is list:
                    capabilities = capabilities[0]
                for capa in capabilities:
                    if "urn:ietf:params:netconf:base:" in capa:
                        capas.add(capa.split(":")[-1])
                message_summary = f"Netconf Version Supported {', '.join(capas)}"
            elif tags == "schema":
                message_summary = f"get-schema {dic['get-schema']['identifier']}"
        except Exception as e:
            dic = {"": f"Failed to parse data: {e}"}
        try:
            analyze_rpc_for_oran(dic, message_type, d, message_id)
        except Exception as e:
            print(e)
        if len(data) >= ENORMOUS_RPC_SIZE and not parse_enormous_rpc.get():
            message_summary = message_summary + " (RPC too big check Parse Enormous RPCs and parse again to display the tree)"
        parent = result_box.insert('', 'end', text='', values=(
            message_id, d, message_type, f"\t\t{message_summary}", "", xml), tags=tags)
        if len(data) < ENORMOUS_RPC_SIZE or parse_enormous_rpc.get():
            json_tree(parent, dic, tags, xml=xml)


def search_in_element(query, element):
    if query.lower() in str(result_box.item(element)['values'][2]) or query.lower() in str(
            result_box.item(element)['values'][3]) or query.lower() in str(result_box.item(element)['values'][4]):
        return True
    result = False
    for child in result_box.get_children(element):
        result = result or search_in_element(query, child)
    return result


def search(event):
    query = filter_text.get()
    selections = []
    for child in result_box.get_children():
        if not search_in_element(query, child):
            selections.append(child)
            detached_items.append(child)
        items.append(child)
    for item in selections:
        result_box.detach(item)


def clear_search(event):
    for (index, i) in enumerate(items):
        if i in detached_items:
            result_box.reattach(i, '', index)
    detached_items.clear()
    items.clear()


def clear_tree(event):
    if len(items) == 0:
        for child in result_box.get_children():
            items.append(child)
    for item in items:
        result_box.delete(item)
    items.clear()
    detached_items.clear()
    message_id_without_counterpart.clear()


def get_text_box(event):
    result_box.delete(*result_box.get_children())
    analysis_box.delete(*analysis_box.get_children())
    back_to_tree_view(None)
    full = text_box.get("1.0", tk.END)
    text_box.delete("1.0", tk.END)
    import threading
    t1 = threading.Thread(target=threaded_operation, args=(full,))
    t1.start()

def monitor(thread):
    if thread.is_alive():
        window.after(100, lambda: monitor(thread))


def threaded_operation(full):
    result_box.pack_forget()
    parse_file(full)
    # Apply no counterparts tag
    for child in result_box.get_children():
        if result_box.item(child)['values'][0] != "N/A" and int(
                result_box.item(child)['values'][0]) in message_id_without_counterpart:
            result_box.item(child, tags=['no-counterpart'])
    result_box.tag_configure("hello", background='lightyellow')
    result_box.tag_configure("req", background='lightblue')
    result_box.tag_configure("schema", background='#70c38e')
    result_box.tag_configure("resp", background='lightgreen')
    result_box.tag_configure("notif", background='#faebd7')
    result_box.tag_configure("netconf-config-change", background='#cd9575')
    result_box.tag_configure("rpc-error", background='#ff6242')
    result_box.tag_configure("no-counterpart", background='orange')
    analysis_box.tag_configure("success", background='lightgreen')
    analysis_box.tag_configure("failure", background='#ff6242')
    background_cells = [
        "#32cd32",
        "#93dc5c",
        "#b7e892",
        "#dbf3c9",
        "#c3f550"
    ]
    for index, i in enumerate(cells_found):
        analysis_box.tag_configure(f"cell_{i}", background=background_cells[index%5])
    result_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
    pb.pack_forget()
    label_pb.pack_forget()
    label_step.pack_forget()

def load_file_dialog(event):
    f = filedialog.askopenfile()
    text_box.insert('1.0', f.readlines())


def copy_to_clipboard(event):
    window.clipboard_clear()
    full = message_text_box.get("1.0", tk.END)
    window.clipboard_append(full)
    window.update()

def launch_oran_analysis(event):
    back_to_tree.pack()
    oran_analysis.pack_forget()
    result_box.pack_forget()
    analysis_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
    analysis_box.config(xscrollcommand=sb2.set)
    analysis_box.config(yscrollcommand=sb.set)
    sb.config(command=analysis_box.yview)
    sb2.config(command=analysis_box.xview)

def back_to_tree_view(event):
    back_to_tree.pack_forget()
    oran_analysis.pack()
    analysis_box.pack_forget()
    result_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
    result_box.config(xscrollcommand=sb2.set)
    result_box.config(yscrollcommand=sb.set)
    sb.config(command=result_box.yview)
    sb2.config(command=result_box.xview)


def open_children(parent, box):
    box.item(parent, open=True)
    for child in box.get_children(parent):
        open_children(child, box)

def handleOpenEvent(event, box):
    open_children(box.focus(), box)


def update_title(file):
    window.title(f"NetConfParser {VERSION} - {file}")

def load_file(file):
    clear_tree(None)
    message_id_without_counterpart.clear()
    oran_steps.clear()
    text_box.delete('1.0', tk.END)
    pb.pack(pady=60)

    label_pb.pack()
    label_step.pack()
    with open(file.data, 'r') as f:
        text_box.insert('1.0', f.readlines())
    get_text_box(None)
    update_title(file.data)

def show_message_in_text(event):
    itemid = result_box.identify('item', event.x, event.y)
    x = result_box.item(itemid)
    xml_str = x['values'][-1]
    st = xml.dom.minidom.parseString(xml_str)
    pps = st.toprettyxml(indent='    ')
    pps = re.sub(r'<.xml version="1.0" .>\n', "", pps)
    message_text_box.delete('1.0', tk.END)
    message_text_box.insert('1.0', pps)


if __name__ == "__main__":

    try:
        try:
            uu.decode('fs_ico_encoded', 'fs.ico')
        except:
            pass
        window = TkinterDnD.Tk()
        s = ttk.Style()
        #window = ttk.Window(themename="solar")


        # workaround for row coloring
        # if window.getvar('tk_patchLevel') == '8.6.9':
        def fixed_map(option):
            return [elm for elm in s.map('Treeview', query_opt=option) if elm[:2] != ('!disabled', '!selected')]


        s.map('Treeview', foreground=fixed_map('foreground'),
              background=fixed_map('background'))
        # end workaround
        window.title(f'NetConfParser {VERSION}')
        try:
            window.wm_iconbitmap('fs.ico')
            window.iconbitmap('fs.ico')
        except:
            pass
        window.state('zoomed')
        frame_l = tk.Frame(width=200, height=400)
        frame_r = tk.Frame(width=100, height=200)

        label = tk.Label(master=frame_r, text="Paste log here")
        text_box = tk.Text(master=frame_r, width=20, height=20)
        oran_analysis = tk.Button(master=frame_r, text="See ORAN Analysis")
        back_to_tree = tk.Button(master=frame_r, text="Back to Tree")
        parse_enormous_rpc = tk.IntVar()
        parse_snapshot = tk.Checkbutton(master=frame_r, text='Parse Enormous RPCs', variable=parse_enormous_rpc, onvalue=1, offvalue=0)
        filter_text = tk.Entry(master=frame_l)
        filter_button = tk.Button(master=frame_l, text="Filter")
        clear_button = tk.Button(master=frame_l, text="Clear Search")
        clear_tree_button = tk.Button(master=frame_l, text="Clear Tree")

        result_box = ttk.Treeview(master=frame_l)
        result_box["columns"] = ("id", "direction", "type", "data", "data2", "xml")
        result_box["displaycolumns"] = ("id", "direction", "type", "data", "data2")
        result_box.column("#0", width=150, minwidth=10, stretch=tk.NO)
        result_box.column("id", width=50, minwidth=20,
                          stretch=tk.NO, anchor="c")
        result_box.column("direction", width=50, minwidth=100,
                          stretch=tk.NO, anchor="c")
        result_box.column("type", width=100, minwidth=100,
                          stretch=tk.NO, anchor="c")
        result_box.column("data", width=400, minwidth=400)
        result_box.column("data2", width=200, minwidth=200)
        result_box.heading('#0', text='', anchor=tk.CENTER)
        result_box.heading('id', text='id', anchor=tk.CENTER)
        result_box.heading('direction', text='dir', anchor=tk.CENTER)
        result_box.heading('type', text='type', anchor=tk.CENTER)
        result_box.heading('data', text='data', anchor=tk.CENTER)
        result_box.heading('data2', text='', anchor=tk.CENTER)

        result_box.bind('<<TreeviewOpen>>', lambda x: handleOpenEvent(x, result_box))

        message_text_box = tk.Text(master=frame_r, width=20, height=20)
        copy_to_clip = tk.Button(master=frame_r, text="Copy To Clipboard")




        sb = tk.Scrollbar(frame_l, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb2 = tk.Scrollbar(frame_l, orient=tk.HORIZONTAL)
        sb2.pack(side=tk.BOTTOM, fill=tk.X)

        result_box.config(xscrollcommand=sb2.set)
        result_box.config(yscrollcommand=sb.set)
        sb.config(command=result_box.yview)
        sb2.config(command=result_box.xview)

        parse_button = tk.Button(master=frame_r, text="Parse")
        load_button = tk.Button(master=frame_r, text="Load File")

        filter_text.place(y=20, x=50, width=400)
        filter_button.bind("<Button-1>", search)
        filter_button.place(y=20, x=500, width=200)
        clear_button.bind("<Button-1>", clear_search)
        clear_button.place(y=20, x=710, width=200)
        clear_tree_button.bind("<Button-1>", clear_tree)
        clear_tree_button.place(y=20, x=920, width=200)
        label.pack(anchor="center")
        text_box.pack(anchor="center", after=label)

        text_box.drop_target_register(DND_FILES)
        text_box.dnd_bind('<<Drop>>', load_file)
        result_box.drop_target_register(DND_FILES)
        result_box.dnd_bind('<<Drop>>', load_file)

        result_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
        pb = ttk.Progressbar(frame_r, orient='vertical', mode='determinate', length=280)
        pb.pack_forget()
        label_step = ttk.Label(frame_r, text="... Starting ...")
        label_step.pack_forget()
        label_pb = ttk.Label(frame_r, text="0%")
        label_pb.pack_forget()


        analysis_box = ttk.Treeview(master=frame_l)
        analysis_box["columns"] = ("msg-id", "category", "status", "information", "data2")
        analysis_box.column("#0", width=50, minwidth=10, stretch=tk.NO)
        analysis_box.column("msg-id", width=50, minwidth=20,
                          stretch=tk.NO, anchor="c")
        analysis_box.column("category", width=100, minwidth=100,
                          stretch=tk.NO, anchor="c")
        analysis_box.column("status", width=50, minwidth=100,
                          stretch=tk.NO, anchor="c")
        analysis_box.column("information", width=400, minwidth=400)
        analysis_box.column("data2", width=200, minwidth=200)
        analysis_box.heading('#0', text='', anchor=tk.CENTER)
        analysis_box.heading('msg-id', text='msg-id', anchor=tk.CENTER)
        analysis_box.heading('category', text='category', anchor=tk.CENTER)
        analysis_box.heading('status', text='status', anchor=tk.CENTER)
        analysis_box.heading('information', text='information', anchor=tk.CENTER)
        analysis_box.heading('data2', text='', anchor=tk.CENTER)

        analysis_box.bind('<<TreeviewOpen>>', lambda x: handleOpenEvent(x, analysis_box))
        analysis_box.pack_forget()

        parse_button.bind("<Button-1>", get_text_box)
        parse_button.pack(anchor="center", after=text_box)
        load_button.bind("<Button-1>", load_file_dialog)
        load_button.pack(anchor="center", after=parse_button)
        parse_snapshot.pack(anchor="center", after=load_button)
        message_text_box.pack(anchor="center", after=parse_snapshot)
        copy_to_clip.pack(anchor="center", after=message_text_box)
        oran_analysis.pack(anchor="center", after=copy_to_clip)

        #back_to_tree.place(y=560, relx=.5, anchor="center")
        back_to_tree.pack_forget()

        back_to_tree.bind("<Button-1>", back_to_tree_view)
        oran_analysis.bind("<Button-1>", launch_oran_analysis)
        copy_to_clip.bind("<Button-1>", copy_to_clipboard)
        result_box.bind("<Button-1>", show_message_in_text)


        frame_l.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        frame_r.grid_propagate(False)
        frame_r.pack(fill=tk.Y, side=tk.RIGHT)
        window.mainloop()
    except Exception as e:
        logger.error("Exception Caught!")
        for l in traceback.format_exc().splitlines():
            logger.error(l)
