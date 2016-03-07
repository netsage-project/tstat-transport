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

When the logs in each directory have been successfully processed (all the data have been sent, delivery confirmations received, etc), a dotfile named `.processed` will be dropped in that directory. This directory will not be processed on subsequent runs, and this could be used in conjunction with a find to set up cron jobs that will cull the older logs.

Currently, the only "transport" that is supported is sending the JSON to a RabbitMQ server, but it would be relatively straightforward to implement other transports like using HTTP to send to a REST API.

## Usage

### tstat_send arguments

#### Required

##### --directory

This is the path to the "root" of the directory structure where tstat writes the timestamped directories and logfiles. No default.

##### --config

Path to the .ini style config file used to pass configuration directives to the underlying transport code.

Default: `./config.ini`.

#### Optional

##### --bits

The transfer threshold in bytes. Any transfer below this threshold below will be ignored/not archived.

Default: `25Gb`.

##### --transport

Specify the underlying transport to send the JSON over. Currently, only RabbitMQ is supported.

Default: `rabbit`.

##### --single

Only process a single "timestamped directory" of files, send JSON and exit. This is mostly useful for development or debugging.

##### --verbose and --debug

`--verbose` just outputs additional logging information built in to the code. `--debug` changes the log level to `logging.DEBUG` in the transport module. This is primarily for debugging connection problems with RabbitMQ, or get detailed output on the transactions with the remote server.

## Config file

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

## Message format

Every log line might generate zero, one or two JSON objects. This depends on the threshold set with the `--bits` flag and what kind of transfer it is. The generated objects will be sub-divided into a list of lists of up to 100 objects. That way each send operation is of a manageable size rather than sending one huge list.

All numeric values are being converted to "actual" numeric types, all floating point values are being rounded to three decimal places to avoid small values being rendered in scientific notation, and the timestamps (reported in ms) are being `int(value / 1000)` to convert to epoch seconds.

### UDP logs

This is the most basic format.

    {
        "interval": 600,
        "values": {
            "duration": 0.0,
            "num_bits": 544,
            "num_packets": 1
        },
        "meta": {
            "src_ip": "198.129.77.102",
            "src_port": 123,
            "dst_ip": "198.124.252.130",
            "dst_port": 123,
            "protocol": "udp"
        },
        "start": 1455745857,
        "end": 1455745857
    },

### TCP logs

The TCP logs are identical, but have additional values in cluded in the `values` stanza:

    {
        "interval": 600,
        "values": {
            "duration": 191.796,
            "num_bits": 22120,
            "num_packets": 14,
            "tcp_rexmit_bytes": 0,
            "tcp_rexmit_pkts": 0,
            "tcp_rtt_avg": 4.442,
            "tcp_rtt_min": 0.007,
            "tcp_rtt_max": 39.094,
            "tcp_rtt_std": 10.648,
            "tcp_pkts_rto": 0,
            "tcp_pkts_fs": 0,
            "tcp_pkts_reor": 0,
            "tcp_pkts_dup": 0,
            "tcp_pkts_unk": 0,
            "tcp_pkts_fc": 0,
            "tcp_pkts_unrto": 0,
            "tcp_pkts_unfs": 0,
            "tcp_cwin_min": 16,
            "tcp_cwin_max": 960,
            "tcp_out_seq_pkts": 0,
            "tcp_window_scale": 7,
            "tcp_mss": 1460,
            "tcp_max_seg_size": 960,
            "tcp_min_seg_size": 16,
            "tcp_win_max": 960,
            "tcp_win_min": 16,
            "tcp_initial_cwin": 21
        },
        "meta": {
            "src_ip": "198.128.14.246",
            "src_port": 58635,
            "dst_ip": "198.129.77.102",
            "dst_port": 22,
            "protocol": "tcp"
        },
        "start": 1455698490,
        "end": 1455698490
    },

## Utility programs

### tstat_cull

Crawls a tstat directory to cull old processed logs from disk.  It checks the `mtime` of the `.processed` state file that is generated when a directory of logs is successfully processed. If `mtime` is older than the default time to live in hours (default: 48), the directory and logs are removed.

#### Required args

##### --directory

This is the path to the "root" of the directory structure where tstat writes the timestamped directories and logfiles. No default.

#### Optional args

##### --ttl

The time to live value in hours.  Set this if you don't want to use the default of 48 hours.

##### --dry-run

Do a dry run. Just log the directories that will be deleted but don't delete them.

## Extending tstat_send with additional transports

Initially, `tstat_send` only supported sending the JSON objects to a RabbitMQ server for processing and archiving. Adding additional transports (for example: send the JSON objects to a REST endpoint) is not too difficult however.

The first thing to do is to pick a single word name for your new transport type - e.g.: `rest`, `redis`, etc.

### Config file

Add a new stanza to the config file (documented above) using the name of your new transport type (example: `[rest]`). This is where you will put any configuration directives specific to your new transport.

Default configuration values like `host`, `port`, `username`, `password` and `use_ssl` are already provided by default. Both `host` and `port` are required.

### New transport class

A new transport class should start by subclassing `transport.BaseTransport`. There are a couple of methods to override in this subclass:

#### __init__

Call the superclass constructor first to let it pull in the required "global" configuration values from the config file. Then parse/validate any transport specific configuration variables (see `transport.BaseTransport._safe_cfg_val()`), and set up any persistent connections. An HTTP based transport that can just use the default configuration variables and does not have a persistent connection might not need any of thise.

#### send()

Fairly self explanatory. Void method. The inherited class member `self._payload` will have the string version of the list of JSON objects ready to go. Fill in the code to send the payload string to the remote server. Like a POST using one of the python http libraries.

### Transport map

The dict `transport.TRANSPORT_MAP` contains the mappings between the "transport type name" and the class that will be used to process that type. Add a new key using your new transport name (the same one used in the config file stanza), and point it at the new transport class.

    TRANSPORT_MAP = dict(
        rabbit=RabbitMQTransport,
        rest=MyNewRestTransport,
    )

Now just just use the `--transport` argument to tell the tool do use the new transport type:

    tstat_send --directory ./tstat --transport rest