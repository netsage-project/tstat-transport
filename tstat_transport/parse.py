"""
Classes to parse and encapsulate data from the tstat logs.
"""

import collections
import csv
import json
import os
import warnings

from .common import (
    TstatBase,
    TstatParseException,
    TstatParseWarning,
    TstatTransportException,
)

from .transport import TRANSPORT_MAP

# These classes encapsulate and manipulate the data from the
# tstat logs.


class BaseLogEntryCapsule(object):
    """Base class for the capsule classes."""

    def __init__(self, values, logtype):
        self._values = self._xform_values(values)
        self._logtype = logtype

    def _generate_range(self):
        """override in subclasses - generate a list of the column indexes
        that we want to extract from the logs we're reading."""
        raise NotImplementedError

    @property
    def header_trim(self):
        """override in subclass - string to shave from keys from the
        csv DictReader header."""
        raise NotImplementedError

    @property
    def ts_column(self):
        """override in subclass - column that contains the timestamp
        we're using for the payload."""
        raise NotImplementedError

    def _xform_values(self, valuedict):  # pylint: disable=no-self-use
        """Transform the row values. Shave column :nn from key and return an
        OrderedDict of the values."""
        rng = self._generate_range()

        row_values = dict()

        for k in valuedict.keys():
            label, idx = k.replace(self.header_trim, '').split(':')
            idx = int(idx)
            if idx in rng:
                row_values[idx] = (label, valuedict[k])

        ret = collections.OrderedDict()

        for i in rng:
            ret[row_values[i][0]] = row_values[i][1]

        return ret

    def to_json_packet(self):
        """Return the payload as a json packet formatted to send to TSDS."""
        return dict(
            interval=600,
            time=self.timestamp,
            protocol=self._logtype,
            values=self.value_dict(),
        )

    def value_dict(self):
        """Return a xformed dict of the values."""
        return self._values

    @property
    def timestamp(self):
        """Get the appropriate timestamp column value and round to an int."""
        return int(round(float(self._values.get(self.ts_column)))) / 1000

    @property
    def c_bytes_all(self):
        """Get the c_bytes_all value as an int to the walker can see if we
        want to add this to they payload."""
        return int(self._values.get('c_bytes_all'))


class TcpLogEntryCapsule(BaseLogEntryCapsule):
    """
    Encapsulates a line from a tstat tcp log. Returns data in a form that can
    be sent to TSDS.

    capture columns: 1-30, 45-58, and X-(X+45) where X is the offset where
    the tcp options set starts.
    """
    def __init__(self, values, logtype):
        self._offset = self._get_offset(values)
        super(TcpLogEntryCapsule, self).__init__(values, logtype)

    def _get_offset(self, vals):  # pylint: disable=no-self-use
        """get the offset for the tcp options set values."""
        for k in vals.keys():
            if k.startswith('c_f1323_opt:'):
                return int(k.split(':')[1])

    def _generate_range(self):
        return range(1, 31) + range(45, 59) + range(self._offset, self._offset+46)

    @property
    def header_trim(self):
        """string to shave from keys from the csv DictReader header keys."""
        return '#09#'

    @property
    def ts_column(self):
        """column that contains the timestamp we're using for the payload."""
        return 'first'


class UdbLogEntryCapsule(BaseLogEntryCapsule):
    """
    Encapsulates a line from a tstat udp log. Returns data in a form that can
    be sent to TSDS.

    capture columns: 1-18
    """
    def _generate_range(self):
        return range(1, 19)

    @property
    def header_trim(self):
        """string to shave from keys from the csv DictReader header keys."""
        return '#'

    @property
    def ts_column(self):
        """column that contains the timestamp we're using for the payload."""
        return 'c_first_abs'


# This code is responsible for parsing the tstat logs to get the data into
# the capsule classes and send the data off to the transport layer.


