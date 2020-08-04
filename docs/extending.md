# Extending tstat_send with additional transports

This document is primarily meant for people in ESnet/LBL that might that might be extending the code base, but it might be useful for external users as well.

Initially, `tstat_send` only supported sending the tstat JSON objects to a RabbitMQ server for archiving. Adding additional transports (for example: to send the JSON objects to a REST endpoint) is not too difficult.

The first thing to do is to pick a single word name for your new transport type - e.g.: `rest`, `redis`, etc. This will be used as a term of art at various points in these instructions.

## Config file

Add a new stanza to the config file (documented in README.md) using the name of your new transport type (example: `[rest]`). This is where you will put any configuration directives specific to your new transport.

Both `host` and `port` values are required in your new stanza. Define `username` and `password` here as well and enable them in your new class (see below).

## New transport class

A new transport class should start by sub-classing `tstat_transport.transport.BaseTransport`. There are a couple of methods to override in this subclass:

### \__init__

Call the superclass constructor first to let it pull in and validate the required "global" configuration values from the config file. The optional boolean kwarg `init_user_pass=True` can be passed to the superclass constructor to pull in the `username` and `password` values from the config file if you need them.

Then parse/validate any transport specific configuration variables (see `transport.BaseTransport._safe_cfg_val()`), and set up any persistent connections. An HTTP based transport that can just use the default configuration variables and doesn't have a persistent connection might not need any of this.

### send()

Fairly self explanatory. A void method. The inherited class member `self._payload` will have the string version of the list of JSON objects ready to go. Fill in the code to send the payload string to the remote server. Like a POST using one of the python http libraries.

### (optional) set_payload()

Does not need to be overridden by default. But if you really need to massage or modify the JSON lists passed in by the parser, do something like this:

    def set_payload(self, p_load):
        new_json_list = self._reformat_json(p_load)
        self._payload = new_json_list

## Transport map

The dict `transport.TRANSPORT_MAP` contains the mappings between the "transport type name" and the class that will be used to process that type. Add a new key using the new transport name (the same one used in the config file stanza), and point it at the new transport class.

    TRANSPORT_MAP = dict(
        rabbit=RabbitMQTransport,
        rest=MyNewRestTransport,
    )

Now use the `--transport` argument to tell the tool do use the new transport type instead of the default one:

    tstat_send --directory ./tstat --transport rest
