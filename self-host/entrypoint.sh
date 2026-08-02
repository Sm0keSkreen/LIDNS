#!/bin/bash
set -e

echo "=== LIDNS Starting ==="

# Open firewall ports on the host via iptables (requires --cap-add NET_ADMIN)
echo "Opening firewall ports..."
PORTS_OPENED=false

# Try iptables first (works on most Linux VPS)
if iptables -I INPUT -p tcp --dport 53  -j ACCEPT 2>/dev/null && \
   iptables -I INPUT -p udp --dport 53  -j ACCEPT 2>/dev/null && \
   iptables -I INPUT -p tcp --dport 80  -j ACCEPT 2>/dev/null && \
   iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null; then
    echo "  [OK] ports 53/80/443 opened via iptables"
    PORTS_OPENED=true
fi

# Try nftables if iptables didn't work (Fedora/newer systems)
if [ "$PORTS_OPENED" = false ] && command -v nft &>/dev/null; then
    nft add table inet lidns 2>/dev/null || true
    nft add chain inet lidns input '{ type filter hook input priority 0; }' 2>/dev/null || true
    nft add rule inet lidns input tcp dport '{53, 80, 443}' accept 2>/dev/null && \
    nft add rule inet lidns input udp dport 53 accept 2>/dev/null && \
    echo "  [OK] ports 53/80/443 opened via nftables" && PORTS_OPENED=true
fi

if [ "$PORTS_OPENED" = false ]; then
    echo "  [WARN] could not open ports automatically. Make sure ports 53/80/443 are open in your firewall/router"
fi

