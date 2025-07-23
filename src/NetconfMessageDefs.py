from enum import Enum
from Logger import logger
import re
import xmltodict
import TimestampComputer


class MessageType(Enum):
    HELLO = 0
    RPC = 1
    RPC_REPLY = 2
    NOTIFICATION = 3


class Tag(Enum):
    RPC = 0
    RPC_WITHOUT_COUNTERPART = 1
    RPC_REPLY = 2
    NOTIFICATION = 3
    HELLO = 4
    SCHEMA = 5
    NOTIFICATION_NETCONF_CONFIG_CHANGE = 6
    RPC_ERROR = 7


class Direction(Enum):
    TO_SERVER = 0
    TO_CLIENT = 1
    UNKNOWN = 2


class Message:
    def __init__(self, message_id: str, message_type: MessageType, tag: Tag, direction: Direction):
        self.message_type: MessageType = message_type
        self.message_id: str = message_id
        self.raw_data: str = ""
        self.summary: str = ""
        self.tag: Tag = tag
        self.direction: Direction = direction
        self.data: dict = {}
        self.timestamp: str = self.get_timestamp()

    def __str__(self):
        return f'{self.message_type.name} id {self.message_id} tag {self.tag} summary {self.summary} '

    def get_values(self):
        return (
            self.timestamp,
            self.message_id if self.message_id else "N/A",
            "<-" if self.direction == Direction.TO_CLIENT else "->",
            self.message_type.name.lower(),
            f"\t\t{self.summary}",
            "",
            self.raw_data
        )

    def fill_fields(self, data: str):
        logger.error('Message.fill_fields() not implemented')
        return

    @staticmethod
    def remove_unwanted_parts(data: str):
        data = re.sub(r'} {', '', data, flags=re.DOTALL)
        data = re.sub(r'\n', '', data, flags=re.DOTALL)
        return data

    def received_reply(self):
        logger.error('Message.receive_reply() not implemented')

    def get_timestamp(self):
        return ""


class RpcMessage(Message):
    def __init__(self, message_id: str, data: str, timestampcomputer: TimestampComputer.TimestampComputer):
        super(RpcMessage, self).__init__(message_id, MessageType.RPC, Tag.RPC_WITHOUT_COUNTERPART, Direction.TO_SERVER)
        self.fill_fields(data)
        self.timestamp = timestampcomputer.get_timestamp(self.message_id)

    def get_edit_config_summary(self, data):
        modules = ''.join(self.data['edit-config']['config'].keys())
        table = {}
        for module in self.data['edit-config']['config'].keys():
            for object in self.data['edit-config']['config'][module]:
                if isinstance(self.data['edit-config']['config'][module][object], list):
                    for object_list in self.data['edit-config']['config'][module][object]:
                        if "operation" in object_list:
                            if object not in table:
                                table[object] = {}
                            if object_list["operation"] not in table[object]:
                                table[object][object_list["operation"]] = 0
                            table[object][object_list["operation"]] += 1
                        else:
                            if object not in table:
                                table[object] = {}
                            if " " not in table[object]:
                                table[object][" "] = 0
                            table[object][" "] += 1
                elif "operation" in self.data['edit-config']['config'][module][object]:
                    if object not in table:
                        table[object] = {}
                    if self.data['edit-config']['config'][module][object]["operation"] not in table[object]:
                        table[object][self.data['edit-config']['config'][module][object]["operation"]] = 0
                    table[object][self.data['edit-config']['config'][module][object]["operation"]] += 1
                else:
                    if object not in table and object != "operation":
                        table[object] = {}
                    if " " not in table[object]:
                        table[object][" "] = 0
                    table[object][" "] += 1
        summary = f"edit-config {modules} | "
        operations = []
        for object in table:
            for operation in table[object]:
                operation_str = f'{operation}d ' if len(operation)>1 else 'created/modified '
                operations.append(f"{table[object][operation]} {operation_str}{object}")
        return summary + " | ".join(operations)

    def fill_fields(self, data: str):
        self.raw_data = self.remove_unwanted_parts(f'<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{data}</rpc>')
        data = re.sub(r' nc:operation=\"([^\"]+)\">', r"><operation>\1</operation>", data)
        data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)
        data = re.sub('\n', '', data)
        self.data = xmltodict.parse(self.remove_unwanted_parts(data))
        if "get-schema" in self.raw_data:
            self.tag = Tag.SCHEMA
            self.summary = f"get-schema {self.data['get-schema']['identifier']}"
        elif "get" in self.data:
            try:
                self.summary = f"get {'|'.join(self.data['get']['filter'].keys())}"
            except:
                self.summary = "get"
        elif "edit-config" in self.data:
            try:
                self.summary = self.get_edit_config_summary(self.data)
            except:
                self.summary = "edit-config"
        else:
            self.summary = f"rpc {''.join(self.data.keys())}"

    def received_reply(self):
        if self.tag == Tag.RPC_WITHOUT_COUNTERPART:
            self.tag = Tag.RPC


