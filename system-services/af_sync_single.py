#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    Usage:
      af-sync-single.py --host <host> --service <service> --format <format> [--date <date>] [--mapfile <map_file>]

      Options:
        -h, --host=<host>          The host to be used to source the files.
        -s, --service=<service>    The AudioFile service name to be synchronised.
        -f, --format=<format>      Provide the format to sync, mp2 or mp3.
        -d, --date=<date>          Only process files for given date (Format YYYY-MM-DD).
        -m, --mapfile=<map_file>  Give the absolute path of a map file to use.
"""
__version__ = '0.2'

# DEFAULTS
DEFAULT_PARAMS_FILE = '/etc/af-sync.d/af-sync.conf'
DEFAULT_LOG_PATH = '/var/log/audiofile'
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_INTER_DELTA_MIN_TIME = 750
DEFAULT_DELTA_RETRIES = 2
DEFAULT_NO_PROGRESS_MAX_WAIT = 120000
DEFAULT_MAIN_LOOP_MIN_TIME = 750

LOGGING = {}

class AFSingle(set):
    """
    This class is used to hold the parameters and state of a synchronising
    process.
    instance = AFSingle(host=host, service=service, format=format
        [, date=date)[, map_file=map_file][, params=params_dict])
    params_dict = {
        'inter_delta_min_time': int milliseconds,
        'no_progress_max_wait': int milliseconds
    }
    """

    def __init__(self, **kwargs):
        """
        Method involved in setting up an instance of the AFSingle class.
        """
        for key in kwargs:
            self.__dict__[key] = kwargs[key]
        # Required arguments
        if not hasattr(self, 'host') or \
            not hasattr(self, 'service') or \
            not hasattr(self, 'format'):
            raise Exception('host, service and format are required parameters')

        # Optional arguments
        if not hasattr(self, 'date'):
            self.date = None
        if not hasattr(self, 'map_file'):
            self.map_file = None
        if hasattr(self, 'params'):
            for key in self.params:
                self.__dict__[key] = self.params[key]
            del self.params
        if not hasattr(self, 'inter_delta_min_time'):
                self.inter_delta_min_time = DEFAULT_INTER_DELTA_MIN_TIME
        if not hasattr(self, 'delta_retries'):
                self.delta_retries = DEFAULT_DELTA_RETRIES
        if not hasattr(self, 'no_progress_max_wait'):
                self.no_progress_max_wait = DEFAULT_NO_PROGRESS_MAX_WAIT
        if not hasattr(self, 'log_path'):
                self.log_path = DEFAULT_LOG_PATH
        if not hasattr(self, 'log_level'):
                self.log_level = DEFAULT_LOG_LEVEL

        import logging
        self.logger = logging.getLogger('.'.join(['af-sync',
            self.service, self.format]))
        self.logger.info('Initialised', self.service, self.format)
        self.logger.debug('Host: %s, Date: %s, Map File: %s' % (self.host,
            self.date, self.map_file))

        # Initialise internal parameters
        for record in self.get_file_list():
            self.add(record)

        import datetime
        self._next_run_time = datetime.datetime.now()
        self._delta_failures = 0
        self._no_progress_sleep_time = 0

    def get_file_list(self):
        """
        Gets a JSON list of files available on the server for a particular
        format, service and date.
        """
        self.logger.debug('Called get_file_list()')
        return []

    def fetch_delta(self):
        """
        This method is used to actually fetch the next chunk of data and append
        it to the target file.
        return True if we succeed in getting data
        return False if we have problems retreiving data
        return None if we decide not to get data
        """
        self.logger.debug('Called fetch_delta()')

        return True

    def step(self):
        """
        This method is used to carry out the next operation of the
        synchronising process.
        return True if we succeed in getting data
        return False if we have problems retreiving data
        return None if we decide not to get data
        """
        self.logger.debug('Called step()')

        if datetime.datetime.now() < self._next_run_time:
            return None

        self._next_run_time = datetime.datetime.now() + datetime.timedelta(
            milliseconds=self.inter_delta_min_time)

        if self.fetch_delta():
            self._delta_failures = 0
            self._no_progress_sleep_time = 0
            return True
        self._delta_failures += 1

        # We didn't receive any data because:
        # 1. We already have the full file
        # 2. We are finished today's files
        # 3. The recorder has stopped
        # 4. There is a network issue...

        if self._delta_failures > self.delta_retries:
            for record in self.get_file_list():
                self.add(record)
            self._no_progress_sleep_time = self._no_progress_sleep_time * 2 or 1
            self._retry_after = datetime.datetime.now() + datetime.timedelta(
                seconds=self._no_progress_sleep_time)
            return False

if __name__ == '__main__':
    # Parse arguments
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    # Instantiate class
    single = AFSingle(host=args['--host'], service=args['--service'],
        format=args['--format'], date=args['--date'], map_file=['--mapfile'])

    # main loop
    while 1:
        single.step()
