"""Ariston API"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

import asyncio
import aiohttp
import requests

from .const import (
    ARISTON_API_URL,
    ARISTON_USER_AGENT,
    ARISTON_BSB_ZONES,
    ARISTON_BUS_ERRORS,
    ARISTON_DATA_ITEMS,
    ARISTON_LITE,
    ARISTON_LOGIN,
    ARISTON_PLANTS,
    ARISTON_REMOTE,
    ARISTON_REPORTS,
    ARISTON_TIME_PROGS,
    ARISTON_VELIS,
    ARISTON_MENU_ITEMS,
    ARISTON_R2_HOME,
    ARISTON_R2_LOGIN_PAGE,
    ARISTON_R2_SLP_GET_DATA,
    ARISTON_R2_SLP_SET_DATA,
    ARISTON_R2_USER_AGENT,
    BsbOperativeMode,
    BsbZoneMode,
    DeviceFeatures,
    DeviceProperties,
    LydosPlantMode,
    NuosSplitOperativeMode,
    PlantData,
    ThermostatProperties,
    WaterHeaterMode,
    ZoneAttribute,
    MenuItemNames,
)

_LOGGER = logging.getLogger(__name__)

_RATE_LIMIT_RE = re.compile(rb"blocked for (\d+) seconds", re.IGNORECASE)
_UNPARSABLE_INITIAL_WAIT_SECONDS = 5
_UNPARSABLE_COOLDOWN_BASE_SECONDS = 60
_UNPARSABLE_COOLDOWN_MAX_SECONDS = 600


def _parse_block_seconds(content: bytes) -> Optional[int]:
    """Extract the block duration in seconds from a 429 response body."""
    match = _RATE_LIMIT_RE.search(content)
    if match is None:
        return None
    return int(match.group(1))


def _parse_retry_after_seconds(headers: Any) -> Optional[int]:
    """Extract an integer Retry-After delay in seconds from response headers."""
    if not headers or not hasattr(headers, "get"):
        return None
    raw = headers.get("Retry-After")
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if raw.isdigit():
        return max(1, int(raw))
    return None


def _rate_limit_wait_seconds(content: bytes) -> int:
    """Effective wait for a 429: parsed duration + 1s margin, else 5s."""
    parsed = _parse_block_seconds(content)
    if parsed is None:
        _LOGGER.warning(
            "Rate limited (429) without parsable block duration; "
            "falling back to %ss wait",
            _UNPARSABLE_INITIAL_WAIT_SECONDS,
        )
        return _UNPARSABLE_INITIAL_WAIT_SECONDS
    _LOGGER.warning("Rate limited (429) for %s seconds; waiting it out", parsed + 1)
    return parsed + 1


def _collect_menu_item_ids(
    items: list[Any], fallback_group: tuple[MenuItemNames, ...] | None = None
) -> list[int]:
    """Extract integer item IDs from a menu-items payload."""
    found = [
        item["id"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), int)
    ]
    if found or not items or fallback_group is None:
        return found
    return [menu_item.value for menu_item in fallback_group]


def _menu_items_path(api_url: str, gw_id: str, menu_items_query: str) -> str:
    """Build the menuItems endpoint URL for a gateway and comma-joined IDs."""
    return f"{api_url}{ARISTON_MENU_ITEMS}/{gw_id}?menuItems={menu_items_query}"


class ConnectionException(Exception):
    """When can not connect to Ariston cloud"""


class AristonAPI:
    """Ariston API class"""

    def __init__(
        self,
        username: str,
        password: str,
        api_url: str = ARISTON_API_URL,
        user_agent: str = ARISTON_USER_AGENT,
    ) -> None:
        """Constructor for Ariston API."""
        self.__username = username
        self.__password = password
        self.__api_url = api_url
        self.__token = ""
        self.__user_agent = user_agent
        # Web-app (R2) cookie session; created lazily (aiohttp.CookieJar
        # needs a running event loop) and logged in on first use.
        self.__r2_cookies: Optional[aiohttp.CookieJar] = None
        self.__r2_logged_in = False
        # Per-instance 429 block window: instances for different accounts or
        # API URLs must not silence each other; the three coordinators for
        # one account still share one API instance.
        self._blocked_until = 0.0
        self._rate_limit_streak = 0
        # Cached comma-separated menu item IDs per gateway once hybrid discovery succeeds.
        self._hybrid_menu_items: dict[str, str] = {}
        # Sync (requests) R2 web-app session; created lazily on first use.
        self.__r2_requests_session: Optional[requests.Session] = None

    def _prepare_rate_limit_retry(
        self, content: bytes, headers: Any, is_retry: bool
    ) -> Optional[int]:
        """Update the rate-limit window; return sleep seconds if a retry should run."""
        parsed = _parse_block_seconds(content)
        if parsed is None:
            parsed = _parse_retry_after_seconds(headers)

        if parsed is not None:
            wait_seconds = parsed + 1
            _LOGGER.warning(
                "Rate limited (429) for %s seconds; waiting it out", wait_seconds
            )
            self._blocked_until = max(self._blocked_until, time.time() + wait_seconds)
            return None if is_retry else wait_seconds

        if not is_retry and self._rate_limit_streak == 0:
            wait_seconds = _rate_limit_wait_seconds(content)
            self._blocked_until = max(self._blocked_until, time.time() + wait_seconds)
            return wait_seconds

        self._rate_limit_streak += 1
        cooldown = min(
            _UNPARSABLE_COOLDOWN_MAX_SECONDS,
            _UNPARSABLE_COOLDOWN_BASE_SECONDS
            * (2 ** min(self._rate_limit_streak - 1, 4)),
        )
        _LOGGER.warning(
            "Rate limited (429) without parsable block duration (streak %s); "
            "cooling down for %s seconds",
            self._rate_limit_streak,
            cooldown,
        )
        self._blocked_until = max(self._blocked_until, time.time() + cooldown)
        return None

    def _r2_cookies(self) -> aiohttp.CookieJar:
        """Lazily create the R2 cookie jar (requires a running loop)."""
        if self.__r2_cookies is None:
            self.__r2_cookies = aiohttp.CookieJar()
        return self.__r2_cookies

    def connect(self) -> bool:
        """Login to ariston cloud and get token"""

        try:
            response = self._post(
                f"{self.__api_url}{ARISTON_LOGIN}",
                {"usr": self.__username, "pwd": self.__password},
            )

            if response is None:
                return False

            self.__token = response["token"]

            return True

        except Exception as error:
            raise ConnectionException() from error

    def get_detailed_devices(self) -> list[Any]:
        """Get detailed cloud devices"""
        devices = self._get(f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}")
        if devices is not None:
            return list(devices)
        return []

    def get_detailed_velis_devices(self) -> list[Any]:
        """Get detailed cloud devices"""
        devices = self._get(f"{self.__api_url}{ARISTON_VELIS}/{ARISTON_PLANTS}")
        if devices is not None:
            return list(devices)
        return []

    def get_devices(self) -> list[Any]:
        """Get cloud devices"""
        devices = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{ARISTON_LITE}"
        )
        if devices is not None:
            return list(devices)
        return []

    def get_features_for_device(self, gw_id: str) -> dict[str, Any]:
        """Get features for the device"""
        features = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/features"
        )
        if features is not None:
            return features
        return {}

    def get_energy_account(self, gw_id: str) -> dict[str, Any]:
        """Get energy account for the device"""
        energy_account = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/energyAccount"
        )
        if energy_account is not None:
            return energy_account
        return {}

    def get_consumptions_sequences(self, gw_id: str, usages: str) -> list[Any]:
        """Get consumption sequences for the device"""
        consumptions_sequences = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/consSequencesApi8?usages={usages}"
        )
        if consumptions_sequences is not None:
            return list(consumptions_sequences)
        return []

    def get_consumptions_settings(self, gw_id: str) -> dict[str, Any]:
        """Get consumption settings"""
        consumptions_settings = self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/getConsumptionsSettings",
            {},
        )
        if consumptions_settings is not None:
            return consumptions_settings
        return {}

    def set_consumptions_settings(
        self,
        gw_id: str,
        consumptions_settings: dict[str, Any],
    ) -> None:
        """Get consumption settings"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/consumptionsSettings",
            consumptions_settings,
        )

    @staticmethod
    def get_items(features: dict[str, Any]) -> list[dict[str, int]]:
        """Get the Final[str] strings from DeviceProperies and ThermostatProperties"""
        items: list[dict[str, Any]] = DeviceProperties.list(0)
        for zone in features[DeviceFeatures.ZONES]:
            items.extend(ThermostatProperties.list(zone[ZoneAttribute.NUM]))
        return items

    def get_properties(
        self, gw_id: str, features: dict[str, Any], culture: str, umsys: str
    ) -> dict[str, Any]:
        """Get device properties"""
        properties = self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/get?umsys={umsys}",
            {
                "useCache": False,
                "items": self.get_items(features),
                "features": features,
                "culture": culture,
            },
        )
        if properties is not None:
            return properties
        return {}

    def get_bsb_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Get BSB plant data."""
        data = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}"
        )
        if data is not None:
            return data
        return {}

    def get_velis_plant_data(self, plant_data: PlantData, gw_id: str) -> dict[str, Any]:
        """Get Velis properties"""
        data = self._get(f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}")
        if data is not None:
            return data
        return {}

    def get_velis_plant_settings(
        self, plant_data: PlantData, gw_id: str
    ) -> dict[str, Any]:
        """Get Velis settings"""
        settings = self._get(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/plantSettings"
        )
        if settings is not None:
            return settings
        return {}

    @staticmethod
    def _build_hybrid_menu_query(
        core_items: list[Any], discovered_ids: list[int]
    ) -> str:
        """Build a deduplicated comma-separated query preserving core menu items."""
        core_ids = [
            int(item_id) for item_id in MenuItemNames.core_values().split(",")
        ]
        ordered = list(
            dict.fromkeys(
                [*core_ids, *_collect_menu_item_ids(core_items), *discovered_ids]
            )
        )
        return ",".join(str(item_id) for item_id in ordered)

    def get_menu_items(
        self, gw_id: str, include_hybrid_items: bool = False
    ) -> list[dict[str, Any]]:
        """Get core menu items and, when requested, optional hybrid values."""
        if include_hybrid_items:
            cached_query = self._hybrid_menu_items.get(gw_id)
            if cached_query is not None:
                try:
                    cached_items = self._get(
                        _menu_items_path(self.__api_url, gw_id, cached_query)
                    )
                except ConnectionException as error:
                    if error.args[:1] != (500,):
                        raise
                    self._hybrid_menu_items.pop(gw_id, None)
                else:
                    return cached_items or []

        items = self._get(
            _menu_items_path(self.__api_url, gw_id, MenuItemNames.core_values())
        )
        if items is None or not include_hybrid_items:
            return items or []

        core_snapshot = list(items)
        discovered_ids: list[int] = []
        for group in MenuItemNames.hybrid_groups():
            path = _menu_items_path(
                self.__api_url, gw_id, ",".join(str(item.value) for item in group)
            )
            try:
                additional_items = self._get(path)
                group_ids = _collect_menu_item_ids(additional_items or [], group)
            except ConnectionException as error:
                if error.args[:1] != (500,):
                    raise
                additional_items = []
                group_ids = []
                for menu_item in group:
                    item_path = _menu_items_path(
                        self.__api_url, gw_id, str(menu_item.value)
                    )
                    try:
                        item_response = self._get(item_path)
                    except ConnectionException as item_error:
                        if item_error.args[:1] != (500,):
                            raise
                        _LOGGER.debug(
                            "Skipping unsupported GALEVO menu item %s",
                            menu_item.value,
                        )
                        continue
                    if item_response:
                        additional_items.extend(item_response)
                        group_ids.extend(
                            _collect_menu_item_ids(item_response, (menu_item,))
                        )
            if additional_items:
                items.extend(additional_items)
                discovered_ids.extend(group_ids)

        self._hybrid_menu_items[gw_id] = self._build_hybrid_menu_query(
            core_snapshot, discovered_ids
        )
        return items

    def set_property(
        self,
        gw_id: str,
        zone_id: int,
        features: dict[str, Any],
        device_property: str,
        value: float,
        prev_value: float,
        umsys: str,
    ) -> None:
        """Set device properties"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/set?umsys={umsys}",
            {
                "items": [
                    {
                        "id": device_property,
                        "prevValue": prev_value,
                        "value": value,
                        "zone": zone_id,
                    }
                ],
                "features": features,
            },
        )

    def set_evo_number_of_showers(self, gw_id: str, number_of_showers: int) -> None:
        """Set Velis Evo number of showers"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.PD.value}/{gw_id}/showers",
            {
                "new": int(number_of_showers),
            },
        )

    def set_evo_mode(self, gw_id: str, value: WaterHeaterMode) -> None:
        """Set Velis Evo mode"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    def set_lydos_mode(self, gw_id: str, value: LydosPlantMode) -> None:
        """Set Velis Lydos mode"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Se.value}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    def set_nuos_mode(self, gw_id: str, value: NuosSplitOperativeMode) -> None:
        """Set Velis Nuos mode"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/operativeMode",
            {
                "new": value.value,
            },
        )

    def set_bsb_mode(self, gw_id: str, value: BsbOperativeMode) -> None:
        """Set Bsb mode"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}/dhwMode",
            {
                "new": value.value,
            },
        )

    def set_bsb_zone_mode(
        self,
        gw_id: str,
        zone: int,
        value: BsbZoneMode,
        old_value: BsbZoneMode,
        is_cooling: bool,
    ) -> None:
        """Set Bsb zone mode"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_BSB_ZONES}/{gw_id}/{zone}/mode?isCooling={is_cooling}",
            {"new": value.value, "old": old_value.value},
        )

    def set_evo_temperature(self, gw_id: str, value: float) -> None:
        """Set Velis Evo temperature"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    def set_lydos_temperature(self, gw_id: str, value: float) -> None:
        """Set Velis Lydos temperature"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Se.value}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    def set_nuos_temperature(
        self,
        gw_id: str,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
    ) -> None:
        """Set Nuos temperature"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/temperatures",
            {
                "new": {
                    "comfort": comfort,
                    "reduced": reduced,
                },
                "old": {
                    "comfort": old_comfort,
                    "reduced": old_reduced,
                },
            },
        )

    def set_bsb_temperature(
        self,
        gw_id: str,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
    ) -> None:
        """Set Bsb temperature"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}/dhwTemp",
            {
                "new": {
                    "comf": comfort,
                    "econ": reduced,
                },
                "old": {
                    "comf": old_comfort,
                    "econ": old_reduced,
                },
            },
        )

    def set_bsb_zone_temperature(
        self,
        gw_id: str,
        zone: int,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
        is_cooling: bool,
    ) -> None:
        """Set Bsb zone temperature"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_BSB_ZONES}/{gw_id}/{zone}/temperatures?isCooling={is_cooling}",
            {
                "new": {
                    "comf": comfort,
                    "econ": reduced,
                },
                "old": {
                    "comf": old_comfort,
                    "econ": old_reduced,
                },
            },
        )

    def set_nous_boost(self, gw_id: str, boost: bool) -> None:
        """ "Set Nous boost"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/boost",
            boost,
        )

    def set_evo_eco_mode(self, gw_id: str, eco_mode: bool) -> None:
        """Set Velis Evo eco mode"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/switchEco",
            eco_mode,
        )

    def set_lux_power_option(self, gw_id: str, power_option: bool) -> None:
        """Set Velis Lux2 power option"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/switchPowerOption",
            power_option,
        )

    def set_velis_power(self, plant_data: PlantData, gw_id: str, power: bool) -> None:
        """Set Velis power"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/switch",
            power,
        )

    def set_velis_plant_setting(
        self,
        plant_data: PlantData,
        gw_id: str,
        setting: str,
        value: float,
        old_value: float,
    ) -> None:
        """Set Velis plant setting"""
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/plantSettings",
            {setting: {"new": value, "old": old_value}},
        )

    def get_thermostat_time_progs(
        self, gw_id: str, zone: int, umsys: str
    ) -> dict[str, Any]:
        """Get thermostat time programs"""
        thermostat_time_progs = self._get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_TIME_PROGS}/{gw_id}/ChZn{zone}?umsys={umsys}",
        )
        if thermostat_time_progs is not None:
            return thermostat_time_progs
        return {}

    def set_holiday(
        self,
        gw_id: str,
        holiday_end_date: Optional[str],
    ) -> None:
        """Set holidays"""
        self._post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.PD}/{gw_id}/holiday",
            {
                "new": holiday_end_date,
            },
        )

    def set_velis_slp_holiday(
        self,
        gw_id: str,
        holiday_end_date: Optional[str],
    ) -> None:
        """Set holiday on a Velis Slp (Nuos) device.

        Pass an ISO-formatted end date string to schedule the holiday, or
        ``None`` to clear it.
        """
        self._post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/holiday",
            {
                "new": holiday_end_date,
            },
        )

    def get_bus_errors(self, gw_id: str) -> list[Any]:
        """Get bus errors"""
        bus_errors = self._get(
            f"{self.__api_url}{ARISTON_BUS_ERRORS}?gatewayId={gw_id}&blockingOnly=False&culture=en-US"
        )
        if bus_errors is not None:
            return list(bus_errors)
        return []

    def __request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        body: Any = None,
        is_retry: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Request with requests"""
        if not is_retry and time.time() < self._blocked_until:
            raise ConnectionException(
                429,
                "Rate limited; skipping request until the block window ends",
            )
        headers: dict[str, Any] = {
            "User-Agent": self.__user_agent,
            "ar.authToken": self.__token,
        }

        _LOGGER.debug(
            "Request method %s, path: %s, params: %s",
            method,
            path,
            params,
        )
        response = requests.request(
            method, path, params=params, json=body, headers=headers, timeout=30
        )
        if not response.ok:
            match response.status_code:
                case 405:
                    if not is_retry:
                        if self.connect():
                            return self.__request(method, path, params, body, True)
                        raise ConnectionException("Login failed (password changed?)")
                    raise ConnectionException("Invalid token")
                case 404:
                    return None
                case 429:
                    return self.__handle_rate_limit(
                        response, is_retry, method, path, params, body
                    )
                case _:
                    if not is_retry:
                        time.sleep(5)
                        return self.__request(method, path, params, body, True)
                    raise ConnectionException(response.status_code)

        self._rate_limit_streak = 0
        if len(response.content) > 0:
            json = response.json()
            _LOGGER.debug("Response %s", json)
            return json

        return None

    def _post(self, path: str, body: Any) -> Any:
        """POST request"""
        return self.__request("POST", path, None, body)

    def __handle_rate_limit(
        self,
        response,
        is_retry: bool,
        method: str,
        path: str,
        params: Optional[dict[str, Any]],
        body: Any,
    ) -> Optional[dict[str, Any]]:
        """Sleep out the 429 block window, retry once, per-instance deadline."""
        content = response.content
        headers = getattr(response, "headers", None)
        wait_seconds = self._prepare_rate_limit_retry(content, headers, is_retry)
        if wait_seconds is not None:
            sleep_deadline = time.time() + wait_seconds
            time.sleep(wait_seconds)
            if (
                self._rate_limit_streak == 0
                and self._blocked_until <= sleep_deadline + 0.5
            ):
                return self.__request(method, path, params, body, True)
        raise ConnectionException(response.status_code, content.decode())

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        """GET request"""
        return self.__request("GET", path, params, None)

    def _r2_session(self) -> requests.Session:
        """Lazily create the R2 requests session (holds the auth cookies)."""
        if self.__r2_requests_session is None:
            self.__r2_requests_session = requests.Session()
            self.__r2_requests_session.headers["User-Agent"] = ARISTON_R2_USER_AGENT
        return self.__r2_requests_session

    def _r2_login(self) -> None:
        """Log in to the R2 web app (form + anti-forgery token, cookie session)."""
        self.__r2_logged_in = False
        session = self._r2_session()
        login_page = session.get(ARISTON_R2_LOGIN_PAGE)
        if login_page.status_code != 200:
            raise ConnectionException(
                f"R2 login page returned HTTP {login_page.status_code}"
            )
        match = re.search(
            r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', login_page.text
        )
        if match is None:
            raise ConnectionException(
                "R2 login page has no __RequestVerificationToken"
            )
        login = session.post(
            ARISTON_R2_LOGIN_PAGE,
            data={
                "__RequestVerificationToken": match.group(1),
                "email": self.__username,
                "password": self.__password,
                "rememberMe": "false",
            },
            allow_redirects=False,
        )
        if login.status_code not in (200, 302):
            raise ConnectionException(f"R2 login returned HTTP {login.status_code}")
        self.__r2_logged_in = True

    def _r2_get_slp_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Read the Nuos Split plant data through the R2 web app."""
        response = self._r2_session().get(ARISTON_R2_SLP_GET_DATA.format(gw_id))
        if response.status_code != 200:
            raise ConnectionException(
                f"R2 GetData returned HTTP {response.status_code}"
            )
        try:
            body = response.json()
            return body["data"]["plantData"]
        except (KeyError, ValueError) as err:
            # An expired R2 forms-auth session redirects to the login page:
            # HTTP 200 text/html. Surface as ConnectionException so the
            # caller's fresh-login retry fires.
            raise ConnectionException(
                "R2 GetData returned no plant data (session expired?)"
            ) from err

    def _r2_post_set_data(self, gw_id: str, payload: dict[str, Any]) -> None:
        """POST the R2 SetData envelope and validate the response."""
        response = self._r2_session().post(
            ARISTON_R2_SLP_SET_DATA.format(gw_id),
            json=payload,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        if response.status_code != 200:
            raise ConnectionException(
                f"R2 SetData returned HTTP {response.status_code}"
            )
        try:
            body = response.json()
        except ValueError as err:
            raise ConnectionException(
                "R2 SetData returned a non-JSON body (session expired?)"
            ) from err
        if isinstance(body, dict) and body.get("success") is False:
            raise ConnectionException(f"R2 SetData reported failure: {body}")

    def set_nuos_mode_via_r2(self, gw_id: str, value: NuosSplitOperativeMode) -> None:
        """Set a Nuos Split operative mode through the R2 web app.

        api/v2 operativeMode accepts values 1+ but silently drops 0 (GREEN);
        this endpoint applies every value — it is what the official app uses.
        """
        if not self.__r2_logged_in:
            self._r2_login()
        try:
            plant_data = self._r2_get_slp_plant_data(gw_id)
        except ConnectionException:
            # Session may have expired; one fresh login, then retry the read.
            self._r2_login()
            plant_data = self._r2_get_slp_plant_data(gw_id)
        self._r2_post_set_data(
            gw_id, self._build_nuos_r2_payload(plant_data, value.value)
        )

    async def async_connect(self) -> bool:
        """Async login to ariston cloud and get token"""

        try:
            response = await self._async_post(
                f"{self.__api_url}{ARISTON_LOGIN}",
                {"usr": self.__username, "pwd": self.__password},
            )

            if response is None:
                return False

            self.__token = response["token"]

            return True

        except Exception as error:
            raise ConnectionException() from error

    async def async_get_detailed_devices(self) -> list[Any]:
        """Async get detailed cloud devices"""
        detailed_devices = await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}"
        )
        if detailed_devices is not None:
            return list(detailed_devices)
        return []

    async def async_get_detailed_velis_devices(self) -> list[Any]:
        """Async get detailed cloud devices"""
        detailed_velis_devices = await self._async_get(
            f"{self.__api_url}{ARISTON_VELIS}/{ARISTON_PLANTS}"
        )
        if detailed_velis_devices is not None:
            return list(detailed_velis_devices)
        return []

    async def async_get_devices(self) -> list[Any]:
        """Async get cloud devices"""
        devices = await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{ARISTON_LITE}"
        )
        if devices is not None:
            return list(devices)
        return []

    async def async_get_features_for_device(
        self, gw_id: str
    ) -> Optional[dict[str, Any]]:
        """Async get features for the device"""
        return await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/features"
        )

    async def async_get_energy_account(self, gw_id: str) -> dict[str, Any]:
        """Async get energy account for the device"""
        energy_account = await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/energyAccount"
        )
        if energy_account is not None:
            return energy_account
        return {}

    async def async_get_consumptions_sequences(
        self, gw_id: str, usages: str
    ) -> list[Any]:
        """Async get consumption sequences for the device"""
        consumptions_sequences = await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/consSequencesApi8?usages={usages}"
        )
        if consumptions_sequences is not None:
            return list(consumptions_sequences)
        return []

    async def async_get_consumptions_settings(self, gw_id: str) -> dict[str, Any]:
        """Async get consumption settings"""
        consumptions_settings = await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/getConsumptionsSettings",
            {},
        )
        if consumptions_settings is not None:
            return consumptions_settings
        return {}

    async def async_set_consumptions_settings(
        self,
        gw_id: str,
        consumptions_settings: dict[str, Any],
    ) -> None:
        """Async set consumption settings"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/consumptionsSettings",
            consumptions_settings,
        )

    async def async_get_properties(
        self, gw_id: str, features: dict[str, Any], culture: str, umsys: str
    ) -> dict[str, Any]:
        """Async get device properties"""
        path = f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/get?umsys={umsys}"
        items = self.get_items(features)
        try:
            properties = await self._async_request_properties(
                path, items, features, culture, False
            )
        except (ConnectionException, asyncio.TimeoutError) as error:
            if (
                isinstance(error, ConnectionException)
                and error.args[:1] != (500,)
            ) or not items:
                raise
            _LOGGER.warning(
                "GALEVO properties batch failed with HTTP 500 or timed out; retrying in pairs"
            )
            properties = await self._async_recover_properties(
                path, items, features, culture, error
            )
        if properties is not None:
            return properties
        return {}

    async def _async_request_properties(
        self,
        path: str,
        items: list[dict[str, Any]],
        features: dict[str, Any],
        culture: str,
        use_cache: bool,
    ) -> Any:
        """Request a group of GALEVO properties."""
        return await self._async_post(
            path,
            {
                "useCache": use_cache,
                "items": items,
                "features": features,
                "culture": culture,
            },
            timeout_seconds=90,
        )

    async def _async_cached_property(
        self,
        path: str,
        item: dict[str, Any],
        features: dict[str, Any],
        culture: str,
    ) -> Any:
        """Retry a property with the provider cache after a server error or timeout."""
        _LOGGER.warning(
            "GALEVO property %s failed or timed out; trying cached value",
            item["id"],
        )
        try:
            return await self._async_request_properties(
                path, [item], features, culture, True
            )
        except ConnectionException as error:
            _LOGGER.warning(
                "GALEVO property %s also failed with cache (HTTP %s)",
                item["id"],
                error.args[0] if error.args else "unknown",
            )
            raise

    async def _async_recover_property(
        self,
        path: str,
        item: dict[str, Any],
        features: dict[str, Any],
        culture: str,
    ) -> Any:
        """Retry one property fresh, then cached on server error or timeout."""
        try:
            return await self._async_request_properties(
                path, [item], features, culture, False
            )
        except (ConnectionException, asyncio.TimeoutError) as error:
            if isinstance(error, ConnectionException) and error.args[:1] != (500,):
                raise
            return await self._async_cached_property(path, item, features, culture)

    async def _async_recover_property_chunk(
        self,
        path: str,
        chunk: list[dict[str, Any]],
        features: dict[str, Any],
        culture: str,
    ) -> list[dict[str, Any]]:
        """Retry a pair, splitting on server error or timeout."""
        try:
            response = await self._async_request_properties(
                path, chunk, features, culture, False
            )
        except (ConnectionException, asyncio.TimeoutError) as error:
            if isinstance(error, ConnectionException) and error.args[:1] != (500,):
                raise
            if len(chunk) == 1:
                response = await self._async_cached_property(
                    path, chunk[0], features, culture
                )
                return response.get("items", []) if response else []
            recovered = []
            for item in chunk:
                response = await self._async_recover_property(
                    path, item, features, culture
                )
                if response:
                    recovered.extend(response.get("items", []))
            return recovered
        return response.get("items", []) if response else []

    async def _async_recover_properties(
        self,
        path: str,
        items: list[dict[str, Any]],
        features: dict[str, Any],
        culture: str,
        initial_error: ConnectionException | asyncio.TimeoutError,
    ) -> dict[str, Any]:
        """Collect pair retries, preserving the original error if none succeed."""
        properties = {"features": features, "items": []}
        for index in range(0, len(items), 2):
            chunk = items[index : index + 2]
            properties["items"].extend(
                await self._async_recover_property_chunk(
                    path, chunk, features, culture
                )
            )
        if not properties["items"]:
            raise initial_error
        return properties

    async def async_get_bsb_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Get BSB plant data."""
        data = await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}"
        )
        if data is not None:
            return data
        return {}

    async def async_get_velis_plant_data(
        self, plant_data: PlantData, gw_id: str
    ) -> dict[str, Any]:
        """Async get Velis properties"""
        med_plant_data = await self._async_get(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}"
        )
        if med_plant_data is not None:
            return med_plant_data
        return {}

    async def async_get_velis_plant_settings(
        self, plant_data: PlantData, gw_id: str
    ) -> dict[str, Any]:
        """Async get Velis settings"""
        med_plant_settings = await self._async_get(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/plantSettings"
        )
        if med_plant_settings is not None:
            return med_plant_settings
        return {}

    async def async_get_menu_items(
        self, gw_id: str, include_hybrid_items: bool = False
    ) -> list[dict[str, Any]]:
        """Async get core menu items and optional hybrid values."""
        if include_hybrid_items:
            cached_query = self._hybrid_menu_items.get(gw_id)
            if cached_query is not None:
                try:
                    cached_items = await self._async_get(
                        _menu_items_path(self.__api_url, gw_id, cached_query)
                    )
                except ConnectionException as error:
                    if error.args[:1] != (500,):
                        raise
                    self._hybrid_menu_items.pop(gw_id, None)
                else:
                    return cached_items or []

        items = await self._async_get(
            _menu_items_path(self.__api_url, gw_id, MenuItemNames.core_values())
        )
        if items is None or not include_hybrid_items:
            return items or []

        core_snapshot = list(items)
        discovered_ids: list[int] = []
        for group in MenuItemNames.hybrid_groups():
            path = _menu_items_path(
                self.__api_url, gw_id, ",".join(str(item.value) for item in group)
            )
            try:
                additional_items = await self._async_get(path)
                group_ids = _collect_menu_item_ids(additional_items or [], group)
            except ConnectionException as error:
                if error.args[:1] != (500,):
                    raise
                additional_items = []
                group_ids = []
                for menu_item in group:
                    item_path = _menu_items_path(
                        self.__api_url, gw_id, str(menu_item.value)
                    )
                    try:
                        item_response = await self._async_get(item_path)
                    except ConnectionException as item_error:
                        if item_error.args[:1] != (500,):
                            raise
                        _LOGGER.debug(
                            "Skipping unsupported GALEVO menu item %s",
                            menu_item.value,
                        )
                        continue
                    if item_response:
                        additional_items.extend(item_response)
                        group_ids.extend(
                            _collect_menu_item_ids(item_response, (menu_item,))
                        )
            if additional_items:
                items.extend(additional_items)
                discovered_ids.extend(group_ids)

        self._hybrid_menu_items[gw_id] = self._build_hybrid_menu_query(
            core_snapshot, discovered_ids
        )
        return items

    async def async_set_property(
        self,
        gw_id: str,
        zone_id: int,
        features: dict[str, Any],
        device_property: str,
        value: float,
        prev_value: float,
        umsys: str,
    ) -> None:
        """Async set device properties"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/set?umsys={umsys}",
            {
                "items": [
                    {
                        "id": device_property,
                        "prevValue": prev_value,
                        "value": value,
                        "zone": zone_id,
                    }
                ],
                "features": features,
            },
        )

    async def async_set_evo_number_of_showers(
        self, gw_id: str, number_of_showers: int
    ) -> None:
        """Set Velis Evo number of showers"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.PD.value}/{gw_id}/showers",
            {
                "new": int(number_of_showers),
            },
        )

    async def async_set_evo_mode(self, gw_id: str, value: WaterHeaterMode) -> None:
        """Async set Velis Evo mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    async def async_set_lydos_mode(self, gw_id: str, value: LydosPlantMode) -> None:
        """Async set Velis Lydos mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Se.value}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    async def async_set_nuos_mode(
        self, gw_id: str, value: NuosSplitOperativeMode
    ) -> None:
        """Async set Velis Nuos mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/operativeMode",
            {
                "new": value.value,
            },
        )

    @staticmethod
    def _build_nuos_r2_payload(plant_data: dict[str, Any], op_mode: int) -> dict[str, Any]:
        """Build the R2 PlantHomeSlp/SetData envelope for an operative mode.

        Mirrors the official web app: the cached plantData is echoed back
        and only the viewModel fields change.
        """
        return {
            "plantData": {
                "__type__": ["my.entities.entityiface", "my.entities.slpplantdata"],
                "gatewayId": plant_data.get("gw"),
                "on": plant_data.get("on"),
                "mode": plant_data.get("mode"),
                "waterTemp": plant_data.get("waterTemp"),
                "comfortTemp": plant_data.get("comfortTemp"),
                "reducedTemp": plant_data.get("reducedTemp"),
                "procReqTemp": plant_data.get("procReqTemp"),
                "opMode": plant_data.get("opMode"),
                "holidayUntil": plant_data.get("holidayUntil"),
                "boostOn": plant_data.get("boostOn"),
                "hpState": plant_data.get("hpState"),
            },
            "viewModel": {
                "on": plant_data.get("on"),
                "plantMode": plant_data.get("mode"),
                "opMode": op_mode,
                "boostOn": plant_data.get("boostOn"),
                "comfortTemp": plant_data.get("comfortTemp"),
                "holidayUntil": plant_data.get("holidayUntil"),
            },
        }

    async def _async_r2_login(self) -> None:
        """Log in to the R2 web app (form + anti-forgery token, cookie session)."""
        self.__r2_logged_in = False
        async with aiohttp.ClientSession(
            cookie_jar=self._r2_cookies(),
            headers={"User-Agent": ARISTON_R2_USER_AGENT},
        ) as session:
            async with session.get(ARISTON_R2_LOGIN_PAGE) as response:
                html = await response.text()
                if response.status != 200:
                    raise ConnectionException(
                        f"R2 login page returned HTTP {response.status}"
                    )
                match = re.search(
                    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html
                )
                if match is None:
                    raise ConnectionException(
                        "R2 login page has no __RequestVerificationToken"
                    )
                verification_token = match.group(1)

            async with session.post(
                ARISTON_R2_LOGIN_PAGE,
                data={
                    "__RequestVerificationToken": verification_token,
                    "email": self.__username,
                    "password": self.__password,
                    "rememberMe": "false",
                },
                allow_redirects=False,
            ) as response:
                if response.status not in (200, 302):
                    raise ConnectionException(
                        f"R2 login returned HTTP {response.status}"
                    )
        self.__r2_logged_in = True

    async def _async_r2_get_slp_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Read the Nuos Split plant data through the R2 web app."""
        async with aiohttp.ClientSession(
            cookie_jar=self._r2_cookies(),
            headers={"User-Agent": ARISTON_R2_USER_AGENT},
        ) as session:
            async with session.get(
                ARISTON_R2_SLP_GET_DATA.format(gw_id)
            ) as response:
                if response.status != 200:
                    raise ConnectionException(
                        f"R2 GetData returned HTTP {response.status}"
                    )
                try:
                    body = await response.json()
                    return body["data"]["plantData"]
                except (aiohttp.ContentTypeError, KeyError, ValueError) as err:
                    # An expired R2 forms-auth session redirects to the login
                    # page: HTTP 200 text/html. Surface as ConnectionException
                    # so the caller's fresh-login retry fires.
                    raise ConnectionException(
                        "R2 GetData returned no plant data (session expired?)"
                    ) from err

    async def async_set_nuos_mode_via_r2(
        self, gw_id: str, value: NuosSplitOperativeMode
    ) -> None:
        """Set a Nuos Split operative mode through the R2 web app.

        api/v2 operativeMode accepts values 1+ but silently drops 0 (GREEN);
        this endpoint applies every value — it is what the official app uses.
        """
        if not self.__r2_logged_in:
            await self._async_r2_login()
        try:
            plant_data = await self._async_r2_get_slp_plant_data(gw_id)
        except ConnectionException:
            # Session may have expired; one fresh login, then retry the read.
            await self._async_r2_login()
            plant_data = await self._async_r2_get_slp_plant_data(gw_id)
        payload = self._build_nuos_r2_payload(plant_data, value.value)
        await self._async_r2_post_set_data(gw_id, payload)

    async def _async_r2_post_set_data(
        self, gw_id: str, payload: dict[str, Any]
    ) -> None:
        """POST the R2 SetData envelope and validate the response."""
        async with aiohttp.ClientSession(
            cookie_jar=self._r2_cookies(),
            headers={
                "User-Agent": ARISTON_R2_USER_AGENT,
                "X-Requested-With": "XMLHttpRequest",
            },
        ) as session:
            async with session.post(
                ARISTON_R2_SLP_SET_DATA.format(gw_id), json=payload
            ) as response:
                if response.status != 200:
                    raise ConnectionException(
                        f"R2 SetData returned HTTP {response.status}"
                    )
                try:
                    body = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as err:
                    # An expired session turns the POST into a redirect to
                    # the login page (HTTP 200 text/html) — auth failure,
                    # not success.
                    raise ConnectionException(
                        "R2 SetData returned a non-JSON body (session expired?)"
                    ) from err
        if isinstance(body, dict) and body.get("success") is False:
            raise ConnectionException(f"R2 SetData reported failure: {body}")

    async def async_set_bsb_mode(self, gw_id: str, value: BsbOperativeMode) -> None:
        """Async set Bsb mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}/dhwMode",
            {
                "new": value.value,
            },
        )

    async def async_set_bsb_zone_mode(
        self,
        gw_id: str,
        zone: int,
        value: BsbZoneMode,
        old_value: BsbZoneMode,
        is_cooling: bool,
    ) -> None:
        """Async set Bsb zone mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_BSB_ZONES}/{gw_id}/{zone}/mode?isCooling={is_cooling}",
            {"new": value.value, "old": old_value.value},
        )

    async def async_set_evo_temperature(self, gw_id: str, value: float) -> None:
        """Async set Velis Evo temperature"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    async def async_set_lydos_temperature(self, gw_id: str, value: float) -> None:
        """Async set Velis Lydos temperature"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Se.value}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    async def async_set_nuos_temperature(
        self,
        gw_id: str,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
    ) -> None:
        """Async set Velis Lydos temperature"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/temperatures",
            {
                "new": {
                    "comfort": comfort,
                    "reduced": reduced,
                },
                "old": {
                    "comfort": old_comfort,
                    "reduced": old_reduced,
                },
            },
        )

    async def async_set_bsb_temperature(
        self,
        gw_id: str,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
    ) -> None:
        """Async set Bsb temperature"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.Bsb.value}/{gw_id}/dhwTemp",
            {
                "new": {
                    "comf": comfort,
                    "econ": reduced,
                },
                "old": {
                    "comf": old_comfort,
                    "econ": old_reduced,
                },
            },
        )

    async def async_set_bsb_zone_temperature(
        self,
        gw_id: str,
        zone: int,
        comfort: float,
        reduced: float,
        old_comfort: Optional[float],
        old_reduced: Optional[float],
        is_cooling: bool,
    ) -> None:
        """Async set Bsb zone temperature"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_BSB_ZONES}/{gw_id}/{zone}/temperatures?isCooling={is_cooling}",
            {
                "new": {
                    "comf": comfort,
                    "econ": reduced,
                },
                "old": {
                    "comf": old_comfort,
                    "econ": old_reduced,
                },
            },
        )

    async def async_set_nous_boost(self, gw_id: str, boost: bool) -> None:
        """ "Set Nous boost"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/boost",
            boost,
        )

    async def async_set_evo_eco_mode(self, gw_id: str, eco_mode: bool) -> None:
        """Async set Velis Evo eco mode"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/switchEco",
            eco_mode,
        )

    async def async_set_lux_power_option(self, gw_id: str, power_option: bool) -> None:
        """Set Velis Lux2 power option"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Med.value}/{gw_id}/switchPowerOption",
            power_option,
        )

    async def async_set_velis_power(
        self, plant_data: PlantData, gw_id: str, power: bool
    ) -> None:
        """Async set Velis power"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/switch",
            power,
        )

    async def async_set_velis_plant_setting(
        self,
        plant_data: PlantData,
        gw_id: str,
        setting: str,
        value: float,
        old_value: float,
    ) -> None:
        """Async set Velis Evo plant setting"""
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{plant_data.value}/{gw_id}/plantSettings",
            {setting: {"new": value, "old": old_value}},
        )

    async def async_get_thermostat_time_progs(
        self, gw_id: str, zone: int, umsys: str
    ) -> Optional[dict[str, Any]]:
        """Async get thermostat time programs"""
        return await self._async_get(
            f"{self.__api_url}{ARISTON_REMOTE}/{ARISTON_TIME_PROGS}/{gw_id}/ChZn{zone}?umsys={umsys}",
        )

    async def async_set_holiday(
        self,
        gw_id: str,
        holiday_end_date: Optional[str],
    ) -> None:
        """Async set holidays"""

        await self._async_post(
            f"{self.__api_url}{ARISTON_REMOTE}/{PlantData.PD}/{gw_id}/holiday",
            {
                "new": holiday_end_date,
            },
        )

    async def async_set_velis_slp_holiday(
        self,
        gw_id: str,
        holiday_end_date: Optional[str],
    ) -> None:
        """Async set holiday on a Velis Slp (Nuos) device.

        Pass an ISO-formatted end date string to schedule the holiday, or
        ``None`` to clear it.
        """
        await self._async_post(
            f"{self.__api_url}{ARISTON_VELIS}/{PlantData.Slp.value}/{gw_id}/holiday",
            {
                "new": holiday_end_date,
            },
        )

    async def async_get_bus_errors(self, gw_id: str) -> list[Any]:
        """Async get bus errors"""
        bus_errors = await self._async_get(
            f"{self.__api_url}{ARISTON_BUS_ERRORS}?gatewayId={gw_id}&blockingOnly=False&culture=en-US"
        )
        if bus_errors is not None:
            return list(bus_errors)
        return []

    async def __async_request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        body: Any = None,
        is_retry: bool = False,
        timeout_seconds: int = 30,
    ) -> Optional[dict[str, Any]]:
        """Async request with aiohttp"""
        if not is_retry and time.time() < self._blocked_until:
            raise ConnectionException(
                429,
                "Rate limited; skipping request until the block window ends",
            )
        headers: dict[str, Any] = {
            "User-Agent": self.__user_agent,
            "ar.authToken": self.__token,
        }

        _LOGGER.debug(
            "Request method %s, path: %s, params: %s",
            method,
            path,
            params,
        )

        # GALEVO property batches can take longer than other API requests.
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            response = await session.request(
                method, path, params=params, json=body, headers=headers
            )

            if not response.ok:
                match response.status:
                    case 405:
                        if not is_retry:
                            if await self.async_connect():
                                return await self.__async_request(
                                    method, path, params, body, True, timeout_seconds
                                )
                            raise ConnectionException(
                                "Login failed (password changed?)"
                            )
                        raise ConnectionException("Invalid token")
                    case 404:
                        return None
                    case 429:
                        return await self.__async_handle_rate_limit(
                            response, is_retry, method, path, params, body, timeout_seconds
                        )
                    case _:
                        if not is_retry:
                            await asyncio.sleep(5)
                            return await self.__async_request(
                                method, path, params, body, True, timeout_seconds
                            )
                        raise ConnectionException(response.status)

            self._rate_limit_streak = 0
            if response.content_length and response.content_length > 0:
                json = await response.json()
                _LOGGER.debug("Response %s", json)
                return json

            return None

    async def _async_post(
        self, path: str, body: Any, timeout_seconds: int = 30
    ) -> Any:
        """Async POST request"""
        return await self.__async_request(
            "POST", path, None, body, timeout_seconds=timeout_seconds
        )

    async def __async_handle_rate_limit(
        self,
        response,
        is_retry: bool,
        method: str,
        path: str,
        params: Optional[dict[str, Any]],
        body: Any,
        timeout_seconds: int,
    ) -> Optional[dict[str, Any]]:
        """Sleep out the 429 block window, retry once, share the deadline."""
        content = await response.content.read()
        headers = getattr(response, "headers", None)
        wait_seconds = self._prepare_rate_limit_retry(content, headers, is_retry)
        if wait_seconds is not None:
            sleep_deadline = time.time() + wait_seconds
            await asyncio.sleep(wait_seconds)
            if (
                self._rate_limit_streak == 0
                and self._blocked_until <= sleep_deadline + 0.5
            ):
                return await self.__async_request(
                    method, path, params, body, True, timeout_seconds
                )
        raise ConnectionException(response.status, content)

    async def _async_get(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> Any:
        """Async GET request"""
        return await self.__async_request("GET", path, params, None)
