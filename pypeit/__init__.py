"""
pypeit package initialization.

The current main purpose of this is to provide package-level globals
that can be imported by submodules.
"""

# Imports for signal and log handling
import os
import sys
import signal

from .version import version

# Set version
__version__ = version

# Report current coverage
# TODO: How old is this?  Can we update it automatically?
__coverage__ = 0.55

import logging
from pypeit import logger
msgs = logger.get_logger(level=logging.DEBUG)
# Import all the exceptions
from pypeit.exceptions import *

# Import and instantiate the data path parser
# NOTE: This *MUST* come after msgs and __version__ are defined above
from pypeit import pypeitdata
dataPaths = pypeitdata.PypeItDataPaths()

# Send all signals to messages to be dealt with (i.e. someone hits ctrl+c)
def signal_handler(signalnum, handler):
    """
    Handle signals sent by the keyboard during code execution
    """
    if signalnum == 2:
        msgs.info('Ctrl+C was pressed. Ending processes...')
        sys.exit()

signal.signal(signal.SIGINT, signal_handler)

