#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module runs the AudioFile Synchronisation """

# What can be improved:
# - We could inherit from socket.socket in the Server class
# - Refactor some code to get 10/10 when running pylint

# built-in modules
import optparse
import sys
import logging
import socket
import os
import thread
import datetime

# local modules
sys.path.append('/etc/af-sync.d/')
sys.path.append('/usr/local/bin/')
import configuration as g_config
from af_sync_single import AFSingle
from af_sync_single import create_handler, get_log_conf


class ConfigurationSyntaxError(Exception):
    """ Exception to be raised when it finds an error in the configuration file
    """
    def __init__(self, message):
        Exception.__init__(self, message)


class Server(object):
    """ The server class. It will be started as well as the AFMulti object
    and will receive the commands from the script in /etc/init.d """
    def __init__(self):
        self.logger = logging.getLogger('multi')
        self.logger.debug('New server created')

        self.socket = socket.socket()
        self.host = socket.gethostname()
        self.port = g_config.PORT_NUMBER
        self.connection = self.address = None
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.connect()
        except socket.error, error:
            logging.error('An error occurred when connecting the server. %s',
                          error)
            raise

    def connect(self):
        """ Make the server read for connections coming from clients """
        self.logger.debug('Connecting the server')
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self._open_connection()

    def _open_connection(self):
        """ Opens a new connections of a client, when one is shut """
        self.logger.debug('Opening the connection for the client')
        self.connection, self.address = self.socket.accept()

    def _close_client(self):
        """ Close the connection when a client shuts its connectino """
        self.logger.debug('Closing the connection due to closing event '
                          'from the client')
        self.connection.close()

    def reopen_connection(self):
        """ Closes a connection and reopens it """
        self.logger.debug('Reopening the connection')
        self._close_client()
        self._open_connection()

    def read(self):
        """ Waits for the client to send something and returns what it sent """
        content = self.connection.recv(2048)
        self.logger.debug('Received data from the client: %s', content)
        return content

    def close(self):
        """ Closes the server connection """
        self.connection.close()
        self.socket.close()

    def send(self, text):
        """ Send `text` to the client """
        self.connection.send(text)

    def __str__(self):
        return '<Server host: %s, port: %s, connection: %s, address: %s>' % (
            self.host, self.port, self.connection, self.address
        )


