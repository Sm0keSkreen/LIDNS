from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import json, re, logging, subprocess, time, urllib.request, zipfile, io, os, socket
from datetime import datetime

logging.basicConfig(level=logging.INFO)

FAKE_POLICY = json.load(open('/var/www/lsrelay/fake_policy.json'))
FAKE_POLICY_BYTES = json.dumps(FAKE_POLICY).encode()

TRANCO_CACHE = "/tmp/tranco_top1m.txt"
TRANCO_URL = "https://tranco-list.eu/top-1m.csv.zip"

MANUAL_LIST = '/opt/custom_domains.json'

_tranco_lock = threading.Lock()

def load_manual():
    try:
        return set(json.load(open(MANUAL_LIST)))
    except Exception:
        return set()

def save_manual(domains):
    with open(MANUAL_LIST, 'w') as f:
        json.dump(sorted(domains), f)

def get_tranco_domains(n):
    age = time.time() - os.path.getmtime(TRANCO_CACHE) if os.path.exists(TRANCO_CACHE) else 999999
    if age > 86400:
        with _tranco_lock:
            # Re-check after acquiring lock — another thread may have finished while we waited
            age = time.time() - os.path.getmtime(TRANCO_CACHE) if os.path.exists(TRANCO_CACHE) else 999999
            if age > 86400:
                logging.info("Downloading Tranco top 1M list...")
                r = urllib.request.urlopen(TRANCO_URL, timeout=120)
                zf = zipfile.ZipFile(io.BytesIO(r.read()))
                with zf.open("top-1m.csv") as csvf:
                    content = csvf.read().decode("utf-8")
                with open(TRANCO_CACHE, "w") as f:
                    f.write(content)
    domains = []
    with open(TRANCO_CACHE) as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            parts = line.strip().split(",")
            if len(parts) >= 2:
                domains.append(parts[1])
    return domains

_rank_index = {}

def get_tranco_rank(domain):
    global _rank_index
    domain = domain.lower().strip().lstrip('www.')
    if not _rank_index:
        logging.info('Building Tranco rank index...')
        for i, d in enumerate(get_tranco_domains(1000000)):
            dl = d.lower().lstrip('www.')
            if dl not in _rank_index:
                _rank_index[dl] = i + 1
        logging.info('Rank index ready: %d entries', len(_rank_index))
    return _rank_index.get(domain)

def rank_to_tier(rank):
    for n, t in [(1000,'1K'),(5000,'5K'),(10000,'10K'),(25000,'25K'),(50000,'50K'),
                 (100000,'100K'),(250000,'250K'),(500000,'500K'),(1000000,'1M')]:
        if rank <= n:
            return 'Top ' + t
    return 'Top 1M+'

def domain_exists(domain):
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo(domain, 80)
        return True
    except Exception:
        return False

def clean_domain(host):
    host = re.sub(r'https?://', '', str(host))
    host = re.sub(r'[*?%]', '', host)
    host = host.split('/')[0].strip('.')
    if '.' in host and ' ' not in host and len(host) < 120 and not host.startswith('.'):
        if not re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            return host
    return None

def parse_relay_logs():
    try:
        result = subprocess.run(
            ['journalctl', '-u', 'fake-relay', '--no-pager', '--since', '90 days ago'],
            capture_output=True, text=True, timeout=30
        )
        first = {}
        last = {}
        for line in result.stdout.splitlines():
            m = re.match(r'(\w+ \d+ \d+:\d+:\d+).*action=dy_lookup host=(\S+)', line)
            if m:
                ts, host = m.group(1), m.group(2)
                d = clean_domain(host)
                if d:
                    if d not in first:
                        first[d] = ts
                    last[d] = ts
        return {h: {'first': first[h], 'last': last[h]} for h in first}
    except Exception as e:
        logging.warning('parse_relay_logs: ' + str(e))
        return {}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_GET(self):
        if self.path == '/prewarm-api/ping':
            self.send_json(200, {'ok': True})

        elif self.path.startswith("/prewarm-api/top-domains"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            try:
                n = min(max(int(qs.get("n", ["1000"])[0]), 1), 1000000)
            except Exception:
                n = 1000
            try:
                domains = get_tranco_domains(n)
                self.send_json(200, {"domains": domains, "count": len(domains)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        elif self.path.startswith('/prewarm-api/check-canary'):
            try:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query)
                domain = qs.get('domain', [''])[0].strip()
                if not domain or not re.match(r'^[a-z0-9.\-]+$', domain):
                    self.send_json(400, {'error': 'invalid domain'})
                    return
                found = False
                try:
                    with open('/tmp/relay-domains.log', 'r') as f:
                        found = domain in f.read()
                except FileNotFoundError:
                    pass
                self.send_json(200, {'found': found})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path.startswith('/prewarm-api/domain-rank'):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            domain = qs.get('domain', [''])[0].strip()
            if not domain:
                self.send_json(400, {'error': 'missing domain'})
                return
            try:
                rank = get_tranco_rank(domain)
                if rank:
                    self.send_json(200, {'domain': domain, 'rank': rank, 'tier': rank_to_tier(rank)})
                else:
                    self.send_json(200, {'domain': domain, 'rank': None, 'tier': 'Not in top 1M'})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        elif self.path in ('/prewarm-api/custom-add', '/prewarm-api/custom-remove'):
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
            domain = body.get('domain', '').strip().lower()
            if self.path == '/prewarm-api/custom-add':
                if not domain or ' ' in domain or len(domain) > 200:
                    self.send_json(400, {'error': 'invalid domain'})
                    return
                try:
                    if not domain_exists(domain):
                        self.send_json(400, {'error': 'no DNS records found'})
                        return
                    manual = load_manual()
                    manual.add(domain)
                    save_manual(manual)
                    self.send_json(200, {'ok': True, 'count': len(manual)})
                except Exception as e:
                    self.send_json(500, {'error': str(e)})
            else:
                try:
                    manual = load_manual()
                    manual.discard(domain)
                    save_manual(manual)
                    self.send_json(200, {'ok': True, 'count': len(manual)})
                except Exception as e:
                    self.send_json(500, {'error': str(e)})

        elif self.path == '/prewarm-api/custom-blocked':
            try:
                top1m = set(get_tranco_domains(1000000))
                raw = parse_relay_logs()
                domains = sorted(list((set(raw.keys()) | load_manual()) - top1m))
                self.send_json(200, {'domains': domains, 'count': len(domains)})
            except Exception as e:
                self.send_json(500, {'error': str(e)})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path in ('/prewarm-api/custom-add', '/prewarm-api/custom-remove'):
            self.do_GET()
            return
        length = int(self.headers.get('Content-Length', 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(FAKE_POLICY_BYTES)))
        self.end_headers()
        self.wfile.write(FAKE_POLICY_BYTES)

    def log_message(self, *args): pass


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

# Rank index (1M domains, ~100MB+ in memory) is built lazily on first
# /domain-rank or /custom-blocked request instead of at boot, so idle
# memory usage stays low on memory-constrained hosts.

ThreadingHTTPServer(('127.0.0.1', 8446), Handler).serve_forever()
