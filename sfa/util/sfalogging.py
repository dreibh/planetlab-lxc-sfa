#!/usr/bin/python

"""
A reroutable logger that can handle deep tracebacks

Requirements:

* for legacy, we want all our code to just do:

    from sfa.util.sfalogging import logger
    ...
    logger.info('blabla')

* depending on whether the code runs (a) inside the server,
  (b) as part of sfa-import, or (c) as part of the sfi CLI,
  we want these messages to be directed in different places

* also because troubleshooting is very painful, we need a better way
  to report stacks when an exception occurs.

Implementation:

* we use a single unique logger name 'sfa' (wrt getLogger()),
  and provide an auxiliary function `init_logger()` that
  accepts for its `context` parameter one of :
  `server`, `import` `sfi` or `console`
  It will then reconfigure the 'sfa' logger to do the right thing

* also we create our own subclass of loggers, and install it
  with logging.setLoggerClass(), so we can add our own customized
  `log_exc()` method

"""

# pylint: disable=c0111, c0103, w1201

from __future__ import print_function

import os
import os.path
import sys
import traceback
import logging
import logging.handlers
import logging.config

# so that users of this module don't need to import logging
from logging import (CRITICAL, ERROR, WARNING, INFO, DEBUG)


class SfaLogger(logging.getLoggerClass()):
    """
    a rewrite of  old _SfaLogger class that was way too cumbersome
    keep this as much as possible though
    """

    # shorthand to avoid having to import logging all over the place
    def setLevelDebug(self):
        self.setLevel(DEBUG)

    def debugEnabled(self):
        return self.getEffectiveLevel() == logging.DEBUG

    # define a verbose option with s/t like
    # parser.add_option("-v", "--verbose", action="count",
    #                   dest="verbose", default=0)
    # and pass the coresponding options.verbose to this method to adjust level
    def setLevelFromOptVerbose(self, verbose):
        if verbose == 0:
            self.setLevel(logging.WARNING)
        elif verbose == 1:
            self.setLevel(logging.INFO)
        elif verbose >= 2:
            self.setLevel(logging.DEBUG)

    # in case some other code needs a boolean
    @staticmethod
    def getBoolVerboseFromOpt(verbose):
        return verbose >= 1

    @staticmethod
    def getBoolDebugFromOpt(verbose):
        return verbose >= 2

    def log_exc(self, message, limit=100):
        """
        standard logger has an exception() method but this will
        dump the stack only between the frames
        (1) that does `raise` and (2) the one that does `except`

        log_exc() has a limit argument that allows to see deeper than that

        use limit=None to get the same behaviour as exception()
        """
        self.error("%s BEG TRACEBACK" % message + "\n" +
                   traceback.format_exc(limit=limit).strip("\n"))
        self.error("%s END TRACEBACK" % message)

    # for investigation purposes, can be placed anywhere
    def log_stack(self, message, limit=100):
        to_log = "".join(traceback.format_stack(limit=limit))
        self.info("%s BEG STACK" % message + "\n" + to_log)
        self.info("%s END STACK" % message)

    def enable_console(self):
        formatter = logging.Formatter("%(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.addHandler(handler)


# install our class as the default
logging.setLoggerClass(SfaLogger)


# configure
# this is *NOT* passed to dictConfig as-is
# instead we filter 'handlers' and 'loggers'
# to contain just one entry
# so make sure that 'handlers' and 'loggers'
# have the same set of keys
def logging_config(context):
    if context == 'server':
        handlername = 'file'
        filename = '/var/log/sfa.log'
        level = 'INFO'
    elif context == 'import':
        handlername = 'file'
        filename = '/var/log/sfa-import.log'
        level = 'INFO'
    elif context == 'cli':
        handlername = 'file'
        filename = os.path.expanduser("~/.sfi.log")
        level = 'DEBUG'
    elif context == 'console':
        handlername = 'stdout'
        filename = 'ignored'
        level = 'INFO'
    else:
        print("Cannot configure logging - exiting")
        exit(1)

    return {
        'version': 1,
        # IMPORTANT: we may be imported by something else, so:
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'datefmt': '%m-%d %H:%M:%S',
                'format': ('%(asctime)s %(levelname)s '
                           '%(filename)s:%(lineno)d %(message)s'),
            },
        },
        'handlers': {
            'file': {
                'filename': filename,
                'level': level,
                # not using RotatingFileHandler for this first version
                'class': 'logging.FileHandler',
                'formatter': 'standard',
            },
            'stdout': {
                'level': level,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
        },
        'loggers': {
            'sfa': {
                'handlers': [handlername],
                'level': level,
                'propagate': False,
            },
        },
    }


logger = logging.getLogger('sfa')


def init_logger(context):
    logging.config.dictConfig(logging_config(context))


# if the user process does not do anything
# like for the miscell testers and other certificate
# probing/dumping utilities
init_logger('console')
