# LG webOS TV connectivity experiment

This is a local connectivity/pointer experiment based on Home Assistant Core
2026.1.3's `webostv` component. It pins `aiowebostv==0.9.2`, redacts
`macAddress` from diagnostics, and includes these connection repairs:

- Setup, reconnect, pairing, and configuration flows share a client that tries
  secure websocket port 3001 when plain port 3000 rejects or times out.
- SSDP address changes for the same TV update its host and reload the existing
  config entry, preserving its pairing key. The callback unregisters on unload.

These fixes are built into the component. No separate SSDP patch is needed.
Use it on a trusted LAN. Matching an SSDP UUID is not device authentication,
and the pinned client accepts the TV's self-signed TLS certificate.

The newer client may improve registration or connection handling.
This is not a guaranteed `WRITE_SETTINGS` fix. The TV firmware may still reject
the `energySaving` endpoint.

## Verify

Run these checks with Python from a Home Assistant Core 2026.1.3 installation.
`CORE_COMPONENT` must point to the original Core 2026.1.3
`homeassistant/components/webostv` directory:

```sh
python test_exact_override.py CORE_COMPONENT
python tests/test_connection.py .
python tests/test_ssdp.py .
```

CI runs all three checks. The first preserves the original Core provenance,
the exact dependency pin and diagnostics redaction, and byte-for-byte equality
of every unchanged component file. The other checks use fake device responses
to cover connection fallback and SSDP recovery; they do not change a TV.

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
For live tests, use only Off and Minimum unless another mode is explicitly
authorized. Restore the starting selection when it is one of those two modes.
Record physical-device evidence separately from the mocked checks.