class RpcReplyMessage(Message):
    def __init__(self, message_id: str, data: str, timestampcomputer: TimestampComputer.TimestampComputer):
        super(RpcReplyMessage, self).__init__(message_id, MessageType.RPC_REPLY, Tag.RPC_REPLY, Direction.TO_CLIENT)
        self.fill_fields(data)
        self.timestamp = timestampcomputer.get_timestamp(self.message_id)

    def fill_fields(self, data: str):
        self.raw_data = self.remove_unwanted_parts(f'<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{data}</rpc-reply>')
        if len(data) < 10000 and "rpc-error" in data:
            data = f"<rpc-error>{data}</rpc-error>"
            self.tag = Tag.RPC_ERROR
        else:
            data = f"<rpc-reply>{data}</rpc-reply>"
        data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)
        data = re.sub(r'^.*?<', '<', data, flags=re.DOTALL)
        data = re.sub(r'>[^>]*?$', '>', data, flags=re.DOTALL)
        self.data = xmltodict.parse(self.remove_unwanted_parts(data))
        try:
            if "data" in self.data['rpc-reply'] and len(self.data['rpc-reply']['data']) < 100:
                self.summary = f"rpc-reply data {' | '.join(self.data['rpc-reply']['data'].keys())}"
            else:
                self.summary = f"rpc-reply {' '.join(self.data['rpc-reply'].keys())}"
        except:
            pass


class NotificationMessage(Message):
    def __init__(self, data: str, timestampcomputer: TimestampComputer.TimestampComputer):
        super(NotificationMessage, self).__init__("N/A", MessageType.NOTIFICATION, Tag.NOTIFICATION, Direction.TO_CLIENT)
        self.fill_fields(data)
        self.timestamp = timestampcomputer.get_timestamp("notification")

    def fill_fields(self, data: str):
        self.raw_data = self.remove_unwanted_parts(
            f'<notification xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{data}</notification>')
        if "netconf-config-change" in data:
            self.tag = Tag.NOTIFICATION_NETCONF_CONFIG_CHANGE
        data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)
        self.data = xmltodict.parse(self.remove_unwanted_parts(data))
        self.summary = f"notification {''.join(self.data.keys())}"



class HelloMessage(Message):
    def __init__(self, data: str):
        super(HelloMessage, self).__init__("0", MessageType.HELLO, Tag.HELLO, Direction.UNKNOWN)
        self.fill_fields(data)

    def fill_fields(self, data: str):
        self.raw_data = self.remove_unwanted_parts(
            f'<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{data}</hello>')
        data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)
        data = re.sub(r'<session-id.*/session-id>', '', data)
        self.data = xmltodict.parse(self.remove_unwanted_parts(data))
        capas = set()
        capabilities = list(self.data["capabilities"].values())
        if type(capabilities[0]) is list:
            capabilities = capabilities[0]
        for capa in capabilities:
            if "urn:ietf:params:netconf:base:" in capa:
                capas.add(capa.split(":")[-1])
        self.summary = f"Netconf Version Supported {', '.join(capas)}"


class EmptyNetconfMessage(Message):
    def __init__(self):
        super(EmptyNetconfMessage, self).__init__("0", MessageType.HELLO, Tag.HELLO, Direction.UNKNOWN)
