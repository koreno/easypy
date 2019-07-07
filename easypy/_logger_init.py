"""
Here we provide a temporary logger object for all of easypy's module, which will get redirected
to either a logging or logbook Logger, once we've called easypy.logging.initialize()
"""

import logging
from easypy.aliasing import aliases


@aliases("logger")
class DeferredEasypyLogger():
    logger = logging.Logger("easypy")

    # once easypy.logging is initialized, this will point to a function that will instantiate a proper EasypyLogger
    _get_logger = None

    def __init__(self, name):
        self.name = name
        if self._get_logger:
            self.logger = self._get_logger(name)
