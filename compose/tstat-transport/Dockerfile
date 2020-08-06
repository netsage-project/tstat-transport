FROM centos:8


## Setup baseline
RUN  \
    yum install -y epel-release wget  && \
    yum  -y update && \ 
    yum -y install python3 python3-pip && \
    pip3 install --upgrade pip

RUN mkdir -p /code/config /data/tstat
COPY . /code
WORKDIR /code
RUN cp  /code/compose/tstat-transport/docker_config.ini /code/config/config.ini && \
    pip3 install -r /code/requirements.txt && \
    python3 setup.py install


#Config location
VOLUME /code/config
## TStat data location
VOLUME /data/tstat

CMD ["/code/tstat_send", "-c", "/code/config/config.ini", "-d", "/data/tstat", "-v", "-S", "sensorName", "-I", "InstanceName", "-T", "1" ]