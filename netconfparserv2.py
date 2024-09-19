import MessageParser
from Logger import logger


if __name__ == '__main__':
    filepath = r'C:\Users\fsalaun\Downloads\MRBTS-_1.LOG'
    with open(filepath, 'r') as file:
        data = file.read()
    parser = MessageParser.NetConfParser(data)
    parser.parse()
    parser.display()
