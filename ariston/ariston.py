"""Ariston API"""
from __future__ import annotations

import logging
from enum import IntFlag, unique
from typing import Any, Final

import aiohttp

ARISTON_API_URL: Final[str] = "https://www.ariston-net.remotethermo.com/api/v2/"
ARISTON_LOGIN: Final[str] = "accounts/login"
ARISTON_REMOTE: Final[str] = "remote"
ARISTON_VELIS: Final[str] = "velis"
ARISTON_PLANTS: Final[str] = "plants"
ARISTON_LITE: Final[str] = "lite"
ARISTON_DATA_ITEMS: Final[str] = "dataItems"
ARISTON_ZONES: Final[str] = "zones"
ARISTON_PLANT_DATA: Final[str] = "plantData"
ARISTON_MED_PLANT_DATA: Final[str] = "medPlantData"
ARISTON_SE_PLANT_DATA: Final[str] = "sePlantData"
ARISTON_REPORTS: Final[str] = "reports"
ARISTON_TIME_PROGS: Final[str] = "timeProgs"

_LOGGER = logging.getLogger(__name__)


@unique
class PlantMode(IntFlag):
    """Plant mode enum"""

    UNDEFINED = -1
    SUMMER = 0
    WINTER = 1
    HEATING_ONLY = 2
    COOLING = 3
    COOLING_ONLY = 4
    OFF = 5
    HOLIDAY = 6


@unique
class ZoneMode(IntFlag):
    """Zone mode enum"""

    UNDEFINED = -1
    OFF = 0
    MANUAL_NIGHT = 1
    MANUAL = 2
    TIME_PROGRAM = 3


@unique
class DhwMode(IntFlag):
    """Dhw mode enum"""

    DISABLED = 0
    TIME_BASED = 1
    ALWAYS_ACTIVE = 2
    HC_HP = 3
    HC_HP_40 = 4
    GREEN = 5


@unique
class Weather(IntFlag):
    """Weather enum"""

    UNAVAILABLE = 0
    CLEAR = 1
    VARIABLE = 2
    CLOUDY = 3
    RAINY = 4
    RAINSTORM = 5
    SNOW = 6
    FOG = 7
    WINDY = 8
    CLEAR_BY_NIGHT = 129
    VARIABLE_BY_NIGHT = 130


@unique
class GasEnergyUnit(IntFlag):
    """Gas energy unit enum"""

    KWH = 0
    GIGA_JOULE = 1
    THERM = 2
    MEGA_BTU = 3
    SMC = 4
    CUBE_METER = 5


@unique
class GasType(IntFlag):
    """Gas type enu,"""

    NATURAL_GAS = 0
    LPG = 1
    AIR_PROPANED = 2
    GPO = 3
    PROPANE = 4


@unique
class Currency(IntFlag):
    """Currency enum"""

    ARS = 1
    EUR = 2
    BYN = 3
    CNY = 4
    HRK = 5
    CZK = 6
    DKK = 7
    HKD = 8
    HUF = 9
    IRR = 10
    KZT = 11
    CHF = 12
    MOP = 13
    PLZ = 14
    RON = 15
    RUB = 16
    TRY = 17
    UAH = 18
    GBP = 19
    USD = 20


@unique
class SystemType(IntFlag):
    """System type enum"""

    UNKNOWN = -1
    GALILEO1 = 1
    GALILEO2 = 2
    GALEVO = 3
    VELIS = 4
    BSB = 5


@unique
class Brands(IntFlag):
    """Brands enum"""

    Ariston = 1
    Chaffoteaux = 2
    Elco = 3
    Atag = 4
    Nti = 5
    Htp = 6
    Racold = 7


@unique
class EvoPlantMode(IntFlag):
    """Evo plant mode enum"""

    MANUAL = 1
    PROGRAM = 5


@unique
class VelisPlantMode(IntFlag):
    """Velis plant mode enum"""

    MANUAL = 1
    PROGRAM = 5
    NIGHT = 8


@unique
class LydosPlantMode(IntFlag):
    """Lydos hybrid plant mode enum"""

    IMEMORY = 1
    GREEN = 2
    PROGRAM = 6
    BOOST = 7


@unique
class WheType(IntFlag):
    """Whe type enum"""

    Unknown = -1
    LydosHybrid = 2
    NuosSplit = 4
    Evo = 6


