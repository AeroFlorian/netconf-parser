import MessageParser
import Display
from Logger import logger
import traceback
from tkinter import ttk

if __name__ == '__main__':
    # filepath = r'C:\Users\fsalaun\Downloads\MRBTS-_1.LOG'
    # with open(filepath, 'r') as file:
    #     data = file.read()
    # parser = MessageParser.NetConfParser(data)
    # parser.parse()
    # parser.display()
    try:
        window = Display.NetConfParserWindow()

        # end workaround
        window.mainloop()
    except Exception as e:
        logger.error("Exception Caught!")
        for l in traceback.format_exc().splitlines():
            logger.error(l)