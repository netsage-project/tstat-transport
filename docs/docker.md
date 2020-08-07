## Docker Environment

### Setup env 

copy env.example to .env and rename it according to your preference / environment

## Configuration

The configuration is driven by the values in the .env file.  You alternatively directly modify the config file which is expose in data/config.

By default it will send the data to the rabbitmq host running inside docker, you can change that behavior to publish to an external rabbitMQ.

### SSL Configuration

If for any reason you wish to use SSL in rabbitMQ, this is primarily used to testing to validate SSL communication works, but if you have a use case simple uncomment the following lines.

``` sh
SSL_ENABLED=true
RABBITMQ_SSL_CERTFILE=/tmp/ssl/testca_cacert.pem
RABBITMQ_SSL_CACERTFILE=/tmp/ssl/server_cert.pem
RABBITMQ_SSL_KEYFILE=/tmp/ssl/server_key.pem
RABBITMQ_SSL_VERIFY=verify_none
RABBITMQ_SSL_FAIL_IF_NO_PEER_CERT=false
```

The SSL certificates are all self signed and are stored in the ssl folder.  If you wish to re-generate the ssl certs simply go to the scripts folder and run `generate_ssl.sh`
then copy the content of the `out` directory to `ssl`


**IMPORTANT:**

The SSL is an untrusted certificate and the rabbitMQ MGMT didn't work for me.  All standard browsers blocked the web interface.

The Ports will change.  

  + Non-SSL

``` 
MANAGEMENT: 15672
RABBIT: 5672
```

  + SSL:

``` 
MANAGEMENT: 15671
RABBIT: 5671
```

### TStat Collector (Optional)

This part is optional.  a docker container is provided to run the tstat binary and write data to data/tstat.  Alternatively run the tsat collector on your server and simply configure it to write to the same location ./data/tstat or update the docker-compose file to point to the output location of your data collection.

The docker-compose provides the default 'command' being executed.  You can feel free to change that to match your environment.

### TStat Send

Before running this container, please make sure you look over the command specified in docker-compose.yml.  By default we set a threshold of 0 which will immediately send any data collected.

Have a look at bin/tstat_send you may need to adjust the setting for you needs.  Specifically the sensorName and instanceName might need to be updated.

the first time you run this the app it will create a data/config folder with the container's configuration file.

Update those settings accordingly or rely on ENV driven settings.  You may choose to deliver the files to the rabbitmq container (provided for convenience) or to an external rabbitMQ host.
