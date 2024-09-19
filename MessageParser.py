import NetconfMessageDefs
import OranMessageDefs
import LineRemover
import re
from Logger import logger


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

    def display(self):
        logger.info('************** OranAnalysisTree: **************')
        for message in self.analysis_messages:
            logger.info(message)


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


class RegexToNetconfMessage:
    def __init__(self, match):
        self.match = match

    def to_netconf_message(self):
        if self.match[0] != '':
            return NetconfMessageDefs.RpcMessage(int(self.match[0]), self.match[1])
        elif self.match[2] != '':
            return NetconfMessageDefs.RpcReplyMessage(int(self.match[2]), self.match[3])
        elif self.match[4] != '':
            return NetconfMessageDefs.NotificationMessage(self.match[4])
        elif self.match[5] != '':
            return NetconfMessageDefs.HelloMessage(self.match[5])
        else:
            logger.error('RegexToNetconfMessage.to_netconf_message() not implemented')
            return None


class NetConfParser:
    def __init__(self, data: str):
        self.data = data
        self.trees = Trees()

    def parse(self):
        filtered_lines = LineRemover.LineRemover().remove_unwanted_parts(self.data)
        reg = r'<rpc .*? message-id=.(\d+).>(.*?)</rpc>|' \
              r'<rpc-reply .*? message-id=.(\d+).>(.*?)</rpc-reply>|' \
              r'<notification .*?/eventTime>(.*?)</notification>|' \
              r'<hello xmlns=\".*?\">(.*?)</hello>'

        all_matches = re.findall(reg, filtered_lines, re.MULTILINE | re.DOTALL)
        for match in all_matches:
            message = RegexToNetconfMessage(match).to_netconf_message()
            self.trees.handle_message(message)
        self.trees.apply_after_computation_tags()
        return

    def display(self):
        self.trees.display()