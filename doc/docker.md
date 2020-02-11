## Docker Environment


### Setup env 

copy env.example to .env and rename it according to your preference / environment

### TStat Collector (Optional)

This part is optional.  a docker container is provided to run the tstat binary and write data to data/tstat.  Alternatively run the tsat collector on your server and simply configure it to write to the same location ./data/tstat or update the docker-compose file to point to the output location of your data collection.

The docker-compose provides the default 'command' being executed.  You can feel free to change that to match your environment.

### TStat Send

the first time you run this the app will probably error out.  It'll
create a data/config folder with the container's configuration file.

Update that accordingly to your environment.  You may choose to deliver the files to the rabbitmq container (provided for convenience) or to an external rabbitMQ host.

Recommended configuration, (Check main README.md for more up to date configuration details)


```ini
[rabbit]
# host/port are required for all transport variants
host = localhost
# this is the rabbit ssl port, if not, use default 5672 or custom port
port = 5672
# these are required for some transports
username = guest
password = guest
use_ssl = False
# these are rabbit specific - the exchange key is required
# even if you don't set the value to anything/use the default "".
vhost = /
queue = netsage_deidentifier_raw
routing_key = netsage_deidentifier_raw
exchange =

# This is an optional stanza. The key/value pairs
# will be passed to channel.queue_declare() as kwargs
# (ie: durable, exclusive, auto_delete, etc).
[rabbit_queue_options]

# This is an optional stanza. The key/value pairs
# will generate a dict to be passed as kwargs to ssl.wrap_socket()
# https://docs.python.org/2/library/ssl.html#ssl.wrap_socket
[ssl_options]
```

