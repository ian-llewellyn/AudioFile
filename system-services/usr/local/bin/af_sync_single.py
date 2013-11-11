#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" This module handles a single Audio File process """

## Import Modules
import urllib2
import time
import datetime
import os
import sys
import optparse
import logging
import logging.handlers
import simplejson

sys.path.append('/etc/af-sync.d')
import configuration

sys.path.append('/usr/local/lib')
import logging_functions as lf


class AFSingle(object):
    """ Single process. It creates deltas objects """
    def __init__(self, host, service, file_format, logger,
                 options=None, date=None):
        """ Constructor of the class. Parameters:
            - host: string that represents the hostname
            - file_format: a string that represents the file format (mp2, mp3)
            - service: a string that represents a service.
                (usually read from the config file)
            - options: a dictionnary that contains a couple of options.
                It's expecting the keys: 'date', 'noop', 'map_file'
                and won't do anything about the other keys
        """

        self.deltas = []
        self.number_of_iterations = 0
        self.host = host
        self.file_format = file_format
        self.service = service
        self.date = date
        self.operation = True
        self.map_file = None
        if options is not None:
            if 'date' in options:
                self.date = options['date']
            else:
                self.date = None
            if 'noop' in options:
                self.operation = not options['noop']
            if 'map_file' in options:
                self.map_file = options['map_file']
        self.records = get_file_list(host, file_format, service,
                                     self.date)

        self.logger = logger

    @property
    def target_file(self):
        record = self.records[self.number_of_iterations]
        filename = record['file']
        return file_map(self.date, self.map_file,
                        filename,
                        self.file_format, self.service)

    @property
    def filename(self):
        return self.records[self.number_of_iterations]['file']

    @property
    def size(self):
        return self.records[self.number_of_iterations]['size']

    def step(self):
        """ Process the single instance """
        recent_truncations = []
        try:
            # Get a list of files for this date from the server
            # and loop through them
            # For ease...
            if not self.target_file:
                # I can't possibly go on - I have no target!
                self.logger.warning('file_map returned no target file '
                                    'for source file: %s', self.filename)
                return

            # Reset variable for each file that's encountered
            delta_failures = 0

            # Prepare the file or skip it altogether!
            if(self.filename != os.path.basename(self.target_file)
               and self.target_file not in recent_truncations):
                # A map file is being used, empty this file
                # (it hasn't been done in over a day!)
                self.logger.info('Truncated target file: %s', self.target_file)
                try:
                    open(self.target_file, 'w').truncate()
                except IOError:
                    directory_array = self.target_file.split(os.path.sep)[:-1]
                    directory = os.path.sep.join(directory_array)
                    os.makedirs(directory)
                recent_truncations.append(self.target_file)
                if len(recent_truncations) > 24:
                    recent_truncations.remove(recent_truncations[0])

            elif(os.path.isfile(self.target_file)
                 and self.size == os.stat(self.target_file).st_size):
                # Source and target files have the same size,
                # so target is probably fully up-to-date
                self.logger.info('Target File: %s has same size as '
                                 'Source File: %s', self.target_file,
                                 self.filename)

            # Work is to be done on this file
            # (only if tgt_file size == 0) ?
            self.logger.info('Target File: %s started', self.target_file)
            today_string = str(datetime.datetime.utcnow().date())
            req_uri = ('http://%(host)s/audio/%(file_format)s/%(service)s'
                       '/%(date)s/%(filename)s' %
                       {'host': self.host,
                        'file_format': self.file_format,
                        'service': self.service,
                        'date': self.date and self.date or today_string,
                        'filename': self.filename})

            self.logger.info('Processing: Host: %(host)s, '
                             'Service: %(service)s, '
                             'Format: %(file_format)s, '
                             'File: %(file_name)s',
                             {'host': self.host,
                              'service': self.service,
                              'file_format': self.file_format,
                              'file_name': self.filename})
            # The Delta object is the object that will
            # actually download the data
            delta = Delta(req_uri, self.target_file, operation=self.operation,
                          logger=self.logger)
            while delta_failures <= configuration.DELTA_RETRIES:
                while delta.fetch():
                    # Successful update - reset failure count and sleep
                    delta_failures = 0
                    self.logger.debug('Delta success - About to sleep '
                                      'for %d ms',
                                      configuration.INTER_DELTA_SLEEP_TIME)
                    time.sleep(configuration.INTER_DELTA_SLEEP_TIME / 1000.0)

                # Unsuccessful update - mark as a failure and sleep
                delta_failures += 1
                self.logger.debug('Delta failed %d time(s) '
                                  '- About to sleep for %d ms',
                                  delta_failures,
                                  configuration.INTER_DELTA_SLEEP_TIME)
                time.sleep(configuration.INTER_DELTA_SLEEP_TIME / 1000.0)

            # (at least once an hour - more if errors)
            self.logger.info('Delta retries: %d exceeded',
                             configuration.DELTA_RETRIES)
            # Here we close the file
            delta.tgt_fp.close()

        except:
            self.logger.exception('Caught unhandled exception')
            raise

        if (self.number_of_iterations+1) < len(self.records):
            self.number_of_iterations += 1
            return True
        else:
            return False


