# Orange Pi Zero LTS Tenda U2v5 Wi-Fi setup

This documents the working USB Wi-Fi setup for the Prusa Mini Klipper host.
It is intended as a recovery checklist after reflashing the Orange Pi image.

## Known working state

- Board: Orange Pi Zero LTS
- OS: Armbian
- Kernel at setup time: `6.18.35-current-sunxi`
- USB Wi-Fi adapter: Tenda U2 v5.0
- Storage/ZeroCD USB ID before driver switch: `a69c:5721 aicsemi Aic MSC`
- Wi-Fi USB ID after switch: `2604:0014 Tenda AIC8800DC`
- Working Wi-Fi interface name: `wlxc83a35edc7d4`
- Working Wi-Fi MAC: `c8:3a:35:ed:c7:d4`
- Onboard flaky Wi-Fi driver to disable after USB Wi-Fi works: `xradio_wlan`
- Working USB Wi-Fi driver modules:
  - `aic_load_fw`
  - `aic8800_fdrv`

Do not force-bind `2604:0014` with `new_id`; that crashed the kernel with the
non-official driver. Use the official Tenda `.deb`.

## Install official Tenda driver

Download the official U2 v5.0 Linux driver:

https://www.tendacn.com/product/help/U2V5#download

The package used successfully was:

- `AX300 USB Adapter Driver for Linux (Ubuntu) (3.10~6.17) V1.0.1.3`
- ZIP file downloaded from Tenda as `690945314889797.zip`
- Contains `Linux（Ubuntu）OS Driver/ax300-wifi-adapter-linux-driver.deb`

Copy the ZIP to the Orange Pi, then run:

```sh
sudo apt update
sudo apt install unzip build-essential
unzip 690945314889797.zip -d ~/tenda-u2v5-driver
cd ~/tenda-u2v5-driver/Linux*Driver
sudo apt install ./ax300-wifi-adapter-linux-driver.deb
sudo reboot
```

If `apt install linux-headers-$(uname -r)` cannot find headers on Armbian, that
is not necessarily fatal for this `.deb`. The successful setup did not require
that header package to be installed manually.

## Verify driver and interface

After reboot, with the Tenda plugged in:

```sh
lsusb
lsmod | grep -Ei 'aic|8800'
ip -br link
dmesg -T | grep -Ei 'aic|2604|0014|5721|firmware|wlan' | tail -160
```

Expected:

```text
Bus ... ID 2604:0014 Tenda AIC8800DC
aic8800_fdrv ...
aic_load_fw ...
wlxc83a35edc7d4  DOWN  c8:3a:35:ed:c7:d4
```

The driver log should include:

```text
New interface create wlan1
usb ... wlxc83a35edc7d4: renamed from wlan1
```

## Configure netplan for USB Wi-Fi

Use the generated interface name directly. The `networkd` backend does not
support `match:` for Wi-Fi devices.

Edit:

```sh
sudo nano /etc/netplan/01-printer-network.yaml
```

Use:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    end0:
      dhcp4: true
      optional: true
  wifis:
    wlxc83a35edc7d4:
      dhcp4: true
      optional: true
      access-points:
        "T-519781":
          password: "YOUR_REAL_WIFI_PASSWORD"
```

Apply:

```sh
sudo chmod 600 /etc/netplan/01-printer-network.yaml
sudo netplan generate
sudo netplan apply
sudo systemctl restart systemd-networkd
```

Verify:

```sh
ip -br addr
networkctl status wlxc83a35edc7d4
ping -I wlxc83a35edc7d4 -c 20 192.168.1.1
```

Expected:

```text
wlxc83a35edc7d4  UP  192.168.1.x/24
```

## Disable onboard Orange Pi Wi-Fi

Only do this after the Tenda USB Wi-Fi has an IP and can ping the router.

```sh
sudo nano /etc/modprobe.d/blacklist-xradio.conf
```

Put:

```conf
blacklist xradio_wlan
```

Reboot:

```sh
sudo reboot
```

Verify:

```sh
ip -br addr
lsmod | grep -Ei 'aic|xradio'
```

Expected final state:

```text
wlxc83a35edc7d4  UP  192.168.1.x/24
aic8800_fdrv ...
aic_load_fw ...
```

There should be no `xradio_wlan` module loaded.

## SSH

Use the current DHCP address from `ip -br addr`, or mDNS:

```sh
ssh pi@mini-klipper.local
```

If the image was reflashed and SSH complains about host identity:

```sh
ssh-keygen -R mini-klipper.local
ssh-keygen -R mini-klipper.home
ssh-keygen -R 192.168.1.150
```

Then reconnect and accept the new host key.

## Kernel update warning

The Tenda U2v5 driver is out-of-tree. A kernel update may break it or require
reinstalling `ax300-wifi-adapter-linux-driver.deb`.

Avoid casual kernel upgrades on the printer host. If Wi-Fi disappears after an
upgrade, reconnect Ethernet or use onboard Wi-Fi temporarily, reinstall the
official Tenda `.deb`, reboot, and verify `wlxc83a35edc7d4` again.

