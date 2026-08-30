# LG webOS TV connectivity experiment

This is a local connectivity/pointer experiment based on Home Assistant Core
2026.1.3's `webostv` component. Its runtime changes are the `aiowebostv 0.9.2`
pin and redaction of `macAddress` from diagnostics.

The newer client may improve registration or connection handling.
This is not a guaranteed `WRITE_SETTINGS` fix. The TV firmware may still reject
the `energySaving` endpoint.

## Acceptance gates

The experiment passes only when all of these are observed on the target TV:

1. The existing `media_player` is available and diagnostics report
   `is_connected: true` after reload or restart.
2. `settings/getSystemSettings` returns the physical `energySaving` value.
3. A slider change produces the mapped value on the TV and the same value in a
   fresh `settings/getSystemSettings` readback.
4. The original energy-saving value is restored and confirmed by another
   readback.

Helper or fan state alone does not pass these gates.