## Global Function Definitions
class Delta(object):
    """ Delta class that fetches the data from the server """
    def __init__(self, uri, target_file, logger, operation=True):
        """ Constructor. It needs a URI, and a target file """
        self.logger = logger
        self.uri = uri
        self.target_file = target_file
        self.operation = operation
        try:
            self.tgt_fp = open(self.target_file, 'ab')
        except IOError:
            folder = os.path.sep.join(self.target_file.split(os.path.sep)[:-1])
            os.makedirs(folder)
            self.tgt_fp = open(self.target_file, 'ab')
        self.failures = 0

    def fetch(self):
        """ fetch_delta(host, format, service) -> True/False
        Does a HTTP range request to http://host/format/service/date/file
        fetching only the bytes beyond the end of the target_file size.
        """
        # Move file pointer to the end of the file
        self.tgt_fp.seek(0, 2)
        # How many bytes have we got already?
        offset = self.tgt_fp.tell()
        self.logger.debug('File: %s has size: %d', self.target_file, offset)

        http_req = urllib2.Request(self.uri)
        # Only get updates - THIS IS THE MAGIC
        http_req.headers['Range'] = 'bytes=%s-' % offset

        self.logger.debug('Requesting: %s', self.uri)
        try:
            http_resp = urllib2.urlopen(http_req)
        except urllib2.HTTPError, error:
            self.logger.warning('Received HTTP error: %d - %s',
                                error.code, error.reason)
            # We know about only one type of HTTP error
            # we can recover from - A 416
            if error.code != 416:
                self.logger.exception('Can\'t handle HTTP error: %d - %s',
                                      error.code, error.reason)
                raise
            # Certain servers produce
            # HTTP 416: Requested Range Not Satisfiable responses
            data_length = 0
            resp_code = error.code
        except urllib2.URLError, error:
            # If a firewall is blocking access, you get:
            # 113, 'No route to host'
            self.logger.warning('Received URLError in function: '
                                'fetch_delta(%s, %s): %s',
                                self.uri, self.target_file, error)
            return False
        else:
            data_length = int(http_resp.headers.getheader('content-length'))
            resp_code = http_resp.code

        # If the file size hasn't changed since the last request, some servers
        # return a 200 response and the full file.
        # Others respond with a HTTP 416
        # error (which is handled in the except above)

        # One of two conditions signify a failed update:
        # 1. We're not at the start of the file and
        #    a partial content response was not recieved
        # 2. No data was received for update
        offset = self.tgt_fp.tell()
        # TODO:
        # 3 conditions
        if (offset != 0 and resp_code != 206) or data_length <= 0:
            self.logger.info('Delta failure %d: Offset: %d '
                             'HTTP_STATUS_CODE: %d data_length: %d',
                             self.failures + 1, offset, resp_code, data_length)
            return False

        # No operation
        if not self.operation:
            self.logger.info('Dry run %d: Offset: %d '
                             'HTTP_STATUS_CODE: %d data_length: %d',
                             self.failures + 1, offset, resp_code, data_length)
            return False

        # Write the update and flush to disk
        chunk = True
        while chunk:
            chunk = http_resp.read(configuration.CHUNK_SIZE)
            self.tgt_fp.write(chunk)
            self.tgt_fp.flush()

        self.logger.debug('Delta success: HTTP_STATUS_CODE: %d '
                          'data_length: %d', resp_code, data_length)
        return True


## Local Function Definitions
def usage():
    """ Prints the right way to use the script """
    print('%s -h <host> -s <service> -f <format> [-m map file] [-d date] '
          '[-v] [-n]' % sys.argv[0])


def file_map(date, map_file, src_file, file_format, service):
    """ file_map(src_file) -> target_file
    For a given source file, do a lookup in the map and return the
    relevant target file.
    """
    date = date or str(datetime.datetime.utcnow().date())
    if not map_file:
        return os.path.sep.join(
            [configuration.AUDIOFILE_DAY_CACHE_STORAGE, file_format,
             service, date, src_file]
        )
    else:
        # calculate the key i.e. local day of week and hour
        dow, hour = utc_file_to_local(src_file)
        # open mapping file
        map_file_full_path = '/etc/af-sync.d/%(map_file)s' % locals()
        map_file = open(map_file_full_path, 'r')
        # read contents into array or such
        for line in map_file.readlines():
            # Ignore comment lines
            if line.startswith('#'):
                continue
            kdow, khour, kfile = line.split()
            if dow == int(kdow) and hour == int(khour):
                # return the corrsponding value
                return kfile
        return None


