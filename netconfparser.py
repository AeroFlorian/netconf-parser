import Display
from Logger import logger
import traceback

if __name__ == '__main__':

    try:
        window = Display.NetConfParserWindow()
        window.mainloop()
    except Exception as e:
        logger.error("Exception Caught!")
        for l in traceback.format_exc().splitlines():
            logger.error(l)