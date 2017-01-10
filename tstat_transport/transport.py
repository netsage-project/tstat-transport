"""
Classes to handle the sending of the json-formatted by the appropriate transport layers.
"""

import logging
import warnings

import pika
from pika.adapters.blocking_connection import BlockingConnection as PikaConnection

from .common import (
    TstatBase,
    TstatConfigException,
    TstatTransportException,
    TstatTransportWarning,
)

TRANSPORT_DEFAULT = 'rabbit'


class BaseTransport(TstatBase):
    """Base class for the transport-specific classes."""

    def __init__(self, config_capsule, init_user_pass=False):
        super(BaseTransport, self).__init__(config_capsule)

        self._host = self._config.get_cfg_val('host')
        self._port = self._config.get_cfg_val('port', as_int=True)

        # Initialize user/pass from ini file if transport needs it.
        if init_user_pass:
            self._username = self._safe_cfg_val('username')
            self._password = self._safe_cfg_val('password')

        self._payload = None

        # Flip on logging.DEBUG to diagnose issues with the
        # transport subclasses (rabbit connection issues, etc).
        if self._options.debug:
            logging.basicConfig(level=logging.DEBUG)

    def _safe_cfg_val(self, value, **kwargs):
        """
        Call in subclasses to get transport specific config values
        and raise an exception if it's not found.
        """
        try:
            return self._config.get_cfg_val(value, **kwargs)
        except TstatConfigException:
            msg = '[{0}] is a required config value for transport [{1}]'.format(
                value, self._options.transport)
            raise TstatTransportException(msg)

    def send(self):
        """
        Transport/driver specific code to send the payload.
        Set in subclass.
        """
        raise NotImplementedError

    def set_payload(self, p_load):
        """
        Method to set the payload to be sent across the wire.

        Can be overridden in subclasses in case there needs to be
        any additional massaging of the payload before sending.
        """
        self._payload = p_load

    def warn(self, msg):  # pylint: disable=no-self-use
        """Emit a warning."""
        warnings.warn(msg, TstatTransportWarning, stacklevel=2)


class RabbitMQTransport(BaseTransport):
    """
    Class to send JSON payload to a RabbitMQ server.

    If connection requires special ssl_options, these can be set in the
    optional [ssl_options] stanza in the configuration file.
    """
    def __init__(self, config_capsule):
        super(RabbitMQTransport, self).__init__(config_capsule, init_user_pass=True)

        # Retrieve config values before setting everything up to
        # allow any configuration errors to be raised first.

        self._use_ssl = self._safe_cfg_val('use_ssl', as_bool=True)
        self._connect_info = self._connection_params()

        self._queue = self._safe_cfg_val('queue')
        self._exchange = self._safe_cfg_val('exchange')
        self._routing_key = self._safe_cfg_val('routing_key')

        # if _options.no_transport is set, let the configuration
        # validate and exit.

        if self._options.no_transport:
            self._log('rabbit.init', '--no-transport set, not opening connections')
            return

        try:
            self._connection = PikaConnection(self._connect_info)
        except pika.exceptions.ConnectionClosed:
            msg = 'unable to connect to rabbit at: {0}'.format(self._connect_info)
            msg += ' - retry with --debug flag to see verbose connection output'
            self._log('rabbit.init.error', msg)
            raise TstatTransportException(msg)

        if not self._connection.is_open:
            msg = 'connection object successfully initialized, but no longer open.'
            raise TstatTransportException(msg)

        self._log('rabbit.init.connection', 'status - is_open: {0}'.format(
            self._connection.is_open))

        # set up the channel
        self._channel = self._connection.channel()
        # just set the queue, presume opts set on server.
        self._channel.queue_declare(
            queue=self._queue, **self._config.get_rabbit_queue_opts())
        # enable message delivery confirmation
        self._channel.confirm_delivery()

    def _connection_params(self):
        """Generate pika connection parameters object/options."""

        credentials = pika.PlainCredentials(self._username, self._password)

        params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            virtual_host=self._safe_cfg_val('vhost'),
            credentials=credentials,
            ssl=self._use_ssl,
            ssl_options=self._config.get_ssl_opts(),
        )

        self._verbose_log('_connection_params.end', params)

        return params

    def send(self):
        """Send the payload to the remote server."""

        self._verbose_log('rabbit.send', 'publishing message')

        if self._connection.is_open:
            if self._channel.basic_publish(
                    exchange=self._exchange,
                    routing_key=self._routing_key,
                    body=self._payload,
                    properties=pika.BasicProperties(
                        content_type='application/json',
                        delivery_mode=1,
                    )
            ):
                self._log('rabbit.send', 'basic_publish success')
            else:
                msg = 'could not confirm publish success'
                self._log('rabbit.send.error', msg)
                raise TstatTransportException(msg)
        else:
            msg = 'rabbit mq connection is no longer open - send failed.'
            self._log('rabbit.send.error', msg)
            raise TstatTransportException(msg)


TRANSPORT_MAP = dict(
    rabbit=RabbitMQTransport,
)

TRANSPORT_TYPE = [x for x in list(TRANSPORT_MAP.keys())]
