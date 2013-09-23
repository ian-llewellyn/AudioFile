#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import sys

sys.path.append('/home/paco/Projects/RTÉ/audiofile/etc/af-sync.d')
import configuration as conf


def get_log_conf(service=None, file_format=None):
    if service and file_format:
        parameters = '%s-%s' % (service, file_format)
    elif service or file_format:
        parameters = '%s' % (service if service else file_format)
    else:
        parameters = 'multi'

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


def setup_log_handlers(logger, log_dict, logger_level=logging.DEBUG):
    """ Sets up the log handlers """

    # Otherwise it filters the DEBUG and INFO messages
    logger.setLevel(logger_level)

    # FILE HANDLER
    file_handler = logging.FileHandler(log_dict['LOGFILE']['log_file'])
    file_handler.setLevel(log_dict['LOGFILE']['log_level'])
    formatter = logging.Formatter(log_dict['GENERAL']['log_format'])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # DEBUG FILE HANDLER
    file_handler = logging.FileHandler(log_dict['LOGFILE DEBUG']['log_file'])
    file_handler.setLevel(log_dict['LOGFILE DEBUG']['log_level'])
    formatter = logging.Formatter(log_dict['GENERAL']['log_format'])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # STDERR HANDLER
    stderr_handler = logging.StreamHandler(sys.stdout)
    stderr_handler.setLevel(log_dict['STDERR']['log_level'])
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    #email_handler = logging.handlers.SMTPHandler(
    #    'localhost',
    #    'AudioFile Rea-Time Sync <af-sync-%s-%s@%s>'
    #    % (args.service, args.format, gethostname()),
    #    configuration.ADMIN_EMAILS, 'Log output from af-sync-%s-%s'
    #    % (args.service, args.file_format)
    #)
    #
    #email_handler.setLevel(configuration.EMAIL_LOG_LEVEL)
    #email_handler.setFormatter(standard_format)
    #print(email_handler)
    #
    #logger.addHandler(email_handler)
    return logger
