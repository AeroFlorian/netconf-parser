from enum import Enum
from Logger import logger
from OranMessageUtils import GenericUtilities, OranSpecificUtilities
from collections import defaultdict
import NetconfMessageDefs


class OranMessageStatus(Enum):
    SUCCESS = 0
    FAILURE = 1


class OranMessage:
    def __init__(self, netconf_message: NetconfMessageDefs.Message):
        if netconf_message is not None:
            self.message_id: int = netconf_message.message_id
            self.category: str = "RU"
            self.information: str = ""
            self.data_to_display: dict = defaultdict(lambda: {})
            self.status: OranMessageStatus = OranMessageStatus.SUCCESS
            self.is_important_in_analysis: bool = False
            self.fill_from_netconf_message(netconf_message)
            self.raw_data = netconf_message.raw_data

    def __str__(self):
        return f'{self.message_id} - {self.category} - {self.information} - {self.status}'

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        logger.error('OranMessage.fill_from_netconf_message() not implemented')

    def should_be_present_in_analysis(self):
        return self.is_important_in_analysis

    def get_values(self):
        return (
            "",
            self.message_id if self.message_id else "N/A",
            self.category,
            "✅" if self.status == OranMessageStatus.SUCCESS else "❎",
            self.information,
            "",
            self.raw_data
        )

    def check_without_counterpart(self):
        pass


class OranRpcMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcMessage):
        super(OranRpcMessage, self).__init__(netconf_message)
        self.message = netconf_message

    def check_without_counterpart(self):
        if self.message.tag == NetconfMessageDefs.Tag.RPC_WITHOUT_COUNTERPART:
            self.fill_rpc_without_counterpart()
        elif not self.information:
            self.is_important_in_analysis = False

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        self.is_important_in_analysis = True
        if "edit-config" not in netconf_message.data:
            return
        if GenericUtilities.get_value_if_exists_recurse(netconf_message.data, "user-plane-configuration"):
            self.fill_user_plane_configuration(netconf_message.data)

    def fill_rpc_without_counterpart(self):
        self.status = OranMessageStatus.FAILURE
        self.category = "WRN"
        self.information = f"RPC Not replied for message id {self.message_id}"
        self.is_important_in_analysis = True

    def fill_user_plane_configuration(self, data):
        low_level_rx_endpoints = GenericUtilities.get_value_as_list(
            GenericUtilities.get_all_values_for_key_recurse(data, "low-level-rx-endpoints", []))
        if low_level_rx_endpoints:
            self.fill_low_level_rx_endpoints(low_level_rx_endpoints)
        low_level_tx_endpoints = GenericUtilities.get_value_as_list(
            GenericUtilities.get_all_values_for_key_recurse(data, "low-level-tx-endpoints", []))
        if low_level_tx_endpoints:
            self.fill_low_level_tx_endpoints(low_level_tx_endpoints)
        low_level_rx_links = GenericUtilities.get_value_as_item(
            GenericUtilities.get_all_values_for_key_recurse(data, "low-level-rx-links", []))
        if low_level_rx_links:
            self.fill_low_level_rx_links(low_level_rx_links)
        low_level_tx_links = GenericUtilities.get_value_as_item(
            GenericUtilities.get_all_values_for_key_recurse(data, "low-level-tx-links", []))
        if low_level_tx_links:
            self.fill_low_level_tx_links(low_level_tx_links)
        rx_array_carriers = GenericUtilities.get_value_as_item(
            GenericUtilities.get_all_values_for_key_recurse(data, "rx-array-carriers", []))
        if rx_array_carriers:
            self.fill_rx_array_carriers(rx_array_carriers)
        tx_array_carriers = GenericUtilities.get_value_as_item(
            GenericUtilities.get_all_values_for_key_recurse(data, "tx-array-carriers", []))
        if tx_array_carriers:
            self.fill_tx_array_carriers(tx_array_carriers)

    def fill_low_level_rx_endpoints(self, low_level_rx_endpoints):
        if isinstance(low_level_rx_endpoints[0], list):
            value = low_level_rx_endpoints[0][0]
            list_endpoints = low_level_rx_endpoints[0]
        else:
            value = low_level_rx_endpoints[0]
            list_endpoints = low_level_rx_endpoints
        if GenericUtilities.get_value_if_exists_recurse(value, "eaxc-id"):
            self.fill_creation_low_level_rx_endpoints(list_endpoints)
        else:
            self.fill_deletion_low_level_rx_endpoints(list_endpoints)

    def fill_creation_low_level_rx_endpoints(self, low_level_rx_endpoints):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-rx-endpoints"] = [
            {
                "name": rx_endpoint["name"],
                "eaxc-id": GenericUtilities.get_value_if_exists_recurse(rx_endpoint, "eaxc-id"),
                "type": OranSpecificUtilities.get_type_from_endpoint(
                    GenericUtilities.get_value_if_exists_recurse(rx_endpoint, "scs"), "ul")
            }
            for rx_endpoint in low_level_rx_endpoints
        ]
        types_d = defaultdict(lambda: 0)
        for endpoint in self.data_to_display["User Plane Configuration"]["low-level-rx-endpoints"]:
            types_d[endpoint["type"]] += 1
        types = ", " + ' '.join([f"{v} {k}" for k, v in types_d.items()])
        self.information += f'O-DU creates {len(low_level_rx_endpoints)} Low Level Rx Endpoints {types} '
        self.is_important_in_analysis = True

    def fill_deletion_low_level_rx_endpoints(self, low_level_rx_endpoints):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-rx-endpoints"] = [
            {
                "name": rx_endpoint["name"]
            }
            for rx_endpoint in low_level_rx_endpoints
        ]
        self.information += f'O-DU deletes {len(low_level_rx_endpoints)} Low Level Rx Endpoints '
        self.is_important_in_analysis = True

    def fill_low_level_tx_endpoints(self, low_level_tx_endpoints):
        if(isinstance(low_level_tx_endpoints[0], list)):
            value = low_level_tx_endpoints[0][0]
            list_endpoints = low_level_tx_endpoints[0]
        else:
            value = low_level_tx_endpoints[0]
            list_endpoints = low_level_tx_endpoints
        if GenericUtilities.get_value_if_exists_recurse(value, "eaxc-id"):
            self.fill_creation_low_level_tx_endpoints(list_endpoints)
        else:
            self.fill_deletion_low_level_tx_endpoints(list_endpoints)

    def fill_creation_low_level_tx_endpoints(self, low_level_tx_endpoints):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-tx-endpoints"] = [
            {
                "name": tx_endpoint["name"],
                "eaxc-id": GenericUtilities.get_value_if_exists_recurse(tx_endpoint, "eaxc-id"),
                "type": OranSpecificUtilities.get_type_from_endpoint(
                    GenericUtilities.get_value_if_exists_recurse(tx_endpoint, "scs"), "dl")
            }
            for tx_endpoint in low_level_tx_endpoints
        ]
        types_d = defaultdict(lambda: 0)
        for endpoint in self.data_to_display["User Plane Configuration"]["low-level-tx-endpoints"]:
            types_d[endpoint["type"]] += 1
        types = ", " + ' '.join([f"{v} {k}" for k, v in types_d.items()])
        self.information += f'O-DU creates {len(low_level_tx_endpoints)} Low Level Tx Endpoints {types} '
        self.is_important_in_analysis = True


    def fill_deletion_low_level_tx_endpoints(self, low_level_tx_endpoints):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-tx-endpoints"] = [
            {
                "name": tx_endpoint["name"]
            }
            for tx_endpoint in low_level_tx_endpoints
        ]
        self.information += f'O-DU deletes {len(low_level_tx_endpoints)} Low Level Tx Endpoints '
        self.is_important_in_analysis = True

    def fill_low_level_rx_links(self, low_level_rx_links):
        if GenericUtilities.get_value_if_exists_recurse(low_level_rx_links[0], "rx-array-carrier"):
            self.fill_creation_low_level_rx_links(low_level_rx_links)
        else:
            self.fill_deletion_low_level_rx_links(low_level_rx_links)

    def fill_creation_low_level_rx_links(self, low_level_rx_links):
        self.data_to_display["User Plane Configuration"]["low-level-rx-links"] = [
            {
                "name": rx_link["name"],
                "rx-array-carrier": rx_link["rx-array-carrier"],
                "low-level-rx-endpoint": rx_link["low-level-rx-endpoint"]
            }
            for rx_link in low_level_rx_links
        ]
        self.category = 'Cell'
        self.information += f'O-DU creates {len(low_level_rx_links)} Low Level Rx Links'
        self.is_important_in_analysis = True

    def fill_deletion_low_level_rx_links(self, low_level_rx_links):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-rx-links"] = [
            {
                "name": rx_link["name"]
            }
            for rx_link in low_level_rx_links
        ]
        self.information += f'O-DU deletes {len(low_level_rx_links)} Low Level Rx Links'
        self.is_important_in_analysis = True

    def fill_low_level_tx_links(self, low_level_tx_links):
        if GenericUtilities.get_value_if_exists_recurse(low_level_tx_links[0], "tx-array-carrier"):
            self.fill_creation_low_level_tx_links(low_level_tx_links)
        else:
            self.fill_deletion_low_level_tx_links(low_level_tx_links)

    def fill_creation_low_level_tx_links(self, low_level_tx_links):
        self.data_to_display["User Plane Configuration"]["low-level-tx-links"] = [
            {
                "name": tx_link["name"],
                "tx-array-carrier": tx_link["tx-array-carrier"],
                "low-level-tx-endpoint": tx_link["low-level-tx-endpoint"],
            }
            for tx_link in low_level_tx_links
        ]
        self.category = 'Cell'
        self.information += f'O-DU creates {len(low_level_tx_links)} Low Level Tx Links'
        self.is_important_in_analysis = True

    def fill_deletion_low_level_tx_links(self, low_level_tx_links):
        self.category = 'Cell'
        self.data_to_display["User Plane Configuration"]["low-level-tx-links"] = [
            {
                "name": tx_link["name"]
            }
            for tx_link in low_level_tx_links
        ]
        self.information += f'O-DU deletes {len(low_level_tx_links)} Low Level Tx Links'
        self.is_important_in_analysis = True

    def fill_rx_array_carriers(self, rx_array_carriers):
        if GenericUtilities.get_value_if_exists_recurse(rx_array_carriers[0], "type") or \
                GenericUtilities.get_value_if_exists_recurse(rx_array_carriers[0], "channel-bandwidth"):
            self.fill_creation_rx_array_carriers(rx_array_carriers)
        elif GenericUtilities.get_value_if_exists_recurse(rx_array_carriers[0], "active"):
            self.fill_activation_deactivation_rx_array_carriers(rx_array_carriers)
        elif not GenericUtilities.get_value_if_exists_recurse(rx_array_carriers[0], "n-ta-offset"):
            self.fill_deletion_rx_array_carriers(rx_array_carriers)

    def fill_activation_deactivation_rx_array_carriers(self, rx_array_carriers):
        self.data_to_display["User Plane Configuration"]["rx-array-carriers"] = [
            {
                "name": rx_array_carrier["name"],
                "active": rx_array_carrier["active"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(rx_array_carrier["name"]))
            }
            for rx_array_carrier in rx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["rx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        active = "Activates" if rx_array_carriers[0]["active"] == "ACTIVE" else "Deactivates"
        self.information += f'O-DU {active} {len(rx_array_carriers)} Rx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True

    def fill_creation_rx_array_carriers(self, rx_array_carriers):
        self.data_to_display["User Plane Configuration"]["rx-array-carriers"] = [
            {
                "name": array_carrier["name"],
                "active": GenericUtilities.get_value_if_exists_recurse(array_carrier, "active"),
                "type": "N/A" if GenericUtilities.get_value_if_exists_recurse(array_carrier,
                                                                              "type") == "" else GenericUtilities.get_value_if_exists_recurse(
                    array_carrier, "type"),
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in rx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["rx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-DU Creates {len(rx_array_carriers)} Rx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True

    def fill_deletion_rx_array_carriers(self, rx_array_carriers):
        self.data_to_display["User Plane Configuration"]["rx-array-carriers"] = [
            {
                "name": array_carrier["name"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in rx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["rx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-DU Deletes {len(rx_array_carriers)} Rx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True

    def fill_tx_array_carriers(self, tx_array_carriers):
        if GenericUtilities.get_value_if_exists_recurse(tx_array_carriers[0], "type") or \
                GenericUtilities.get_value_if_exists_recurse(tx_array_carriers[0], "channel-bandwidth"):
            self.fill_creation_tx_array_carriers(tx_array_carriers)
        elif GenericUtilities.get_value_if_exists_recurse(tx_array_carriers[0], "active"):
            self.fill_activation_deactivation_tx_array_carriers(tx_array_carriers)
        elif not GenericUtilities.get_value_if_exists_recurse(tx_array_carriers[0], "gain"):
            self.fill_deletion_tx_array_carriers(tx_array_carriers)

    def fill_activation_deactivation_tx_array_carriers(self, tx_array_carriers):
        self.data_to_display["User Plane Configuration"]["tx-array-carriers"] = [
            {
                "name": tx_array_carrier["name"],
                "active": tx_array_carrier["active"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(tx_array_carrier["name"]))
            }
            for tx_array_carrier in tx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["tx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        active = "Activates" if tx_array_carriers[0]["active"] == "ACTIVE" else "Deactivates"
        self.information += f'O-DU {active} {len(tx_array_carriers)} Tx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True

    def fill_creation_tx_array_carriers(self, tx_array_carriers):
        self.data_to_display["User Plane Configuration"]["tx-array-carriers"] = [
            {
                "name": array_carrier["name"],
                "active": GenericUtilities.get_value_if_exists_recurse(array_carrier, "active"),
                "type": "N/A" if GenericUtilities.get_value_if_exists_recurse(array_carrier,
                                                                              "type") == "" else GenericUtilities.get_value_if_exists_recurse(
                    array_carrier, "type"),
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in tx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["tx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-DU Creates {len(tx_array_carriers)} Tx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True

    def fill_deletion_tx_array_carriers(self, tx_array_carriers):
        self.data_to_display["User Plane Configuration"]["tx-array-carriers"] = [
            {
                "name": array_carrier["name"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in tx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in self.data_to_display["User Plane Configuration"]["tx-array-carriers"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-DU Deletes {len(tx_array_carriers)} Tx Array Carriers for cell {cell_id} '
        self.is_important_in_analysis = True


class OranNotificationMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcMessage):
        super(OranNotificationMessage, self).__init__(netconf_message)

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        if "tx-array-carriers-state-change" in netconf_message.data:
            tx_array_carriers = GenericUtilities.get_value_as_list(
                GenericUtilities.get_value_if_exists_recurse(netconf_message.data, "tx-array-carriers"))
            self.fill_tx_array_carrier_state_change(tx_array_carriers)
        elif "rx-array-carriers-state-change" in netconf_message.data:
            rx_array_carriers = GenericUtilities.get_value_as_list(
                GenericUtilities.get_value_if_exists_recurse(netconf_message.data, "rx-array-carriers"))
            self.fill_rx_array_carrier_state_change(rx_array_carriers)

    def fill_tx_array_carrier_state_change(self, tx_array_carriers):
        self.data_to_display["User Plane Configuration"]["tx-array-carriers-state-change"] = [
            {
                "name": array_carrier["name"],
                "state": array_carrier["state"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in tx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in
                 self.data_to_display["User Plane Configuration"]["tx-array-carriers-state-change"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-RU Changes state of {len(tx_array_carriers)} Tx Array Carriers to ' \
                            f'{self.data_to_display["User Plane Configuration"]["tx-array-carriers-state-change"][0]["state"]} for cell {cell_id}'
        self.is_important_in_analysis = True

    def fill_rx_array_carrier_state_change(self, rx_array_carriers):
        self.data_to_display["User Plane Configuration"]["rx-array-carriers-state-change"] = [
            {
                "name": array_carrier["name"],
                "state": array_carrier["state"],
                "cell_id": str(OranSpecificUtilities.compute_cell_id(array_carrier["name"]))
            }
            for array_carrier in rx_array_carriers
        ]
        cell_id = ', '.join(
            set([ll["cell_id"] for ll in
                 self.data_to_display["User Plane Configuration"]["rx-array-carriers-state-change"]]))
        self.category = f'Cell {cell_id}'
        self.information += f'O-RU Changes state of {len(rx_array_carriers)} Rx Array Carriers to ' \
                            f'{self.data_to_display["User Plane Configuration"]["rx-array-carriers-state-change"][0]["state"]} for cell {cell_id}'
        self.is_important_in_analysis = True


class OranRpcReplyMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcReplyMessage):
        self.category = 'RU'
        super(OranRpcReplyMessage, self).__init__(netconf_message)


    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.RpcReplyMessage):
        if netconf_message.tag == NetconfMessageDefs.Tag.RPC_ERROR:
            self.fill_rpc_error()
        elif GenericUtilities.get_value_if_exists_recurse(netconf_message.data,
                                                          "supported-mplane-version"):
            self.fill_supported_mplane(netconf_message.data)
        elif GenericUtilities.check_value_if_exists_recurse(netconf_message.data, "o-ran-hw:O-RAN-RADIO"):
            self.fill_hardware(netconf_message.data)
        elif GenericUtilities.get_value_if_exists_recurse(netconf_message.data, "module-capability"):
            self.fill_module_capability(netconf_message.data)
        elif GenericUtilities.get_value_if_exists_recurse(netconf_message.data, "user-plane-configuration"):
            self.fill_user_plane_configuration(netconf_message.data)

    def fill_rpc_error(self):
        self.status = OranMessageStatus.FAILURE
        self.category = "ERR"
        self.information = f"RPC Error for message id {self.message_id}"
        self.is_important_in_analysis = True

    def fill_supported_mplane(self, data):
        supported_mplane_version = GenericUtilities.get_value_if_exists_recurse(data,
                                                                                "supported-mplane-version")
        self.information = f"Supported MPLANE version: {supported_mplane_version}"
        self.is_important_in_analysis = True

    def fill_hardware(self, data):
        mfg_name = GenericUtilities.get_value_if_exists_recurse(data, "mfg-name")
        product_code = GenericUtilities.get_value_if_exists_recurse(data, "product-code")
        serial_num = GenericUtilities.get_value_if_exists_recurse(data, "serial-num")
        o_ran_name = GenericUtilities.get_value_if_exists_recurse(data, "o-ran-name")
        if not mfg_name or not product_code or not serial_num or not o_ran_name:
            return
        self.data_to_display = {
            "Detected Hardware": {
                "mfg-name": mfg_name,
                "product-code": product_code,
                "serial-num": serial_num,
                "o-ran-name": o_ran_name
            }
        }
        self.information = f'O-DU Detects Hardware {mfg_name} {product_code} {serial_num} {o_ran_name}'
        self.is_important_in_analysis = True

    def fill_module_capability(self, data):
        bands = GenericUtilities.get_all_values_for_key_recurse(data, "band-capabilities", [])
        if len(bands) > 0 and type(bands[0]) is not list:
            bands = [bands]
        if bands:
            self.data_to_display = {
                "Bands Supported": [
                    {
                        "band-number": band["band-number"],
                        "supported-technology-dl": OranSpecificUtilities.display_list_tech(
                            band["supported-technology-dl"] if "supported-technology-dl" in band else ""),
                        "supported-technology-ul": OranSpecificUtilities.display_list_tech(
                            band["supported-technology-ul"] if "supported-technology-ul" in band else "")
                    }
                    for band in bands[0]]
            }
            self.information = f'O-DU Gets Module Capabilities: Bands {"/".join([str(band["band-number"]) for band in self.data_to_display["Bands Supported"]])}'
            self.is_important_in_analysis = True

    def fill_user_plane_configuration(self, data):
        tx_arrays = GenericUtilities.get_value_as_list(
            GenericUtilities.get_all_values_for_key_recurse(data, "tx-arrays", []))
        rx_arrays = GenericUtilities.get_value_as_list(
            GenericUtilities.get_all_values_for_key_recurse(data, "rx-arrays", []))
        self.information = 'O-DU Retrieves information for '
        if tx_arrays and tx_arrays[0]:
            self.data_to_display["User Plane Configuration"]["tx-arrays"] = [
                {
                    "tx-array": tx_array["name"],
                    "band-number": tx_array["band-number"],
                    "supported-technology-dl": OranSpecificUtilities.get_supported_techs(tx_array, "dl"),
                }
                for tx_array in tx_arrays[0]
            ]
            self.is_important_in_analysis = True
            self.information += f'{len(tx_arrays[0])} TX Arrays '
        if rx_arrays and rx_arrays[0]:
            self.data_to_display["User Plane Configuration"]["rx-arrays"] = [
                {
                    "rx-array": rx_array["name"],
                    "band-number": rx_array["band-number"],
                    "supported-technology-ul": OranSpecificUtilities.get_supported_techs(rx_array, "ul"),
                }
                for rx_array in rx_arrays[0]
            ]
            self.is_important_in_analysis = True
            self.information += f'{len(rx_arrays[0])} RX Arrays'


class NetconfClientConnectedMessage(OranMessage):
    def __init__(self):
        super(NetconfClientConnectedMessage, self).__init__(None)
        self.message_id = 0
        self.category = 'RU'
        self.information = 'Netconf Client connected'
        self.status = OranMessageStatus.SUCCESS
        self.is_important_in_analysis = True
        self.data_to_display = None
        self.raw_data = "<hello/>"