# Get public IP
PUBLIC_IP=$(curl -s --max-time 10 https://api.ipify.org || curl -s --max-time 10 https://ifconfig.me || true)
echo "Public IP: $PUBLIC_IP"

# Generate new CA for this host if not already present
cd /etc/ssl/lsrelay
if [ ! -f ca.crt ] || [ ! -f ca.key ]; then
    echo "Generating new CA certificate for this host..."
    
    # Generate CA key
    openssl genrsa -out ca.key 4096
    
    # Generate self-signed CA certificate
    openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
        -out ca.crt -subj "/CN=LIDNS-Local-CA" 2>/dev/null
    
    echo "CA certificate generated."
else
    echo "Using existing CA certificate."
fi

# Generate server cert signed by this host's CA
if [ ! -f server.crt ]; then
    echo "Generating server certificate for $PUBLIC_IP..."

    # Build ext.cnf dynamically so the server cert also covers the bare IP
    cat > /etc/ssl/lsrelay/ext.cnf << EXTEOF
[req]
req_extensions = v3_req
[v3_req]
subjectAltName = @alt_names
[alt_names]
DNS.1 = lsrelay-config-production.s3.amazonaws.com
DNS.2 = lsrelay-extensions-production.s3.amazonaws.com
DNS.3 = lsrelay-reports-production.s3.amazonaws.com
DNS.4 = lsrelayaccess.com
DNS.5 = *.lsrelayaccess.com
DNS.6 = agent-backend-api-production.lightspeedsystems.com
DNS.7 = *.lightspeedsystems.com
DNS.8 = *.lightspeedsystems.app
DNS.9 = *.ably.io
DNS.10 = production-gc.lsfilter.com
DNS.11 = *.lsfilter.com
DNS.12 = devices.filter.relay.school
DNS.13 = *.filter.relay.school
DNS.14 = *.relay.school
IP.1 = $PUBLIC_IP
EXTEOF

    openssl genrsa -out server.key 2048
    openssl req -new -key server.key -out server.csr \
        -subj "/CN=lsrelay-config-production.s3.amazonaws.com" 2>/dev/null
    openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
        -out server.crt -days 3650 -extfile /etc/ssl/lsrelay/ext.cnf -extensions v3_req 2>/dev/null
    echo "Server certificate generated."
else
    echo "Using existing server certificate."
fi

# Write the hosts file for CoreDNS
cat > /etc/coredns/lshosts << EOF
$PUBLIC_IP lsrelay-config-production.s3.amazonaws.com
$PUBLIC_IP lsrelay-extensions-production.s3.amazonaws.com
$PUBLIC_IP lsrelay-reports-production.s3.amazonaws.com
$PUBLIC_IP lsrelayaccess.com
$PUBLIC_IP agent-backend-api-production.lightspeedsystems.com
$PUBLIC_IP production-gc.lsfilter.com
$PUBLIC_IP lsfilter.com
$PUBLIC_IP devices.filter.relay.school
$PUBLIC_IP filter.relay.school
$PUBLIC_IP relay.school
EOF

# Generate CoreDNS Corefile
cat > /etc/coredns/Corefile << EOF
. {
    cache 300
    hosts /etc/coredns/lshosts {
        fallthrough
    }
    template IN A lightspeedsystems.com {
        match "^(.*\\.)?lightspeedsystems\\.com\\.$"
        answer "{{ .Name }} 60 IN A $PUBLIC_IP"
        fallthrough
    }
    template IN A lightspeedsystems.app {
        match "^(.*\\.)?lightspeedsystems\\.app\\.$"
        answer "{{ .Name }} 60 IN A $PUBLIC_IP"
        fallthrough
    }
    template IN A lsfilter.com {
        match "^(.*\\.)?lsfilter\\.com\\.$"
        answer "{{ .Name }} 60 IN A $PUBLIC_IP"
        fallthrough
    }
    template IN A ably.io {
        match "^(.*\\.)?ably\\.io\\.$"
        answer "{{ .Name }} 60 IN A $PUBLIC_IP"
        fallthrough
    }
    template IN A relay.school {
        match "^(.*\\.)?relay\\.school\\.$"
        answer "{{ .Name }} 60 IN A $PUBLIC_IP"
        fallthrough
    }
    forward . 1.1.1.1 8.8.8.8 9.9.9.9
    errors
}
EOF

echo "CoreDNS configured."

# Start Python services
python3 /opt/fake-relay.py &
python3 /opt/prewarm-api.py &

# Start CoreDNS (ignore if port 53 is already in use)
coredns -conf /etc/coredns/Corefile &
COREDNS_PID=$!
sleep 1
if ! kill -0 $COREDNS_PID 2>/dev/null; then
    echo "[WARN] CoreDNS failed to start (port 53 may be in use). Continuing without DNS."
fi

echo ""
echo "=== LIDNS Ready ==="
echo "Server IP:    $PUBLIC_IP"
echo "Setup guide:  http://$PUBLIC_IP/setup"
echo "Prewarm tool: https://lsrelay-config-production.s3.amazonaws.com/prewarm"
echo "CA cert:      http://$PUBLIC_IP/ca.crt"
echo ""

# Check if required ports are reachable from the outside
echo "=== Port Check ==="

# Give services a moment to bind
sleep 1

check_tcp() {
    local port=$1 label=$2
    if nc -z -w4 "$PUBLIC_IP" "$port" 2>/dev/null; then
        echo "  [OK]   $label (port $port/tcp) is reachable from outside"
    else
        echo "  [WARN] $label (port $port/tcp) looks blocked. Open this port in your firewall/router"
    fi
}

check_dns() {
    local result
    result=$(dig @"$PUBLIC_IP" -p 53 production-gc.lsfilter.com A +short +time=4 2>/dev/null || true)
    if [ -n "$result" ]; then
        echo "  [OK]   DNS (port 53/udp) is reachable from outside. Resolved to $result"
    else
        echo "  [WARN] DNS (port 53/udp) looks blocked. Open port 53 UDP in your firewall/router"
    fi
}

check_tcp 80  "HTTP  (setup page)"
check_tcp 443 "HTTPS (filter bypass)"
check_dns
echo ""

# Run nginx in foreground to keep container alive
exec /usr/sbin/nginx -g 'daemon off;'