@unique
class ConsumptionType(IntFlag):
    """Consumption type"""

    CENTRAL_HEATING_TOTAL_ENERGY = 1
    DOMESTIC_HOT_WATER_TOTAL_ENERGY = 2
    CENTRAL_HEATING_GAS = 7
    DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY = 8
    DOMESTIC_HOT_WATER_RESISTOR_ELECTRICITY = 9
    DOMESTIC_HOT_WATER_GAS = 10
    CENTRAL_HEATING_ELECTRICITY = 20
    DOMESTIC_HOT_WATER_ELECTRICITY = 21


@unique
class ConsumptionTimeInterval(IntFlag):
    """Consumption time interval"""

    # I am not sure. This is just a guess.

    LAST_DAY = 1
    LAST_WEEK = 2
    LAST_MONTH = 3
    LAST_YEAR = 4


class DeviceAttribute:
    """Constants for device attributes"""

    GW: Final[str] = "gw"  # gwId
    HPMP_SYS: Final[str] = "hpmpSys"
    IS_OFFLINE_48H: Final[str] = "isOffline48H"
    LNK: Final[str] = "lnk"  # gwLink
    LOC: Final[str] = "loc"  # location
    CONSUMPTION_SETTINGS: Final[str] = "consumptionsSettings"
    GEOFENCE_CONFIG: Final[str] = "geofenceConfig"
    MQTT_API_VERSION: Final[str] = "mqttApiVersion"  # mqttApiVersion
    NAME: Final[str] = "name"  # plantName
    SN: Final[str] = "sn"  # gwSerial
    SYS: Final[str] = "sys"  # gwSysType
    TC_BY_GUEST: Final[str] = "tcByGuest"  # controlledByGuest
    UTC_OFT: Final[str] = "utcOft"
    WEATHER_PROVIDER: Final[str] = "weatherProvider"


class GalevoDeviceAttribute(DeviceAttribute):
    """Constants for galevo device attributes"""

    ZONES: Final[str] = "zones"
    SOLAR: Final[str] = "solar"
    CONV_BOILER: Final[str] = "convBoiler"
    HYBRID_SYS: Final[str] = "hybridSys"
    DHW_PROG_SUPPORTED: Final[str] = "dhwProgSupported"
    VIRTUAL_ZONES: Final[str] = "virtualZones"
    HAS_VMC: Final[str] = "hasVmc"
    HAS_EXT_TP: Final[str] = "hasExtTP"  # extendedTimeProg
    HAS_BOILER: Final[str] = "hasBoiler"
    PILOT_SUPPORTED: Final[str] = "pilotSupported"
    UMSYS: Final[str] = "umsys"
    IS_VMC_R2: Final[str] = "isVmcR2"
    IS_EVO2: Final[str] = "isEvo2"
    FW_VER: Final[str] = "fwVer"


class VelisDeviceAttribute(DeviceAttribute):
    """Constants for velis device attributes"""

    NOTIFY_ON_CONDENSATE_TANK_FULL: Final[str] = "notifyOnCondensateTankFull"
    NOTIFY_ON_ERRORS: Final[str] = "notifyOnErrors"
    NOTIFY_ON_READY_SHOWERS: Final[str] = "notifyOnReadyShowers"
    WHE_MODEL_TYPE: Final[str] = "wheModelType"
    WHE_TYPE: Final[str] = "wheType"


class ZoneAttribute:
    """Constants for zone attributes"""

    NUM: Final[str] = "num"
    NAME: Final[str] = "name"
    ROOM_SENS: Final[str] = "roomSens"
    GEOFENCE_DEROGA: Final[str] = "geofenceDeroga"


class CustomDeviceFeatures:
    """Constants for custom device features"""

    HAS_DHW: Final[str] = "hasDhw"
    HAS_OUTSIDE_TEMP: Final[str] = "hasOutsideTemp"


