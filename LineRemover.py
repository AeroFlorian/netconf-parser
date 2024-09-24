import re
from Logger import logger


class LineRemoverRule:
    def __init__(self):
        pass

    def apply(self, full_lines: str):
        logger.error("LineRemoverRule.apply() not implemented")
        pass


class LineRemoverRegexRule(LineRemoverRule):
    def __init__(self, condition: str, pattern: str, replacement: str):
        super(LineRemoverRegexRule, self).__init__()
        self.condition = condition
        self.pattern = pattern
        self.replacement = replacement

    def apply(self, full_lines: str):
        if self.condition in full_lines:
            return re.sub(self.pattern, self.replacement, full_lines)
        return full_lines


class LineRemoverLogicRule(LineRemoverRule):
    def __init__(self, condition: str, logic):
        super(LineRemoverLogicRule, self).__init__()
        self.condition = condition
        self.logic = logic

    def apply(self, full_lines: str):
        if self.condition in full_lines:
            return self.logic(full_lines)
        return full_lines


class LineRemover:
    def __init__(self):
        self.rules = [
            LineRemoverLogicRule("830 for SSH connections",
                                 lambda x: "\n".join([line for line in x.split("\n") if ">" in line or "<" in line])),
            LineRemoverRegexRule("Session 0: Sending message",
                                 r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z Dbg: .*? Session \d+: (?:Sending|Received) message:",
                                 ""),
            LineRemoverRegexRule("Sending",
                                 r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{7} INF (?:Sending|Received) message: ", "")]

    def remove_unwanted_parts(self, full_lines: str):
        for rule in self.rules:
            full_lines = rule.apply(full_lines)
        return full_lines
