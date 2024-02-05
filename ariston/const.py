"""Constants for ariston module"""
from enum import Enum, IntEnum, unique
from typing import Final

ARISTON_API_URL: Final[str] = "https://www.ariston-net.remotethermo.com/api/v2/"
ARISTON_LOGIN: Final[str] = "accounts/login"
ARISTON_REMOTE: Final[str] = "remote"
ARISTON_VELIS: Final[str] = "velis"
ARISTON_PLANTS: Final[str] = "plants"
ARISTON_LITE: Final[str] = "lite"
ARISTON_DATA_ITEMS: Final[str] = "dataItems"
ARISTON_ZONES: Final[str] = "zones"
ARISTON_BSB_ZONES: Final[str] = "bsbZones"
ARISTON_REPORTS: Final[str] = "reports"
ARISTON_TIME_PROGS: Final[str] = "timeProgs"
ARISTON_BUS_ERRORS: Final[str] = "busErrors"


@unique
class PlantData(str, Enum):
    """Plant data enum"""

    PD = "plantData"
    Med = "medPlantData"
    Se = "sePlantData"
    Slp = "slpPlantData"
    Bsb = "bsbPlantData"


@unique
class PlantMode(Enum):
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
class ZoneMode(Enum):
    """Zone mode enum"""

    UNDEFINED = -1
    OFF = 0
    MANUAL_NIGHT = 1
    MANUAL = 2
    TIME_PROGRAM = 3

@unique
class BsbZoneMode(Enum):
    """BSB zone mode enum"""

    UNDEFINED = -1
    OFF = 0
    TIME_PROGRAM = 1
    MANUAL = 2
    MANUAL_NIGHT = 3

@unique
class DhwMode(Enum):
    """Dhw mode enum"""

    DISABLED = 0
    TIME_BASED = 1
    ALWAYS_ACTIVE = 2
    HC_HP = 3
    HC_HP_40 = 4
    GREEN = 5


@unique
class Weather(Enum):
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
class GasEnergyUnit(IntEnum):
    """Gas energy unit enum"""

    KWH = 0
    GIGA_JOULE = 1
    THERM = 2
    MEGA_BTU = 3
    SMC = 4
    CUBE_METER = 5


@unique
class GasType(IntEnum):
    """Gas type enu,"""

    NATURAL_GAS = 0
    LPG = 1
    AIR_PROPANED = 2
    GPO = 3
    PROPANE = 4


@unique
class Currency(IntEnum):
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
class SystemType(Enum):
    """System type enum"""

    UNKNOWN = -1
    GALILEO1 = 1
    GALILEO2 = 2
    GALEVO = 3
    VELIS = 4
    BSB = 5


@unique
class Brands(Enum):
    """Brands enum"""

    Ariston = 1
    Chaffoteaux = 2
    Elco = 3
    Atag = 4
    Nti = 5
    Htp = 6
    Racold = 7


class WaterHeaterMode(Enum):
    """Base class for plant modes"""


@unique
class BsbOperativeMode(WaterHeaterMode):
    """BSB operative mode enum"""

    OFF = 0
    ON = 1

@unique
class LuxPlantMode(WaterHeaterMode):
    """Lux plant mode enum"""

    MANUAL = 1
    PROGRAM = 5
    BOOST = 9


@unique
class EvoPlantMode(WaterHeaterMode):
    """Evo plant mode enum"""

    MANUAL = 1
    PROGRAM = 5


@unique
class VelisPlantMode(WaterHeaterMode):
    """Velis plant mode enum"""

    MANUAL = 1
    PROGRAM = 5
    NIGHT = 8


@unique
class NuosSplitPlantMode(Enum):
    """NuosSplit plant mode enum"""

    MANUAL = 1
    PROGRAM = 2


@unique
class NuosSplitOperativeMode(WaterHeaterMode):
    """NuosSplit operative mode enum"""

    GREEN = 0
    COMFORT = 1
    FAST = 2
    IMEMORY = 3


@unique
class LydosPlantMode(WaterHeaterMode):
    """Lydos hybrid plant mode enum"""

    IMEMORY = 1
    GREEN = 2
    PROGRAM = 6
    BOOST = 7


@unique
class WheType(Enum):
    """Whe type enum"""

    Unknown = -1
    Evo = 1
    LydosHybrid = 2
    Lydos = 3
    NuosSplit = 4
    Andris2 = 5
    Evo2 = 6
    Lux2 = 7
    Lux = 8


@unique
class ConsumptionType(Enum):
    """Consumption type"""

    CENTRAL_HEATING_TOTAL_ENERGY = 1
    DOMESTIC_HOT_WATER_TOTAL_ENERGY = 2
    CENTRAL_COOLING_TOTAL_ENERGY = 3
    CENTRAL_HEATING_GAS = 7
    DOMESTIC_HOT_WATER_HEATING_PUMP_ELECTRICITY = 8
    DOMESTIC_HOT_WATER_RESISTOR_ELECTRICITY = 9
    DOMESTIC_HOT_WATER_GAS = 10
    CENTRAL_HEATING_ELECTRICITY = 20
    DOMESTIC_HOT_WATER_ELECTRICITY = 21


