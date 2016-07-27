"""
Classes to format the log entries, code to access them, etc.

Direction is relative to the host so - in and out from the host perspective.
i.e.: when direction is 'in', the source is the client and dest is the dest.
"""

import collections
import warnings

DIRECTIONS = ('in', 'out')


class TstatFormatException(Exception):
    """Custom TstatFormat exception"""
    def __init__(self, value):
        # pylint: disable=super-init-not-called
        self.value = value

    def __str__(self):
        return repr(self.value)


class TstatFormatWarning(Warning):
    """Custom TstatFormat warning"""
    pass


class EntryCapsuleBase(object):
    """Base for the format capsule classes."""
    def __init__(self, row, protocol, direction):
        self._row = self._sanitize_row(row)
        self._protocol = protocol
        self._direction = direction
        self._prefixes = {'in': 'c_', 'out': 's_'}

    @property
    def header_trim(self):
        """override in subclass - string to shave from keys from the
        csv DictReader header."""
        raise NotImplementedError

    def _sanitize_row(self, row):
        """Remove any jank from the log headers so we have a dict with
        'pure' key names stripped of garbage and the :nn index part."""
        for k in row.keys():
            row[k.replace(self.header_trim, '').split(':')[0]] = row.pop(k)
        return row

    def _directional_key(self, key):
        """
        Returns the proper c_ or s_ variant from the row payload depending
        on the direction that this instance is going. Casts numeric strings
        to actual numeric values.
        """
        key = '{d}{k}'.format(d=self._prefixes.get(self._direction), k=key)
        return self._cast_to_numeric(self._row.get(key))

    def _static_key(self, key):
        """
        Return a "non-directional" value from the payload. Used to contrast
        against _directional_key() and to have one entry point for casting.
        Casts numeric strings to actual numeric values.
        """
        return self._cast_to_numeric(self._row.get(key))

    def _cast_to_numeric(self, val):  # pylint: disable=no-self-use
        """Take the string values from the logs and attempt to cast them
        to actual numeric types.
        """

        if isinstance(val, str) or isinstance(val, unicode):

            try:
                return int(val)
            except ValueError:
                pass

            try:
                return round(float(val), 3)
            except ValueError:
                pass

            return val
        else:
            return val

    def _base_document(self):
        """Generate the 'outer' structure of the object. Calls other
        methods to generate sub-documents."""

        doc = collections.OrderedDict(
            [
                ('type', 'flow'),
                ('interval', 600),
                ('values', self._value_doc()),
                ('meta', self._meta_doc()),
                ('start', self.start),
                ('end', self.end),
            ]
        )

        return doc

    def _value_doc(self):
        """Generate the base/shared value doc.

        Override this in the subclass to add in additional fields (ie: tcp logs)
        """
        doc = collections.OrderedDict(
            [
                ('duration', self.duration),
                ('num_bits', self.num_bits),
                ('num_packets', self.num_packets),
            ]
        )

        return doc

    def _meta_map(self):
        """
        Arrange the values in the meta stanza depending on the direction.
        This is different than just using _directional_key().
        """
        if self._direction == 'in':
            return dict(
                src_ip=self._static_key('c_ip'), src_port=self._static_key('c_port'),
                dst_ip=self._static_key('s_ip'), dst_port=self._static_key('s_port'),
                )
        else:
            return dict(
                src_ip=self._static_key('s_ip'), src_port=self._static_key('s_port'),
                dst_ip=self._static_key('c_ip'), dst_port=self._static_key('c_port'),
                )

    def _meta_doc(self):
        """
        Generate the meta sub-stanza.
        """
        meta_vals = self._meta_map()

        doc = collections.OrderedDict(
            [
                ('src_ip', meta_vals.get('src_ip')),
                ('src_port', meta_vals.get('src_port')),
                ('dst_ip', meta_vals.get('dst_ip')),
                ('dst_port', meta_vals.get('dst_port')),
                ('protocol', self._protocol),
            ]
        )

        return doc

    # Properties to subclass to handle variants in the fields.
    @property
    def num_bits(self):
        """override in subclass - get num_bits."""
        raise NotImplementedError

    @property
    def num_packets(self):
        """override in subclass - get num_packets."""
        raise NotImplementedError

    @property
    def duration(self):
        """override in subclass - get duration."""
        raise NotImplementedError

    @property
    def start(self):
        """override in subclass - get start."""
        raise NotImplementedError

    @property
    def end(self):
        """override in subclass - get start."""
        raise NotImplementedError

    def to_json_packet(self):
        """Public wrapper around document method. Primarily for compatability
        with TsdsParse/the original rendering classes."""
        return self._base_document()

    def rowdict(self):
        """Return the payload dict."""
        return self._row


