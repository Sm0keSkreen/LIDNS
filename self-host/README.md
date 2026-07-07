# LIDNS - Lightspeed Bypass Server

A self-hosted server that intercepts Lightspeed's filter infrastructure, returning fake "allow all" responses so Chromebooks bypass content filtering entirely.

## VPS vs. Running It At Home

Running LIDNS on your home network sounds simple, but it almost never works:

- **ISPs block the ports.** LIDNS needs ports 53 (DNS), 80 (HTTP), and 443 (HTTPS) reachable from outside your network. Most residential ISPs block inbound traffic on port 53 entirely, and many block 80/443 too unless you pay for a business plan.
- **Dynamic IP addresses.** Your home IP changes whenever your router reboots. You would have to update your Chromebook's DNS setting every time.
- **Router configuration.** You need to set up port forwarding correctly and keep it working. If your router reboots or your ISP pushes a firmware update, it may reset.
- **Always on.** Your home machine has to be running 24/7. A VPS is always on for $2/month.

**A cheap VPS solves all of these problems.** It has a static public IP, ports are open by default, and it runs 24/7. I recommend RackNerd.

---

## Step 1: Get a VPS from RackNerd

### Purchase

1. Go to [racknerd.com](https://www.racknerd.com/kvm-vps).
2. Find the cheapest KVM plan (usually around $10-23/year depending on current deals). These specs are more than enough:
   - 512 MB RAM / 1 vCore / 10-30 GB SSD / 1 IP
3. Click **Order Now** on that plan.
4. On the configuration page:
   - **Location:** Pick whichever datacenter is closest to you.
   - **Operating System:** Select **Ubuntu 22.04** (recommended) or any Debian/RHEL-based Linux.
   - Leave everything else default.
5. Add to cart, create an account, and check out.

### Welcome Email

After paying, you will get a welcome email that looks like this:

```
Subject: New VPS Server Information

Your VPS has been set up and is now ready to use.

Hostname: vps.example.com
Main IP: 123.45.67.89
Root Password: SomeRandomPassword123

You can manage your VPS at: https://nerdvm.racknerd.com
```

Write down:
- **Main IP** - this is your server's IP address
- **Root Password** - the SSH login password
- **Management URL** - usually `https://nerdvm.racknerd.com`

---

## Step 2: Log Into Your VPS

### Option A: SSH (recommended)

On Mac or Linux, open Terminal. On Windows, open PowerShell or install [PuTTY](https://putty.org):

```bash
ssh root@YOUR_VPS_IP
```

Enter the root password from your welcome email when prompted. You should see a shell prompt like `root@vps:~#`.

### Option B: VNC Console (if SSH is not working)

If SSH fails, use the VNC console in your RackNerd dashboard:

1. Go to `https://nerdvm.racknerd.com` and log in with the account you created at checkout.
2. Click your VPS in the list.
3. Click **VNC** or **Console** - this opens a virtual screen of your server right in the browser.
4. Log in with username `root` and the password from your welcome email.
5. You now have a terminal inside the browser - run the install command from here.

---

## Step 3: Install LIDNS

Run this one command on your VPS:

```bash
curl -fsSL https://raw.githubusercontent.com/Sm0keSkreen/LIDNS/main/self-host/install.sh | bash
```

This will:
- Install git if it is not already installed
- Clone the LIDNS repo to `/root/lidns`
- Run the setup script automatically

The setup script handles everything:
- Installs Docker
- Stops anything already using ports 53, 80, or 443
- Opens firewall ports
- Builds and starts all services in Docker
- Generates SSL certs tied to your server's IP

This will take a while, it is done when no new text is being printed.

---

## Step 4: Set Up Your Chromebook

On your home network or hotspot (not school Wi-Fi), visit:

```
http://YOUR_VPS_IP/setup
```

Follow the steps on that page to install the cert and set your DNS. After setting the DNS, do `chrome://restart` then test by visiting [coolmathgames.com](https://coolmathgames.com) to confirm things are being unblocked.

also if the ip is blocked on your chromebook, then vist on anathere device like your phone or pc if you have one.

---

## Step 5: Prewarm

This step caches sites so they stay unblocked on school Wi-Fi, even when you're not on your home network or hotspot.

After changing DNS and installing the cert (send it to your school email if blocked), visit:

```
http://YOUR_VPS_IP/prewarm
```

Run the prewarm with 25K domains. When it finishes, switch to your school network, then go to `chrome://restart` to lock it in.

The bypass works for about 10 days before Lightspeed pushes a new filter policy. Re-run the prewarm tool to refresh.

---

## Running on Windows or Mac (Unsupported)

> **Warning:** LIDNS was designed and tested on Linux only. Windows support is experimental and may be broken. If you run into issues on Windows, use a VPS instead.

If you want to run LIDNS on a home machine, you need [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed first.

**Windows:** double-click `setup.bat`

**Mac/Linux:**
```bash
./setup.sh
```

Your machine also needs to be reachable from the internet. That means port forwarding 53 (UDP), 80, and 443 from your router to your machine's local IP. This varies by router model. A VPS is much easier.

---

## Architecture

```
Chromebook
  |
  +-- DNS --> VPS (CoreDNS resolves all LS domains to VPS IP)
  |
  +-- HTTPS --> nginx (intercepts with spoofed cert)
  |     +-- lsrelay-config-production.s3.amazonaws.com
  |     |     +-- /setup       --> setup guide
  |     |     +-- /prewarm     --> prewarm UI
  |     |     +-- noupdate.xml --> blocks extension updates
  |     |
  |     +-- production-gc.lsfilter.com --> fake-relay.py (WebSocket)
  |     |     +-- dy_lookup --> always returns cat:1 (allowed)
  |     |
  |     +-- devices.filter.relay.school --> prewarm-api.py
  |           +-- /filter/chrome/v2/user_policy --> fake policy (all disabled)
  |
  +-- Prewarm tool --> fires fetch() to top 1M domains
        +-- Lightspeed sees all domains --> marks them allowed in local cache
```

---

## Notes

- Do all setup steps on your home network or hotspot. School Wi-Fi routes DNS through its own servers so the custom DNS won't work there.
- The CA cert is generated fresh for your server IP when you first run setup. Each instance gets its own unique cert.
- The `coredns.tgz` in this repo contains the CoreDNS binary. You can also download it from [coredns.io](https://coredns.io).
