import re


class GenericUtilities:
    @classmethod
    def get_value_if_exists_recurse(self, dic: dict, key: str) -> str:
        for (k, v) in dic.items():
            if k == key:
                return v
            elif isinstance(v, dict):
                val = self.get_value_if_exists_recurse(v, key)
                if val is not None:
                    return val
        return ""

    @classmethod
    def get_all_values_for_key_recurse(self, dic: dict, key: str, values: list) -> list:
        for (k, v) in dic.items():
            if k == key:
                values.append(v)
            elif isinstance(v, dict):
                self.get_all_values_for_key_recurse(v, key, values)
        return values

    @classmethod
    def check_value_if_exists_recurse(self, dic: dict, value: str) -> bool:
        for (k, v) in dic.items():
            if v == value:
                return True
            elif isinstance(v, dict):
                return self.check_value_if_exists_recurse(v, value)
        return False

    @classmethod
    def get_value_as_list(self, value: object) -> list:
        if len(value) > 0 and type(value) is not list:
            return [value]
        return value


class OranSpecificUtilities:

    @classmethod
    def display_list_tech(self, l: object) -> str:
        if type(l) is not list:
            l = [l]
        return " + ".join([str(x) for x in l])

    @classmethod
    def compute_cell_id(self, dn: str) -> int:
        pattern = r".*?\.[A-Za-z]+(\d+).*"
        match = re.match(pattern, dn)
        if match:
            return int(match.group(1))
        return -1

    @classmethod
    def get_supported_techs(self, array, direction):
        try:
            return self.display_list_tech(array["capabilities"][f"supported-technology-{direction}"])
        except:
            return ""