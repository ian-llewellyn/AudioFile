#!/usr/bin/env python
""" This module handles a single Audio File process """

## Import Modules
import urllib2
import time
import datetime
import os
import sys
import optparse
#from socket import gethostname
import logging
import logging.handlers

sys.path.append('/home/paco/Projects/RTE/usr/local/lib/')
import values


class AFSingle(object):
    """ Single process. It creates deltas objects """
    def __init__(self, host, service, file_format, record, options=None):
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
        self.host = host
        self.file_format = file_format
        self.service = service
        self.date = values.DATE
        self.operation = True
        self.map_file = None
        self.filename = record['file']
        self.size = record['size']
        self.title = record['title']
        if options is not None:
            if 'date' in options:
                self.date = options['date']
            if 'noop' in options:
                self.operation = not options['noop']
            if 'map_file' in options:
                self.map_file = options['map_file']
        self.target_file = file_map(self.date, self.map_file,
                                    self.filename,
                                    self.file_format,
                                    self.service)

    def process(self):
        """ Process the single instance """
        recent_truncations = []
        no_progress_sleep_time = 0
        try:
            # Get a list of files for this date from the server
            # and loop through them
            # For ease...
            if not self.target_file:
                # I can't possibly go on - I have no target!
                logging.warning('file_map returned no target file '
                                'for source file: %s', self.filename)
                return

            # Reset variable for each file that's encountered
            delta_failures = 0

            # Prepare the file or skip it altogether!
            if(self.filename != os.path.basename(self.target_file)
               and self.target_file not in recent_truncations):
                # A map file is being used, empty this file
                # (it hasn't been done in over a day!)
                logging.info('Truncated target file: %s', self.target_file)
                open(self.target_file, 'w').truncate()
                recent_truncations.append(self.target_file)
                if len(recent_truncations) > 24:
                    recent_truncations.remove(recent_truncations[0])

            elif(os.path.isfile(self.target_file)
                 and self.size == os.stat(self.target_file).st_size):
                # Source and target files have the same size,
                # so target is probably fully up-to-date
                logging.info('Target File: %s has same size as '
                             'Source File: %s', self.target_file,
                             self.filename)
                return

            # Work is to be done on this file
            # (only if tgt_file size == 0) ?
            logging.info('Target File: %s started', self.target_file)
            req_uri = ('http://%(host)s/audio/%(file_format)s/%(service)s'
                       '/%(date)s/%(filename)s' %
                       {'host': self.host,
                        'file_format': self.file_format,
                        'service': self.service,
                        'date': self.date,
                        'filename': self.filename})

            delta = Delta(req_uri, self.target_file, self.operation)
            while delta_failures <= values.DELTA_RETRIES:
                while delta.fetch():
                    # Successful update - reset failure count and sleep
                    delta_failures = 0
                    no_progress_sleep_time = 0
                    logging.debug('Delta success - About to sleep '
                                  'for %d ms', values.INTER_DELTA_SLEEP_TIME)
                    time.sleep(values.INTER_DELTA_SLEEP_TIME / 1000.0)

                # Unsuccessful update - mark as a failure and sleep
                delta_failures += 1
                logging.debug('Delta failed %d time(s) '
                              '- About to sleep for %d ms',
                              delta_failures, values.INTER_DELTA_SLEEP_TIME)
                time.sleep(values.INTER_DELTA_SLEEP_TIME / 1000.0)

            # (at least once an hour - more if errors)
            logging.info('Delta retries: %d exceeded', values.DELTA_RETRIES)
            delta.tgt_fp.close()
            delta.tgt_fp = None

            # If a date was passed in, then exit now
            if self.date:
                logging.info('No more updates for date: %s - Exiting',
                             self.date)
                return

            # If no progress is made, we don't want the script going
            # to 100% CPU. Back off..
            if no_progress_sleep_time > values.NO_PROGRESS_SLEEP_TIME:
                no_progress_sleep_time = values.NO_PROGRESS_SLEEP_TIME
                logging.warning('no_progress_sleep_time hit max. '
                                'About to sleep for %d ms',
                                no_progress_sleep_time)
            else:
                logging.info('No progress - About to sleep for %d ms',
                             no_progress_sleep_time)

            time.sleep(no_progress_sleep_time / 1000)
            no_progress_sleep_time = (no_progress_sleep_time * 2) + 1000
        except:
            logging.exception('Caught unhandled exception')
            raise


