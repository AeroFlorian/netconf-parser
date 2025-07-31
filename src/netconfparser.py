import Display
from Logger import logger
import traceback

def main():
    try:
        window = Display.NetConfParserWindow()
        window.mainloop()
    except Exception as e:
        logger.error("Exception Caught!")
        for l in traceback.format_exc().splitlines():
            logger.error(l)

if __name__ == '__main__':
    main()