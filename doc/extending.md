# Extending tstat_send with additional transports

Initially, `tstat_send` only supported sending the JSON objects to a RabbitMQ server for processing and archiving. Adding additional transports (for example: send the JSON objects to a REST endpoint) is not too difficult however.

The first thing to do is to pick a single word name for your new transport type - e.g.: `rest`, `redis`, etc.

## Config file

Add a new stanza to the config file (documented above) using the name of your new transport type (example: `[rest]`). This is where you will put any configuration directives specific to your new transport.

Default configuration values like `host`, `port`, `username`, `password` and `use_ssl` are already provided by default. Both `host` and `port` are required.

## New transport class

A new transport class should start by subclassing `transport.BaseTransport`. There are a couple of methods to override in this subclass:

### __init__

Call the superclass constructor first to let it pull in the required "global" configuration values from the config file. Then parse/validate any transport specific configuration variables (see `transport.BaseTransport._safe_cfg_val()`), and set up any persistent connections. An HTTP based transport that can just use the default configuration variables and does not have a persistent connection might not need any of thise.

### send()

Fairly self explanatory. Void method. The inherited class member `self._payload` will have the string version of the list of JSON objects ready to go. Fill in the code to send the payload string to the remote server. Like a POST using one of the python http libraries.

## Transport map

The dict `transport.TRANSPORT_MAP` contains the mappings between the "transport type name" and the class that will be used to process that type. Add a new key using your new transport name (the same one used in the config file stanza), and point it at the new transport class.

    TRANSPORT_MAP = dict(
        rabbit=RabbitMQTransport,
        rest=MyNewRestTransport,
    )

Now just just use the `--transport` argument to tell the tool do use the new transport type:

    tstat_send --directory ./tstat --transport rest