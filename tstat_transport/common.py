"""
Custom superclasses, exceptions and common code for tstat_trasport package.
"""

from configparser import ConfigParser

from .util import valid_hostname

PROTOCOLS = ('tcp', 'udp')


class TstatBase(object):  # pylint: disable=too-few-public-methods
    """
    Base class for tstat log parsing classes and the transport classes.
    Primarily to handle the ConfigurationCapsule and provide properties
    to access the contents.
    """
    def __init__(self, config_capsule):
        self._config = config_capsule

    @property
    def _options(self):
        """Return the OptionParser options object."""
        return self._config.options

    @property
    def _log(self):
        """Return the underlying logger."""
        return self._config.log

    def _verbose_log(self, event, msg):
        """Log events if running in verbose mode."""
        if self._options.verbose:
            self._log(event, msg)

    def _debug_log(self, event, msg):
        """Log events if running in debug mode."""
        if self._options.debug:
            self._log(event, msg)


class TstatConfigException(Exception):
    """Custom TstatConfig exception"""
    def __init__(self, value):
        # pylint: disable=super-init-not-called
        self.value = value

    def __str__(self):
        return repr(self.value)


class TstatConfigWarning(Warning):
    """Custom TstatConfig warning"""
    pass


class ConfigurationCapsule(object):
    """
    Encapsulation class to carry command line args, the logging handler
    and config file information through the parse and transport classes.

    Also handles reading and and validating the config.ini file.
    """
    def __init__(self, options, log, config_path):
        self._options = options
        self._log = log
        self._config = ConfigParser()
        self._config.read(config_path)

        self._validate_config(config_path)

    def _validate_config(self, config_path):
        """Validate the config file."""

        # makes sure there is a stanza for the transport that
        # has been selected
        if self.options.transport not in self.config.sections():
            msg = '{t} selected as transport, but no  [{t}] stanza in config {f}'.format(
                t=self.options.transport, f=config_path)
            raise TstatConfigException(msg)

        # make sure we have the universal bare minimum host and port values
        try:
            self.get_cfg_val('host')
            self.get_cfg_val('port')
        except TstatConfigException:
            msg = '"port" and "host" are required in [{t}] config stanza'.format(
                t=self.options.transport)
            raise TstatConfigException(msg)

        # is the hostname valid?
        if not valid_hostname(self.get_cfg_val('host')):
            msg = '{h} is not a valid hostname'.format(h=self.get_cfg_val('host'))
            raise TstatConfigException(msg)

        # is the port an integer?
        try:
            self.get_cfg_val('port', as_int=True)
        except TstatConfigException:
            msg = 'port {0} is not a valid integer'.format(
                self._config.get(self.options.transport, 'port'))
            raise TstatConfigException(msg)

    # pylint: disable=missing-docstring

    def get_cfg_val(self, value, as_int=False, as_bool=False):
        """
        Return a named value from the config file stanza that matches
        the currently selected transport.
        """
        try:
            if as_int:
                return self._config.getint(self.options.transport, value)
            elif as_bool:
                return self._config.getboolean(self.options.transport, value)
            else:
                return self._config.get(self.options.transport, value)
        except ConfigParser.NoOptionError:
            msg = '{0} config value not found'.format(value)
            raise TstatConfigException(msg)
        except ValueError:
            msg = '{0} config value improper type'.format(value)
            raise TstatConfigException(msg)

    def _config_stanza_to_dict(self, stanza):
        opts = dict()

        if stanza in self.config.sections() and len(self.config.options(stanza)):
            for i in self.config.options(stanza):
                opts[i] = self.config.get(stanza, i)
            self._log('_config_stanza_to_dict',
                      'stanza [{s}] to dict: {d}'.format(s=stanza, d=opts))

        return opts

    def get_ssl_opts(self):
        return self._config_stanza_to_dict('ssl_options')

    # Some rabbit specific option calls to pass addional kwargs to
    # pika methods.

    def get_rabbit_queue_opts(self):
        return self._config_stanza_to_dict('rabbit_queue_options')

    # expose the internals as properties.

    @property
    def options(self):
        return self._options

    @property
    def log(self):
        return self._log

    @property
    def config(self):
        return self._config


class TstatParseException(Exception):
    """Custom TstatParse exception"""
    def __init__(self, value):
        # pylint: disable=super-init-not-called
        self.value = value

    def __str__(self):
        return repr(self.value)


class TstatParseWarning(Warning):
    """Custom TstatParse warning"""
    pass


class TstatTransportException(Exception):
    """Custom TstatTransport exception"""
    def __init__(self, value):
        # pylint: disable=super-init-not-called
        self.value = value

    def __str__(self):
        return repr(self.value)


class TstatTransportWarning(Warning):
    """Custom TstatTransport warning"""
    pass
