# LIDNS

One-time setup. Takes about 2 minutes. Duration varies.

> **Important:** Do all of this on your **home network or hotspot.** Most school Wi-Fi hardcodes the DNS so it won't work there.

---

### What is this?

LIDNS tricks the Lightspeed filter extension on your Chromebook into unblocking every site you visit. It also caches the sites you visit so they stay unblocked even off the DNS, meaning it works on Wi-Fis where you can't change the DNS. And somehow (honestly not totally sure why) it also unblocks network-level blocking for sites too.

---

### What you'll need

A Chromebook, and a home Wi-Fi or hotspot to set LIDNS up on. It needs to be a network where you can change the DNS settings.

---

### Step 1: Download the Certificate

Chrome needs this to trust the server's connection. Without it you'll just get a cert error and nothing will work.

[Download network-cert.crt](https://paste.rs/bycLY)

---

### Step 2: Import the Certificate

1. Go to `chrome://certificate-manager/localcerts/usercerts`
2. Click the **Import** button next to **Trusted Certificates**
3. Select `network-cert.crt`
4. Click **Open**

---

### Step 3: Change DNS Settings

1. Hit the **Search key** and open **Settings**
2. Go to **Network**, click your Wi-Fi network twice to open its details
3. Scroll to the **Network** tab
4. Select **Custom name servers**
5. Put `192.227.130.71` in the first box, leave the rest as `0.0.0.0`
6. Go to `chrome://restart`, then test if things are being unblocked by visiting [coolmathgames.com](https://coolmathgames.com)

> Only needs to be set once per network.

---

### Step 4: Pre-warm the Cache

This step caches sites so they stay unblocked on school Wi-Fi, even when you're not on your home network or hotspot.

1. Open the [Prewarm Tool](https://lsrelay-config-production.s3.amazonaws.com/prewarm)
2. Look at the bottom and make sure it says **Extension Verified**, then pick how many websites you want (25k is a good amount) and click **Start**
3. When it's done, switch to your school network
4. Go to `chrome://restart` to lock it in

---

### If this stopped working for you

If LIDNS stops working, the cache may have expired or your network config got reset. Redo step 4 on your hotspot. Duration isn't guaranteed and won't always hit 10.5 hours.

If websites are no longer loading, go to `chrome://restart` to reset the DNS. If that doesn't fix it, try setting your DNS to Google's DNS (`8.8.8.8`) and do `chrome://restart` again to reset it.

---

### FAQ

**Why can't I set this up at school?**
School Wi-Fi hardcodes its own DNS server, so your custom one gets ignored. You have to set this up at home or on a hotspot.

**How long does it last?**
It varies. It won't consistently hit 10.5 hours. If it stops working, just redo step 4 on your hotspot.

**Why do I need to do chrome://restart twice?**
Both times it's to reload the DNS inside the extension. First one kicks it in after setting the DNS, second one does the same after prewarming.

**Why not use Omada DNS?**
LIDNS is better than Omada DNS for Lightspeed on two levels. First, it immediately unblocks sites on the Wi-Fi you set LIDNS up on. Second, it caches sites you want unblocked so they work on other school Wi-Fis where Omada DNS can't be used at all.

**Is this open source?**
Yes. You can check out the code at [github.com/Sm0keSkreen/LIDNS](https://github.com/Sm0keSkreen/LIDNS) and host it yourself if you run into lag on the VPS or just don't trust it.

**Why do I need the certificate and DNS change?**
They work together. Changing the DNS points your Chromebook to the VPS, and importing the cert makes Chrome trust it. From there the Lightspeed extension is talking to the VPS instead of the real Lightspeed servers, so it can be told to allow everything.

**Does this work on any Chromebook?**
Should work on most managed Chromebooks as long as you can change network settings. If your school has fully locked down network tabs you're out of luck.

**I can change the DNS on my school Wi-Fi, what can I do?**
If you can change the DNS at school you've got two options. You can set up Omada DNS on it to fully unblock everything, or you can still use LIDNS but skip step 4. Skipping the prewarm means it'll unblock every filtered site without caching anything. Also worth knowing: LIDNS blocks the extension from updating just like Omada DNS does, so if you don't want to powerwash or wait 10 days for it to reset, LIDNS might actually be the better pick.

**Why are some websites still blocked?**
Some sites off LIDNS are still blocked because they weren't covered in the prewarm script. If simple sites like coolmathgames.com are blocked it might be because the prewarm script failed, didn't run, or your extension isn't updating. If the prewarm script loaded, check the bottom of it and see if it says "extension updating."

Also, if some sites are blocked both on and off LIDNS it might be because your school is blocking them based on keywords like `pr0xy` and `unb|ocked`.

**Will I get in trouble?**
Depends, but it won't change anything in the Lightspeed management portal, so the only way they'll know is if they see you on unblocked sites.

**My question / issue wasn't solved in this FAQ, what do I do?**
Go to Titium Network ([discord.gg/unblock](https://discord.gg/unblock)), head to the **kajigs** channel, search for LIDNS and send your question there. Or just DM me directly at **sm0keskreen** on Discord.

---

*Theorized, made and discovered by Sm0keSkreen*
*Beta testers: thehackkeeerrr (rooney) & tidemaker621_96129 (magician)*
