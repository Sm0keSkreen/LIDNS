FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -q && \
    apt-get install -y nginx python3-pip openssl curl dnsutils netcat-openbsd iptables nftables && \
    pip3 install websockets && \
    rm -rf /var/lib/apt/lists/*

# CoreDNS
COPY coredns.tgz /tmp/
RUN tar -xzf /tmp/coredns.tgz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/coredns && \
    rm /tmp/coredns.tgz

# App files
COPY fake-relay.py prewarm-api.py /opt/
COPY lsrelay/ /var/www/lsrelay/
COPY ext.cnf /etc/ssl/lsrelay/ext.cnf

# CA is generated at runtime per-host
RUN mkdir -p /etc/ssl/lsrelay /etc/coredns

# nginx setup - use custom main config
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-lsrelay.conf /etc/nginx/conf.d/lidns.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 53/udp 53/tcp 80/tcp 443/tcp

ENTRYPOINT ["/entrypoint.sh"]
