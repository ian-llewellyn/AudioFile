#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import datetime

## Global Variables
AUDIOFILE_DAY_CACHE_STORAGE = '/mnt/audiofile-day-cache/audio'
## Set Defaults
INTER_DELTA_SLEEP_TIME = 750
DELTA_RETRIES = 2
NO_PROGRESS_SLEEP_TIME = 120000
CHUNK_SIZE = 4 * 1024 * 1024
ADMIN_EMAILS = []  # While debugging the script
#ADMIN_EMAILS = ['Ian.Llewellyn@rte.ie', 'radiomnt@rte.ie']
STDERR_LOG_LEVEL = logging.INFO
LOGFILE_LOG_LEVEL = logging.INFO
EMAIL_LOG_LEVEL = logging.WARNING
date = str(datetime.datetime.utcnow().date())
