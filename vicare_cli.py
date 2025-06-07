import argparse
import json
import logging
import sys # Added for sys.exit()
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from PyViCare.PyViCare import PyViCare
from PyViCare.PyViCareDevice import PyViCareDevice
from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig
from PyViCare.PyViCareUtils import (
    PyViCareInvalidCredentialsError,
    PyViCareNotSupportedFeatureError,
    PyViCareRateLimitError,
    PyViCareInvalidDataError,
)
# It's good practice to see if PyViCare itself uses requests and handle its potential ConnectionError
# For now, let's assume direct import might be needed if value_getters directly make web calls
# not wrapped by PyViCare's error handling.
import requests # For requests.exceptions.ConnectionError

# Basic logger setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_LOGGER = logging.getLogger(__name__)


# Simplified dataclass for sensor descriptions for CLI use
@dataclass
class ViCareSensorEntityDescription:
    """A class that describes ViCare sensor entities."""
    key: str
    value_getter: Callable[[Any], Any]
    unit_getter: Optional[Callable[[Any], Any]] = None
    # HA specific fields omitted for CLI: name, translation_key, device_class,
    # state_class, entity_category, entity_registry_enabled_default, native_unit_of_measurement


# Copied and simplified GLOBAL_SENSORS from HA core
# For CLI, we might not need device_class, state_class, or extensive unit mapping unless we want to pretty print.
# Focusing on getting the raw value and unit string.

# Placeholder for units if needed, otherwise, we'll just use strings from unit_getter
# For example, if unit_getter returns "°C", we just use that.
# No direct equivalent for SensorDeviceClass, SensorStateClass, UnitOfTemperature needed for basic CLI.

