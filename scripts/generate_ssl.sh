#!/usr/bin/env bash
## Reference material: https://docs.vmware.com/en/vCloud-Availability-for-vCloud-Director/2.0/com.vmware.vcavcd.install.config.doc/GUID-8C344104-47E5-46A3-95C7-B11845C6907A.html
#    -dname "CN=*.corp-ext.local,OU=Test, O=Corp, L=Palo Alto S=CA C=US" \
#    -ext san=dns:test2.local,dns:test3.local,dns:testrabbitmqlb.local,ip:0.0.0.0
rm -fr out
keytool -genkeypair \
    -keystore rootca.jks \
    -storepass vmware \
    -keyalg RSA \
    -validity 3650 \
    -keypass vmware \
    -alias rabbitmq \
    -dname "CN=*.local,OU=Test, O=Corp, L=Palo Alto S=CA C=US" \
    -ext san=ip:0.0.0.0,127.0.0.1

keytool -importkeystore -srckeystore rootca.jks \
    -destkeystore foo.p12 -deststoretype pkcs12 \
    -srcstorepass vmware -deststorepass vmware \
    -alias rabbitmq

openssl pkcs12 -in foo.p12 -out foo.pem -passin pass:vmware -passout pass:vmware

sed -n '/-----BEGIN ENCRYPTED PRIVATE KEY-----/,/-----END ENCRYPTED PRIVATE KEY-----/p' foo.pem >enc.pem

openssl rsa -in enc.pem -out unenc.pem -passin pass:vmware

sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' foo.pem >cert.pem

mkdir out/
cp cert.pem out/testca_cacert.pem
cp cert.pem out/server_cert.pem
cp unenc.pem out/server_key.pem
cp cert.pem out/client_cert.pem
cp unenc.pem out/client_key.pem
