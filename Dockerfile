FROM python:2.7-alpine

LABEL maintainer Svein Seldal <sveinse@seldal.com>

COPY docker/init /init
COPY setup.py README.rst /installer/
COPY lumina/ /installer/lumina/
COPY www/ /www/
COPY conf/lumina.json /etc/lumina/lumina.json

RUN apk --no-cache add gcc musl-dev && \
    pip --no-cache install /installer && \
    apk del gcc musl-dev && \
    rm -rf /installer

ENTRYPOINT [ "/init" ]
CMD [ "lumina", "server", "--config", "/etc/lumina/lumina.json" ]
