# Prusa Mini+ Sherpa/Revo Klipper Migration

This document tracks the migration of a Prusa Mini+ Buddy Rev 1 printer with a
Sherpa Mini direct drive extruder, E3D Revo Micro/ObXidian hotend, stock Mini
LCD/jogwheel, and Mainsail/Fluidd host workflow.

Base Klipper commit: `c707dd19214709dc23684b254a68e3bf69e4cfb3`

Reference repositories inspected:

- `https://github.com/singh-gur/mini_klipper`
- `https://github.com/keenzkustoms/klippermini`
- `https://github.com/Doranku/Prusa-Mini-Klipper`
- `https://github.com/Klipper3d/klipper`

The old forks were used for comparison only. The port keeps ST7789V display
support isolated under `klippy/extras/display` and does not change motion
planning, heaters, TMC internals, or MCU-side `src/` code.

## What Was Ported

- `lcd_type: st7789v` for the stock Mini 240x320 display.
- Buddy display pins from the old Mini forks:
  - `spi_bus: spi2a`
  - `cs_pin: PC9`
  - `rs_pin: PD11`
  - `rst_pin: PC8`
- Stock jogwheel pins:
  - `encoder_pins: ^PE13, ^PE15`
  - `click_pin: ^!PE12`
- A bounded 20x4 Klipper text/menu area rendered onto the color LCD.

The old ST7789V implementation used `numpy` and `Pillow`; this port avoids
those dependencies for Raspberry Pi Zero W friendliness.

## Host Assumptions

- Raspberry Pi Zero W or similar host running Klipper plus Moonraker.
- Mainsail or Fluidd for primary control.
- OrcaSlicer for slicing and upload.
- No OctoPrint, KlipperScreen, camera, timelapse, or Obico requirement.

Deploy `config/printer-prusa-mini-plus-sherpa-revo-klipper.cfg` as the printer
config, then adjust:

- `[mcu] serial` to the actual `/dev/serial/by-id/...` path.
- `[extruder] nozzle_diameter` to the installed Revo nozzle.
- Sherpa `rotation_distance` after calibration.
- PID values after hotend and bed PID tuning.

## Firmware Build

Run:

```sh
make menuconfig
```

Select:

- Enable extra low-level configuration options
- Micro-controller architecture: `STMicroelectronics STM32`
- Processor model: `STM32F407`
- Bootloader offset: `128KiB + 512 byte offset`
- Clock Reference: `12 MHz crystal`
- Communication interface: `USB on PA11/PA12`

Build:

```sh
make
```

Do not erase or replace the Prusa bootloader unless you explicitly decide to.

## First Flash

Put the Buddy board into DFU mode using the board's DFU jumper/header. Older
boards may use a 3-pin jumper; newer boards may use a 2-pin header.

Check USB visibility:

```sh
lsusb
```

Expected ST DFU ID:

```text
0483:df11
```

Flash:

```sh
make flash FLASH_DEVICE=0483:df11
```

Fully power-cycle the Buddy board after flashing from Prusa firmware. If this
is skipped, Klipper may fail to communicate with the TMC2209 drivers and report
an `IFCNT` UART error.

## First Boot Checks

1. Confirm Klipper connects to the Buddy board.
2. Confirm temperatures read plausibly at room temperature.
3. Confirm all fans are off unless commanded.
4. Run `STEPPER_BUZZ STEPPER=stepper_x`, `stepper_y`, `stepper_z`, and
   `extruder` without filament loaded.
5. Confirm endstops/probe with `QUERY_ENDSTOPS`.
6. Confirm the stock LCD initializes and shows the Klipper status screen.
7. Confirm jogwheel direction and click. If one detent skips or requires two
   clicks, change `encoder_steps_per_detent` between `4` and `2`. If direction
   is reversed, swap the two `encoder_pins`.

## Z Offset And Sheets

Baseline:

- Textured PLA Prusa Live Z: `-1.940`
- Klipper `[probe] z_offset`: `1.940`
- `SHEET_TEXTURED_PLA`: `SET_GCODE_OFFSET Z=0`

Configured sheet offsets:

