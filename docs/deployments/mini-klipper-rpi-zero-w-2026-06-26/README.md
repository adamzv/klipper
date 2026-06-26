# Mini Klipper Raspberry Pi Zero W Backup - 2026-06-26

This directory captures the working Raspberry Pi Zero W deployment before
moving the Prusa Mini+ Klipper host to an Orange Pi Zero LTS.

Included files:

- `printer.cfg`: active Klipper printer configuration from
  `/home/pi/printer_data/config/printer.cfg`.
- `moonraker.conf`: active Moonraker configuration from
  `/home/pi/printer_data/config/moonraker.conf`.
- `pi-state.txt`: host OS, service state, Klipper branch, and Klipper checkout
  revision at backup time.

Important details:

- Active printer config includes Mainsail macros and the real Buddy MCU serial:
  `/dev/serial/by-id/usb-Klipper_stm32f407xx_5B003A0013504B4D31383220-if00`.
- Stock Mini LCD/jogwheel support is not active in `printer.cfg`; it remains
  optional via `config/prusa-mini-stock-lcd.cfg` because it triggered
  `Timer too close` on the Raspberry Pi Zero W during homing.
- The filament switch sensor is disabled because it is not connected.
- At backup time, the Pi's `~/klipper` checkout was still at `f60ade073`, while
  the active config had already been deployed from the newer local branch state.
  For a new host, use the latest pushed branch instead of this old checkout
  revision.

Restore outline for a new host:

1. Install Klipper, Moonraker, and Mainsail.
2. Check out branch `prusa-mini-sherpa-revo-klipper-migration`.
3. Copy `printer.cfg` and `moonraker.conf` into the new
   `~/printer_data/config/`.
4. Verify the Buddy MCU serial under `/dev/serial/by-id/` and update
   `[mcu] serial` if it differs.
5. Restart Klipper and Moonraker.