@unique
class ConsumptionTimeInterval(Enum):
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
    IS_HIDDEN: Final[str] = "isHidden"


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

class EvoOneDeviceProperties:
    """Contants for Velis Evo device properties"""

    AV_SHW: Final[str] = "avShw"
    ECO: Final[str] = "eco"
    GW: Final[str] = "gw"
    MAX_AV_SHW: Final[str] = "maxAvShw"
    MAX_REQ_SHW: Final[str] = "maxReqShw"
    MODE: Final[str] = "mode"
    ON: Final[str] = "on"
    PROC_REQ_SHW: Final[str] = "procReqShw"
    REQ_SHW: Final[str] = "reqShw"
    RM_TM: Final[str] = "rmTm"
    SHW_P1: Final[str] = "shwP1"
    STATE: Final[str] = "state"
    TEMP: Final[str] = "temp"
    TM_P1: Final[str] = "tmP1"

class VelisDeviceProperties:
    """Contants for Velis device properties"""

    GW: Final[str] = "gw"
    MODE: Final[str] = "mode"
    ON: Final[str] = "on"
    PROC_REQ_TEMP: Final[str] = "procReqTemp"


class NuosSplitProperties(VelisDeviceProperties):
    """Constants for NuosSplit device properties"""

    WATER_TEMP: Final[str] = "waterTemp"
    COMFORT_TEMP: Final[str] = "comfortTemp"
    REDUCED_TEMP: Final[str] = "reducedTemp"
    OP_MODE: Final[str] = "opMode"
    BOOST_ON: Final[str] = "boostOn"
    HP_STATE: Final[str] = "hpState"


class EvoLydosDeviceProperties(VelisDeviceProperties):
    """Constants for evo and lydos device properties"""

    ANTI_LEG: Final[str] = "antiLeg"
    AV_SHW: Final[str] = "avShw"
    HEAT_REQ: Final[str] = "heatReq"
    REQ_TEMP: Final[str] = "reqTemp"
    TEMP: Final[str] = "temp"


class EvoDeviceProperties(EvoLydosDeviceProperties):
    """Contants for Velis Evo device properties"""

    ECO: Final[str] = "eco"
    PWR_OPT: Final[str] = "pwrOpt"
    RM_TM: Final[str] = "rmTm"


class LydosDeviceProperties(EvoLydosDeviceProperties):
    """Contants for Velis Lydos device properties"""

    BOOST_REQ_TEMP: Final[str] = "boostReqTemp"

class BsbDeviceProperties:
    """Constants for bsb device properties."""

    DHW_COMF_TEMP: Final[str] = "dhwComfTemp"
    DHW_ENABLED: Final[str] = "dhwEnabled"
    DHW_MODE: Final[str] = "dhwMode"
    DHW_PROG_READ_ONLY: Final[str] = "dhwProgReadOnly"
    DHW_REDU_TEMP: Final[str] = "dhwReduTemp"
    DHW_STORAGE_TEMP_ERROR: Final[str] = "dhwStorageTempError"
    DHW_TEMP: Final[str] = "dhwTemp"
    FLAME: Final[str] = "flame"
    GW: Final[str] = "gw"
    HAS_DHW_TEMP: Final[str] = "hasDhwTemp"
    HAS_OUT_TEMP: Final[str] = "hasOutTemp"
    HP_ON: Final[str] = "hpOn"
    OUTSIDE_TEMP_ERROR: Final[str] = "outsideTempError"
    OUT_TEMP: Final[str] = "outTemp"
    ZONES: Final[str] = "zones"


