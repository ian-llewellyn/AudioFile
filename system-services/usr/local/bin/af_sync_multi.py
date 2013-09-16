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
import collections

sys.path.append('/home/paco/Projects/RTE/usr/local/lib/')
import values

sys.path.append('/home/paco/Projects/RTE/usr/local/bin/')
from af_sync_single import AFSingle


class ConfigurationSyntaxError(Exception):
    """ Exception to be raised when it finds an error in the configuration file
    """
    pass


def update(dict1, dict2):
    """ Update a dictionnary recursively with another dictionnary """
    for key, value in dict2.iteritems():
        if isinstance(value, collections.Mapping):
            ret = update(dict1.get(key, {}), value)
            dict1[key] = ret
        else:
            dict1[key] = dict2[key]
    return dict1


class Server(object):
    """ The server class. It will be started as well as the AFMulti object
    and will receive the commands from the script in /etc/init.d """
    def __init__(self):
        self.socket = socket.socket()
        self.host = socket.gethostname()
        self.port = values.PORT_NUMBER
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
        config_path = config or values.CONFIG_PATH
        self.config = self._parse_config(config_path)
        # FIXME: if self.date is None, it means: do not stop at the end of the
        # day. Else, download everything for a specific day
        # The way it is now, it will stop at the end of the day
        self.date = values.DATE
        self.target_file = ''

    def run(self, args):
        """ Run the process of going through all the
        hosts/services/file_formats in the configuration in order to download
        the files """
        run_host = False
        run_service = False

        host_gen = self.run_host()
        host = host_gen.next()

        service_gen = self.run_service(host)
        service = service_gen.next()

        file_format_gen = self.run_file_format(host, service)

        processed = 0
        records_map = self.get_files_to_update()
        while True:

            try:
                # Goes through all the file formats
                file_format = file_format_gen.next()
                run_service_gen = False
            except StopIteration:
                run_service = True

            try:
                # This means, we went through all the files format
                # and now we need to go to the next service
                if run_service:
                    service = service_gen.next()
                    file_format_gen = self.run_file_format(host, service)
                    file_format = file_format_gen.next()
                    run_host = False
                    run_service = False
            except StopIteration:
                service_gen = self.run_service(host)
                run_host = True

            try:
                # We are finished with one service and all its file_formats
                # We need to go through the next host, and do the same stuff
                # again
                if run_host:
                    host = host_gen.next()
                    service_gen = self.run_service(host)
                    service = service_gen.next()
                    file_format_gen = self.run_file_format(host, service)
                    file_format = file_format_gen.next()
                    run_host = False
                    run_service = False
            except StopIteration:
                host_gen = self.run_host()
                host = host_gen.next()
                service_gen = self.run_service(host)
                service = service_gen.next()
                file_format_gen = self.run_file_format(host, service)
                file_format = file_format_gen.next()
                run_service = False
                run_host = False
                processed += 1

            # Get the the records for a specific host, service and format
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
                instance = AFSingle(host=host, file_format=file_format,
                                    service=service, record=current_record)
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

        new_config = self._parse_config(values.CONFIG_PATH)
        configured = 0
        for host in new_config:
            for service in new_config[host]:
                for file_format in new_config[host][service]:
                    configured += 1
        output += 'Configured instances: %(configured)d\n' % locals()

        running = 0
        for host in new_config:
            if host in self.config:
                for service in new_config[host]:
                    if service in self.config[host]:
                        for file_format in new_config[host][service]:
                            if file_format in self.config[host][service]:
                                running += 1
        output += 'Configured and running: %(diff)d\n' % {'diff': running}
        output += 'Configured and not running: %(diff)d\n' % {
            'diff': configured - running
        }

        diff = 0

        for host in self.config:
            if host in new_config:
                for service in self.config[host]:
                    if service in new_config[host]:
                        for file_format in self.config[host][service]:
                            if file_format not in new_config[host][service]:
                                diff += 1
                    else:
                        for _ in self.config[host][service]:
                            diff += 1
            else:
                for service in self.config[host]:
                    for _ in self.config[host][service]:
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
            self.config = self._parse_config(values.CONFIG_PATH)
        message = 'Configuration has been loaded'
        self.server.send(message)

    def run_host(self):
        """ Returns one host at a time """
        for host in self.config:
            yield host

    def run_service(self, host):
        """ Returns one service at a time """
        for service in self.config[host]:
            yield service

    def run_file_format(self, host, service):
        """ Returns one file format at a time """
        for file_format in self.config[host][service]:
            yield file_format

    def get_files_to_update(self):
        """ Gets all the files that can be downloaded based on
        the different hosts/service/formats """
        records_map = {}
        for host in self.config:
            for service in self.config[host]:
                for file_format in self.config[host][service]:

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

        config = {}
        for config_line in lines:
            # We skip comments and empty lines
            if config_line.startswith('#') or config_line.rstrip() == '':
                continue
            config_bit = self._extract_config(config_line)
            config = update(config, config_bit)

        config_file.close()
        return config

    @staticmethod
    def _extract_config(config_line):
        """ extract_instances(config_line) -> [ ( SyncInstances )* ]
        Given a valid line in the config file, this function
        will extrapolate the instance or instances to be started.
        """
        #map_file_invalid = False
        try:
            host = config_line.split()[0]
            file_format, service = config_line.split()[1].split(':')
        except ValueError:
            raise ConfigurationSyntaxError('Badly written line: %s'
                                           % config_line)

        # Does format need expansion?
        if file_format == '*':
            file_formats = ['mp2', 'mp3']
        else:
            file_formats = [file_format]

        # Does service need expansion? - Not implemented yet!
        if service == '*':
            raise ConfigurationSyntaxError(
                '* Not yet implemented for service on line: ' + config_line
            )
        else:
            services = [service]

        # Is map_file the next parameter on the line?
        #if i != len(rest) - 1 and rest[i+1].startswith(os.path.sep):
        #   # Yes - set it
        #   map_file = rest[i+1]
        #   # Skip over the map file on the next loop
        #   i += 1
        #else:
        #    # No - set it to None
        #    map_file = None

        # Map file not allowed if more than 1 service or format
        #if((len(file_formats) != 1 or len(services) != 1)
        #   and map_file is not None):
        #    raise ConfigurationSyntaxError(
        #        'Map file cannot be used when *'
        #        'is used for format or service'
        #    )

        config = {}

        # Append this/these format(s) and service(s) to the result array
        if host not in config:
            config[host] = {}
        for file_format in file_formats:
            for service in services:
                if service not in config[host]:
                    config[host][service] = []
                config[host][service].append(file_format)
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
    config_file = args.config_file or values.CONFIG_PATH

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