class TcpCapsule(EntryCapsuleBase):
    """Capsule for tcp log lines."""

    def _value_doc(self):
        """Subclass variant to add in the tcp-specific values."""
        doc = super(TcpCapsule, self)._value_doc()

        val_doc = collections.OrderedDict(
            [
                ('tcp_rexmit_bytes', self._directional_key('bytes_retx')),
                ('tcp_rexmit_pkts', self._directional_key('pkts_retx')),
                ('tcp_rtt_avg', self._directional_key('rtt_avg')),
                ('tcp_rtt_min', self._directional_key('rtt_min')),
                ('tcp_rtt_max', self._directional_key('rtt_max')),
                ('tcp_rtt_std', self._directional_key('rtt_std')),
                ('tcp_pkts_rto', self._directional_key('pkts_rto')),
                ('tcp_pkts_fs', self._directional_key('pkts_fs')),
                ('tcp_pkts_reor', self._directional_key('pkts_reor')),
                ('tcp_pkts_dup', self._directional_key('pkts_dup')),
                ('tcp_pkts_unk', self._directional_key('pkts_unk')),
                ('tcp_pkts_fc', self._directional_key('pkts_fc')),
                ('tcp_pkts_unrto', self._directional_key('pkts_unrto')),
                ('tcp_pkts_unfs', self._directional_key('pkts_unfs')),
                ('tcp_cwin_min', self._directional_key('cwin_min')),
                ('tcp_cwin_max', self._directional_key('cwin_max')),
                ('tcp_out_seq_pkts', self._directional_key('pkts_ooo')),
                ('tcp_window_scale', self._directional_key('win_scl')),
                ('tcp_mss', self._directional_key('mss')),
                ('tcp_max_seg_size', self._directional_key('mss_max')),
                ('tcp_min_seg_size', self._directional_key('mss_min')),
                ('tcp_win_max', self._directional_key('cwin_max')),
                ('tcp_win_min', self._directional_key('cwin_min')),
                ('tcp_initial_cwin', self._directional_key('cwin_ini')),
            ]
        )

        for k, v in val_doc.items():
            doc.update({k: v})

        return doc

    @property
    def header_trim(self):
        """string to shave from keys from the csv DictReader header keys."""
        return '#09#'

    @property
    def duration(self):
        """get duration."""
        return round(self._static_key('durat') / 1000, 2)

    @property
    def num_bits(self):
        """Get num_bits."""
        return self._directional_key('bytes_uniq') * 8

    @property
    def num_packets(self):
        """Get num_packets."""
        return self._directional_key('pkts_data')

    @property
    def start(self):
        """Get start."""
        return int(self._static_key('first') / 1000)

    @property
    def end(self):
        """Get end."""
        return int(self._static_key('last') / 1000)


class UdpCapsule(EntryCapsuleBase):
    """Capsule for udp log lines."""
    @property
    def header_trim(self):
        """string to shave from keys from the csv DictReader header keys."""
        return '#'

    @property
    def duration(self):
        """get duration."""
        return round(self._directional_key('durat') / 1000, 2)

    @property
    def num_bits(self):
        """Get num_bits."""
        return self._directional_key('bytes_all') * 8

    @property
    def num_packets(self):
        """Get num_packets."""
        return self._directional_key('pkts_all')

    @property
    def start(self):
        """Get start."""
        return int(self._directional_key('first_abs') / 1000)

    @property
    def end(self):
        """Get end."""
        return int(self.start + self.duration)


def capsule_factory(row, protocol, config):
    """Process both directions of the log row for a given protocol.

    Will return a list of 0, 1 or 2 objects.
    """

    capsule_map = dict(
        tcp=TcpCapsule,
        udp=UdpCapsule,
    )

    ret = list()

    for i in DIRECTIONS:
        capsule = capsule_map.get(protocol)(row, protocol, i)

        try:
            # Render the whole payload to catch malformed log
            # entries. Example: a log with a duplicate header line in it
            # which will cause division errors etc etc etc.
            capsule.to_json_packet()
        except TypeError as ex:
            msg = 'Unable to render capsule with TypeError/payload: {t} {p}'.format(
                t=str(ex), p=capsule.rowdict())
            warnings.warn(msg, TstatFormatWarning, stacklevel=2)
            config.log('capsule_factory.warn', msg)
            continue

        if capsule.num_bits >= config.options.bits:
            ret.append(capsule)

    return ret
