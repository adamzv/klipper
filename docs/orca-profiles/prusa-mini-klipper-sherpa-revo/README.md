# Prusa Mini Klipper Sherpa/Revo Orca Profiles

These repo-local profiles are migration templates. They do not modify the live
OrcaSlicer configuration in `~/Library/Application Support/OrcaSlicer`.

## Source Profiles Inspected

- `Prusa MINIIS 0.6 nozzle - Sherpa mini`
- `Prusa MINIIS 0.6 nozzle - Sherpa mini - Calibration M593 OFF`
- `0.20mm Balanced - Daily @MINIIS 0.6`
- `0.20mm Quality - Small Parts @MINIIS 0.6`
- `0.20mm Fast - Experimental @MINIIS 0.6`
- `0.20mm Calibration - Ringing M593 OFF @MINIIS 0.6`
- User filament profiles for PLA, PETG, ASA, and TPU 95A where present

## Import Strategy

1. Import the machine profile matching the installed Revo nozzle.
2. Import the matching process starter profile.
3. Use material profiles separately from nozzle/process profiles.
4. Set the `SHEET=` argument in the machine start g-code per print or per
   copied machine profile.

The machine start g-code intentionally delegates printer preparation to Klipper:

```gcode
START_PRINT BED_TEMP=[bed_temperature_initial_layer_single] EXTRUDER_TEMP=[nozzle_temperature_initial_layer] SHEET=TEXTURED_PLA
```

The end g-code is:

```gcode
END_PRINT
```

## Nozzle Rules

Whenever changing physical nozzle size:

1. Update `nozzle_diameter` in the deployed Klipper config.
2. Select the matching Orca machine/process profile.
3. Verify first layer with the selected sheet macro.
4. Verify material/nozzle max volumetric flow.
5. Retune pressure advance if needed.

The 0.6 mm profile preserves the existing Sherpa direct-drive retraction
starting point. The 0.25 and 0.4 mm profiles are conservative starters and need
independent PA, flow, first-layer, and max-volumetric calibration.