- `SHEET_TEXTURED_PETG`: `Z=0.05`
- `SHEET_TEXTURED_TPU95`: `Z=0.10`
- `SHEET_SMOOTH_PLA`: `Z=0.27`
- `SHEET_SMOOTH_ASA`: `Z=0.39`
- `SHEET_TEXTURED_WOODFILL`: `Z=0.08`, validation required

Placeholders are present for `SHEET_SMOOTH_PETG`, `SHEET_PC`, and `SHEET_PCCF`.
Validate those with slow first-layer tests before using them for production
prints.

## Nozzle Changes

Available Revo nozzles:

- `0.250`
- `0.400`
- `0.600`

When changing nozzle size:

1. Update `[extruder] nozzle_diameter` in the Klipper config.
2. Restart Klipper.
3. Select the matching Orca machine/process profile.
4. Verify first layer on the selected sheet.
5. Recheck max volumetric flow for the material/nozzle combination.
6. Retune pressure advance if needed.

The 0.6 mm Orca profile is the best existing Sherpa reference. The 0.25 and
0.4 mm profiles are conservative starters.

## OrcaSlicer Setup

Repo-local starter profiles live in:

```text
docs/orca-profiles/prusa-mini-klipper-sherpa-revo/
```

Machine start g-code:

```gcode
START_PRINT BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer] SHEET=TEXTURED_PLA
```

Machine end g-code:

```gcode
END_PRINT
```

Create copied machine profiles or edit the start g-code per print for:

- `SHEET=TEXTURED_PLA`
- `SHEET=TEXTURED_PETG`
- `SHEET=TEXTURED_TPU95`
- `SHEET=SMOOTH_PLA`
- `SHEET=SMOOTH_ASA`
- `SHEET=TEXTURED_WOODFILL`

Use Klipper/Moonraker upload settings in Orca if available. Preserve
material-specific temperatures, cooling, flow, retraction, and max volumetric
speed in filament/process profiles rather than hardcoding them in Klipper.

## Adaptive Mesh

The config uses:

```ini
[bed_mesh]
speed: 100
horizontal_move_z: 5
mesh_min: 10, 10
mesh_max: 141, 167
probe_count: 5, 5
algorithm: bicubic
fade_start: 1
fade_end: 10
adaptive_margin: 5
```

`START_PRINT` runs:

```gcode
BED_MESH_CLEAR
BED_MESH_CALIBRATE ADAPTIVE=1
```

For best adaptive bounds, ensure Orca emits object information compatible with
Klipper's `[exclude_object]`.

## Input Shaper

Do not do heavy graph analysis on the Pi Zero W.

Temporary include:

```ini
[include adxl345-rpi-zero.cfg]
```

Workflow:

1. Install/enable the Linux MCU service on the Pi.
2. Include `config/adxl345-rpi-zero.cfg` temporarily.
3. Run `ACCELEROMETER_QUERY`.
4. Capture resonance data with `ACCELEROMETER_MEASURE` or `SHAPER_CALIBRATE`.
5. Copy `/tmp/adxl345-*.csv` to a faster machine.
6. Run Klipper's graph/calibration scripts there.
7. Paste final measured `[input_shaper]` values into the printer config.

Do not invent input shaper values from the existing M593 placeholders.

## Rollback

Keep a known-good Prusa firmware image ready.

If the Prusa bootloader remains intact, use the normal Prusa firmware update
path. If DFU flashing is required:

```sh
dfu-util -a 0 -D firmware.dfu
```

Breaking the appendix is irreversible and may affect warranty or resale. Some
rollback paths may require flashing an older Prusa firmware first depending on
bootloader and firmware version; verify the exact Prusa firmware path before
starting rollback.

## Manual Printer Checklist

- LCD initializes and no longer remains on the bootloader/blank screen.
- Jogwheel scrolls one menu item per detent and click enters/selects.
- Status screen shows ready/printing/error state, hotend temp, bed temp,
  progress, time, and status message.
- Menu can pause, resume, cancel, preheat PLA/PETG, cooldown, load/unload,
  home, move axes, and adjust Z offset.
- Mainsail/Fluidd can still start, pause, resume, cancel, and upload prints.
- First layer is validated for each sheet and material combination.
- Sherpa rotation distance, pressure advance, and material max volumetric flow
  are calibrated before relying on production profiles.