class AFMulti(object):
    """ The class that handles all the instances.
    It reads the configuration file, and then starts the AF_Single instances
    """
    def __init__(self, log_dict, config=None, start_server=False,
                 date=None, one_day=False):
        """
        self.config is a dictionnary which has this format:
            host1
            |-> service 1
            |   |-> format 1
            |   |-> format 2
            |-> service 2
            |   |-> format 1
            |   |-> format 2

            host2
            |-> service 1
            |   |-> format 1
            |   |-> format 2
            |-> service 2
            |   |-> format 1
            |   |-> format 2
        """
        self.log_dict = log_dict

        # self.logger creates the multi logger
        # the one that will generates messages if an error happens
        # on the server for example (connection issue is an example)
        self.logger = logging.getLogger('multi')
        self.logger.setLevel(log_dict['STDERR']['log_level'])

        if not start_server:
            handler = create_handler(
                name='multi stream' % locals(),
                handler_key='stream',
                level=self.log_dict['STDERR']['log_level'],
                log_format=self.log_dict['GENERAL']['log_format']
            )
            self.logger.addHandler(handler)

        handler = create_handler(
            name='multi file' % locals(),
            handler_key='file',
            level=self.log_dict['LOGFILE']['log_level'],
            log_format=self.log_dict['GENERAL']['log_format'],
            options={'filename': log_dict['LOGFILE']['log_file'] % 'multi'}
        )
        self.logger.addHandler(handler)
        handler = create_handler(
            name='multi file' % locals(),
            handler_key='email',
            level=g_config.EMAIL_LOG_LEVEL,
            log_format=self.log_dict['GENERAL']['log_format'],
            options={'mailhost': 'localhost',
                     'subject': 'AudioFile Real-Time Sync',
                     'toaddrs': g_config.ADMIN_EMAILS,
                     'fromaddr': 'Audiofile'}
        )
        self.logger.addHandler(handler)
        # We create the StreamHandler here, and not with the other ones since
        # this is one will remain open all the time
        # We can not create a stream handler to STDERR
        # if we're running the program as a daemon, it would crash
        # propagate turned off, so what is printed doesn't appear twice
        # We disable the propagation so the children of root
        # won't return it the messages, and so, they won't appear twice

        # if start_server we start the server (the daemon)
        self.start_server = start_server
        self.server = None
        if start_server:
            try:
                self.server = Server()
            except socket.error, error:
                self.logger.error('An error occurred when starting the server.'
                                  ' Traceback: %s', str(error))
                raise

        # If no config, we get the default one
        config_path = config or g_config.CONFIG_PATH
        # then we parse it
        self.config = self._parse_config(config_path)
        # FIXME: if self.date is None, it means: do not stop at the end of the
        # day. Else, download everything for a specific day
        # The way it is now, it will stop at the end of the day
        self.date = date
        self.target_file = ''
        self.list_instances = []

    def run(self, args):
        """ Run the process of going through all the
        hosts/services/file_formats in the configuration in order to download
        the files """
        self.logger.debug('AF Sync Multi Instance running')

        self.configure()

        while(self.list_instances is not None
              and self.list_instances != [None] * len(self.list_instances)):
            for i, instance in enumerate(self.list_instances):
                self.target_file = instance.target_path
                if instance.step() is False:
                    self.list_instances = None
            # If no progress is made, we don't want the script
            # going to 100% CPU. Back off..
            # We end the process when a date has been passed in and we have
            # downloaded all the files

    def configure(self):
        self.list_instances = []
        for config in self.config:
            host = config['host']
            service = config['service']
            file_formats = config['file_formats']
            map_file = config['map_file']

            # Get the the records for a specific host,
            # service and format
            for file_format in file_formats:

                options = {'map_file': map_file}
                if self.date is not None:
                    options['date'] = self.date

                # Here is the most important part
                # This is where where we create the instance and start
                # it
                self.logger.info('New instance of AFSingle: %(host)s, '
                                 '%(file_format)s, %(service)s', locals())
                try:
                    instance = AFSingle(host=host,
                                        file_format=file_format,
                                        service=service,
                                        options=options)
                except StopIteration:
                    self.logger.error('No files found for: '
                                      'host: %s, file_format %s, service: %s '
                                      'on the %s', host, file_format, service,
                                      self.date or
                                      str(datetime.datetime.utcnow().date()))
                else:
                    self.list_instances.append(instance)

    def fullstatus(self):
        """ Get the full status using the status method """
        self.logger.debug('Sending full status to client')
        self.status(full=True)

    def status(self, full=False):
        """ Returns the current status.

        To do so, we simply return the current config (formatted of course) """
        self.logger.debug('Sending status to client')
        output = 'File being processed: %(current_file)s\n' % {
            'current_file': self.target_file
        }

        new_config = self._parse_config(g_config.CONFIG_PATH)
        # 1 service, 1 host, 1 or 2 file formats
        # -> Returns 1 or 2 per config
        configured = sum([len(conf['file_formats']) for conf in self.config])
        output += 'Configured instances: %(configured)d\n' % locals()

        running = 0
        for config in new_config:
            if config in self.config:
                for file_format in config['file_formats']:
                    running += 1
        output += 'Configured and running: %(diff)d\n' % {'diff': running}

        diff = 0

        for config in new_config:
            if config not in self.config:
                for file_format in config['file_formats']:
                    diff += 1
        output += 'Configured and not running: %(diff)d\n' % {
            'diff': diff
        }

        diff = 0
        for config in self.config:
            if config not in new_config:
                for file_format in config['file_formats']:
                    diff += 1
        output += 'Running but not configured: %(diff)d\n' % {'diff': diff}

        if full:
            for config in self.config:
                host = config['host']
                service = config['service']
                file_format = ', '.join(config['file_formats'])
                output += 'Hostname: %(host)s\n' % locals()
                output += '\tService: %(service)s\n' % locals()
                output += '\t\tFormat: %(file_format)s\n' % locals()
        self.logger.info(output)
        self.send(output)

    def stop(self):
        """ Terminates the program """
        self.logger.debug('Sending stop to client')
        # sending '' means shutting down the communication
        self.send('')
        if self.start_server:
            self.server.close()
            thread.exit()

    def reload(self, lock):
        """ Reload the configuration """
        self.logger.debug('Sending reload to client')
        # We need to make sure that the other thread is not doing anything with
        # the config
        lock.acquire()
        self.config = self._parse_config(g_config.CONFIG_PATH)
        self.configure()
        lock.release()
        message = 'Configuration has been loaded'
        self.server.send(message)

    def _parse_config(self, config_path):
        """ expand_config(config_file) -> [ ( SyncInstance )* ]
        Return a list of SyncInstances that have been configured in the file
        provided.

        Any duplicates found in the file are removed.
        """
        logging.debug('Parsing config file')
        try:
            config_file = open(config_path)
            lines = config_file.readlines()
        except IOError:
            self.logger.critical('There was a problem opening config file: %s',
                                 config_path)
            sys.exit(os.EX_OSFILE)

        config = []
        for config_line in lines:
            # We skip comments and empty lines
            if config_line.startswith('#') or config_line.rstrip() == '':
                continue
            config_bit = self._extract_config(config_line)
            config.append(config_bit)

        config_file.close()
        return config

    @staticmethod
    def _extract_config(config_line):
        """ extract_instances(config_line) -> [ ( SyncInstances )* ]
        Given a valid line in the config file, this function
        will extrapolate the instance or instances to be started.
        """
        config = {}
        try:
            config['host'] = config_line.split()[0]
            file_format, service = config_line.split()[1].split(':')
            config['service'] = service
            config['map_file'] = None
            if len(config_line.split()) > 2:
                config['map_file'] = config_line.split()[2]
        except ValueError:
            raise ConfigurationSyntaxError('Badly written line: %s'
                                           % config_line)

        # Does format need expansion?
        if file_format == '*':
            config['file_formats'] = ['mp2', 'mp3']
        else:
            config['file_formats'] = [file_format]

        # Does service need expansion? - Not implemented yet!
        if service == '*':
            raise ConfigurationSyntaxError(
                '* Not yet implemented for service on line: ' + config_line
            )

        # Map file not allowed if more than 1 format
        if len(config['file_formats']) != 1 and config['map_file'] is not None:
            raise ConfigurationSyntaxError(
                'Map file cannot be used when * is used for format'
            )

        return config

    def send(self, message):
        """ Sends a message to the client through the connection """
        if self.start_server:
            self.server.send(message)
        else:
            self.logger.debug(message)

    def __str__(self):
        return '<AFMulti server: %s, config: %s, date: %s>' % (
            self.server, self.config, self.date
        )