class TstatParse(TstatBase):
    """
    Class to handle processing the files in a TSTAT data hierarchy,
    and format the output for sending over HTTP.
    """
    LOG_PATTERN = 'log_{0}_complete'
    COMPLETED = '.processed'
    SLICE_SIZE = 100

    def __init__(self, config_capsule):
        super(TstatParse, self).__init__(config_capsule)
        self._tstat_dir = self._validate_path(self._options.directory)
        self._has_data = False
        self._protocols = ['tcp', 'udp']
        self._capsules = dict(
            tcp=TcpLogEntryCapsule,
            udp=UdbLogEntryCapsule,
        )

    def _fix_path(self, path, *args):  # pylint: disable=no-self-use
        """normalize and absolute-ize a path or set of path components"""
        return os.path.abspath(
            os.path.normpath(
                os.path.join(path, *args)
            )
        )

    def _validate_path(self, path, *args):
        """call _fix_path and validate that the path indicated exists."""
        fpath = self._fix_path(path, *args)

        if not os.path.exists(fpath):
            raise TstatParseException('Invalid path: {0}'.format(fpath))

        return fpath

    def _get_state(self, log_path):
        """Get path to the state file for the directory being processed.
        If the state file already exists, return None, otherwise, return
        a path where it will be written to."""
        spath = self._fix_path(log_path, self.COMPLETED)

        if os.path.exists(spath):
            return None

        return spath

    def _get_log(self, log_path, log_type):
        """Get path to the output log to process. Return none if
        it does not exist."""
        try:
            return self._validate_path(log_path, self.LOG_PATTERN.format(log_type))
        except TstatParseException:
            return None

    def _check_row(self, rowdict):  # pylint: disable=no-self-use
        """Make sure that the csv DictReader returned a valid row.
        Some logs have a bogus last line."""
        valid = True
        for v in rowdict.values():
            if v is None:
                valid = False
                break
        return valid

    def _get_capsule(self, logtype):
        """Return the appropriate encapsulation class."""
        return self._capsules.get(logtype)

    def process_output(self, root, _, files):
        """Process the logs in a single tstat output directory."""

        # is this a tstat output directory?
        if not root.endswith('.out'):
            return

        # does it potentailly contain any logs?
        logs_found = False

        for i in self._protocols:
            if self.LOG_PATTERN.format(i) in files:
                logs_found = True
                break

        if not logs_found:
            return

        log_path = self._validate_path(root)

        # has this directory been processed already?
        if self._get_state(log_path) is None:
            self._verbose_log('process_output.done', 'skipping: {0}'.format(log_path))
            return

        # try to process both logs
        payload = list()

        for i in self._protocols:
            if self._get_log(log_path, i) is None:
                self.warn('No {0} log at path: {1} - skipping'.format(i, log_path))
                continue
            else:
                self._log('process_output.run',
                          'processing: {0}'.format(self._get_log(log_path, i)))
                # print 'processing', self._get_log(log_path, i)
                with open(self._get_log(log_path, i), 'rb') as(csvfile):
                    reader = csv.DictReader(csvfile, delimiter=' ')
                    for row in reader:
                        # validate the row before we proceed
                        if not self._check_row(row):
                            self._log('process_output.warn',
                                      'bad row in {0}: {1}'.format(self._get_log(log_path, i), row))
                            self.warn('bad row in {0}: {1}'.format(self._get_log(log_path, i), row))
                            continue
                        # looks good
                        log_capsule = self._get_capsule(i)(row, i)
                        if log_capsule.c_bytes_all >= self._options.bytes:
                            payload.append(log_capsule)

        # try to process and mark that directory done if the
        # processing is successful
        try:
            self._process_payload(payload)

            with open(self._get_state(log_path), 'w') as fh:
                fh.write('processed')

            # self._log('process_output.done', 'processed')

        except TstatParseException as ex:
            self._log('process_output.error', 'Payload processing failed: {0}'.format(str(ex)))
            raise TstatParseException(
                'Error sending to transport [{0}]: {1}'.format(self._options.transport, str(ex)))

    def _slice_payload(self, payload):
        """Generate a list of smaller lists to keep the writes to the remote
        message queue sane."""
        return [payload[x:x+self.SLICE_SIZE] for x in range(0, len(payload), self.SLICE_SIZE)]  # pylint: disable=line-too-long

    def _process_payload(self, payload):
        """Ship the payload off in appropriately sized blasts."""

        if len(payload):

            self._has_data = True

            for i in self._slice_payload(payload):

                status, err = self._xport(i)

                if status:
                    self._verbose_log('_process_payload.run', 'successfully processed slice')
                else:
                    self._log('_process_payload.error', 'error processing slice: {0}'.format(err))
                    raise TstatParseException(err)
        else:
            self._log('_process_payload.done', 'no playload')

    def _get_json_string(self, objs):  # pylint: disable=no-self-use
        ret = [x.to_json_packet() for x in objs]
        return json.dumps(ret, indent=4)

    def _xport(self, objs):
        """Send a measured list of objects to message queue."""

        p_load = self._get_json_string(objs)

        status = True
        err = ''

        try:
            xport = TRANSPORT_MAP.get(self._options.transport)(self._config)

            xport.set_payload(p_load)
            xport.send()

            # print p_load
        except TstatTransportException as ex:
            status = False
            err = ex.value

        return status, err

    @property
    def has_data(self):
        """Has the walker seen data?"""
        return self._has_data

    def warn(self, msg):  # pylint: disable=no-self-use
        """Emit a warning."""
        warnings.warn(msg, TstatParseWarning, stacklevel=2)
