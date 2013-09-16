#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Contains the default values for the AF_SYN_RT program """

import logging
import datetime

# Logging
ADMIN_EMAILS = []  # While debugging the script
#ADMIN_EMAILS = ['Ian.Llewellyn@rte.ie', 'radiomnt@rte.ie']
STDERR_LOG_LEVEL = logging.INFO
LOGFILE_LOG_LEVEL = logging.INFO
EMAIL_LOG_LEVEL = logging.WARNING

# Files
AUDIOFILE_DAY_CACHE_STORAGE = '/mnt/audiofile-day-cache/audio'
LOCK_FILE = '/var/lock/subsys/af-sync.lock'

# Other
INTER_DELTA_SLEEP_TIME = 750
DELTA_RETRIES = 2
NO_PROGRESS_SLEEP_TIME = 120000
CHUNK_SIZE = 520160
DATE = str(datetime.datetime.utcnow().date())

PORT_NUMBER = 11111
CONFIG_PATH = '/etc/af-sync.d/af-sync.conf'

LOG_FILE = '/var/log/audiofile//af-sync-controller.log'
LOG_LEVEL = 2
VERB_LEVEL = 1