class DeviceFeatures:
    """Constants for device features"""

    AUTO_THERMO_REG: Final[str] = "autoThermoReg"
    BMS_ACTIVE: Final[str] = "bmsActive"
    BUFFER_TIME_PROG_AVAILABLE: Final[str] = "bufferTimeProgAvailable"
    CASCDE_SYS: Final[str] = "cascadeSys"
    CONV_BOILER: Final[str] = "convBoiler"
    DHW_BOILER_PRESENT: Final[str] = "dhwBoilerPresent"
    DHW_HIDDEN: Final[str] = "dhwHidden"
    DHW_MODE_CHANGEABLE: Final[str] = "dhwModeChangeable"
    DHW_PROG_SUPPORTED: Final[str] = "dhwProgSupported"
    DICTINCT_HEAT_COOL_SETPOINT: Final[str] = "distinctHeatCoolSetpoints"
    EXTENDED_TIME_PROG: Final[str] = "extendedTimeProg"
    HAS_BOILER: Final[str] = "hasBoiler"
    HAS_EM20: Final[str] = "hasEm20"
    HAS_FIREPLACE: Final[str] = "hasFireplace"
    HAS_METERING: Final[str] = "hasMetering"
    HAS_SLP: Final[str] = "hasSlp"  # Low Pressure Pump
    HAS_TWO_COOLING_TEMP: Final[str] = "hasTwoCoolingTemp"
    HAS_VMC: Final[str] = "hasVmc"
    HAS_ZONE_NAMES: Final[str] = "hasZoneNames"
    HP_CASCADE_CONFIG: Final[str] = "hpCascadeConfig"
    HP_CASCADE_SYS: Final[str] = "hpCascadeSys"
    HP_SYS: Final[str] = "hpSys"
    HV_INPUT_OFF: Final[str] = "hvInputOff"
    HYBRID_SYS: Final[str] = "hybridSys"
    IS_EVO2: Final[str] = "isEvo2"
    IS_VMC_R2: Final[str] = "isVmcR2"
    PILOT_SUPPORTED: Final[str] = "pilotSupported"
    PRE_HEATING_SUPPORTED: Final[str] = "preHeatingSupported"
    SOLAR: Final[str] = "solar"
    VIRTUAL_ZONES: Final[str] = "virtualZones"
    ZONES: Final[str] = "zones"
    WEATHER_PROVIDER: Final[str] = "weatherProvider"


class VelisDeviceProperties:
    """Contants for Velis device properties"""

    ANTI_LEG: Final[str] = "antiLeg"
    AV_SHW: Final[str] = "avShw"
    GW: Final[str] = "gw"
    HEAT_REQ: Final[str] = "heatReq"
    MODE: Final[str] = "mode"
    ON: Final[str] = "on"
    PROC_REQ_TEMP: Final[str] = "procReqTemp"
    REQ_TEMP: Final[str] = "reqTemp"
    TEMP: Final[str] = "temp"


class EvoDeviceProperties(VelisDeviceProperties):
    """Contants for Velis Evo device properties"""

    ECO: Final[str] = "eco"
    PWR_OPT: Final[str] = "pwrOpt"
    RM_TM: Final[str] = "rmTm"


class LydosDeviceProperties(VelisDeviceProperties):
    """Contants for Velis Lydos device properties"""

    BOOST_REQ_TEMP: Final[str] = "boostReqTemp"


class MedDeviceSettings:
    """Constatns for Med device settings"""

    MED_ANTILEGIONELLA_ON_OFF: Final[str] = "MedAntilegionellaOnOff"
    MED_HEATING_RATE: Final[str] = "MedHeatingRate"
    MED_MAX_SETPOINT_TEMPERATURE: Final[str] = "MedMaxSetpointTemperature"
    MED_MAX_SETPOINT_TEMPERATURE_MAX: Final[str] = "MedMaxSetpointTemperatureMax"
    MED_MAX_SETPOINT_TEMPERATURE_MIN: Final[str] = "MedMaxSetpointTemperatureMin"


