import logging
import logging.handlers


class Logger:
    def __init__(self, logger_name,
                 logfile=None,
                 verbose=False):
        self.logger = logging.getLogger(logger_name)
        if len(self.logger.handlers) != 0:
            return
        self.logger.setLevel(logging.DEBUG)
        if verbose == True:
            self.enableVerbose()
        self.addFileHandler(logfile)

    def enableVerbose(self):
        for hdlr in self.logger.handlers:
            if type(hdlr) == logging.StreamHandler:
                hdlr.setLevel(logging.INFO)
                return
        stdout_handler = logging.StreamHandler()
        stdout_formatter = logging.Formatter(
            '%(levelname)s %(name)s: %(message)s')
        stdout_handler.setFormatter(stdout_formatter)
        stdout_handler.setLevel(logging.INFO)
        self.logger.addHandler(stdout_handler)

    def disableVerbose(self):
        for hdlr in self.logger.handlers:
            if type(hdlr) == logging.StreamHandler:
                hdlr.setLevel(logging.CRITICAL+1)

    def addFileHandler(self, logfile, level=logging.DEBUG):
        if logfile != None:
            handler = logging.handlers.RotatingFileHandler(logfile,
                                                           maxBytes=52444160,
                                                           backupCount=3)
            handler.setLevel(level)
            formatstr = ('%(asctime)s %(levelname)s %(filename)s: %(message)s')
            formatter = logging.Formatter(formatstr)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def getLogger(self):
        return self.logger


logger = Logger('Logger', None, True).getLogger()