def setup_parser():
    """ Setup the need options for the parser """
    parser = optparse.OptionParser()

    parser.add_option('-c', '--config', dest='config_file', type=str, nargs=1)
    parser.add_option('-v', '--verbose', dest='verbosity', type=str, nargs=1)
    parser.add_option('-d', '--date', dest='date', type=str, nargs=1)
    return parser.parse_args()[0]


def main(start_server=True):
    """ This function actually runs the program. """
    logger = logging.getLogger('multi')
    logger.propagate = False
    # We disable the propagation so the children of root won't return it the
    # messages, and so, they won't appear twice
    log_dict = get_log_conf()

    args = setup_parser()
    config_file = args.config_file or g_config.CONFIG_PATH
    if args.verbosity:
        log_dict['STDERR']['log_level'] = getattr(logging, args.verbosity)

    # Creation of the main object
    multi = AFMulti(config=config_file, log_dict=log_dict,
                    start_server=start_server,
                    date=args.date)

    if start_server:
        # Here we create the lock that we will need when reload the config
        lock = thread.allocate_lock()
        # The main thread will wait for messages coming from the client
        # (the script in init.d)
        my_thread = thread.start_new_thread(multi.run, (lock,))
        while my_thread:
            # Get what the client sends
            content = multi.server.read()
            # If the client closes the connection, we reopen a new one
            if not content:
                multi.server.reopen_connection()
            else:
                try:
                    method = getattr(multi, content)
                except AttributeError:
                    string = '%s is not a valid command'
                    multi.server.send(string % content)
                    multi.server.send('')
                    logger.error(string, content)
                    sys.exit(1)
                else:
                    if content == 'reload':
                        method(lock)
                    else:
                        method()
    else:
        # If we want to start the daemon in the foreground
        # And get to use the logging messages
        multi.run(())

if __name__ == '__main__':
    main(start_server=False)
