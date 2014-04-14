#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Usage:
  af_sync_multi.py [options]
  af_sync_multi.py [start|restart] [options]
  af_sync_multi.py [stop|reload|status|fullstatus] [options]

  -p, --params=<params_file>  The parameters file to load.
                              [default: /etc/af-sync.d/af-sync.conf]
  -c, --config=<config_file>  The multi instance configuration file to load.
                              [default: /etc/af-sync.d/af-sync-multi.conf]
  -d, --date=<date>           Only process files on this date (Format: YYYY-mm-dd).
                              This option has no effect in the third usage pattern.
  -n, --noop                  Skip file operations.
                              This option has no effect in the third usage pattern.
"""
__version__ = '0.2'

import logging, os, sys

# DEFAULTS
DEFAULT_LOG_PATH = '/var/log/audiofile'
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_CONTROL_PORT = 12345

from af_sync_single import AFSingle, load_params
import socket, thread

class ConfigItem(dict):
    """
    ConfigItem is a wrapper around a single instance config dict
    which makes it hashable, and allows it to be used in a set.
    """
    def __init__(self, details):
        super(ConfigItem, self).__init__(details)
        self.host = self['host']
        self.service = self['service']
        self.format = self['format']
        self.date = self['date']
        self.map_file = self['map_file']
        logger.debug('Initiated ConfigItem: %s' % self)

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
        if self.service != other.service:
            return False
        if self.format != other.format:
            return False
        if self.date != other.date:
            return False
        if self.map_file != other.map_file:
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
                    # Blank line
                    continue
                if line.startswith('#'):
                    # Comment line
                    continue
                host, _, rest = line.partition(' ')
                svc_format, _, map_file = rest.partition(' ')
                map_file = map_file or None
                formats, service = svc_format.split(':')
                if formats == '*':
                    formats = ['mp2', 'mp3']
                else:
                    formats = [formats]
                for fmt in formats:
                    logger.debug('Adding configuration for %s, %s, %s, %s' % \
                        (host, service, fmt, map_file))
                    self.add(ConfigItem(
                        {'host': host, 'service': service,
                         'format': fmt, 'date': date,
                         'map_file': map_file}))
            logger.info('Loaded configuration file %s' % config_file)

class AFMulti(set):
    """
    The AFMulti class is a simple set used as a manager for the single
    instances it contains.
    """

    def __init__(self, multi_config, params=None):
        """
        Standard constructor method.
        """
        super(AFMulti, self).__init__()
        if params is None:
            params = {}
        for single_config in multi_config:
            single_instance = AFSingle(params=params, **single_config)
            self.add(single_instance)
        logger.debug('AFMulti Initialised')

    def add(self, single_instance):
        """
        Override the standard add() method to ensure the element being
        added is an instance of AFSingle.
        """
        if not isinstance(single_instance, AFSingle):
            raise TypeError('Not an instance of AFSingle')
        super(AFMulti, self).add(single_instance)

    def stop(self):
        """
        Gently stop the AFMulti service by setting running = False.
        This method allows the daemon to complete it's current main loop first.
        """
        global running
        running = False
        return (os.EX_OK, 'Terminating on next loop.')

    def restart(self):
        """
        This should probably not be implemented here.
        """
        return (os.EX_OK, 'restart') # os.EX_CONFIG, os.EX_NOHOST

    def reload(self):
        """
        Reload the AFMulti class with a freshly read configuration.
        """
        global multi, params
        # Read in the configuration
        instances = Configuration(args['--config'])
        # Recreate the multi set()
        multi = AFMulti(instances, params=params)
        return (os.EX_OK, 'Reload complete - changes may not take effect ' \
            'immediately.') # os.EX_CONFIG

    def status(self):
        """
        Return a string of the terse status for the currently running AFMulti
        class. Also provide a return code which is 0 for complete success, and
        1 for anything else.
        """
        configured = Configuration(args['--config'])
        running = self # or multi

        if configured == running:
            output = "%d instances configured and running\n" \
                'Note: this does not guarantee that data is coming ' \
                'from the configured hosts.' % len(configured)
            code = os.EX_OK
        else:
            output = "%d instances running.\n" % len(running)
            output += "%d instances configured but not running.\n" \
                % len(configured.difference(running))
            output += "%d instances running but not configured.\n" \
                % len(running.difference(configured))
            code = 1
        return (code, output) # 1 = reload required

    def fullstatus(self):
        """
        Return a string of verbose status for the currently running AFMulti
        class. Also provide a return code which is 0 for complete success, and
        1 for anything else.
        """
        configured = Configuration(args['--config'])
        running = self # or multi

        output = "%d instances running.\n" % len(running)
        for single_instance in running:
            output += "%s\n" % single_instance.fullstatus()

        if configured == running:
            code = os.EX_OK
        else:
            output += "\n%d instances configured but not running.\n" \
                % len(configured.difference(running))
            for sync in configured.difference(running):
                output += 'host: %s, service: %s, format: %s, date: %s, ' \
                    "map_file: %s\n" % tuple([getattr(sync, key) for key in [
                    'host', 'service', 'format', 'date', 'map_file']])

            output += "\n%d instances running but not configured.\n" \
                % len(running.difference(configured))
            for sync in running.difference(configured):
                output += "%s\n" % sync.fullstatus()

            code = 1

        return (code, output) # 1 = reload required

    def foreground(self):
        """
        Returns true if the process is running in the foregound.
        """
        return (os.EX_OK, str(foreground))

    def pid(self):
        """
        Return the PID of this process
        """
        return (os.EX_OK, str(os.getpid()))

class AFMultiServer(object):
    """
    The AFMultiServer class will be started along with and instance
    of the AFMulti class. It listens on a TCP port for commands.
    """
    def __init__(self, params=None):
        """
        Initialises the Server class for AFMulti.
        """
        self.socket = socket.socket()
        self.host = socket.gethostname()
        if params is None:
            params = {}
        try:
            self.port = params['control_port']
        except KeyError:
            self.port = DEFAULT_CONTROL_PORT
        #self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.connect()
        except socket.error, error:
            logger.error('An error occurred when bind()ing: %s', error)
            raise
        logger.info('AFMulti server started on %s:%d' % (self.host, self.port))

    def connect(self):
        """
        Bind to the machines address.
        """
        self.socket.bind((self.host, self.port))
        logger.debug('AFMultiServer bound to %s:%d' % (self.host, self.port))
        return True

    def run(self):
        """
        This is a never ending loop that simply receives commands
        and dispatches them.
        """
        self.socket.listen(0)
        logger.debug('AFMultiServer listening for connections')
        while running:
            (connection, address) = self.socket.accept()
            logger.info('AFMultiServer received connection from %s:%d' % \
                address)
            command = connection.recv(1024)
            #connection.shutdown(socket.SHUT_RD) # The client shuts down the
                                                 # writing end of the pipe.
            try:
                code, output = getattr(multi, command)()
            except AttributeError:
                raise
                code = 64
                output = 'AttributeError: Command not implemented'
            #except TypeError:
            #    code = 64
            #    output = 'TypeError: Command not implemented'
            connection.send(','.join([str(code), str(len(output)), output]))

            #connection.shutdown(socket.SHUT_WR)
            #connection.close() # Allow the client call the close() function
                                # so that TIME_WAIT is on the client side.
            logger.info('AFMultiServer finished writing to %s:%d' % address)

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
        super(AFMultiClient, self).__init__()
        try:
            self.control_port = params['control_port']
        except KeyError:
            self.control_port = DEFAULT_CONTROL_PORT
        self.socket = None
        self.connected = False
        if connect:
           self.connected = self.connect()

    def communicate(self, message):
        """
        Sends a message to the AFMulti instance and returns a 2 tuple
        containing both a return code and any textual output.

        The 'on wire' protocol is to send a return code, the length of
        the message, and the message itself.
        """
        self.socket.send(message)
        #self.socket.shutdown(socket.SHUT_WR)

        code, length, output = list(self.socket.recv(1024).split(',', 2))
        length = int(length)

        while len(output) != length:
            output += self.socket.recv(1024)

        code = int(code)
        return (code, output)

    def connect(self):
        """
        connect() Establishes a connection between the client and the
        AFMulti instance listening on the configured TCP port.
        """
        # Open socket and prepare for comms
        self.socket = socket.socket()
        try:
            self.socket.connect((socket.gethostname(), self.control_port))
            return True
        except socket.error:
            return False

    def disconnect(self):
        """
        disconnect() Breaks the connection with the AFMulti instance.
        """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        return True

if __name__ == '__main__':
    # Parse arguments
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    # Load parameters
    params = load_params(args['--params'])

    foreground = False
    commands = ['start', 'stop', 'restart', 'reload', 'status', 'fullstatus']
    # If command == stop | restart | reload | status
    for command in commands:
        if args[command] == True:
            break
        else:
            # We have to set the default action here
            command = 'start'
            foreground = True

    if command != 'start':
        # command in ['stop', 'restart', 'reload', 'status']:
        # - load AFMultiClient class, send message to server and exit
        client = AFMultiClient(params)

        if not client.connected:
            print 'Cannot connect to AFSyncMulti process - ' \
                'perhaps it is not running.'
            sys.exit(1)

        if command == 'restart':
            print 'The restart command has been disabled for development.\n' \
                'Please stop and start the service manually.'
            client.disconnect()
            sys.exit(os.EX_USAGE)
            # Determine if we have to restart in the background, foreground, or not at all.
            code, foreground = client.communicate('foreground')
            client.disconnect()

            foreground = foreground == 'True'

            client.connect()
            code, pid = client.communicate('pid')
            client.disconnect()

            client.connect()
            client.communicate('stop')
            client.disconnect()

            import signal
            os.kill(int(pid), signal.SIGTERM)

        else:
            code, output = client.communicate(command)
            client.disconnect()

            # Show what we got
            print output

            sys.exit(code)

    logger = logging.getLogger(__name__)
    logger.addHandler(logging.FileHandler(params['log_path'] \
        + '/af-sync-multi.log'))
    logger.handlers[0].setFormatter(logging.Formatter(fmt='%(asctime)s ' \
        '[%(process)d] [%(levelname)s] Line: %(lineno)d: %(message)s'))
    logger.level = DEFAULT_LOG_LEVEL
    if params.has_key('log_level'):
        logger.level = params['log_level']

    # Start program proper
    logger.info('Starting AFMulti process')

    instances = Configuration(args['--config']) # or \
                              #params['multi_sync_config'] or \
                              #DEFAULT_MULTI_INSTANCE_CONFIG_FILE)

    # Create instances
    multi = AFMulti(instances, params=params)

    # A variable that will help us end gracefully
    # Used in main loop and in communications thread
    running = True

    # Fork at this point
    if not foreground:
        logger.info('Daemonising...')
        pid = os.fork()
        if pid > 0:
            # This is the parent
            logger.info('Child started with PID: %d. Parent exiting.' % pid)
            sys.exit(os.EX_OK)
        elif pid < 0:
            logger.critical('Failed to fork() child process - exiting!')
            sys.exit(os.EX_OSERR)
        # pid == 0 - This is the child
        logger.info('Child successfully fork()ed.')

    # Initiate AFMultiServer
    try:
        multi_server = AFMultiServer(params)
    except:
        logger.critical('Encountered a problem initiating AFMultiServer')
        sys.exit(os.EX_TEMPFAIL)

    # Start AFMultiServer thread
    thread.start_new_thread(multi_server.run, ())

    import datetime, time

    # infinite loop
    logger.debug('Entering main loop')
    while running:
        next_run_time = datetime.datetime.now() + datetime.timedelta(
            milliseconds=params['main_loop_min_time'])

        for instance in multi:
            instance.step()

        now = datetime.datetime.now()
        if now < next_run_time:
            sleep_time = (next_run_time - now).seconds + \
                         (next_run_time - now).microseconds / 1000000.0
            logger.info('Main loop sleeping for %f seconds' % sleep_time)
            time.sleep(sleep_time)
