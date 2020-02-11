FROM centos:7

RUN mkdir -p /code/config /data/tstat
COPY . /code 

## Setup baseline
RUN  \
    yum install -y epel-release wget  && \
    yum  -y update && \ 
    yum -y install python-pip && \
    pip install --upgrade pip && \
    pip install -r /code/requirements.txt
    
RUN cp  /code/docker_config.ini /code/config/config.ini

#Config location
VOLUME /code/config 
## TStat data location
VOLUME /data/tstat

CMD ["/code/tstat_send", "-c", "/code/config/config.ini", "-d", "/data/tstat"]