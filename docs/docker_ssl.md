## Generate an SSL
```sh
mkdir temp && cd $_ 
wget https://github.com/michaelklishin/tls-gen/archive/master.zip
unzip master.zip
cd tls-get-master/basic
make 
rm -fr ../../../ssl/; mkdir -v $_; mv server ../../../ssl/
```
