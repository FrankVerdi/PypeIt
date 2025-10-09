"""
PypeIt logging

Implementation heavily references loggers from astropy and sdsstools.
"""

import traceback
import copy
import inspect
import logging
from pathlib import Path
import re
import sys
from typing import Optional

from IPython import embed

import warnings

#def short_warning(message, category, filename, lineno, file=None, line=None):
#    """
#    Return the format for a short warning message.
#    """
#    embed()
#    exit()
#    return f'{category.__name__}: {message}'
#
#warnings.formatwarning = short_warning

# NOTE: This is essentially a hack to deal with all the RankWarnings that numpy
# can throw during polynomial fitting.  Specifically this happens frequently
# in pypeit.core.fitting.PypeItFit.fit.  We should instead determine why these
# rank warnings are happening and address the root cause!
# 'default' means: "print the first occurrence of matching warnings for each
# location (module + line number) where the warning is issued"
# See: https://docs.python.org/3/library/warnings.html#warning-filter
import numpy as np
warnings.simplefilter('default', np.exceptions.RankWarning)


#WARNING_RE = re.compile(r"^.*?\s*?(\w*?Warning): (.*)")


def color_text(text, color, bold=False, nchar=None):
    msg = '\033[1;' if bold else '\033['
    _text = f'{text}' if nchar is None else f'{text:>{nchar}}'
    return f'{msg}38;2;{color[0]};{color[1]};{color[2]}m{_text}\033[0m'


class StreamFormatter(logging.Formatter):
    """
    Custom `Formatter <logging.Formatter>` for the stream handler.
    """

    base_level = None

    def format(self, record):

        level_colors = {
            'debug': [116, 173, 209],
            'info': [49, 54, 149],
            'warning': [253, 174, 97],
            'error': [215, 48, 39],
            'critical': [165, 0, 38],
        }
        inspect_color = level_colors['debug']

        rec = copy.copy(record)
        levelname = rec.levelname.lower()
        if levelname not in level_colors:
            # Unknown level name so default to the standard formatter
            return logging.Formatter.format(self, record)

        # Add the level in colored text
        msg = color_text(f'[{levelname.upper()}]', level_colors[levelname], bold=True, nchar=10)
        msg += ' - '
        if self.base_level == logging.DEBUG:
            # If including debug messages, include file inspection in *all* log
            # messages.
            msg += color_text(f'{rec.filename}:{rec.funcName}:{rec.lineno}', inspect_color) + ' - '
        # Add the message header
        rec.msg = msg + rec.msg

# NOTE: This is in the sdsstools looger, but I'm not sure what it does.  I have
# commented it out for the moment, but we may want to bring it back.
#        if levelname == "warning" and rec.args and len(rec.args) > 0:
#            warning_category_groups = WARNING_RE.match(rec.args[0])
#            if warning_category_groups is not None:
#                wcategory, wtext = warning_category_groups.groups()
#                wcategory_colour = color_text(wcategory, level_colors['warning'])
#                message = f'{color_text(wtext, [256, 256, 256])}' + wcategory_colour
#                rec.args = tuple([message] + list(args[1:]))

        # Return the base formatting
        return logging.Formatter.format(self, rec)


class DebugStreamFormatter(StreamFormatter):
    """
    Set the base logging level to DEBUG
    """
    base_level = logging.DEBUG


class FileFormatter(logging.Formatter):
    """
    Custom `Formatter <logging.Formatter>` for the file handler.
    """

    base_fmt = "%(levelname)8s | %(asctime)s | %(filename)s:%(funcName)s:%(lineno)s | %(message)s"
#    ansi_escape = re.compile(r'\x1b[^m]*m')

    def __init__(self, fmt=base_fmt):
        logging.Formatter.__init__(self, fmt, datefmt='%Y-%m-%d %H:%M:%S')

#    def format(self, record):
#        # Copy the record so that any modifications we make do not
#        # affect how the record is displayed in other handlers.
#        record_cp = copy.copy(record)
#
#        record_cp.msg = self.ansi_escape.sub("", record_cp.msg)
#
#        # TODO: Pulled this from sdsstools, but I'm not sure if it's still
#        # relevant
#        args = list(record_cp.args)
#
#        # The format of a warnings redirected with warnings.captureWarnings
#        # has the format <path>: <category>: message\n  <some-other-stuff>.
#        # We reorganise that into a cleaner message. For some reason in this
#        # case the message is in record.args instead of in record.msg.
#        if (
#            record_cp.levelno == logging.WARNING
#            and record_cp.args
#            and len(record_cp.args) > 0
#        ):
#            match = re.match(r"^(.*?):\s*?(\w*?Warning): (.*)", args[0])
#            if match:
#                message = "{1} - {2} [{0}]".format(*match.groups())
#                record_cp.args = tuple([message] + list(args[1:]))
#
#        return logging.Formatter.format(self, record_cp)

