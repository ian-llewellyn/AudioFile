#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Contains the default values for the AF_SYN_RT program """

import logging

LOG_FORMAT = '[%(asctime)s] %(process)d %(levelname)s: %(message)s'
LOG_FILE = '/var/log/audiofile/af-sync-%s.log'
DEBUG_LOG_FILE = '/var/log/audiofile/af-sync-%s_debug.log'

# Logging
#ADMIN_EMAILS = ['Ian.Llewellyn@rte.ie', 'radiomnt@rte.ie']
ADMIN_EMAILS = ['francois.ribemont@gmail.com']
STDERR_LOG_LEVEL = logging.DEBUG
LOGFILE_LOG_LEVEL = logging.INFO
LOGFILE_DEBUG_LOG_LEVEL = logging.DEBUG
EMAIL_LOG_LEVEL = logging.WARNING

# Files
AUDIOFILE_DAY_CACHE_STORAGE = '/mnt/audiofile-day-cache/audio'
LOCK_FILE = '/var/lock/subsys/af-sync.lock'

# Other
INTER_DELTA_SLEEP_TIME = 750
DELTA_RETRIES = 2
CHUNK_SIZE = 520160

PORT_NUMBER = 11111
CONFIG_PATH = '/etc/af-sync.d/af-sync.conf'

LOG_LEVEL = 2
VERB_LEVEL = 1
NP_SLEEP_TIME = 20000
