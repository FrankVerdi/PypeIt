
import io
import logging
import re
import sys
import warnings

from IPython import embed
import pytest

from pypeit import log
from pypeit import PypeItError

def test_basic():

    embed()
    exit()

    warnings.warn('test')

    ansi_escape = re.compile(r'\x1b[^m]*m')

    # Test the different levels
    logst = io.StringIO()
    log.init(level=logging.DEBUG, stream=logst)

    log.debug('test')
    log.info('test')
    log.warning('test')
    log.error('test')
    log.critical('test')
    
    msg = logst.getvalue()
    msg = ansi_escape.sub("", msg).split('\n')

    embed()
    exit()
    log.info('test')
    log.warning('test')

    _stdout = sys.stdout
    _stderr = sys.stderr
    cap_out = io.StringIO()
    cap_err = io.StringIO()
    sys.stdout = cap_out
    sys.stderr = cap_err

    log.init(level=logging.DEBUG)
    log.debug('test')
    sys.stdout = _stdout
    sys.stderr = _stdout

    embed()
    exit()

    log.info('test')
    log.warning('test')
    log.error('test')
    log.critical('test')
    warnings.warn('test')

    with pytest.raises(ValueError):
        raise ValueError('test')
    with pytest.raises(PypeItError):
        raise PypeItError('test')
    
    sys.stdout = _stdout

    
test_basic()
