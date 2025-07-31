import re
from collections import defaultdict

class TimestampComputer:
    def __init__(self):
        self.timestampregex = [r'(\d{2}:\d{2}:\d{2}\.\d+)']
        self.message_ids_regex = [r'message-id=\"([a-z0-9\:\-]+)\"', r'<(notification) ']
        self.message_id_to_timestamp = defaultdict(list)


    def parse(self, lines):
        reg = '|'.join(list(self.timestampregex + self.message_ids_regex))
        all_matches = re.findall(reg, lines, re.DOTALL)
        last_timestamp = ""
        for index, match in enumerate(all_matches):
            if match[0]:
                last_timestamp = match[0]
            if match[1]:
                self.message_id_to_timestamp[match[1]].append(last_timestamp)
            if match[2]:
                self.message_id_to_timestamp[match[2]].append(last_timestamp)


    def get_timestamp(self, message_id: str):
        if message_id in self.message_id_to_timestamp:
            if self.message_id_to_timestamp[message_id]:
                return self.message_id_to_timestamp[message_id].pop(0)
        return "No timestamp"
