#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Usage:
  af_sync_single.py -h <host> -s <service> -f <format> [-d <YYYY-mm-dd>]                                                [-m <map_file>] [-p <params_file>] [--noop]
  af_sync_single.py (--help | --version)

  Options:
    -h, --host=<host>           The host to be used to source the files.
    -s, --service=<service>     The AudioFile service name to be synchronised.
    -f, --format=<format>       Provide the format to sync, mp2 or mp3.
    -d, --date=<date>           Only process files for given date (Format YYYY-MM-DD).
    -m, --mapfile=<map_file>    Give the absolute path of a map file to use.
    -p, --params=<params_file>  Path to a file containing AFSingle parameters.
                                [default: /etc/af-sync.d/af-sync.conf]
    -n, --noop                  No file operations, show what would be done.
    --help                      Show this screen.
    --version                   Show version number and exit.
"""
__version__ = '0.2'

import logging

# DEFAULTS
#DEFAULT_PARAMS_FILE = '/etc/af-sync.d/af-sync.conf'
DEFAULT_LOG_PATH = '/var/log/audiofile'
DEFAULT_LOG_LEVEL = 'DEBUG'
DEFAULT_INTER_DELTA_MIN_TIME = 1250
DEFAULT_DELTA_RETRIES = 2
DEFAULT_NO_PROGRESS_MAX_WAIT = 120000
DEFAULT_MAIN_LOOP_MIN_TIME = 750
DEFAULT_DOWNLOAD_CHUNK_SIZE_MAX = 2 * 1024 * 1024
DEFAULT_AUDIO_STORAGE_PATH = '/var/audiofile/audio'


import datetime, urllib2, simplejson, os, time
LOGGING = {}

def utc_file_to_local(file_title):
    """ utc_file_to_local(file_title) -> 2 tuple
    This function takes the time provided in the file name as UTC, converts
    it to local time and returns a tuple with the day-of-week and hour.
    File title should be of the format YYYY-mm-dd-HH-MM-SS-xx.mp2/3.
    """
    # Strip unrequired trailing characters and append UTC to force strptime's hand
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

class Record(dict):
    def __hash__(self):
        return hash(self['file'])

    def __eq__(self, other):
        # This only works because we know that this will only be
        # called from within one instance, i.e. service.
        return self['file'] == other['file']

class AFSingle(set):
    """
    This class is used to hold the parameters and state of a synchronising
    process.
    instance = AFSingle(host=host, service=service, format=format
        [, date=date][, map_file=map_file][, params=params_dict])
    params_dict = {
        'inter_delta_min_time': int milliseconds,
        'no_progress_max_wait': int milliseconds
    }
    """

    def __init__(self, **kwargs):
        """
        Method involved in setting up an instance of the AFSingle class.
        """
        for key in kwargs:
            self.__dict__[key] = kwargs[key]
        # Required arguments
        if not hasattr(self, 'host') or \
            not hasattr(self, 'service') or \
            not hasattr(self, 'format'):
            raise Exception('host, service and format are required parameters')

        # Optional arguments
        if not hasattr(self, 'date'):
            self.date = None
        elif self.date != None:
            self.date = datetime.datetime.strptime(self.date, '%Y-%m-%d')
        if not hasattr(self, 'map_file'):
            self.map_file = None
        if hasattr(self, 'params'):
            for key in self.params:
                self.__dict__[key] = self.params[key]
            del self.params
        if not hasattr(self, 'inter_delta_min_time'):
                self.inter_delta_min_time = DEFAULT_INTER_DELTA_MIN_TIME
        if not hasattr(self, 'delta_retries'):
                self.delta_retries = DEFAULT_DELTA_RETRIES
        if not hasattr(self, 'no_progress_max_wait'):
                self.no_progress_max_wait = DEFAULT_NO_PROGRESS_MAX_WAIT
        if not hasattr(self, 'log_path'):
                self.log_path = DEFAULT_LOG_PATH
        if not hasattr(self, 'log_level'):
                self.log_level = DEFAULT_LOG_LEVEL
        if not hasattr(self, 'download_chunk_size_max'):
                self.download_chunk_size_max = DEFAULT_DOWNLOAD_CHUNK_SIZE_MAX
        if not hasattr(self, 'audio_storage_path'):
                self.audio_storage_path = DEFAULT_AUDIO_STORAGE_PATH

        self.logger = logging.getLogger('.'.join(['af-sync',
            self.service, self.format]))
        self.logger.addHandler(logging.StreamHandler())
        self.logger.level = self.log_level
        self.logger.info('Initialised %s %s' % (self.service, self.format))
        self.logger.debug('Host: %s, Date: %s, Map File: %s' % (self.host,
            self.date, self.map_file))

        # Initialise internal parameters
        self._target_fp = None
        self._old_records = set()
        self.records_iter = self.__iter__()
        self.next_file()

        self._next_run_time = datetime.datetime.now()
        self._delta_failures = 0
        self._no_progress_sleep_time = 0

    def file_map(self, src_file):
        """ file_map(src_file) -> target_file
        For a given source file, do a lookup in the map and return the
        relevant target file.
        """
        if not self.map_file:
            date = '-'.join(src_file.split('-')[:3])
            return os.path.sep.join([self.audio_storage_path,
                                     self.format, self.service, date, src_file])

        # Calculate the key i.e. local day of week and hour
        dow, hour = utc_file_to_local(src_file)
        # Open mapping file
        map_file = open(self.map_file, 'r')
        # Read contents into array or such
        for line in map_file.readlines():
            # Ignore comment lines
            if line.startswith('#'):
                continue
            kdow, khour, kfile = line.split()
            if dow == int(kdow) and hour == int(khour):
                # Return the corrsponding value
                return kfile
        return None

    def get_file_list(self):
        """
        Gets a JSON list of files available on the server for a particular
        format, service and date.
        """
        """
        get_file_list(host, format, service, date) -> [
            {
                'title': '01:00:00',
                'file': '2012-08-30-00-00-00-00.mp2',
                'size': 123456
            }*
        ]
        Returns an array from the directory listing received by a HTTP call
        such as: http://host/format/service/date/
        """
        self.logger.debug('Called get_file_list()')
        date = datetime.datetime.now().strftime('%Y-%m-%d') \
               if not self.date else self.date.strftime('%Y-%m-%d')
        req = urllib2.Request('http://%s/webservice/v2/listfiles.php?'
                              'format=%s&service=%s&date=%s' % \
                              (self.host, self.format, self.service, date))

        try:
            resp = urllib2.urlopen(req)

        except urllib2.URLError, error:
            # If a firewall is blocking access, you get:
            # HTTP 113, 'No route to host'
            self.logger.warning('Received URLError in function: get_file_list('
                           '%s, %s, %s, %s): %s' % \
                           (self.host, self.format, self.service, date,
                            error))
            return []

        else:
            decoded = simplejson.loads(resp.read())

        #return record['file'] for record in decoded['files']]
        return decoded['files']

    def next_file(self, no_op=False):
        """
        This method lines up the next file for processing. This may involve
        calling the get_file_list method.
        return True if a new file has been lined up
        return False if a new file is not lined up
        We need to determine if we have another file to go to,
        or if we get_file_list again.
        FIXME: How to not go over files numerous times?
        """
        if self._target_fp:
            # Close the existing file if it's open
            no_op or self._target_fp.close()

        try:
            # Get the next record
            current_record = self.records_iter.next()

        except StopIteration:
            # Get the file list
            for record in self.get_file_list():
                self.add(Record(record))

            if self.issuperset(self._old_records):
                # Intersect with old records to pick up where we left off
                self.difference_update(self._old_records)
            else:
                # Clear out old records list
                self._old_records.clear()

            # If no files were received, we failed
            if len(self) == 0:
                return False

            # Set up the iterator
            self.records_iter = sorted(self, key=lambda record: record['file']).__iter__()
            # Get the first record
            current_record = self.records_iter.next()

        self.logger.debug('got next record: %s' % current_record)

        # This stops us going over the same files again
        self._old_records.add(current_record)

        date = '-'.join(current_record['file'].split('-')[:3])
        self._req_URI = 'http://%s/audio/%s/%s/%s/%s' % (self.host,
                        self.format, self.service, date, current_record['file'])
        self._target_file = self.file_map(current_record['file'])
        # Does the directory exist?
        if not os.path.exists(os.path.dirname(self._target_file)):
            # Create the directory - date_dir most likely
            self.logger.info('Creating directory: %s' % \
                        os.path.dirname(self._target_file))
            no_op or os.mkdir(os.path.dirname(self._target_file), 0755)

        self.logger.info('Opening file: %s in append mode' % self._target_file)
        if not no_op:
            self._target_fp = open(self._target_file, 'ab')
            if self.map_file != None:
                # When using map files, we must ensure that we overwrite target
                # files every time to guarantee consistency with the source.
                self._target_fp.truncate(0)
        else:
            self._target_fp = None

        self._delta_failures = 0
        self._no_progress_sleep_time = 0

        return True


    def fetch_delta(self, no_op=False):
        """
        This method is used to actually fetch the next chunk of data and append
        it to the target file.
        return True if we succeed in getting data
        return False if we have problems retreiving data
        return None if we decide not to get data
        """
        """ fetch_delta(host, format, service) -> True/False
        Does a HTTP range request to http://host/format/service/date/file
        fetching only the bytes beyond the end of the target_file size.
        """
        self.logger.debug('Called fetch_delta()')

        if self._target_fp == None:
            self.logger.warning('fetch_delta() fail - No target file')
            return False

        # Move file pointer to the end of the file
        self._target_fp.seek(0, 2)
        # How many bytes have we got already?
        offset = self._target_fp.tell()
        self.logger.debug('File: %s has size: %d' % (self._target_file, offset))

        http_req = urllib2.Request(self._req_URI)
        # Only get updates - THIS IS THE MAGIC
        http_req.headers['Range'] = 'bytes=%s-' % offset

        try:
            self.logger.debug('Requesting: %s' % self._req_URI)
            http_resp = urllib2.urlopen(http_req)

        except urllib2.HTTPError, error:
            self.logger.warning('Received HTTP error: %d - %s' % \
                           (error.code, error.reason))
            # We know about only one type of HTTP error that we can
            # recover from: HTTP 416
            if error.code != 416:
                self.logger.exception(1, 'Can\'t handle HTTP error: %d - %s' % \
                                 (error.code, error.reason))
                raise
            # Certain servers produce HTTP 416:
            # Requested Range Not Satisfiable responses
            data_length = 0
            resp_code = error.code

        except urllib2.URLError, error:
            # If a firewall is blocking access, you get:
            # 113, 'No route to host'
            self.logger.warning('Received URLError in function: '
                           'fetch_delta(%s, %s): %s' % \
                           (self._req_URI, self._target_file, error))
            return False

        else:
            data_length = int(http_resp.headers.getheader('content-length'))
            resp_code = http_resp.code

        # If the file size hasn't changed since the last request, some servers
        # return a 200 response and the full file. Others respond with a
        # HTTP 416 error (which is handled in the except above)

        # One of two conditions signify a failed update:
        # Condition 1
        if offset != 0 and resp_code != 206:
            # We are some way into the file and we did not receive
            # a partial HTTP response
            self.logger.info('Delta failure %d: Partial response not received: '
                        'Offset: %d HTTP_STATUS_CODE: %d data_length: %d' % \
                        (self._delta_failures + 1, offset, resp_code, data_length))
            return False

        # Condition 2
        if data_length <= 0:
            # We received no data at all
            self.logger.info('Delta failure %d: No data received: '
                        'Offset: %d HTTP_STATUS_CODE: %d data_length: %d' % \
                        (self._delta_failures + 1, offset, resp_code, data_length))
            return False

        # The method was called with no operation mode
        if no_op:
            self.logger.info('Dry run %d: Offset: %d '
                        'HTTP_STATUS_CODE: %d data_length: %d' % \
                        (self._delta_failures + 1, offset, resp_code, data_length))
            return False

        # Write the update and flush to disk
        while True:
            chunk = http_resp.read(self.download_chunk_size_max)
            if not chunk:
                break
            self._target_fp.write(chunk)
            self._target_fp.flush()

        self.logger.debug('Delta success: HTTP_STATUS_CODE: %d '
                     'data_length: %d' % (resp_code, data_length))
        return True

    def step(self):
        """
        This method is used to carry out the next operation of the
        synchronising process.
        return True if we succeed in getting data
        return False if we have problems retreiving data
        return None if we decide not to get data
        """
        self.logger.debug('Called step()')

        if datetime.datetime.now() < self._next_run_time:
            self.logger.info('next run time not reached yet, '
                             'returning from step()')
            return None

        self._next_run_time = datetime.datetime.now() + datetime.timedelta(
            milliseconds=self.inter_delta_min_time)

        if self.fetch_delta():
            self._delta_failures = 0
            self._no_progress_sleep_time = 0
            return True
        self._delta_failures += 1
        self.logger.info('Delta failure: %d of %d' % (self._delta_failures,
                                                   self.delta_retries))

        # We didn't receive any data because:
        # 1. We already have the full file
        # 2. We are finished today's files
        # 3. The recorder has stopped
        # 4. There is a network issue...

        if self._delta_failures < self.delta_retries:
            # We should fail delta_retries times before we go
            # on to the next file.
            return False

        if not self.next_file() and self.date != None:
            # Failed to get another file and a date was passed into the program
            return None

        self._no_progress_sleep_time = self._no_progress_sleep_time * 2 or 1
        if self._no_progress_sleep_time > self.no_progress_max_wait:
            self._no_progress_sleep_time = self.no_progress_max_wait
        self._next_run_time = datetime.datetime.now() + datetime.timedelta(
            seconds=self._no_progress_sleep_time)
        return False

    def __hash__(self):
        """
        Implements the standard __hash__ method to allow comparisons.
        """
        # Purposly ommitting self['host'] gives us a nice way to ensure
        # we don't accidentally configure the same service and format
        # from two different hosts.
        return hash(self.service + self.format + (self.date or '') +
                    (self.map_file or ''))

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

    def __str__(self):
        values = [getattr(self, key) for key in ['host', 'service', 'format',
            'date', 'map_file']]
        return 'host: %s, service: %s, format: %s, date: %s, map_file: %s' % \
            tuple(values)

def load_params(params_file):
    params = {}
    try:
        with file(params_file) as params_file:
            eval(compile(params_file.read(), '/dev/null', 'exec'),
                 globals(), params)

    except IOError:
        # Params file not found, using built-in defaults.
        pass

    keys = params.keys()
    for key in keys:
        params[key.lower()] = params[key]
        params.pop(key)

    return params

if __name__ == '__main__':
    # Parse arguments
    from docopt import docopt
    args = docopt(__doc__, version=__version__)

    # Get the parameters
    params = load_params(args['--params'])

    # Instantiate class
    single = AFSingle(host=args['--host'], service=args['--service'],
        format=args['--format'], date=args['--date'],
        map_file=args['--mapfile'], params=params)

    # main loop
    while True:
        next_run_time = datetime.datetime.now() + datetime.timedelta(
            milliseconds=DEFAULT_MAIN_LOOP_MIN_TIME)

        single.step()

        if datetime.datetime.now() < next_run_time:
            sleep_time = (next_run_time - datetime.datetime.now()).total_seconds()
            single.logger.info('main loop is executing too quickly, '
                'sleeping for %f seconds' % sleep_time)
            time.sleep(sleep_time)
