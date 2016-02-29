# Tstat (TCP STatistic and Analysis Tool) Transport Tools

Client programs and library to read a tstat file hierarchy, parse the logs, and generate json to send to a remote archive like a RabbitMQ server.

## Overview

### tstat_send

When invoked, it crawls a tstat file hierarchy laid out like this:

    tstat/2016_02_17_12_53.out:
    total 808
    -rw-r--r--@ root users  135103 Feb 17 13:54 log_tcp_complete
    -rw-r--r--@ root users  277154 Feb 17 13:54 log_udp_complete

    tstat/2016_02_17_13_54.out:
    total 792
    -rw-r--r--@ root users  123801 Feb 17 14:54 log_tcp_complete
    -rw-r--r--@ root users  278301 Feb 17 14:54 log_udp_complete

Selected data are extracted from the relevant logs, the data are formatted into JSON objects, and lists of JSON are sent to a remote server for archiving. All the objects from a single log are broken into a list of smaller lists (the current default is 100 objects per list). Each "sub-list" gets sent to the remote server so no one single send operation swamps the remote server.

When the logs in each directory.

Currently, the only "transport" that is supported is sending the JSON to a RabbitMQ server, but it would be relatively straightforward to implement other transports like using HTTP to send to a REST API.

## Usage

### tstat_send arguments

#### Required

##### --directory

This is the path to the "root" of the directory structure where tstat writes the timestamped directories and logfiles.

##### --config

Path to the .ini style config file used to pass configuration directives to the underlying transport code.

Default: `./config.ini`.

#### Optional

##### --bytes

The transfer threshold in bytes. Any transfer below this threshold below will be ignored/not archived.

Default: `25Gb`.

##### --transport

Specify the underlying transport to send the JSON over. Currently, only RabbitMQ is supported.

Default: `rabbit`.

##### --single

Only process a single "timestamped directory" of files, send JSON and exit. This is mostly useful for development or debugging.

##### --verbose and --debug

`--verbose` just outputs additional logging information built in to the code. `--debug` changes the log level to `logging.DEBUG` in the transport module. This is primarily for debugging connection problems with RabbitMQ, or get detailed output on the transactions with the remote server.

### Config file

tstat_send uses an .ini style config file to pass options to the underlying transport code. Doing this with command-line args would be too ponderous. Example config file:

    [rabbit]
    # host/port are required for all transport variants
    host = localhost
    # this is the rabbit ssl port, if not, use default 5672 or custom port
    port = 5671
    # these are required for some transports
    username = esnet
    password = some_mysterious_password
    use_ssl = True
    # these are rabbit specific - the exchange key is required
    # even if you don't set the value to anything/use the default "".
    vhost = netsage
    queue = netsage_tstat
    routing_key = netsage_tstat
    exchange =

    # This is an optional stanza. The key/value pairs
    # will be passed to channel.queue_declare() as kwargs
    # (ie: durable, exclusive, auto_delete, etc).
    [rabbit_queue_options]

    # This is an optional stanza. The key/value pairs
    # will generate a dict to be passed to ssl_options
    # connection parameters. These are the args passed
    # to ssl.wrap_socket()
    # https://docs.python.org/2/library/ssl.html#ssl.wrap_socket
    [ssl_options]

* The values `host` and `port` will be required for all transport variants. If they are not supplied, a configuration error occur.
* The rabbit transport requires the `username` and `password` config values.
* `vhost, queue, routing_key and exchange` should be self-explanatory RabbitMQ directives.
* The `rabbit_queue_options` stanza is optional and can be used to pass additional kwargs to `queue_declare()` if need be. By default the code only passes the `queue` argument with the name of the queue.
* The `ssl_options` stanza is optional too. Only necessary if additional args (paths to keyfiles, etc) need to be passed to the underlying `ssl` library.

