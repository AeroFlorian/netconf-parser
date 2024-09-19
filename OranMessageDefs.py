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
            self.category: str = None
            self.information: str = None
            self.data_to_display: dict = defaultdict(lambda: {})
            self.status: OranMessageStatus = OranMessageStatus.SUCCESS
            self.is_important_in_analysis: bool = False
            self.fill_from_netconf_message(netconf_message)

    def __str__(self):
        return f'{self.message_id} - {self.category} - {self.information} - {self.status}'

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        logger.error('OranMessage.fill_from_netconf_message() not implemented')

    def should_be_present_in_analysis(self):
        return self.is_important_in_analysis


class OranRpcMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcMessage):
        super(OranRpcMessage, self).__init__(netconf_message)

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        if "edit-config" not in netconf_message.data:
            return


class OranNotificationMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcMessage):
        super(OranNotificationMessage, self).__init__(netconf_message)

    def fill_from_netconf_message(self, netconf_message: NetconfMessageDefs.Message):
        logger.error('OranNotificationMessage.fill_from_netconf_message() not implemented')


class OranRpcReplyMessage(OranMessage):
    def __init__(self, netconf_message: NetconfMessageDefs.RpcReplyMessage):
        super(OranRpcReplyMessage, self).__init__(netconf_message)
        self.category = 'RU'

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