## Global Function Definitions
class Delta(object):
    """ Delta class that fetches the data from the server """
    def __init__(self, uri, target_file, operation=True):
        """ Constructor. It needs a URI, and a target file """
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
        logging.debug('File: %s has size: %d', self.target_file, offset)

        http_req = urllib2.Request(self.uri)
        # Only get updates - THIS IS THE MAGIC
        http_req.headers['Range'] = 'bytes=%s-' % offset

        logging.debug('Requesting: %s', self.uri)
        try:
            http_resp = urllib2.urlopen(http_req)
        except urllib2.HTTPError, error:
            logging.warning('Received HTTP error: %d - %s',
                            error.code, error.reason)
            # We know about only one type of HTTP error
            # we can recover from - A 416
            if error.code != 416:
                logging.exception('Can\'t handle HTTP error: %d - %s',
                                  error.code, error.reason)
                raise
            # Certain servers produce
            # HTTP 416: Requested Range Not Satisfiable responses
            data_length = 0
            resp_code = error.code
        except urllib2.URLError, error:
            # If a firewall is blocking access, you get:
            # 113, 'No route to host'
            logging.warning('Received URLError in function: '
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
            logging.info('Delta failure %d: Offset: %d '
                         'HTTP_STATUS_CODE: %d data_length: %d',
                         self.failures + 1, offset, resp_code, data_length)
            return False

        # No operation
        if not self.operation:
            logging.info('Dry run %d: Offset: %d '
                         'HTTP_STATUS_CODE: %d data_length: %d',
                         self.failures + 1, offset, resp_code, data_length)
            return False

        # Write the update and flush to disk
        chunk = True
        while chunk:
            chunk = http_resp.read(values.CHUNK_SIZE)
            self.tgt_fp.write(chunk)
            self.tgt_fp.flush()

        logging.debug('Delta success: HTTP_STATUS_CODE: %d data_length: %d',
                      resp_code, data_length)
        return True


## Local Function Definitions
def usage():
    """ Prints the right way to use the script """
    print '%s -h <host> -s <service> -f <format> [-v] [-n]' % sys.argv[0]
    return


def file_map(date, map_file, src_file, file_format, service):
    """ file_map(src_file) -> target_file
    For a given source file, do a lookup in the map and return the
    relevant target file.
    """
    date = date or str(datetime.datetime.utcnow().date())
    if not map_file:
        return os.path.sep.join(
            [values.AUDIOFILE_DAY_CACHE_STORAGE, file_format,
             service, date, src_file]
        )
    else:
        # calculate the key i.e. local day of week and hour
        dow, hour = utc_file_to_local(src_file)
        # open mapping file
        map_file = open(map_file, 'r')
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

#    parser.add_argument('-h', '--host', dest='host', type=str, required=True)
#    parser.add_argument('-f', '--format', dest='file_format', type=str,
#                        required=True,
#                        help=('The format of your audio file, '
#                              'either mp2 or mp3'))

#    parser.add_argument('-s', '--service', dest='service', type=str,
#                        required=True,
#                        help='The service where the data comes from')
#
#    parser.add_argument('-d', '--date', dest='date', type=str,
#                        help='The date you want to get the data for')
#    parser.add_argument('-m', '--map-file', dest='map_file', type=str,
#                        help='No idea')
#
#    parser.add_argument('-v', '--verbose', dest='verbosity', type=int,
#                        help='Verbosity level.')
#    parser.add_argument('-n', '--noop', dest='noop', action='store_true',
#                        default=False, help='Dry run. Doesn\'t do anything.')

    args = parser.parse_args()
    return args[0]

## Pre-processing


def setup_log_handlers(log_dict):
    """ Sets up the log handlers """
    log_format = '[%(asctime)s] %(process)d %(levelname)s: %(message)s'
    logging.basicConfig(format=log_format, level=log_dict['level'])
    log_file = log_dict['log_file']
    standard_format = log_dict['standard_format']
    file_handler = log_dict['file_handler']

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(values.LOGFILE_LOG_LEVEL)
    file_handler.setFormatter(standard_format)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(values.STDERR_LOG_LEVEL)
    stderr_handler.setFormatter(standard_format)

    #email_handler = logging.handlers.SMTPHandler(
    #    'localhost',
    #    'AudioFile Rea-Time Sync <af-sync-%s-%s@%s>'
    #    % (args.service, args.format, gethostname()),
    #    values.ADMIN_EMAILS, 'Log output from af-sync-%s-%s'
    #    % (args.service, args.file_format)
    #)
    #
    #email_handler.setLevel(values.EMAIL_LOG_LEVEL)
    #email_handler.setFormatter(standard_format)
    #print(email_handler)
    #
    #


def test():
    """ Tests a single instance """
    args = setup_parser()

    try:
        log_level = getattr(logging, args.verbosity.upper())
    except AttributeError:
        logging.critical('Please provide a good verbosity option: '
                         'info, debug, critical or warning')
        sys.exit()

    log_file = ('/var/log/audiofile/af-sync-%s-%s.log'
                % (args.service, args.file_format))

    log_dict = {
        'stderr_log_level': args.verbosity or values.STDERR_LOG_LEVEL,
        'log_file': ('/var/log/audiofile/af-sync-%s-%s.log'
                     % (args.service, args.file_format)),
        'standard_format': logging.Formatter(
            '[%(asctime)s] %(process)d %(levelname)s: %(message)s'
        ),
        'file_handler': logging.FileHandler(log_file),
        'level': log_level
    }
    setup_log_handlers(log_dict)
    ## System Integrity Checks
    # Bail out early if the target directory doesn't exist.
    # Only happens if a map file is not being used.
    if(not args.map_file
       and not os.path.exists(values.AUDIOFILE_DAY_CACHE_STORAGE)):
        logging.fatal('AUDIOFILE_DAY_CACHE_STORAGE: %s does not exist',
                      values.AUDIOFILE_DAY_CACHE_STORAGE)
        sys.exit(os.EX_OSFILE)

    #NO_OP = args.noop
    if not args.host or not args.file_format or not args.service:
        usage()
        sys.exit(os.EX_USAGE)
    # Set today's date !!! UTC
    host = args.host
    file_format = args.file_format
    service = args.service

    date = str(datetime.datetime.utcnow().date())

    records = af_sync_multi.get_file_list(host, file_format, service, date)
    for record in records:
        instance = AFSingle(host=host, service=service,
                            file_format=file_format,
                            record=record)
        instance.process()

if __name__ == '__main__':
    import af_sync_multi
    test()