class PypeItLogger(logging.Logger):
    """
    Custom logging system for pypeit.

    This borrows heavily from implementations in astropy and sdsstools.
    """
    _excepthook_orig = None

    def init(self,
        level: int = logging.INFO,
        capture_exceptions: bool = True,
        capture_warnings: bool = True,
        stream = None,
        log_file: Optional[str | Path] = None,
        log_file_level: Optional[int] = None,
    ):
        """
        Initialise the logger.

        Parameters
        ----------
        level
            The logging level printed to the console
        capture_exceptions
            Override the exception hook and redirect all exceptions to the
            logging system.
        capture_warnings
            Capture warnings and redirect them to the log.
        log_file
            Name for a log file.  If None, logging is only recorded to the
            console.  If the file provided already exists, it will be
            ovewritten!
        log_file_level
            The logging level specific to the log file.  If None, adopt the
            console logging level.
        """
        self.warnings_logger = logging.getLogger("py.warnings")

        embed()
        exit()

        self.setLevel(logging.DEBUG)

        # Clear handlers before recreating.
        for handler in self.handlers.copy():
            if handler in self.warnings_logger.handlers:
                # Remove any added to the warnings logger
                self.warnings_logger.removeHandler(handler)
            self.removeHandler(handler)

        # Reset the exception hook (only if it was reset by this logger)
        if self._excepthook_orig is not None and sys.excepthook == self._excepthook:
            sys.excepthook = self._excepthook_orig
            self._excepthook_orig = None

        # Catch and parse exceptions
        if capture_exceptions:
            self._excepthook_orig = sys.excepthook
            sys.excepthook = self._excepthook

        # Set the stream handler
        self.sh = logging.StreamHandler(stream=stream)
        formatter = DebugStreamFormatter() if level <= logging.DEBUG else StreamFormatter()
        self.sh.setFormatter(formatter)
        self.sh.setLevel(level)
        self.addHandler(self.sh)

        if capture_warnings:
            logging.captureWarnings(True)

            # Only enable the sh handler if none is attached to the warnings
            # logger yet. Prevents duplicated prints of the warnings.
            for handler in self.warnings_logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    return

            self.warnings_logger.addHandler(self.sh)

        # Get the file handler
        if log_file is None:
            self.fh = None
            self.log_filename = None
        else:
            if log_file_level is None:
                log_file_level = level
            self.log_file = Path(log_file).absolute()
            self.fh = logging.FileHandler(str(self.log_file), mode='w')
            self.fh.setFormatter(FileFormatter())
            self.fh.setLevel(log_file_level)
            self.addHandler(self.fh)

            if self.warnings_logger:
                self.warnings_logger.addHandler(self.fh)

    def _excepthook(self, etype, value, trace):
        """
        Override the default exception hook to log an error message.
        """
        tb = trace
        if tb is None:
            exc_info = None
        else:
            # If the traceback is available, jump to the calling frame, which
            # gets passed to makeRecord
            while tb.tb_next:
                tb = tb.tb_next
            exc_info = (etype, value, tb)

        # Add the error type to the message.
        if len(value.args) > 0:
            message = f"{etype.__name__}: {str(value)}"
        else:
            message = str(etype.__name__)

        # Log the error
        self.error(message, exc_info=exc_info)

        # Call the original exception hook
        self._excepthook_orig(etype, value, trace)

    def makeRecord(
            self, name, level, pathname, lineno, msg, args, exc_info, func=None, extra=None,
            sinfo=None
    ):
        """
        Override the default makeRecord function to rework the message for exceptions.
        """

        embed()
        exit()

        # If this is an error message, the execution information is provided,
        # and the error originates from the exception hook, reset the frame
        # information (file, function, and line number) to the calling function.
        if (level == logging.ERROR
            and exc_info is not None
            and Path(pathname).name == 'logger.py'
            and func is not None
            and func == '_excepthook'
        ):
            calling_frame = traceback.extract_tb(exc_info[2])[-1]
            pathname = calling_frame.filename
            lineno = calling_frame.lineno
            func = calling_frame.name
            # This keeps the traceback from being printed twice!
            exc_info = None
        return logging.Logger.makeRecord(
            self, name, level, pathname, lineno, msg, args, exc_info, func=func, extra=extra,
            sinfo=sinfo
        )

def get_logger(
    level: int = logging.INFO,
    capture_exceptions: bool = True,
    capture_warnings: bool = True,
    log_file: Optional[str | Path] = None,
    log_file_level: Optional[int] = None,
):
    """
    Instantiate a new logger.

    Parameters
    ----------
    level
        The logging level printed to the console
    capture_exceptions
        Override the exception hook and redirect all exceptions to the
        logging system.
    capture_warnings
        Capture warnings and redirect them to the log.
    log_file
        Name for a log file.  If None, logging is only recorded to the
        console.  If the file provided already exists, it will be
        ovewritten!
    log_file_level
        The logging level specific to the log file.  If None, adopt the
        console logging level.
    """

    orig_logger = logging.getLoggerClass()
    logging.setLoggerClass(PypeItLogger)

    try:
        log = logging.getLogger("pypeit")
        log.init(
            level=level,
            capture_exceptions=capture_exceptions,
            capture_warnings=capture_warnings,
            log_file=log_file,
            log_file_level=log_file_level
        )
    finally:
        logging.setLoggerClass(orig_logger)

    return log
