#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Usage:
  af_sync_multi.py [-c <config_file>] [-d <date>]
  af_sync_multi.py start [-c <config_file>] [-d <date>]
  af_sync_multi.py stop [-c <config_file>]
  af_sync_multi.py status [-c <config_file>]
  af_sync_multi.py reload [-c <config_file>]
  af_sync_multi.py restart [-c <config_file>] [-d <date>]

  Options:
    -c, --config=<config_file>  The configuration file to load.
    -d, --date=<date>           The date to process (Format: YYYY-MM-DD).
"""
__version__ = '0.2'

# DEFAULTS
DEFAULT_PARAMS_FILE = '/etc/af-sync.d/af-sync.conf'
DEFAULT_LOG_PATH = '/var/log/audiofile'
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_MULTI_INSTANCE_CONFIG_FILE = '/etc/af-sync.d/af-sync-multi.conf'
DEFAULT_CONTROL_PORT = 1111
DEFAULT_MAIN_LOOP_MIN_TIME = 750

import logging
logger = logging.getLogger(__name__)

class Configuration(set):
    def __init__(self, config_file, date=None):
        # Two configuration files:
        # 1. The multi instance config file
        # 2. The config that defines timeouts, logfiles, etc...
        with file(config_file) as f:
            for line in f.readlines():
                if line == '':
                    continue
                if line.startswith('#'):
                    continue
                host, svc_format, map_file = (line + ' ').split(' ', 2)
                service, formats = svc_format.split(':')
                if formats == '*':
                    formats = ['mp2', 'mp3']
                else:
                    formats = [formats]
                for format in formats:
                    self.add(
                        {'host': host, 'service': service,
                            'format': format, 'date': date})

class AFMulti(set):
    def __init__(self, configuration):
        for instance_config in configuration:
            instance = AFSingle(instance_config)
            self.add(instance)

    def add(self, instance):
        if not isinstance(instance, AFSingle):
            raise TypeError('Not an instance of AFSingle')
        super(AFMulti, self).add(instance)

class AFMultiClient(object):
    def __init__(self, configuration):
        # Open socket and prepare for comms
        pass

    def communicate(self, message):
        code = 0
        output = ''
        return (code, output)

if __name__ == '__main__':
    # Parse arguments
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    # Load multi configuration
    configuration = Configuration(args['--config'])

    # If command == stop | restart | reload | status
    if not args['start']:
    #if command in ['stop', 'restart', 'reload', 'status']:
    #     load AFMultiClient class, send message to server and exit
        client = AFClient(configuration)
        print client.communicate(command)
        sys.exit() # What are the exit codes, and how to evaluate them??

    # Create instances
    multi = AFMulti(configutarion)

    # Start communications interface thread

    # infinite loop
    while 1:
        next_run_time = datetime.datetime.now() + datetine.timedelta(
            milliseconds=configuration.MAIN_LOOP_MIN_TIME)

        for instance in multi:
            instance.step()

        if datetime.datetime.now() < next_run_time:
            time.sleep((next_run_time - datetime.datetime.now()).to_seconds())
