#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import logging

sys.path.append('/etc/af-sync.d')
import configuration as conf


def get_log_conf(service=None, file_format=None, name=None):
    if service and file_format:
        parameters = '%s-%s' % (service, file_format)
    elif name is not None:
        parameters = 'multi'
    else:
        parameters = '%s'

    log_dict = {
        'LOGFILE': {
            'log_level': conf.LOGFILE_LOG_LEVEL,
            'log_file': conf.LOG_FILE % parameters,
        },
        'LOGFILE DEBUG': {
            'log_level': conf.LOGFILE_DEBUG_LOG_LEVEL,
            'log_file': conf.DEBUG_LOG_FILE % parameters,
        },
        'STDERR': {
            'log_level': conf.STDERR_LOG_LEVEL,
        },
        'EMAIL': {
            'log_level': conf.EMAIL_LOG_LEVEL,
        },
        'GENERAL': {
            'log_format': conf.LOG_FORMAT
        }
    }
    return log_dict


def create_handler(name, handler_key, level, log_format, option=None):
    """ Given a new, a handler key a level, a log_format, and an option
    (if the key is 'file' or 'file debug') returns a handler """
    handlers_mapping = {
        'file': logging.FileHandler,
        'email': logging.handlers.SMTPHandler,
        'file debug': logging.FileHandler,
        'stream': logging.StreamHandler
    }
    if option is not None:
        handler = handlers_mapping[handler_key](option)
    else:
        handler = handlers_mapping[handler_key]()
    handler.setLevel(level)
    handler.name = name
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    return handler