class SeDeviceSettings:
    """Constatns for Se device settings"""

    SE_ANTILEGIONELLA_ON_OFF: Final[str] = "SeAntilegionellaOnOff"
    SE_ANTI_COOLING_ON_OFF: Final[str] = "SeAntiCoolingOnOff"
    SE_NIGHT_MODE_ON_OFF: Final[str] = "SeNightModeOnOff"
    SE_PERMANENT_BOOST_ON_OFF: Final[str] = "SePermanentBoostOnOff"
    SE_MAX_SETPOINT_TEMPERATURE: Final[str] = "SeMaxSetpointTemperature"
    SE_MAX_SETPOINT_TEMPERATURE_MAX: Final[str] = "SeMaxSetpointTemperatureMax"
    SE_MAX_SETPOINT_TEMPERATURE_MIN: Final[str] = "SeMaxSetpointTemperatureMin"
    SE_ANTI_COOLING_TEMPERATURE: Final[str] = "SeAntiCoolingTemperature"
    SE_ANTI_COOLING_TEMPERATURE_MAX: Final[str] = "SeAntiCoolingTemperatureMin"
    SE_ANTI_COOLING_TEMPERATURE_MIN: Final[str] = "SeAntiCoolingTemperatureMax"
    SE_MAX_GREEN_SETPOINT_TEMPERATURE: Final[str] = "SeMaxGreenSetpointTemperature"
    SE_HEATING_RATE: Final[str] = "SeHeatingRate"
    SE_NIGHT_BEGIN_AS_MINUTES: Final[str] = "SeNightBeginAsMinutes"
    SE_NIGHT_BEGIN_MIN_AS_MINUTES: Final[str] = "SeNightBeginMinAsMinutes"
    SE_NIGHT_BEGIN_MAX_AS_MINUTES: Final[str] = "SeNightBeginMaxAsMinutes"
    SE_NIGHT_END_AS_MINUTES: Final[str] = "SeNightEndAsMinutes"
    SE_NIGHT_END_MIN_AS_MINUTES: Final[str] = "SeNightEndMinAsMinutes"
    SE_NIGHT_END_MAX_AS_MINUTES: Final[str] = "SeNightEndMaxAsMinutes"


class DeviceProperties:
    """Constants for device properties"""

    PLANT_MODE: Final[str] = "PlantMode"
    IS_FLAME_ON: Final[str] = "IsFlameOn"
    IS_HEATING_PUMP_ON: Final[str] = "IsHeatingPumpOn"
    HOLIDAY: Final[str] = "Holiday"
    OUTSIDE_TEMP: Final[str] = "OutsideTemp"
    WEATHER: Final[str] = "Weather"
    HEATING_CIRCUIT_PRESSURE: Final[str] = "HeatingCircuitPressure"
    CH_FLOW_TEMP: Final[str] = "ChFlowTemp"
    CH_FLOW_SETPOINT_TEMP: Final[str] = "ChFlowSetpointTemp"
    DHW_TEMP: Final[str] = "DhwTemp"
    DHW_STORAGE_TEMPERATURE: Final[str] = "DhwStorageTemperature"
    DHW_TIMEPROG_COMFORT_TEMP: Final[str] = "DhwTimeProgComfortTemp"
    DHW_TIMEPROG_ECONOMY_TEMP: Final[str] = "DhwTimeProgEconomyTemp"
    DHW_MODE: Final[str] = "DhwMode"
    AUTOMATIC_THERMOREGULATION: Final[str] = "AutomaticThermoregulation"
    ANTILEGIONELLA_ON_OFF: Final[str] = "AntilegionellaOnOff"
    ANTILEGIONELLA_TEMP: Final[str] = "AntilegionellaTemp"
    ANTILEGIONELLA_FREQ: Final[str] = "AntilegionellaFreq"


class ThermostatProperties:
    """Constants for thermostat properties"""

    ZONE_MEASURED_TEMP: Final[str] = "ZoneMeasuredTemp"
    ZONE_DESIRED_TEMP: Final[str] = "ZoneDesiredTemp"
    ZONE_COMFORT_TEMP: Final[str] = "ZoneComfortTemp"
    ZONE_MODE: Final[str] = "ZoneMode"
    ZONE_HEAT_REQUEST: Final[str] = "ZoneHeatRequest"
    ZONE_ECONOMY_TEMP: Final[str] = "ZoneEconomyTemp"
    ZONE_DEROGA: Final[str] = "ZoneDeroga"
    ZONE_IS_ZONE_PILOT_ON: Final[str] = "IsZonePilotOn"
    ZONE_VIRT_TEMP_OFFSET_HEAT: Final[str] = "VirtTempOffsetHeat"
    HEATING_FLOW_TEMP: Final[str] = "HeatingFlowTemp"
    HEATING_FLOW_OFFSET: Final[str] = "HeatingFlowOffset"
    COOLING_FLOW_TEMP: Final[str] = "CoolingFlowTemp"
    COOLING_FLOW_OFFSET: Final[str] = "CoolingFlowOffset"