def utc_file_to_local(file_title):
    """ utc_file_to_local(file_title) -> 2 tuple
    This function takes the time provided in the file name as UTC, converts
    it to local time and returns a tuple with the day-of-week and hour.
    File title should be of the format YYYY-mm-dd-HH-MM-SS-xx.mp2/3.
    """
    # Strip unrequired trailing characters and
    # append UTC to force strptime's hand
    string = file_title.rstrip('0123456789.mp').rstrip('-') + ' UTC'

    # Generate a UTC time tuple
    utc_time = time.strptime(string, '%Y-%m-%d-%H-%M-%S %Z')

    # Convert to a local time tuple - via seconds since the UNIX Epoch
    local_time = time.localtime(time.mktime(utc_time))

    # Extract the bits we want
    dow = time.strftime('%w', local_time)
    hour = local_time.tm_hour

    # Return
    return (int(dow), hour)


def get_file_list(host, file_format, service, date):
    """ get_file_list(host, format, service, date) -> [
        {'title': '01:00:00', 'file': '2012-08-30-00-00-00-00.mp2',
         'size': 123456}*
    ]
    Returns an array from the directory listing received by a HTTP call such
    as: http://host/format/service/date/
    """
    logger = logging.getLogger(__name__)

    # If date is None that means that we didn't pass in a date, so we keep
    # downloading file and refreshing this date variable to get
    # the latest files
    if date is None:
        date = str(datetime.datetime.utcnow().date())
    url = ('http://%s/webservice/v2/listfiles.php?format=%s&service=%s&date=%s'
           % (host, file_format, service, date))
    logging.debug('Getting file list at: %s', url)
    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req)
    except urllib2.URLError, error:
        # If a firewall is blocking access, you get: 113, 'No route to host'
        logger.warning('Received URLError in function: '
                       'get_file_list(%s, %s, %s, %s): %s',
                       host, file_format, service, date, error)
        return []
    else:
        decoded = simplejson.loads(resp.read())

    #return record['file'] for record in decoded['files']]
    return decoded['files']


## Parse Command Line Arguments
def setup_parser():
    """ Sets up the parser with the good options

    Returns the parsed options"""
    parser = optparse.OptionParser()

    parser.remove_option('-h')

    parser.add_option('-h', '--host', dest='host', type=str, nargs=1,
                      help='The host where the data comes from')
    parser.add_option('-f', '--format', dest='file_format', type=str, nargs=1)
    parser.add_option('-s', '--service', dest='service', type=str, nargs=1)
    parser.add_option('-d', '--date', dest='date', type=str, nargs=1)
    parser.add_option('-m', '--map-file', dest='map_file', type=str, nargs=1)
    parser.add_option('-v', '--verbose', dest='verbosity', type=str, nargs=1)
    parser.add_option('-n', '--noop', dest='noop', action='store_true',
                      default=False)

    args = parser.parse_args()
    return args[0]


def start_single():
    """ Tests a single instance """
    args = setup_parser()

    host = args.host
    file_format = args.file_format
    service = args.service

    log_dict = lf.get_log_conf(service, file_format)
    logger = logging.getLogger(__name__)
    logger.setLevel(log_dict['LOGFILE DEBUG']['log_level'])
    logger.propagate = False

    handler = lf.create_handler(
        name='stream multi' % locals(),
        handler_key='stream',
        level=log_dict['STDERR']['log_level'],
        log_format=log_dict['GENERAL']['log_format'],
    )
    logger.addHandler(handler)

    if args.verbosity is not None:
        try:
            log_level = getattr(logging, args.verbosity.upper())
        except AttributeError:
            logging.critical('Please provide a good verbosity option: '
                             'DEBUG, INFO, WARNING, ERROR or CRITICAL')
            sys.exit()
        else:
            log_dict['LOGFILE DEBUG']['log_level'] = log_level

    #lf.setup_log_handlers(logger, log_dict)
    ## System Integrity Checks
    # Bail out early if the target directory doesn't exist.
    # Only happens if a map file is not being used.
    if(not args.map_file
       and not os.path.exists(configuration.AUDIOFILE_DAY_CACHE_STORAGE)):
        logging.critical('AUDIOFILE_DAY_CACHE_STORAGE: %s does not exist',
                         configuration.AUDIOFILE_DAY_CACHE_STORAGE)
        sys.exit(os.EX_OSFILE)

    #NO_OP = args.noop
    if not args.host or not args.file_format or not args.service:
        usage()
        sys.exit(os.EX_USAGE)

    options = {}
    if args.map_file:
        options['map_file'] = args.map_file
    if args.noop:
        options['noop'] = args.noop
    if args.date:
        try:
            datetime.datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            raise SyntaxError('date should respect this format: YYYY-MM-DD')
        options['date'] = args.date
    else:
        options['date'] = str(datetime.datetime.utcnow().date())

    instance = AFSingle(host=host, service=service,
                        file_format=file_format,
                        options=options,
                        logger=logger)
    while instance.step():
        pass

if __name__ == '__main__':
    start_single()