GLOBAL_SENSORS: tuple[ViCareSensorEntityDescription, ...] = (
    ViCareSensorEntityDescription(
        key="outside_temperature",
        value_getter=lambda api: api.getOutsideTemperature(),
        # Assuming unit_getter might not be needed if getOutsideTemperature includes units or it's fixed
        # If getOutsideTemperature returns a number, and unit is fixed e.g. Celsius:
        # unit_getter=lambda api: "°C", # Or a more complex getter if the API provides it
    ),
    ViCareSensorEntityDescription(
        key="return_temperature",
        value_getter=lambda api: api.getReturnTemperature(),
        # unit_getter=lambda api: "°C", # If applicable
    ),
    ViCareSensorEntityDescription(
        key="boiler_temperature",
        value_getter=lambda api: api.getBoilerTemperature(),
        # unit_getter=lambda api: "°C",
    ),
    ViCareSensorEntityDescription(
        key="boiler_supply_temperature",
        value_getter=lambda api: api.getBoilerCommonSupplyTemperature(),
         # unit_getter=lambda api: "°C",
    ),
    ViCareSensorEntityDescription(
        key="dhw_storage_temperature",
        value_getter=lambda api: api.getDHWStorageTemperature(),
        # unit_getter=lambda api: "°C",
    ),
    ViCareSensorEntityDescription(
        key="dhw_temperature",
        value_getter=lambda api: api.getDHWTemperature(),
        # unit_getter=lambda api: "°C",
    ),
    ViCareSensorEntityDescription(
        key="dhw_outlet_temperature",
        value_getter=lambda api: api.getDHWOutletTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="dhw_max_temperature",
        value_getter=lambda api: api.getDHWMaxTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="dhw_min_temperature",
        value_getter=lambda api: api.getDHWMinTemperature(),
    ),
    # Viessmann API specific gas consumption sensors
    ViCareSensorEntityDescription(
        key="gas_consumption_heating_today",
        value_getter=lambda api: api.getGasConsumptionHeatingToday(),
        # unit_getter=lambda api: "kWh", # Example, adjust if API provides unit
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_heating_this_week",
        value_getter=lambda api: api.getGasConsumptionHeatingThisWeek(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_heating_this_month",
        value_getter=lambda api: api.getGasConsumptionHeatingThisMonth(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_heating_this_year",
        value_getter=lambda api: api.getGasConsumptionHeatingThisYear(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_dhw_today",
        value_getter=lambda api: api.getGasConsumptionDhwToday(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_dhw_this_week",
        value_getter=lambda api: api.getGasConsumptionDhwThisWeek(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_dhw_this_month",
        value_getter=lambda api: api.getGasConsumptionDhwThisMonth(),
    ),
    ViCareSensorEntityDescription(
        key="gas_consumption_dhw_this_year",
        value_getter=lambda api: api.getGasConsumptionDhwThisYear(),
    ),
    # Viessmann API specific power consumption sensors
    ViCareSensorEntityDescription(
        key="power_consumption_today",
        value_getter=lambda api: api.getPowerConsumptionToday(),
    ),
    ViCareSensorEntityDescription(
        key="power_consumption_this_week",
        value_getter=lambda api: api.getPowerConsumptionThisWeek(),
    ),
    ViCareSensorEntityDescription(
        key="power_consumption_this_month",
        value_getter=lambda api: api.getPowerConsumptionThisMonth(),
    ),
    ViCareSensorEntityDescription(
        key="power_consumption_this_year",
        value_getter=lambda api: api.getPowerConsumptionThisYear(),
    ),
    ViCareSensorEntityDescription(
        key="current_power_consumption",
        value_getter=lambda api: api.getCurrentPowerConsumption(),
    ),
     ViCareSensorEntityDescription(
        key="supply_temperature",
        value_getter=lambda api: api.getSupplyTemperature(),
    ),
)

CIRCUIT_SENSORS: tuple[ViCareSensorEntityDescription, ...] = (
    ViCareSensorEntityDescription(
        key="supply_temperature",
        value_getter=lambda circuit: circuit.getSupplyTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="temperature",
        value_getter=lambda circuit: circuit.getTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="current_temperature",
        value_getter=lambda circuit: circuit.getCurrentTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="target_temperature",
        value_getter=lambda circuit: circuit.getTargetTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="current_target_temperature",
        value_getter=lambda circuit: circuit.getCurrentTargetTemperature(),
    ),
    ViCareSensorEntityDescription(
        key="heating_curve_slope",
        value_getter=lambda circuit: circuit.getHeatingCurveSlope(),
    ),
    ViCareSensorEntityDescription(
        key="heating_curve_shift",
        value_getter=lambda circuit: circuit.getHeatingCurveShift(),
    ),
)

BURNER_SENSORS: tuple[ViCareSensorEntityDescription, ...] = (
    ViCareSensorEntityDescription(
        key="modulation",
        value_getter=lambda burner: burner.getModulation(),
        # unit_getter=lambda burner: "%", # Example
    ),
    ViCareSensorEntityDescription(
        key="hours",
        value_getter=lambda burner: burner.getHours(),
        # unit_getter=lambda burner: "h",
    ),
    ViCareSensorEntityDescription(
        key="starts",
        value_getter=lambda burner: burner.getStarts(),
    ),
)

COMPRESSOR_SENSORS: tuple[ViCareSensorEntityDescription, ...] = (
    ViCareSensorEntityDescription(
        key="active",
        value_getter=lambda compressor: compressor.getActive(),
    ),
    ViCareSensorEntityDescription(
        key="hours",
        value_getter=lambda compressor: compressor.getHours(),
        # unit_getter=lambda compressor: "h",
    ),
    ViCareSensorEntityDescription(
        key="starts",
        value_getter=lambda compressor: compressor.getStarts(),
    ),
    ViCareSensorEntityDescription(
        key="phase",
        value_getter=lambda compressor: compressor.getPhase(),
    ),
)


# Mappings like VICARE_UNIT_TO_HA_UNIT might be overly complex for CLI.
# If unit_getter returns a raw unit string (e.g. "BAR", "CEL"), we can just display that.
# For now, omitting VICARE_UNIT_TO_DEVICE_CLASS and VICARE_UNIT_TO_HA_UNIT.

# Based on homeassistant/components/vicare/const.py
class HeatingType(Enum):
    """Possible options for heating type."""
    AUTO = "auto"
    GAS = "gas"
    OIL = "oil"
    PELLETS = "pellets"
    HEATPUMP = "heatpump"
    FUELCELL = "fuelcell"
    HYBRID = "hybrid"

HEATING_TYPE_TO_CREATOR_METHOD = {
    HeatingType.AUTO: "asAutoDetectDevice",
    HeatingType.GAS: "asGasBoiler",
    HeatingType.OIL: "asOilBoiler",
    HeatingType.PELLETS: "asPelletsBoiler",
    HeatingType.HEATPUMP: "asHeatPump",
    HeatingType.FUELCELL: "asFuelCell",
    HeatingType.HYBRID: "asHybridDevice",
}

def login_to_vicare(args):
    """Logs in to the Viessmann ViCare API."""
    vicare_api = PyViCare()
    # Using _LOGGER for consistency if we adopt more logging
    _LOGGER.info("Setting cache duration to 60 seconds.")
    vicare_api.setCacheDuration(60)

    try:
        _LOGGER.info("Attempting to initialize with credentials...")
        vicare_api.initWithCredentials(
            args.username,
            args.password,
            args.client_id,
            args.token_cache_path
        )
        _LOGGER.info("Successfully initialized with credentials.")
        return vicare_api
    except PyViCareInvalidCredentialsError:
        _LOGGER.error("Invalid credentials. Please check your username, password, and client ID.")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        _LOGGER.error(f"Connection error during login: {e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred during login: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main function to parse arguments, log in, fetch device info, and discover sensors."""
    try:
        parser = argparse.ArgumentParser(description="Viessmann ViCare CLI")

    heating_type_choices = [ht.value for ht in HeatingType]
    parser.add_argument("--username", required=True, help="Viessmann ViCare username (email address)")
    parser.add_argument("--password", required=True, help="Viessmann ViCare password")
    parser.add_argument("--client-id", required=True, help="Viessmann ViCare API client ID")
    parser.add_argument("--heating-type", default=HeatingType.AUTO.value, choices=heating_type_choices, help="Type of heating system (default: auto)")
    parser.add_argument("--token-cache-path", default="vicare_token.save", help="Path to store/load the API token (default: vicare_token.save)")

    args = parser.parse_args()

    _LOGGER.info("Attempting to log in to ViCare API...")
    vicare_api = login_to_vicare(args)

    if vicare_api:
        _LOGGER.info("Successfully logged in to ViCare API.")
        device = get_vicare_device(vicare_api, args.heating_type)
        if device:
            _LOGGER.info("Successfully fetched device information.")
            try:
                serial = device.getSerial()
                _LOGGER.info(f"Device Serial: {serial}")
            except PyViCareNotSupportedFeatureError:
                _LOGGER.warning("Device serial number not available (feature not supported).")
            except Exception as e:
                _LOGGER.error(f"Error retrieving device serial: {e}", exc_info=True)

            _LOGGER.info("Discovering available sensors...")
            # discover_sensors now correctly called with only device
            available_sensors = discover_sensors(device)

            # Print only the JSON data to stdout for easy piping
            print(json.dumps(available_sensors, indent=2, ensure_ascii=False))

        # Original argument printing for verification can be commented out or removed
        # _LOGGER.info("\nParsed arguments (for verification):")
        # _LOGGER.info(f"  Username: {args.username}")
        # _LOGGER.info(f"  Client ID: {args.client_id}")
        # _LOGGER.info(f"  Heating Type: {args.heating_type}")
        # _LOGGER.info(f"  Token Cache Path: {args.token_cache_path}")
    except Exception as e:
        _LOGGER.error(f"A critical error occurred in the main execution block: {e}", exc_info=True)
        sys.exit(1)

def get_vicare_device(vicare_api, heating_type_str):
    """Gets the ViCare device object based on the heating type."""
    if not vicare_api.devices:
        _LOGGER.error("No devices found on your ViCare account.")
        sys.exit(1)

    device_config = vicare_api.devices[0]
    _LOGGER.info(f"Found device: {device_config.getModel()} (ID: {device_config.getInstallationId()}/{device_config.getGatewaySerial()})")


    try:
        heating_type_enum = HeatingType(heating_type_str)
        creator_method_name = HEATING_TYPE_TO_CREATOR_METHOD[heating_type_enum]
        _LOGGER.info(f"Using creator method: {creator_method_name} for heating type: {heating_type_str}")

        if not isinstance(device_config, PyViCareDeviceConfig):
            _LOGGER.error("Device configuration object is not of the expected type PyViCareDeviceConfig.")
            sys.exit(1)

        device = getattr(device_config, creator_method_name)()
        return device
    except KeyError: # Should not happen due to argparse choices, but good for robustness
        _LOGGER.error(f"Heating type '{heating_type_str}' is valid but not mapped in HEATING_TYPE_TO_CREATOR_METHOD.")
        sys.exit(1)
    except AttributeError:
        _LOGGER.error(f"Could not find method '{creator_method_name}' on device config. Check PyViCare library or mapping.", exc_info=True)
        sys.exit(1)
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred while creating device object: {e}", exc_info=True)
        sys.exit(1)

def get_components(device_method_name: str, component_name_plural: str, device: PyViCareDevice) -> list:
    """Helper to retrieve components (circuits, burners, compressors) from a device."""
    components = []
    try:
        components_list = getattr(device, device_method_name)() # e.g., device.getCircuits()
        if components_list is not None: # Check if the method returned something
            components.extend(components_list)
        _LOGGER.debug(f"Found {len(components)} {component_name_plural}.")
    except PyViCareNotSupportedFeatureError:
        _LOGGER.info(f"{component_name_plural.capitalize()} feature not supported by this device.")
    except AttributeError:
        _LOGGER.warning(f"Device object does not have method '{device_method_name}'. Update PyViCare or check device type.")
    except Exception as e:
        _LOGGER.error(f"Error getting {component_name_plural} from device: {e}", exc_info=True)
    return components

def discover_sensors(device: PyViCareDevice) -> dict:
    """Discovers available global and component-level sensors and their values."""
    available_sensors = {}
    _LOGGER.info("Starting sensor discovery...")

    # 1. Global Sensors
    _LOGGER.info(f"Attempting to retrieve data for {len(GLOBAL_SENSORS)} global sensor types.")
    for desc in GLOBAL_SENSORS:
        # Using a helper to avoid code duplication for fetching and error handling
        _fetch_and_store_sensor(device, desc, available_sensors, "global")

    # 2. Circuit Sensors
    circuits = get_components("getCircuits", "circuits", device)
    for i, circuit in enumerate(circuits):
        _LOGGER.info(f"Discovering sensors for circuit {i}...")
        for desc in CIRCUIT_SENSORS:
            _fetch_and_store_sensor(circuit, desc, available_sensors, f"circuit_{i}")

    # 3. Burner Sensors
    burners = get_components("getBurners", "burners", device)
    for i, burner in enumerate(burners):
        _LOGGER.info(f"Discovering sensors for burner {i}...")
        # Assuming burner objects might have 'id' or similar, using index 'i' for now.
        # PyViCare's burner objects are typically identified by an index (e.g. burner 0, burner 1)
        for desc in BURNER_SENSORS:
            _fetch_and_store_sensor(burner, desc, available_sensors, f"burner_{i}")

    # 4. Compressor Sensors
    compressors = get_components("getCompressors", "compressors", device)
    for i, compressor in enumerate(compressors):
        _LOGGER.info(f"Discovering sensors for compressor {i}...")
        for desc in COMPRESSOR_SENSORS:
            _fetch_and_store_sensor(compressor, desc, available_sensors, f"compressor_{i}")

    _LOGGER.info(f"Sensor discovery complete. Found data for {len(available_sensors)} sensors in total.")
    return available_sensors

def _fetch_and_store_sensor(component_or_device: Any,
                            desc: ViCareSensorEntityDescription,
                            storage: dict,
                            prefix: str):
    """Fetches a single sensor value and stores it, handling errors."""
    sensor_key_full = f"{prefix}_{desc.key}"
    _LOGGER.debug(f"Trying to fetch sensor: {sensor_key_full}")

    try:
        value = desc.value_getter(component_or_device)
        unit = desc.unit_getter(component_or_device) if desc.unit_getter else None

        if value is None or (isinstance(value, str) and "error" in value.lower()):
            _LOGGER.debug(f"Sensor '{sensor_key_full}' returned no data or an error string: {value}")
            return # Skip this sensor

        sensor_data = {"value": value}
        if unit:
            # Ensure unit is a string, some getters might return None or other types
            unit_str = str(unit) if unit is not None else None
            if unit_str: # Add unit only if it's a non-empty string
                 sensor_data["unit"] = unit_str

        storage[sensor_key_full] = sensor_data
        _LOGGER.debug(f"Successfully fetched sensor: {sensor_key_full} = {value} {unit_str if unit_str else ''}")

    except PyViCareNotSupportedFeatureError:
        _LOGGER.debug(f"Feature not supported for sensor: {sensor_key_full}")
    except PyViCareRateLimitError:
        _LOGGER.error("ViCare API rate limit exceeded. Halting sensor discovery.")
        raise # Re-raise to stop further processing in the main discover_sensors loop perhaps
    except PyViCareInvalidDataError as e:
        _LOGGER.warning(f"Invalid data received for sensor {sensor_key_full}: {e}")
    except requests.exceptions.ConnectionError as e: # Should be caught by PyViCare, but as a safeguard
        _LOGGER.error(f"Connection error while fetching sensor {sensor_key_full}: {e}")
        raise
    except AttributeError as e:
        # Extract component/device type for better logging if possible
        obj_type = type(component_or_device).__name__
        _LOGGER.warning(f"Method not found for sensor {sensor_key_full} on {obj_type} (AttributeError): {e}. This might mean the component type doesn't support it or value_getter is misconfigured.", exc_info=True)
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred while fetching sensor {sensor_key_full}: {e}", exc_info=True)


if __name__ == "__main__":
    main()