class ConsumptionProperties:
    """Constants for consumption properties"""

    CURRENCY: Final[str] = "currency"
    GAS_TYPE: Final[str] = "gasType"
    GAS_ENERGY_UNIT: Final[str] = "gasEnergyUnit"
    ELEC_COST: Final[str] = "elecCost"
    GAS_COST: Final[str] = "gasCost"


class PropertyType:
    """Constants for property types"""

    VALUE: Final[str] = "value"
    OPTIONS: Final[str] = "options"
    OPT_TEXTS: Final[str] = "optTexts"
    UNIT: Final[str] = "unit"
    MIN: Final[str] = "min"
    MAX: Final[str] = "max"
    STEP: Final[str] = "step"
    DECIMALS: Final[str] = "decimals"
    ZONE: Final[str] = "zone"
    EXPIRES_ON: Final[str] = "expiresOn"


class ConnectionException(Exception):
    """When can not connect to Ariston cloud"""


class AristonAPI:
    """Ariston API class"""

    def __init__(self, username: str, password: str) -> None:
        """Constructor for Ariston API."""
        self.__username = username
        self.__password = password
        self.__token = ""

    async def async_connect(self) -> bool:
        """Login to ariston cloud and get token"""

        try:
            response = await self.post(
                f"{ARISTON_API_URL}{ARISTON_LOGIN}",
                {"usr": self.__username, "pwd": self.__password},
            )

            if response is None:
                return False

            self.__token = response["token"]

            return True

        except Exception as error:
            raise ConnectionException() from error

    async def async_get_detailed_devices(self) -> list:
        """Get detailed cloud devices"""
        return list(
            await self.get(f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANTS}")
        )

    async def async_get_detailed_velis_devices(self) -> list:
        """Get detailed cloud devices"""
        return list(
            await self.get(f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_PLANTS}")
        )

    async def async_get_devices(self) -> list:
        """Get cloud devices"""
        return list(
            await self.get(
                f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{ARISTON_LITE}"
            )
        )

    async def async_get_features_for_device(self, gw_id: str) -> dict[str, Any]:
        """Get features for the device"""
        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/features"
        )

    async def async_get_energy_account(self, gw_id: str) -> dict[str, Any]:
        """Get energy account for the device"""
        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/energyAccount"
        )

    async def async_get_consumptions_sequences(self, gw_id: str, usages: str) -> list:
        """Get consumption sequences for the device"""
        return list(
            await self.get(
                f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_REPORTS}/{gw_id}/consSequencesApi8?usages={usages}"
            )
        )

    async def async_get_consumptions_settings(self, gw_id: str) -> dict[str, Any]:
        """Get consumption settings"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/getConsumptionsSettings",
            {},
        )

    async def async_set_consumptions_settings(
        self,
        gw_id: str,
        consumptions_settings,
    ) -> dict[str, Any]:
        """Get consumption settings"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANTS}/{gw_id}/consumptionsSettings",
            consumptions_settings,
        )

    @staticmethod
    def get_items(features: dict[str, Any]):
        """Get the Final[str] strings from DeviceProperies and ThermostatProperties"""
        device_props = [
            getattr(DeviceProperties, device_property)
            for device_property in dir(DeviceProperties)
            if not device_property.startswith("__")
        ]
        thermostat_props = [
            getattr(ThermostatProperties, thermostat_properties)
            for thermostat_properties in dir(ThermostatProperties)
            if not thermostat_properties.startswith("__")
        ]

        items = []
        for device_prop in device_props:
            items.append({"id": device_prop, "zn": 0})

        for zone in features[DeviceFeatures.ZONES]:
            for thermostat_prop in thermostat_props:
                items.append({"id": thermostat_prop, "zn": zone[ZoneAttribute.NUM]})
        return items

    async def async_get_properties(
        self, gw_id: str, features: dict[str, Any], culture: str, umsys: str
    ) -> dict[str, Any]:
        """Get device properties"""

        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/get?umsys={umsys}",
            {
                "useCache": False,
                "items": self.get_items(features),
                "features": features,
                "culture": culture,
            },
        )

    async def async_get_med_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Get Velis properties"""

        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}"
        )

    async def async_get_med_plant_settings(self, gw_id: str) -> dict[str, Any]:
        """Get Velis settings"""
        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/plantSettings"
        )

    async def async_get_se_plant_data(self, gw_id: str) -> dict[str, Any]:
        """Get Velis properties"""

        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}"
        )

    async def async_get_se_plant_settings(self, gw_id: str) -> dict[str, Any]:
        """Get Velis settings"""
        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}/plantSettings"
        )

    async def async_set_property(
        self,
        gw_id: str,
        zone_id: int,
        features: dict[str, Any],
        device_property: str,
        value: float,
        prev_value: float,
        umsys: str,
    ) -> dict[str, Any]:
        """Set device properties"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_DATA_ITEMS}/{gw_id}/set?umsys={umsys}",
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

    async def async_set_evo_mode(
        self, gw_id: str, value: EvoPlantMode
    ) -> dict[str, Any]:
        """Set Velis Evo mode"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    async def async_set_lydos_mode(
        self, gw_id: str, value: LydosPlantMode
    ) -> dict[str, Any]:
        """Set Velis Lydos mode"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}/mode",
            {
                "new": value.value,
            },
        )

    async def async_set_evo_temperature(
        self, gw_id: str, value: float
    ) -> dict[str, Any]:
        """Set Velis Evo temperature"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    async def async_set_lydos_temperature(
        self, gw_id: str, value: float
    ) -> dict[str, Any]:
        """Set Velis Lydos temperature"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}/temperature",
            {
                "new": value,
            },
        )

    async def async_set_evo_eco_mode(
        self, gw_id: str, eco_mode: bool
    ) -> dict[str, Any]:
        """Set Velis Evo power"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/switchEco",
            eco_mode,
        )

    async def async_set_evo_power(self, gw_id: str, power: bool) -> dict[str, Any]:
        """Set Velis Evo power"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/switch",
            power,
        )

    async def async_set_lydos_power(self, gw_id: str, power: bool) -> dict[str, Any]:
        """Set Velis Lydos power"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}/switch",
            power,
        )

    async def async_set_evo_plant_setting(
        self,
        gw_id: str,
        setting: str,
        value: float,
        old_value: float,
    ) -> dict[str, Any]:
        """Set Velis Evo plant setting"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_MED_PLANT_DATA}/{gw_id}/plantSettings",
            {setting: {"new": value, "old": old_value}},
        )

    async def async_set_lydos_plant_setting(
        self,
        gw_id: str,
        setting: str,
        value: float,
        old_value: float,
    ) -> dict[str, Any]:
        """Set Velis Lydos plant setting"""
        return await self.post(
            f"{ARISTON_API_URL}{ARISTON_VELIS}/{ARISTON_SE_PLANT_DATA}/{gw_id}/plantSettings",
            {setting: {"new": value, "old": old_value}},
        )

    async def async_get_thermostat_time_progs(
        self, gw_id: str, zone: int, umsys: str
    ) -> dict[str, Any]:
        """Get thermostat time programs"""
        return await self.get(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_TIME_PROGS}/{gw_id}/ChZn{zone}?umsys={umsys}",
        )

    async def async_set_holiday(
        self,
        gw_id: str,
        holiday_end_date: str | None,
    ) -> None:
        """Set holidays"""

        await self.post(
            f"{ARISTON_API_URL}{ARISTON_REMOTE}/{ARISTON_PLANT_DATA}/{gw_id}/holiday",
            {
                "new": holiday_end_date,
            },
        )

    async def __request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: Any = None,
        is_retry: bool = False,
    ) -> dict[str, Any] | None:
        headers = {"ar.authToken": self.__token}

        _LOGGER.debug(
            "Request method %s, path: %s, params: %s, body: %s",
            method,
            path,
            params,
            body,
        )

        async with aiohttp.ClientSession() as session:
            response = await session.request(
                method, path, params=params, json=body, headers=headers
            )

            if not response.ok:
                if response.status == 405:
                    if not is_retry:
                        if await self.async_connect():
                            return await self.__request(
                                method, path, params, body, True
                            )
                        raise Exception("Login failed (password changed?)")
                    raise Exception("Invalid token")
                if response.status == 404:
                    return None
                raise Exception(response.status)

            if response.content_length and response.content_length > 0:
                json = await response.json()
                _LOGGER.debug("Response %s", json)
                return json

            return None

    async def post(self, path: str, body: Any) -> dict[str, Any]:
        """POST request"""
        result = await self.__request("POST", path, None, body)
        return result

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET request"""
        result = await self.__request("GET", path, params, None)
        return result
