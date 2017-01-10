"""
Classes to parse and encapsulate data from the tstat logs.
"""
from __future__ import print_function

import csv
import json
import os
import sys
import warnings

from .common import (
    PROTOCOLS,
    TstatBase,
    TstatParseException,
    TstatParseWarning,
    TstatTransportException,
)

from .transport import TRANSPORT_MAP
from .format import capsule_factory


class TstatParse(TstatBase):
    """
    Process the logs in a tstat hierarchy.

    Pass the parsed log entries off for formatting and filtering on transfer
    size, then feed the results to the underlying transfer mechanism (rabbit,
    http, etc).
    """
    LOG_PATTERN = 'log_{0}_complete'
    COMPLETED = '.processed'
    SLICE_SIZE = 100

    def __init__(self, config_capsule):
        super(TstatParse, self).__init__(config_capsule)
        self._tstat_dir = self._validate_path(self._options.directory)
        self._has_data = False
        self._protocols = PROTOCOLS

        try:
            self._transport = TRANSPORT_MAP.get(self._options.transport)(self._config)
        except TstatTransportException as ex:
            msg = 'unable to initialize {t} adapter: {e}'.format(
                t=self._options.transport, e=str(ex))
            raise TstatParseException(msg)

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
        Some logs have a bogus last line. If any of the values are
        None, the entire row is considered non-valid.

        Similarly, check the keys for None values as well. If a log line
        is malformed - like if it is too long due to some kind of
        append error - the DictReader will generate a key of None.
        That will also mark the line as non-valid.
        """
        valid = True
        for k, v in list(rowdict.items()):
            if k is None or v is None:
                valid = False
                break
        return valid

    def process_output(self, root, _, files):
        """Process the logs in a single tstat output directory."""

        # is this a tstat output directory?
        if not root.endswith('.out'):
            return

        # does it contain any logs?
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
            # self._debug_log('process_output.done', 'skipping: {0}'.format(log_path))
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

                with open(self._get_log(log_path, i), 'r') as(csvfile):
                    reader = csv.DictReader(csvfile, delimiter=' ')
                    for row in reader:
                        # validate the row before we proceed
                        if not self._check_row(row):
                            self._log('process_output.warn',
                                      'bad row in {0}: {1}'.format(self._get_log(log_path, i), row))
                            self.warn('bad row in {0}: {1}'.format(self._get_log(log_path, i), row))
                            continue
                        # looks good
                        payload += capsule_factory(row, i, self._config)

        # try to process and mark that directory done if the
        # processing is successful
        try:
            self._process_payload(payload)

            with open(self._get_state(log_path), 'w') as fh:
                fh.write('processed')

        except TstatParseException as ex:
            self._log('process_output.error', 'Payload processing failed: {0}'.format(str(ex)))
            raise TstatParseException(
                'Error sending to transport [{0}]: {1}'.format(self._options.transport, str(ex)))

    def _slice_payload(self, payload):
        """Generate a list of smaller lists to keep the writes to the remote
        message queue sane."""
        return [payload[x:x + self.SLICE_SIZE] for x in range(0, len(payload), self.SLICE_SIZE)]  # pylint: disable=line-too-long

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
            self._log('_process_payload.done', 'no payload')

    def _get_json_string(self, objs):  # pylint: disable=no-self-use
        ret = [x.to_json_packet() for x in objs]
        return json.dumps(ret, indent=4)

    def _xport(self, objs):
        """Send a measured list of objects to message queue."""

        p_load = self._get_json_string(objs)

        status = True
        err = ''

        # if --no-transport set, presume message debugging/etc.
        if self._options.no_transport:
            self._log('_xport.no_transport',
                      '--no-transport set, not sending payload/dumping json to stdout')
            print(p_load, file=sys.stdout)
            return status, err

        try:
            self._transport.set_payload(p_load)
            self._transport.send()

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
