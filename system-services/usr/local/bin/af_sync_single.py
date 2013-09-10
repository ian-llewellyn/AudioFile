#!/usr/bin/env python
""" This module handles a single Audio File process """

## Local Variables
tgt_fp = None
recent_truncations = []


## Import Modules
import urllib2
import time
from datetime import datetime
import os
from sys import exit, argv
import simplejson
import argparse
#from socket import gethostname
import logging
import logging.handlers

import sys
sys.path.append('/home/paco/Projects/RTE/usr/local/lib/')
import values


class AF_Single(object):
    def __init__(self, args):
        self.deltas = []
        self._args = args
        self.date = args.date or values.date
        self.host = args.host
        self.format = args.format
        self.service = args.service
        self.map_file = args.map_file
        self.operation = not args.noop

    def _get_args(self, arg):
        return getattr(self._args, arg) or getattr(values, arg)

    def process(self):
        no_progress_sleep_time = 0
        try:
            # Get a list of files for this date from the server
            # and loop through them
            for record in get_file_list(self.host, self.format,
                                        self.service, self.date):
                # For ease...
                src_file = record['file']
                target_file = file_map(self.date, self.map_file, src_file,
                                       self.format, self.service)
                if not target_file:
                    # I can't possibly go on - I have no target!
                    logger.warning('file_map returned no target file '
                                   'for source file: %s' % src_file)
                    continue

                # Reset variable for each file that's encountered
                delta_failures = 0

                # Prepare the file or skip it altogether!
                if(src_file != os.path.basename(target_file)
                   and target_file not in recent_truncations):
                    # A map file is being used, empty this file
                    # (it hasn't been done in over a day!)
                    logger.info('Truncated target file: %s' % target_file)
                    open(target_file, 'w').truncate()
                    recent_truncations.append(target_file)
                    if len(recent_truncations) > 24:
                        recent_truncations.remove(recent_truncations[0])

                elif(os.path.isfile(target_file)
                     and record['size'] == os.stat(target_file).st_size):
                    # Source and target files have the same size,
                    # so target is probably fully up-to-date
                    logger.info('Target File: %s has same size as '
                                'Source File: %s'
                                % (target_file, src_file))
                    continue

                # Work is to be done on this file
                # (only if tgt_file size == 0) ?
                logger.info('Target File: %s started' % target_file)
                req_URI = ('http://%s/audio/%s/%s/%s/%s' %
                           (self.host, self.format,
                            self.service, self.date, src_file))

                delta = Delta(req_URI, target_file, self.operation)
                while delta_failures <= values.DELTA_RETRIES:
                    while delta.fetch():
                        # Successful update - reset failure count and sleep
                        delta_failures = 0
                        no_progress_sleep_time = 0
                        logger.debug('Delta success - About to sleep for %d ms'
                                     % values.INTER_DELTA_SLEEP_TIME)
                        time.sleep(values.INTER_DELTA_SLEEP_TIME / 1000.0)

                    # Unsuccessful update - mark as a failure and sleep
                    delta_failures += 1
                    logger.debug('Delta failed %d time(s) '
                                 '- About to sleep for %d ms' %
                                 (delta_failures,
                                  values.INTER_DELTA_SLEEP_TIME))
                    time.sleep(values.INTER_DELTA_SLEEP_TIME / 1000.0)

                # (at least once an hour - more if errors)
                logger.info('Delta retries: %d exceeded'
                            % values.DELTA_RETRIES)
                delta.tgt_fp.close()
                delta.tgt_fp = None

            # If a date was passed in, then exit now
            if self.date:
                logger.info('No more updates for date: %s - Exiting'
                            % self.date)
                exit(os.EX_OK)

            # If no progress is made, we don't want the script going
            # to 100% CPU. Back off..
            if no_progress_sleep_time > values.NO_PROGRESS_SLEEP_TIME:
                no_progress_sleep_time = values.NO_PROGRESS_SLEEP_TIME
                logger.warning('no_progress_sleep_time hit max. '
                               'About to sleep for %d ms'
                               % no_progress_sleep_time)
            else:
                logger.info('No progress - About to sleep for %d ms'
                            % no_progress_sleep_time)

            time.sleep(no_progress_sleep_time / 1000)
            no_progress_sleep_time = (no_progress_sleep_time * 2) + 1000
        except:
            logger.exception('Caught unhandled exception')
            raise


## Global Function Definitions
class Delta(object):
    def __init__(self, uri, target_file, operation=True):
        self.uri = uri
        self.target_file = target_file
        self.operation = operation
        try:
            self.tgt_fp = open(self.target_file, 'ab')
        except IOError:
            os.makedirs(os.path.dirname(os.path.realpath(self.target_file)))
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
        logger.debug('File: %s has size: %d' % (self.target_file, offset))

        http_req = urllib2.Request(self.uri)
        # Only get updates - THIS IS THE MAGIC
        http_req.headers['Range'] = 'bytes=%s-' % offset

        logger.debug('Requesting: %s' % self.uri)
        try:
            http_resp = urllib2.urlopen(http_req)
        except urllib2.HTTPError, error:
            logger.warning('Received HTTP error: %d - %s'
                           % (error.code, error.reason))
            # We know about only one type of HTTP error
            # we can recover from - A 416
            if error.code != 416:
                logger.exception(1, 'Can\'t handle HTTP error: %d - %s'
                                 % (error.code, error.reason))
                raise
            # Certain servers produce
            # HTTP 416: Requested Range Not Satisfiable responses
            data_length = 0
            resp_code = error.code
        except urllib2.URLError, error:
            # If a firewall is blocking access, you get:
            # 113, 'No route to host'
            logger.warning('Received URLError in function: '
                           'fetch_delta(%s, %s): %s'
                           % (self.uri, self.target_file, error))
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
            logger.info('Delta failure %d: Offset: %d '
                        'HTTP_STATUS_CODE: %d data_length: %d'
                        % (self.failures + 1, offset, resp_code, data_length))
            return False

        # No operation
        if not self.operation:
            logger.info('Dry run %d: Offset: %d '
                        'HTTP_STATUS_CODE: %d data_length: %d'
                        % (self.failures + 1, offset, resp_code, data_length))
            return False

        # Write the update and flush to disk
        chunk = True
        while chunk:
            chunk = http_resp.read(values.CHUNK_SIZE)
            self.tgt_fp.write(chunk)
            self.tgt_fp.flush()

        logger.debug('Delta success: HTTP_STATUS_CODE: %d data_length: %d'
                     % (resp_code, data_length))
        return True


