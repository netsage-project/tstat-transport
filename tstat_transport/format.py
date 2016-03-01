"""
Classes to format the log entries, code to access them, etc.

Direction is relative to the host so - in and out from the host perspective.

In the google doc meta stanza:

in => source_ip would be 1
    in will also correspond to the c_ variants.

out => source_ip would be 15
    out will also correspond to the s_ variants.

check the num_bits fields to see if we should return.

capsule_factory will return a list of 0, 1 or 2 objects.
"""

import collections

DIRECTIONS = ('in', 'out')


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

    def _direction_key(self, key):
        """
        Returns the proper c_ or s_ variant from the row payload depending
        on the direction that this instance is going.
        """
        key = '{d}{k}'.format(d=self._prefixes.get(self._direction), k=key)
        return self._row.get(key)

    def _base_document(self):
        """Generate the general structure of the object."""

        doc = collections.OrderedDict(
            [
                ('interval', '600'),  # XXX? is this right?
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
        """
        if self._direction == 'in':
            return dict(
                src_ip=self._row.get('c_ip'), src_port=self._row.get('c_port'),
                dst_ip=self._row.get('s_ip'), dst_port=self._row.get('s_port'),
                )
        else:
            return dict(
                src_ip=self._row.get('s_ip'), src_port=self._row.get('s_port'),
                dst_ip=self._row.get('c_ip'), dst_port=self._row.get('c_port'),
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


class TcpCapsule(EntryCapsuleBase):
    """Capsule for tcp log lines."""

    def _value_doc(self):
        """Subclass variant to add in the tcp-specific values."""
        doc = super(TcpCapsule, self)._value_doc()

        val_doc = collections.OrderedDict(
            [
                ('tcp_rexmit_bytes', self._direction_key('bytes_retx')),
                ('tcp_rexmit_pkts', self._direction_key('pkts_retx')),
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
    def num_bits(self):
        """Get num_bits."""
        return int(self._direction_key('bytes_uniq')) * 8

    @property
    def num_packets(self):
        """Get num_packets."""
        return self._direction_key('pkts_data')

    @property
    def duration(self):
        """get duration."""
        return float(self._row.get('durat'))

    @property
    def start(self):
        """Get start."""
        return float(self._row.get('first')) / 1000

    @property
    def end(self):
        """Get end."""
        return float(self._row.get('last')) / 1000


class UdpCapsule(EntryCapsuleBase):
    """Capsule for udp log lines."""
    @property
    def header_trim(self):
        """string to shave from keys from the csv DictReader header keys."""
        return '#'

    @property
    def num_bits(self):
        """Get num_bits."""
        return int(self._direction_key('bytes_all')) * 8

    @property
    def num_packets(self):
        """Get num_packets."""
        return self._direction_key('pkts_all')

    @property
    def duration(self):
        """get duration."""
        return float(self._direction_key('durat'))

    @property
    def start(self):
        """Get start."""
        return float(self._direction_key('first_abs')) / 1000

    @property
    def end(self):
        """Get end."""
        return self.start + self.duration


def capsule_factory(row, protocol, config):
    """Return the proper format capsule class."""

    capsule_map = dict(
        tcp=TcpCapsule,
        udp=UdpCapsule,
    )

    ret = list()

    for i in DIRECTIONS:
        capsule = capsule_map.get(protocol)(row, protocol, i)
        if capsule.num_bits >= config.options.bits:
            ret.append(capsule)
            import json
            print 'XXX', i, json.dumps(capsule.to_json_packet(), indent=4)

    return ret
