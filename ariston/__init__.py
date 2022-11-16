"""Ariston module"""
import logging
from asyncio import gather

from .ariston import (
    AristonAPI,
    DeviceAttribute,
    SystemType,
    VelisDeviceAttribute,
    WheType,
)
from .evo_device import AristonEvoDevice
from .galevo_device import AristonGalevoDevice
from .lydos_hybrid_device import AristonLydosHybridDevice

_LOGGER = logging.getLogger(__name__)


class Ariston:
    """Ariston class"""

    def __init__(self) -> None:
        self.api = None
        self.cloud_devices: list[dict] = []

    async def async_connect(self, username: str, password: str) -> bool:
        """Connect to the ariston cloud"""
        self.api = AristonAPI(username, password)
        return await self.api.async_connect()

    async def async_discover(self):
        """Retreive ariston devices from the cloud"""
        if self.api is None:
            _LOGGER.exception("Call async_connect first")
            return None        
        cloud_devices: list[dict] = []
        cloud_devices_tuple = await gather(self.api.async_get_detailed_devices(), self.api.async_get_detailed_velis_devices())

        for devices in cloud_devices_tuple:
            cloud_devices.extend(devices)
        
        self.cloud_devices = cloud_devices
        return cloud_devices

    async def async_hello(self, gateway: str, is_metric=True, language_tag="en-US"):
        """Get ariston device"""
        if self.api is None:
            _LOGGER.exception("Call async_connect() first")
            return

        if len(self.cloud_devices) == 0:
            await self.async_discover()

        device = next(
            (
                dev
                for dev in self.cloud_devices
                if dev.get(DeviceAttribute.GW) == gateway
            ),
            None,
        )
        if device is None:
            _LOGGER.exception(f'No device "{gateway}" found.')
            return None

        system_type = device.get(DeviceAttribute.SYS)
        if system_type == SystemType.GALEVO:
            return AristonGalevoDevice(
                self.api,
                device,
                is_metric,
                language_tag,
            )
        if system_type == SystemType.VELIS:
            whe_type = device.get(VelisDeviceAttribute.WHE_TYPE)
            if whe_type == WheType.LydosHybrid:
                return AristonLydosHybridDevice(
                    self.api,
                    device,
                )
            if whe_type == WheType.Evo:
                return AristonEvoDevice(
                    self.api,
                    device,
                )
            _LOGGER.exception(f"Unsupported whe type {whe_type}")
            return None

        _LOGGER.exception(f"Unsupported system type {system_type}")
        return None
