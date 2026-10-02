"""The LG webOS TV integration."""

from __future__ import annotations

from contextlib import suppress
from functools import partial
from urllib.parse import urlparse

from aiowebostv import WebOsTvPairError

from homeassistant.components import notify as hass_notify
from homeassistant.components import ssdp
from homeassistant.const import (
    ATTR_CONFIG_ENTRY_ID,
    CONF_CLIENT_SECRET,
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.ssdp import ATTR_UPNP_UDN, SsdpServiceInfo
from homeassistant.helpers.typing import ConfigType

from .client import WebOsClient
from .const import DATA_HASS_CONFIG, DOMAIN, PLATFORMS, WEBOSTV_EXCEPTIONS
from .helpers import WebOsTvConfigEntry, update_client_key

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
WEBOSTV_SSDP_ST = "urn:lge-com:service:webos-second-screen:1"


@callback
def _update_host_from_ssdp(
    hass: HomeAssistant,
    entry: WebOsTvConfigEntry,
    discovery_info: SsdpServiceInfo,
    change: ssdp.SsdpChange,
) -> None:
    """Update a moved TV's host from SSDP."""
    if (
        change is ssdp.SsdpChange.BYEBYE
        or discovery_info.ssdp_st != WEBOSTV_SSDP_ST
        or not discovery_info.ssdp_location
    ):
        return

    uuid = discovery_info.upnp.get(ATTR_UPNP_UDN)
    try:
        host = urlparse(discovery_info.ssdp_location).hostname
    except ValueError:
        return
    if (
        not isinstance(uuid, str)
        or uuid.removeprefix("uuid:") != entry.unique_id
        or not host
        or host == entry.data[CONF_HOST]
    ):
        return

    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_HOST: host}
    )
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def _async_register_ssdp_callback(
    hass: HomeAssistant, entry: WebOsTvConfigEntry
) -> None:
    """Listen for this TV at a new SSDP location."""
    entry.async_on_unload(
        await ssdp.async_register_callback(
            hass,
            partial(_update_host_from_ssdp, hass, entry),
            {"st": WEBOSTV_SSDP_ST},
        )
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the LG webOS TV platform."""
    hass.data.setdefault(DOMAIN, {DATA_HASS_CONFIG: config})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: WebOsTvConfigEntry) -> bool:
    """Set the config entry up."""
    host = entry.data[CONF_HOST]
    key = entry.data[CONF_CLIENT_SECRET]

    # Attempt a connection, but fail gracefully if tv is off for example.
    entry.runtime_data = client = WebOsClient(
        host, key, client_session=async_get_clientsession(hass)
    )
    with suppress(*WEBOSTV_EXCEPTIONS):
        try:
            await client.connect()
        except WebOsTvPairError as err:
            raise ConfigEntryAuthFailed(err) from err

    # If pairing request accepted there will be no error
    # Update the stored key without triggering reauth
    update_client_key(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: entry.title,
                ATTR_CONFIG_ENTRY_ID: entry.entry_id,
            },
            hass.data[DOMAIN][DATA_HASS_CONFIG],
        )
    )

    async def async_on_stop(_event: Event) -> None:
        """Unregister callbacks and disconnect."""
        client.clear_state_update_callbacks()
        await client.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_on_stop)
    )
    await _async_register_ssdp_callback(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WebOsTvConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        client = entry.runtime_data
        await hass_notify.async_reload(hass, DOMAIN)
        client.clear_state_update_callbacks()
        await client.disconnect()

    return unload_ok
