#!/usr/bin/env python
"""
 af-sync-rt   Synchronise audio files from another AudioFile/rotter server

 chkconfig: 345 30 70
 description: Starts a multitude of processes to synchronise files for
              format and service from a given HTTP webserver.
"""

## Global Variables

import socket
import sys
from datetime import datetime
import os
import optparse
import logging

sys.path.append('/home/paco/Projects/RTE/usr/local/bin/')
sys.path.append('/home/paco/Projects/RTE/etc/af-sync.d/')
import af_sync_multi
import configuration


class AFDaemon(object):
    """ Audio file Daemon """

    def __init__(self, port, config_path=None):
        """ Constructor that takes a PID file as an argument """
        self.config_path = config_path or configuration.CONFIG_PATH
        self.port = port
        self.socket = socket.socket()
        self.host = socket.gethostname()

    def connect(self):
        """ Connects to the AFMulti instance """
        self.socket.connect((self.host, self.port))

    def read(self):
        """ Reads what the client has to say """
        return self.socket.recv(1024)

    def restart(self):
        """ Send the stop command, and starts the daemon """
        self.stop()
        self.start()

    @staticmethod
    def start(start_server=True):
        """ Starts the process """
        af_sync_multi.main(start_server)

    def status(self):
        """ Send the status command to the server """
        self.send('status')

    def fullstatus(self):
        """ Same as `status` with more verbosity """
        self.send('fullstatus')

    def send(self, text):
        """ Generic method that sends messages to the server """
        self.socket.send(text)

    def close(self):
        """ Closes the socket to free the port """
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def stop(self):
        """ Sends the stop command to the process """
        self.send('stop')

    def reload(self):
        """ Sends the reload command to the process """
        self.send('reload')


def logger(level, message):
    """ Logging definition """
    verb_level = level or configuration.VERB_LEVEL
    log_level = level or configuration.LOG_LEVEL

    current_pid = os.getpid()
    date_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    msg = '[%s] %d %d: %s' % (date_time, current_pid, level, message)
    if level <= verb_level:
        print msg
    if level <= log_level:
        log_file = file(configuration.LOG_FILE, 'a')
        log_file.write(msg + '\n')
        log_file.close()
    return True


def main():
    """ Function that is running when executing this script.
    it reads the command from the user and send it to the daemon it is started.
    it the signal is `start` it starts the daemon. """
    parser = optparse.OptionParser()

    parser.add_option('-c', '--config', dest='config_file', type=str, nargs=1)
    parser.add_option('-v', '--verbose', dest='verbosity', type=str, nargs=1)
    args = parser.parse_args()[0]

    if args.verbosity:
        try:
            level = getattr(logging, args.verbosity)
        except:
            print('Please specify a good logging level. '
                  'i.e DEBUG, INFO, WARNING, ERROR, CRITICAL')
    #try:
    #    args = parser.parse_args()[0]
    #except SystemExit:
    #    usage()
    #    sys.exit(1)

    #if args.config_file:
    #    config_file = args.config_file

    #if args.verbosity:
    #    VERB_LEVEL = args.verbosity
    action = None
    if len(sys.argv) > 1:
        action = sys.argv[1]

    if action:
        daemon = AFDaemon(configuration.PORT_NUMBER)
        if action not in ('fg', 'start', 'restart'):
            daemon.connect()
            try:
                getattr(daemon, action)()
            except AttributeError:
                print '%s is not a valid command' % action
                sys.exit(1)
            response = daemon.read()
            if response:
                print response
        elif action == 'fg':
            AFDaemon.start(start_server=False)
        else:
            if action == 'restart':
                daemon.connect()
                daemon.stop()
            if action != 'fg':
                pid = os.fork()
                if pid == 0:
                    AFDaemon.start(start_server=True)
    else:
        usage()
        sys.exit(1)


# Local Function Definitions
def usage():
    """ Prints the good way to use the script when the user uses a wrong option
    """
    print('%s <start|stop|restart|reload|status> '
          '[-c <config_file>] [-v <1..4>]' % sys.argv[0])
    print('\t-c\tOverrire default configuration file: %s.'
          % configuration.CONFIG_PATH)
    print('\t-v\tBe more verbose on-screen.')

if __name__ == '__main__':
    main()