class BsbZoneProperties:
    """Constants for bsb zone properties."""

    CH_COMF_TEMP: Final[str] = "chComfTemp"
    CH_PROT_TEMP: Final[str] = "chProtTemp"
    CH_RED_TEMP: Final[str] = "chRedTemp"
    COOL_COMF_TEMP: Final[str] = "coolComfTemp"
    COOLING_ON: Final[str] = "coolingOn"
    COOL_PROT_TEMP: Final[str] = "coolProtTemp"
    COOL_RED_TEMP: Final[str] = "coolRedTemp"
    DESIRED_ROOM_TEMP: Final[str] = "desiredRoomTemp"
    HAS_ROOM_SENS: Final[str] = "hasRoomSens"
    HEATING_ON: Final[str] = "heatingOn"
    HEAT_OR_COOL_REQ: Final[str] = "heatOrCoolReq"
    HOLIDAYS: Final[str] = "holidays"
    MODE: Final[str] = "mode"
    ROOM_TEMP: Final[str] = "roomTemp"
    ROOM_TEMP_ERROR: Final[str] = "roomTempError"
    USE_REDUCED_OPERATION_MODE_ON_HOLIDAY: Final[str] = "useReducedOperationModeOnHoliday"

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
    SE_ANTI_COOLING_TEMPERATURE_MAX: Final[str] = "SeAntiCoolingTemperatureMax"
    SE_ANTI_COOLING_TEMPERATURE_MIN: Final[str] = "SeAntiCoolingTemperatureMin"
    SE_MAX_GREEN_SETPOINT_TEMPERATURE: Final[str] = "SeMaxGreenSetpointTemperature"
    SE_HEATING_RATE: Final[str] = "SeHeatingRate"
    SE_NIGHT_BEGIN_AS_MINUTES: Final[str] = "SeNightBeginAsMinutes"
    SE_NIGHT_BEGIN_MIN_AS_MINUTES: Final[str] = "SeNightBeginMinAsMinutes"
    SE_NIGHT_BEGIN_MAX_AS_MINUTES: Final[str] = "SeNightBeginMaxAsMinutes"
    SE_NIGHT_END_AS_MINUTES: Final[str] = "SeNightEndAsMinutes"
    SE_NIGHT_END_MIN_AS_MINUTES: Final[str] = "SeNightEndMinAsMinutes"
    SE_NIGHT_END_MAX_AS_MINUTES: Final[str] = "SeNightEndMaxAsMinutes"


class SlpDeviceSettings:
    """Constatns for Slp device settings"""

    SLP_MAX_GREEN_TEMPERATURE: Final[str] = "SlpMaxGreenTemperature"
    SLP_MAX_SETPOINT_TEMPERATURE: Final[str] = "SlpMaxSetpointTemperature"
    SLP_MAX_SETPOINT_TEMPERATURE_MIN: Final[str] = "SlpMaxSetpointTemperatureMin"
    SLP_MAX_SETPOINT_TEMPERATURE_MAX: Final[str] = "SlpMaxSetpointTemperatureMax"
    SLP_MIN_SETPOINT_TEMPERATURE: Final[str] = "SlpMinSetpointTemperature"
    SLP_MIN_SETPOINT_TEMPERATURE_MIN: Final[str] = "SlpMinSetpointTemperatureMin"
    SLP_MIN_SETPOINT_TEMPERATURE_MAX: Final[str] = "SlpMinSetpointTemperatureMax"
    SLP_ANTILEGIONELLA_ON_OFF: Final[str] = "SlpAntilegionellaOnOff"
    SLP_PRE_HEATING_ON_OFF: Final[str] = "SlpPreHeatingOnOff"
    SLP_HEATING_RATE: Final[str] = "SlpHeatingRate"
    SLP_HC_HP_MODE: Final[str] = "SlpHcHpMode"


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
    HYBRID_MODE: Final[str] = "HybridMode"
    BUFFER_CONTROL_MODE: Final[str] = "BufferControlMode"
    BUFFER_TIME_PROG_COMFORT_HEATING_TEMP: Final[str] = "BufferTimeProgComfortHeatingTemp"
    BUFFER_TIME_PROG_ECONOMY_HEATING_TEMP: Final[str] = "BufferTimeProgEconomyHeatingTemp"
    BUFFER_TIME_PROG_COMFORT_COOLING_TEMP: Final[str] = "BufferTimeProgComfortCoolingTemp"
    BUFFER_TIME_PROG_ECONOMY_COOLING_TEMP: Final[str] = "BufferTimeProgEconomyCoolingTemp"
    IS_QUIET: Final[str] = "IsQuite" # ariston misspelled IsQuiet


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
    ZONE_NAME: Final[str] = "ZoneName"
    VIRT_TEMP_SETPOINT_HEAT: Final[str] = "VirtTempSetpointHeat"
    VIRT_TEMP_SETPOINT_COOL: Final[str] = "VirtTempSetpointCool"
    VIRT_COMFORT_TEMP: Final[str] = "VirtComfortTemp"
    VIRT_REDUCED_TEMP: Final[str] = "VirtReducedTemp"
    ZONE_VIRT_TEMP_OFFSET_COOL: Final[str] = "VirtTempOffsetCool"


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
    ALLOWED_OPTIONS: Final[str] = "allowedOptions"

class BusErrorsProperties:
    """Constants for bus errors properties"""
    GW: Final[str] = "gw"
    TIMESTAMP: Final[str] = "timestamp"
    FAULT: Final[str] = "fault"
    MULT: Final[str] = "mult"
    CODE: Final[str] = "code"
    PRI: Final[str] = "pri"
    ERR_DEX: Final[str] = "errDex"
    RES: Final[str] = "res"
    BLK: Final[str] = "blk"