def get_file_list(host, format, service, date):
    """ get_file_list(host, format, service, date) -> [
        {'title': '01:00:00', 'file': '2012-08-30-00-00-00-00.mp2',
         'size': 123456}*
    ]
    Returns an array from the directory listing received by a HTTP call such
    as: http://host/format/service/date/
    """
    url = ('http://%s/webservice/v2/listfiles.php?format=%s&service=%s&date=%s'
           % (host, format, service, date))
    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req)
    except urllib2.URLError, error:
        # If a firewall is blocking access, you get: 113, 'No route to host'
        logger.warning('Received URLError in function: '
                       'get_file_list(%s, %s, %s, %s): %s'
                       % (host, format, service, date, error))
        return []
    else:
        decoded = simplejson.loads(resp.read())

    #return record['file'] for record in decoded['files']]
    return decoded['files']


## Local Function Definitions
def usage():
    print '%s -h <host> -s <service> -f <format> [-v] [-n]' % argv[0]
    return


def file_map(date, map_file, src_file, format, service):
    """ file_map(src_file) -> target_file
    For a given source file, do a lookup in the map and return the
    relevant target file.
    """
    date = date or str(datetime.utcnow().date())
    if not map_file:
        return os.path.sep.join(
            [values.AUDIOFILE_DAY_CACHE_STORAGE, format,
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
    parser = argparse.ArgumentParser(conflict_handler='resolve')

    parser.add_argument('-h', '--host', dest='host', type=str, required=True,
                        help='The host where the data comes from')
    parser.add_argument('-f', '--format', dest='format', type=str,
                        required=True,
                        help=('The format of your audio file, '
                              'either mp2 or mp3'))

    parser.add_argument('-s', '--service', dest='service', type=str,
                        required=True,
                        help='The service where the data comes from')

    parser.add_argument('-d', '--date', dest='date', type=str,
                        help='The date you want to get the data for')
    parser.add_argument('-m', '--map-file', dest='map_file', type=str,
                        help='No idea')

    parser.add_argument('-v', '--verbose', dest='verbosity', type=int,
                        help='Verbosity level.')
    parser.add_argument('-n', '--noop', dest='noop', action='store_true',
                        default=False, help='Dry run. Doesn\'t do anything.')

    args = parser.parse_args()
    return args

## Pre-processing
logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
standard_format = logging.Formatter('[%(asctime)s] '
                                    '%(process)d %(levelname)s: %(message)s')


def setup_log_handlers(log_dict):
    log_file = log_dict['log_file']
    standard_format = log_dict['standard_format']
    file_handler = log_dict['file_handler']

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(values.LOGFILE_LOG_LEVEL)
    file_handler.setFormatter(standard_format)
    logger.addHandler(file_handler)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(values.STDERR_LOG_LEVEL)
    stderr_handler.setFormatter(standard_format)
    logger.addHandler(stderr_handler)

    #email_handler = logging.handlers.SMTPHandler(
    #    'localhost',
    #    'AudioFile Rea-Time Sync <af-sync-%s-%s@%s>'
    #    % (args.service, args.format, gethostname()),
    #    ADMIN_EMAILS, 'Log output from af-sync-%s-%s'
    #    % (args.service, args.format)
    #)
    #
    #email_handler.setLevel(EMAIL_LOG_LEVEL)
    #email_handler.setFormatter(standard_format)
    #logger.addHandler(email_handler)
    #
    #


def main():
    args = setup_parser()

    instance = AF_Single(args)

    log_file = ('/var/log/audiofile/af-sync-%s-%s.log'
                % (args.service, args.format))

    ## System Integrity Checks
    # Bail out early if the target directory doesn't exist.
    # Only happens if a map file is not being used.
    if(not args.map_file
       and not os.path.exists(values.AUDIOFILE_DAY_CACHE_STORAGE)):
        logger.fatal('AUDIOFILE_DAY_CACHE_STORAGE: %s does not exist'
                     % values.AUDIOFILE_DAY_CACHE_STORAGE)
        exit(os.EX_OSFILE)

    log_dict = {
        'stderr_log_level': args.verbosity or values.STDERR_LOG_LEVEL,
        'log_file': ('/var/log/audiofile/af-sync-%s-%s.log'
                     % (args.service, args.format)),
        'standard_format': logging.Formatter(
            '[%(asctime)s] %(process)d %(levelname)s: %(message)s'
        ),
        'file_handler': logging.FileHandler(log_file)
    }

    setup_log_handlers(log_dict)
    #NO_OP = args.noop
    if not args.host or not args.format or not args.service:
        #usage()
        exit(os.EX_USAGE)
    # Set today's date !!! UTC
    instance = AF_Single(args)
    instance.process()


if __name__ == '__main__':
    main()
