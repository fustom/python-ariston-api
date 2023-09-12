"""Ariston module"""
import asyncio
import logging
from typing import Any, Optional

from .ariston_api import AristonAPI, ConnectionException
from .const import (
    DeviceAttribute,
    SystemType,
    VelisDeviceAttribute,
    WheType,
)
from .bsb_device import AristonBsbDevice
from .lux_device import AristonLuxDevice
from .lux2_device import AristonLux2Device
from .evo_device import AristonEvoDevice
from .galevo_device import AristonGalevoDevice
from .lydos_hybrid_device import AristonLydosHybridDevice
from .nuos_split_device import AristonNuosSplitDevice
from .device import AristonDevice

_LOGGER = logging.getLogger(__name__)


class Ariston:
    """Ariston class"""

    def __init__(self) -> None:
        self.api = None
        self.cloud_devices: list[dict[str, Any]] = []

    async def async_connect(self, username: str, password: str) -> bool:
        """Connect to the ariston cloud"""
        self.api = AristonAPI(username, password)
        return await self.api.async_connect()

    async def async_discover(self) -> Optional[list[dict[str, Any]]]:
        """Retreive ariston devices from the cloud"""
        if self.api is None:
            _LOGGER.exception("Call async_connect first")
            return None
        cloud_devices = await _async_discover(self.api)
        self.cloud_devices = cloud_devices
        return cloud_devices

    async def async_hello(
        self, gateway: str, is_metric: bool = True, language_tag: str = "en-US"
    ) -> Optional[AristonDevice]:
        """Get ariston device"""
        if self.api is None:
            _LOGGER.exception("Call async_connect() first")
            return None

        if len(self.cloud_devices) == 0:
            await self.async_discover()

        return _get_device(
            self.cloud_devices, self.api, gateway, is_metric, language_tag
        )


def _get_device(
    cloud_devices: list[dict[str, Any]],
    api: AristonAPI,
    gateway: str,
    is_metric: bool = True,
    language_tag: str = "en-US",
) -> Optional[AristonDevice]:
    """Get ariston device"""
    device = next(
        (dev for dev in cloud_devices if dev.get(DeviceAttribute.GW) == gateway),
        None,
    )
    if device is None:
        _LOGGER.exception("No device %s found.", gateway)
        return None

    system_type = device.get(DeviceAttribute.SYS)
    if system_type == SystemType.GALEVO.value:
        return AristonGalevoDevice(
            api,
            device,
            is_metric,
            language_tag,
        )
    if system_type == SystemType.VELIS.value:
        whe_type = device.get(VelisDeviceAttribute.WHE_TYPE)
        if whe_type == WheType.LydosHybrid.value:
            return AristonLydosHybridDevice(
                api,
                device,
            )
        if whe_type in [WheType.Evo.value, WheType.Evo2.value]:
            return AristonEvoDevice(
                api,
                device,
            )
        if whe_type == WheType.NuosSplit.value:
            return AristonNuosSplitDevice(
                api,
                device,
            )
        if whe_type == WheType.Lux.value:
            return AristonLuxDevice(
                api,
                device,
            )
        if whe_type == WheType.Andris2.value:
            return AristonEvoDevice(
                api,
                device,
            )
        if whe_type == WheType.Lux2.value:
            return AristonLux2Device(
                api,
                device,
            )
        _LOGGER.exception("Unsupported whe type %s", whe_type)
        return None

    if system_type == SystemType.BSB.value:
        return AristonBsbDevice(api, device)

    _LOGGER.exception("Unsupported system type %s", system_type)
    return None


def _connect(username: str, password: str) -> AristonAPI:
    """Connect to ariston api"""
    api = AristonAPI(username, password)
    api.connect()
    return api


def _discover(api: AristonAPI) -> list[dict[str, Any]]:
    """Retreive ariston devices from the cloud"""
    cloud_devices: list[dict[str, Any]] = []
    cloud_devices.extend(api.get_detailed_devices())
    cloud_devices.extend(api.get_detailed_velis_devices())

    return cloud_devices


def discover(username: str, password: str) -> list[dict[str, Any]]:
    """Retreive ariston devices from the cloud"""
    api = _connect(username, password)
    return _discover(api)


def hello(
    username: str,
    password: str,
    gateway: str,
    is_metric: bool = True,
    language_tag: str = "en-US",
) -> Optional[AristonDevice]:
    """Get ariston device"""
    api = _connect(username, password)
    cloud_devices = _discover(api)
    return _get_device(cloud_devices, api, gateway, is_metric, language_tag)


async def _async_connect(username: str, password: str) -> AristonAPI:
    """Async connect to ariston api"""
    api = AristonAPI(username, password)
    if not await api.async_connect():
        raise ConnectionException
    return api


async def _async_discover(api: AristonAPI) -> list[dict[str, Any]]:
    """Async retreive ariston devices from the cloud"""
    cloud_devices: list[dict[str, Any]] = []
    cloud_devices_tuple: tuple[
        list[dict[str, Any]], list[dict[str, Any]]
    ] = await asyncio.gather(
        api.async_get_detailed_devices(), api.async_get_detailed_velis_devices()
    )

    for devices in cloud_devices_tuple:
        cloud_devices.extend(devices)

    return cloud_devices


async def async_discover(username: str, password: str) -> list[dict[str, Any]]:
    """Retreive ariston devices from the cloud"""
    api = await _async_connect(username, password)
    return await _async_discover(api)


async def async_hello(
    username: str,
    password: str,
    gateway: str,
    is_metric: bool = True,
    language_tag: str = "en-US",
) -> Optional[AristonDevice]:
    """Get ariston device"""
    api = await _async_connect(username, password)
    cloud_devices = await _async_discover(api)
    return _get_device(cloud_devices, api, gateway, is_metric, language_tag)
