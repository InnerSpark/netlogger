# AllStar server setup

Net Logger needs two things from your AllStar server:

1. **Audio:** a private node that sends what it hears to Net Logger over USRP.
2. **Control (optional):** an AMI login so the dashboard can connect and disconnect that node.

**Tip:** the **Health** page in the app has these same steps in its setup guide with your node number, ports, and addresses filled in, plus a live status check.

These steps are for **ASL3**. Other AllStar builds use the same files, but paths and defaults can differ. After each change, check with the commands shown.

Back up `/etc/asterisk` before editing.

## 1. Network path

The AllStar server sends UDP audio to Net Logger on port **34001**, and Net Logger connects to the AllStar server on TCP **5038** for AMI.

- **Same LAN:** use Net Logger's LAN IP. Make sure no firewall blocks those ports.
- **Different networks** (cloud node, logger at home): install **Tailscale** on both and use Net Logger's Tailscale IP (starts with `100.`). No port forwarding, and nothing is exposed to the internet.

## 2. Make sure the USRP channel is loaded

```
sudo asterisk -rx "module show like usrp"
```

If `chan_usrp.so` isn't listed as running, add this to `/etc/asterisk/modules.conf` and restart Asterisk:

```
load = chan_usrp.so
```

## 3. Add the logger's private node

Private node numbers are **under 2000**, aren't registered with AllStarLink, and nobody outside can connect to them. This guide uses **1999**. Pick another if you already use it.

In `/etc/asterisk/rpt.conf`, add a node stanza. Replace the IP with Net Logger's address:

```
[1999](node-main)
rxchannel = USRP/100.64.0.10:34001:32001
duplex = 0
telemdefault = 0
```

- `rxchannel` sends the node's audio to Net Logger (UDP 34001). Net Logger never sends audio back.
- `telemdefault = 0` keeps telemetry quiet on this node.

In the `[nodes]` section of the same file, add:

```
1999 = radio@127.0.0.1/1999,NONE
```

Restart and check:

```
sudo systemctl restart asterisk
sudo asterisk -rx "rpt localnodes"
```

1999 should be listed.

## 4. Link it by hand (optional test)

Before setting up AMI, you can link the logger node from the Asterisk CLI. Replace 2000 with your node:

```
sudo asterisk -rx "rpt cmd 1999 ilink 2 2000"    # connect, monitor only
sudo asterisk -rx "rpt lstats 1999"              # should list 2000
sudo asterisk -rx "rpt cmd 1999 ilink 1 2000"    # disconnect
```

With a net open in the dashboard, key up on the node. You should see the transmission under **Last heard**.

## 5. AMI login for node control

Net Logger uses the Asterisk Manager Interface to run exactly three commands on the logger node: connect (monitor only), disconnect, and list links.

In `/etc/asterisk/manager.conf`, make sure AMI is on:

```
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0
```

Add a user just for Net Logger. Use a long random secret, and allow only Net Logger's address:

```
[netlogger]
secret = paste-a-long-random-secret-here
deny = 0.0.0.0/0.0.0.0
permit = 100.64.0.10/255.255.255.255
read = command
write = command
```

Reload:

```
sudo asterisk -rx "manager reload"
```

Then in Net Logger's `.env`:

```
AMI_HOST=<AllStar server IP, e.g. its Tailscale IP>
AMI_PORT=5038
AMI_USER=netlogger
AMI_SECRET=<the secret above>
LOGGER_NODE=1999
DEFAULT_NODE=<your node, optional>
```

Restart Net Logger with `docker compose up -d`. The **AllStar nodes** card should say it's in monitor mode and let you connect.

## Notes

- **Monitor mode only.** Net Logger always links with `ilink 2`. The logger node can hear the linked node but never sends audio to it.
- **Node IDs** on the private node only go to Net Logger, not the air. They may show up in **Last heard** as text. That's harmless.
- **AUTO_CONNECT=1** links `DEFAULT_NODE` when Net Logger starts. After that, a manual disconnect sticks.
