import sys

def is_dev_mode() -> bool:
    """Check if the application is running in development mode.

    It does that by checking a specific attribute which is only there when running in a bundled app by pyinstaller
    """
    return not hasattr(sys, '_MEIPASS')