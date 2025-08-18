import NetconfMessageDefs
import OranMessageDefs
import LineRemover
import re
from Logger import logger
import TimestampComputer

class NetconfSession:
    def __init__(self):
        self.messages: list = []

    def append_message(self, message: NetconfMessageDefs.Message):
        self.messages.append(message)

    def apply_messages_without_counterpart(self):
        id_to_message_id = {}
        for index, message in enumerate(self.messages):
            if message.message_type == NetconfMessageDefs.MessageType.RPC:
                if message.message_id in id_to_message_id:
                    logger.warning('Multiple RPCs with the same message Id')
                id_to_message_id[message.message_id] = index
            elif message.message_type == NetconfMessageDefs.MessageType.RPC_REPLY:
                if message.message_id in id_to_message_id:
                    rpc_message_id = id_to_message_id.pop(message.message_id)
                    self.messages[rpc_message_id].received_reply()
                else:
                    logger.warning('RPC reply without counterpart')


class ResultTree:
    def __init__(self):
        self.netconf_sessions: list = []
        self.add_netconf_session()

    def add_netconf_session(self):
        self.netconf_sessions.append(NetconfSession())

    def add_message(self, message: NetconfMessageDefs.Message):
        self.netconf_sessions[-1].append_message(message)

    def display(self):
        logger.info('************** ResultTree: **************')
        for index, netconf_session in enumerate(self.netconf_sessions):
            logger.info(f'************** NetconfSession {index + 1}: **************')
            for message in netconf_session.messages:
                logger.info(message)

    def apply_messages_without_counterpart(self):
        for netconf_session in self.netconf_sessions:
            netconf_session.apply_messages_without_counterpart()

    def get_messages(self):
        messages = []
        for session in self.netconf_sessions:
            messages += session.messages
        return messages


class OranAnalysisTree:
    def __init__(self):
        self.analysis_messages: list = []

    def add_netconf_session(self):
        self.analysis_messages.append(OranMessageDefs.NetconfClientConnectedMessage())

    def add_message(self, message: NetconfMessageDefs.Message):
        if message.message_type == NetconfMessageDefs.MessageType.RPC:
            oran_message = OranMessageDefs.OranRpcMessage(message)
        elif message.message_type == NetconfMessageDefs.MessageType.RPC_REPLY:
            oran_message = OranMessageDefs.OranRpcReplyMessage(message)
        elif message.message_type == NetconfMessageDefs.MessageType.NOTIFICATION:
            oran_message = OranMessageDefs.OranNotificationMessage(message)
        else:
            return
        if oran_message.should_be_present_in_analysis():
            self.analysis_messages.append(oran_message)

    def check_message_counterpart(self):
        for message in self.analysis_messages:
            message.check_without_counterpart()
        self.analysis_messages = [ message for message in self.analysis_messages if message.should_be_present_in_analysis()]


    def display(self):
        logger.info('************** OranAnalysisTree: **************')
        for message in self.analysis_messages:
            logger.info(message)

    def get_messages(self):
        return self.analysis_messages

class Trees:
    def __init__(self):
        self.result_tree: ResultTree = ResultTree()
        self.analysis_tree: OranAnalysisTree = OranAnalysisTree()
        self.previous_message_type = None

    def handle_message(self, message: NetconfMessageDefs.Message):
        if self.previous_message_type != NetconfMessageDefs.MessageType.HELLO \
                and message.message_type == NetconfMessageDefs.MessageType.HELLO:
            self.result_tree.add_netconf_session()
            self.analysis_tree.add_netconf_session()
        self.previous_message_type = message.message_type
        self.result_tree.add_message(message)
        self.analysis_tree.add_message(message)

    def display(self):
        #self.result_tree.display()
        self.analysis_tree.display()

    def apply_after_computation_tags(self):
        self.result_tree.apply_messages_without_counterpart()
        self.analysis_tree.check_message_counterpart()


class NetConfParser:
    def __init__(self, data: str):
        self.data = data
        self.trees = Trees()
        self.timestamp_computer = TimestampComputer.TimestampComputer()

    def parse(self):
        self.timestamp_computer.parse(self.data)
        filtered_lines = LineRemover.LineRemover().remove_unwanted_parts(self.data)

        # logger.info(f"Filtered lines: {filtered_lines}")

        reg = r'(<rpc-reply[\s\S]*?</rpc-reply>)|(<notification[\s\S]*?</notification>)|(<hello[\s\S]*?</hello>)|(<rpc[\s\S]*?</rpc>)|'
        all_matches = re.findall(reg, filtered_lines, re.MULTILINE | re.DOTALL)
        # logger.info(f"All matches: {all_matches}")

        for match_tuple in all_matches:
            # Only one group will be non-empty per match
            xml_str = next((m for m in match_tuple if m), None)
            if not xml_str:
                continue
            try:
                message = NetconfMessageDefs.Message.from_xml(xml_str, self.timestamp_computer)
                self.trees.handle_message(message)
            except Exception as e:
                logger.exception(f"Failed to parse message: {xml_str}")
        self.trees.apply_after_computation_tags()
        return

    def display(self):
        self.trees.display()

    def get_netconf_messages(self):
        return self.trees.result_tree.get_messages()

    def get_oran_messages(self):
        return self.trees.analysis_tree.get_messages()