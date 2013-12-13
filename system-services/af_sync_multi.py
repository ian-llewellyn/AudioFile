#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Usage:
  af_sync_multi.py [OPTIONS] [-d <date>]
  af_sync_multi.py (start|restart) [OPTIONS] [-d <date>]
  af_sync_multi.py (stop|status|reload) [OPTIONS]

  Options:
    -c, --config=<config_file>  The multi instance configuration file to load.
    -p, --params=<params_file>  The parameters file to load.
    -n, --noop                  Skip file operations.
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

from af_sync_single import AFSingle, load_params
import socket, thread

class ConfigItem(dict):
    """
    ConfigItem is a wrapper around a single instance config dict
    which makes it hashable, and allows it to be used in a set.
    """
    def __hash__(self):
        """
        Implements the standard __hash__ method to allow comparisons.
        """
        # Purposly ommitting self['host'] gives us a nice way to ensure
        # we don't accidentally configure the same service and format
        # from two different hosts.
        return hash(self['service'] + self['format'] + (self['date'] or '') +
                    (self['map_file'] or ''))

    def __eq__(self, other):
        """
        Implements the standard __eq__ method to allow comparisons.
        """
        if self['service'] != other['service']:
            return False
        if self['.format'] != other['format']:
            return False
        if self['date'] != other['date']:
            return False
        if self['map_file'] != other['map_file']:
            return False
        return True

class Configuration(set):
    """
    The Configuration class is a set that reads a multi instance config file
    and stores the individual configurations as elements in the set.
    """
    def __init__(self, config_file, date=None):
        """
        Standard constructor method.
        """
        super(Configuration, self).__init__()
        # Two configuration files:
        # 1. The multi instance config file
        # 2. The config that defines timeouts, logfiles, etc...
        with file(config_file) as config_fp:
            for line in config_fp.readlines():
                line = line.rstrip()
                if line == '':
                    continue
                if line.startswith('#'):
                    continue
                host, svc_format, map_file = (line + ' ').split(' ', 2)
                map_file = map_file or None
                formats, service = svc_format.split(':')
                if formats == '*':
                    formats = ['mp2', 'mp3']
                else:
                    formats = [formats]
                for fmt in formats:
                    self.add(ConfigItem(
                        {'host': host, 'service': service,
                         'format': fmt, 'date': date,
                         'map_file': map_file}))

class AFMulti(set):
    """
    The AFMulti class is a simple set used as a manager for the single
    instances it contains.
    """
    def __init__(self, multi_config, params={}):
        """
        Standard constructor method.
        """
        super(AFMulti, self).__init__()
        for single_config in multi_config:
            single_instance = AFSingle(params=params, **single_config)
            self.add(single_instance)

    def add(self, single_instance):
        """
        Override the standard add() method to ensure the element being
        added is an instance of AFSingle.
        """
        if not isinstance(single_instance, AFSingle):
            raise TypeError('Not an instance of AFSingle')
        super(AFMulti, self).add(single_instance)

    def stop(self):
        running = False
        return (0, 'Terminating on next loop.')

    def restart(self):
        return (0, '')

    def reload(self):
        return (0, '')

    def status(self):
        return (0, '')

    def fullstatus(self):
        return (0, '')


class AFMultiServer(object):
    """
    The AFMultiServer class will be started along with and instance
    of the AFMulti class. It listens on a TCP port for commands.
    """
    def __init__(self, params={}):
        """
        Initialises the Server class for AFMulti.
        """
        self.socket = socket.socket()
        self.host = socket.gethostname()
        self.port = params['control_port'] or DEFAULT_CONTROL_PORT
        #self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.connect()
        except socket.error, error:
            logger.error('An error occurred when connect()ing the server: %s',
                         error)
            raise

    def connect(self):
        """
        Bind to the machines address.
        """
        self.socket.bind((self.host, self.port))
        return True

    def run(self):
        """
        This is a never ending loop that simply receives commands
        and dispatches them.
        """
        self.socket.listen(0)
        while running:
            connection, address = self.socket.accept()
            command = connection.recv(1024)
            connection.shutdown(socket.SHUT_RD)
            try:
                code, output = getattr(multi, command)()
            except AttributeError:
                code = 64
                output = 'Command not implemented'
            except TypeError:
                code = 64
                output = 'Command not implemented'
            connection.send(','.join([str(code), str(len(output)), output]))
            connection.shutdown(socket.SHUT_WR)
            connection.close()

class AFMultiClient(object):
    """
    This is a TCP client that connects on the configured port to an
    already running AFMulti instance.
    """
    def __init__(self, params={}, connect=True):
        """
        Sets up the AFMultiClient instance and connects to the
        configured AFMulti instance.
        """
        self.control_port = params['control_port'] or DEFAULT_CONTROL_PORT
        self.socket = None
        if connect:
            self.connect()
        super(AFMultiClient, self).__init__()

    def communicate(self, message):
        """
        Sends a message to the AFMulti instance and returns a 2 tuple
        containing both a return code and any textual output.

        The 'on wire' protocol is to send a return code, the length of
        the message, and the message itself.
        """
        self.socket.send(message)
        self.socket.shutdown(socket.SHUT_WR)

        code, length, output = list(self.socket.recv(1024).split(',', 2))
        length = int(length)

        while len(output) != length:
            output += self.socket.recv(1024)

        self.socket.shutdown(socket.SHUT_RD)

        self.disconnect()
        code = int(code)
        return (code, output)

    def connect(self):
        """
        connect() Establishes a connection between the client and the
        AFMulti instance listening on the configured TCP port.
        """
        # Open socket and prepare for comms
        self.socket = socket.socket()
        self.socket.connect(('localhost', self.control_port))
        return True

    def disconnect(self):
        """
        disconnect() Breaks the connection with the AFMulti instance.
        """
        self.socket.close()
        return True

if __name__ == '__main__':
    # Parse arguments
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    # Load parameters
    params = load_params()

    instances = Configuration(args['--config'] or \
                              params['multi_sync_config'] or \
                              DEFAULT_MULTI_INSTANCE_CONFIG_FILE)

    # If command == stop | restart | reload | status
    if args['command'] != 'start':
        # command in ['stop', 'restart', 'reload', 'status']:
        # - load AFMultiClient class, send message to server and exit
        client = AFMultiClient(params)
        code, output = client.communicate(args['command'])
        client.disconnect()

        # Shoe ehat we got
        print output

        import sys
        sys.exit(code) # What are the exit codes, and how to evaluate them??

    # Create instances
    multi = AFMulti(instances)

    # A variable that will help us end gracefully
    # Used in main loop and in communications thread
    running = True

    # Start communications interface thread
    thread.start_new_thread(AFMultiServer(params).run, ())

    import datetime, time

    # infinite loop
    while running:
        next_run_time = datetime.datetime.now() + datetime.timedelta(
            milliseconds=params['main_loop_min_time'])

        for instance in multi:
            instance.step()

        if datetime.datetime.now() < next_run_time:
            time.sleep((next_run_time - datetime.datetime.now()).to_seconds())
