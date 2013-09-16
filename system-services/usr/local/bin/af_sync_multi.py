#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module runs the AudioFile Synchronisation """

import optparse
import sys
import logging
import socket
import urllib2
import simplejson
import os
import time
import thread

sys.path.append('/home/paco/Projects/RTE/etc/af-sync.d/')
import configuration

sys.path.append('/home/paco/Projects/RTE/usr/local/bin/')
from af_sync_single import AFSingle


class ConfigurationSyntaxError(Exception):
    """ Exception to be raised when it finds an error in the configuration file
    """
    pass


class Server(object):
    """ The server class. It will be started as well as the AFMulti object
    and will receive the commands from the script in /etc/init.d """
    def __init__(self):
        self.socket = socket.socket()
        self.host = socket.gethostname()
        self.port = configuration.PORT_NUMBER
        self.connection = self.address = None
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.connect()

    def connect(self):
        """ Make the server read for connections coming from clients """
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self._open_connection()

    def _open_connection(self):
        """ Opens a new connections of a client, when one is shut """
        self.connection, self.address = self.socket.accept()

    def _close_client(self):
        """ Close the connection when a client shuts its connectino """
        self.connection.close()

    def reopen_connection(self):
        """ Closes a connection and reopens it """
        self._close_client()
        self._open_connection()

    def read(self):
        """ Waits for the client to send something and returns what it sent """
        return self.connection.recv(2048)

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
    def __init__(self, config=None, start_server=False):
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
        self.start_server = start_server
        self.server = None
        if start_server:
            self.server = Server()
        config_path = config or configuration.CONFIG_PATH
        self.config = self._parse_config(config_path)
        # FIXME: if self.date is None, it means: do not stop at the end of the
        # day. Else, download everything for a specific day
        # The way it is now, it will stop at the end of the day
        self.date = configuration.DATE
        self.target_file = ''

    def run(self, args):
        """ Run the process of going through all the
        hosts/services/file_formats in the configuration in order to download
        the files """
        run_host = False
        run_service = False

        processed = 0
        records_map = self.get_files_to_update()

        while True:
            for config in self.config:
                host = config['host']
                service = config['service']
                file_formats = config['file_formats']
                map_file = config['map_file']
                # Get the the records for a specific host,
                # service and format
                for file_format in file_formats:
                    records = records_map[(host, service, file_format)]

                    sleep_time = 5
                    if processed >= len(records):
                        time.sleep(sleep_time)
                        records_map = self.get_files_to_update()
                    else:
                        current_record = records[processed]
                        file_name = current_record['file']
                        logging.info('Processing: Host: %(host)s, '
                                     'Service: %(service)s, '
                                     'Format: %(file_format)s,'
                                     'File: %(file_name)s', locals())
                        options = {'map_file': map_file}
                        instance = AFSingle(host=host,
                                            file_format=file_format,
                                            service=service,
                                            record=current_record,
                                            options=options)
                        self.target_file = instance.target_file
                        instance.process()

    def fullstatus(self):
        """ Get the full status using the status method """
        self.status(full=True)

    def status(self, full=False):
        """ Returns the current status.

        To do so, we simply return the current config (formatted of course) """
        output = 'File being processed: %(current_file)s\n' % {
            'current_file': self.target_file
        }

        new_config = self._parse_config(configuration.CONFIG_PATH)
        configured = len(self.config)
        output += 'Configured instances: %(configured)d\n' % locals()

        running = 0
        for config in new_config:
            if config in self.config:
                running += 1
        output += 'Configured and running: %(diff)d\n' % {'diff': running}

        diff = 0

        for config in new_config:
            if config not in self.config:
                diff += 1
        output += 'Configured and not running: %(diff)d\n' % {
            'diff': diff
        }

        diff = 0
        for config in self.config:
            if config not in new_config:
                diff += 1
        output += 'Running but not configured: %(diff)d\n' % {'diff': diff}

        if full:
            for host in self.config:
                output += 'Hostname: %(host)s\n' % locals()
                for service in self.config[host]:
                    output += '\tService: %(service)s\n' % locals()
                    for file_format in self.config[host][service]:
                        output += '\t\tFormat: %(file_format)s\n' % locals()
        self.send(output)

    def stop(self):
        """ Terminates the program """
        self.send('')
        if self.start_server:
            self.server.close()
            thread.exit()

    def reload(self):
        """ Reload the configuration """
        lock = thread.allocate_lock()
        with lock:
            self.config = self._parse_config(configuration.CONFIG_PATH)
        message = 'Configuration has been loaded'
        self.server.send(message)

    def get_files_to_update(self):
        """ Gets all the files that can be downloaded based on
        the different hosts/service/formats """
        records_map = {}
        for config in self.config:
            host = config['host']
            service = config['service']
            file_formats = config['file_formats']
            for file_format in file_formats:
                list_files = get_file_list(host, file_format, service,
                                           self.date)

                records_map[(host, service, file_format)] = list_files
        return records_map

    def _parse_config(self, config_path):
        """ expand_config(config_file) -> [ ( SyncInstance )* ]
        Return a list of SyncInstances that have been configured in the file
        provided.

        Any duplicates found in the file are removed.
        """
        try:
            config_file = open(config_path)
            lines = config_file.readlines()
        except IOError:
            logging.critical('There was a problem opening config file: %s',
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
        #map_file_invalid = False
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

        # Append this/these format(s) and service(s) to the result array
        return config

    def send(self, message):
        """ Sends a message to the client through the connection """
        if self.start_server:
            self.server.send(message)
        else:
            print message

    def __str__(self):
        return '<AFMulti server: %s, config: %s, date: %s>' % (
            self.server, self.config, self.date
        )


def get_file_list(host, file_format, service, date):
    """ get_file_list(host, format, service, date) -> [
        {'title': '01:00:00', 'file': '2012-08-30-00-00-00-00.mp2',
         'size': 123456}*
    ]
    Returns an array from the directory listing received by a HTTP call such
    as: http://host/format/service/date/
    """
    url = ('http://%s/webservice/v2/listfiles.php?format=%s&service=%s&date=%s'
           % (host, file_format, service, date))
    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req)
    except urllib2.URLError, error:
        # If a firewall is blocking access, you get: 113, 'No route to host'
        logging.warning('Received URLError in function: '
                        'get_file_list(%s, %s, %s, %s): %s',
                        host, file_format, service, date, error)
        return []
    else:
        decoded = simplejson.loads(resp.read())

    #return record['file'] for record in decoded['files']]
    return decoded['files']


def setup_parser():
    """ Setup the need options for the parser """
    parser = optparse.OptionParser()

    parser.add_option('-c', '--config', dest='config_file', type=str, nargs=1)
    parser.add_option('-v', '--verbose', dest='verbosity', type=int, nargs=1)
    return parser.parse_args()[0]


def main(start_server=True):
    """ This function actually runs the program. """
    args = setup_parser()
    logging.basicConfig(level=logging.DEBUG)
    config_file = args.config_file or configuration.CONFIG_PATH

    multi = AFMulti(config_file, start_server=start_server)

    if start_server:
        my_thread = thread.start_new_thread(multi.run, (None,))
        while my_thread:
            content = multi.server.read()
            if not content:
                multi.server.reopen_connection()
            else:
                try:
                    method = getattr(multi, content)
                except AttributeError:
                    multi.server.send('%s is not a valid command' % content)
                    sys.exit(1)
                method()
    else:
        multi.run(())

if __name__ == '__main__':
    main(start_server=False)
