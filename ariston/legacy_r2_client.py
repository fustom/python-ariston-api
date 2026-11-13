"""
Legacy R2 (remocon-net) client.

Some GALEVO-classified devices (observed on Elco heat pumps with a BSB
controller) accept writes on the modern REST v2 endpoint
(`/api/v2/remote/dataItems/{gw}/set`) with a `{"success": true}` response,
but the command has NO effect on the physical device.

The official web client (remocon-net.remotethermo.com / ariston-net...)
for these same devices uses a legacy ASP.NET MVC-style endpoint instead:

    POST /R2/PlantHome/GetData/{gatewayId}?umsys={umsys}   (read)
    POST /R2/PlantHome/SetData/{gatewayId}?umsys={umsys}   (write)

This module is a minimal, isolated client for that legacy path, used only
as a fallback when the modern REST v2 write is confirmed to have no effect
(see `GalevoDevice.async_set_plant_mode` for the verification/fallback
logic). It intentionally does NOT share the aiohttp session or auth state
of the main `AristonAPI` client, since the two use different auth
mechanisms (session cookies here vs. bearer token there).

NOTE: `viewModel` returned by the site is NOT available via a clean read
endpoint - it's built client-side in JS from data embedded in the initial
page render. This client works around that by keeping a cached "known
good" viewModel (seeded from a real capture) and patching only the
plant-mode-related fields before writing. This is pragmatic but not fully
general - if Elco/Ariston changes the viewModel schema, or if other
fields turn out to matter for other kinds of writes, this will need
revisiting.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Bundled default viewModel template, captured from a real, confirmed-
# working "set to OFF" action on a specific Elco Aerotop / BSB gateway.
# IMPORTANT LIMITATION: this is device/account-specific pragmatism, not a
# general solution. It is used as a best-effort default so the fallback
# works out of the box for the device it was captured from, but other
# devices (different firmware/model) may have a different viewModel shape
# and this template may not apply cleanly. A more general fix would parse
# the live viewModel out of the initial /R2/Plant/Index page HTML instead
# of relying on a static bundled capture - left as a future improvement.
_DEFAULT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "default_viewmodel_template.json"
)


def _load_default_viewmodel() -> Optional[dict[str, Any]]:
    try:
        with open(_DEFAULT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

_BASE_URL = "https://www.remocon-net.remotethermo.com"

# Confirmed via real captures. Note the sparse enum (value 3 does not
# exist) - do NOT derive this from list position/index.
PLANT_MODE_VALUES: dict[str, int] = {
    "Estate": 0,               # Summer (DHW only)
    "Inverno": 1,              # Winter (CH + DHW)
    "Solo riscaldamento": 2,   # Heating only
    "Solo raffreddamento": 4,  # Cooling only
    "OFF": 5,                  # Off
}


class AristonR2LegacyClient:
    """Minimal client for the legacy /R2/ write path, used as a fallback
    when the REST v2 write silently no-ops on certain devices."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._session: Optional[aiohttp.ClientSession] = None
        self._logged_in = False
        # Cached full viewModel from a real capture - see module docstring
        # and _load_default_viewmodel() for the important caveats.
        self._viewmodel_cache: Optional[dict[str, Any]] = _load_default_viewmodel()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json; charset=UTF-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "ajax-request": "json",
                }
            )
        return self._session

    async def _login(self) -> None:
        session = await self._ensure_session()
        url = f"{_BASE_URL}/R2/Account/Login?returnUrl=%2FR2%2FHome"
        payload = {
            "email": self._username,
            "password": self._password,
            "rememberMe": True,
            "language": "Italian",
        }
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            if not body.get("ok", True):
                raise RuntimeError(f"Legacy R2 login failed: {body}")
        self._logged_in = True
        _LOGGER.debug("Legacy R2 client: login successful")

    async def _get_data(self, gateway_id: str, umsys: str) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"{_BASE_URL}/R2/PlantHome/GetData/{gateway_id}?umsys={umsys}"
        payload = {
            "filter": {"notEssentials": False, "plant": True, "zone": True, "dhw": True},
            "useCache": False,
            "zone": 1,
        }
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            if not body.get("ok"):
                raise RuntimeError(f"Legacy R2 GetData failed: {body}")
            return body["data"]

    async def async_set_plant_mode(
        self,
        gateway_id: str,
        plant_mode_text: str,
        umsys: str = "si",
    ) -> dict[str, Any]:
        """Set plant mode via the legacy /R2/ endpoint.

        `plant_mode_text` must be one of PLANT_MODE_VALUES keys, using the
        *localized* text as returned by the device's own PlantMode
        optTexts (observed in English on some accounts, Italian on
        others - callers should pass the exact text seen in the device's
        own `optTexts`, not a hardcoded assumption).
        """
        if not self._logged_in:
            await self._login()

        if self._viewmodel_cache is None:
            _LOGGER.warning(
                "Legacy R2 client has no cached viewModel yet; a real "
                "capture must seed it before this fallback can work. "
                "See AristonR2LegacyClient.seed_viewmodel()."
            )
            raise RuntimeError("No viewModel template available for legacy write")

        data = await self._get_data(gateway_id, umsys)
        items = data["items"]
        features = data["features"]

        value = PLANT_MODE_VALUES.get(plant_mode_text)
        if value is None:
            raise ValueError(f"Unknown plant mode '{plant_mode_text}'")

        view_model = dict(self._viewmodel_cache)  # shallow copy is enough here
        view_model["plantMode"] = value
        view_model["plantModeAsText"] = plant_mode_text
        view_model["plantModeEval"] = value
        view_model["isOff"] = plant_mode_text == "OFF"
        view_model["isSummer"] = plant_mode_text == "Estate"
        view_model["isWinter"] = plant_mode_text == "Inverno"
        view_model["isHeating"] = plant_mode_text in ("Inverno", "Solo riscaldamento")
        view_model["isCooling"] = plant_mode_text == "Solo raffreddamento"
        if isinstance(view_model.get("desiredTemp"), dict):
            view_model["desiredTemp"] = dict(view_model["desiredTemp"])
            view_model["desiredTemp"]["gatewayId"] = gateway_id

        session = await self._ensure_session()
        url = f"{_BASE_URL}/R2/PlantHome/SetData/{gateway_id}?umsys={umsys}"
        payload = {"features": features, "prevItems": items, "viewModel": view_model}
        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            if not body.get("ok"):
                raise RuntimeError(f"Legacy R2 SetData failed: {body}")
            _LOGGER.debug(
                "Legacy R2 SetData succeeded, changedItems=%s",
                body.get("data", {}).get("changedItems"),
            )
            return body

    def seed_viewmodel(self, viewmodel: dict[str, Any]) -> None:
        """Provide a known-good viewModel captured from a real browser
        session (see project docs / HAR capture instructions). Required
        before async_set_plant_mode can be used, since the site does not
        expose a clean read endpoint for the viewModel itself."""
        self._viewmodel_cache = dict(viewmodel)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
