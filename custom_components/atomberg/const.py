"""Constants for the Atomberg integration."""

from enum import StrEnum

DOMAIN = "atomberg"

UDP_LISTENER = "udp_listener"
ENTRIES = "entries"
SETUP_ACTIVE = "setup_active"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_USE_CLOUD_CONTROL = "use_cloud_control"
CONF_CONTROL_METHOD = "control_method"
CONF_IR_EMITTER_ENTITY = "ir_emitter_entity"
CONF_FAN_MODEL = "fan_model"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_SERIES = "device_series"
CONF_DISPLAY_NAME = "display_name"
CONF_IP_ADDRESS = "ip_address"
MANUFACTURER = "Atomberg"

# Sentinel series value used when the device series is unknown.
UNKNOWN_SERIES = "UNKNOWN"


class ControlMethod(StrEnum):
    """Control method for Atomberg devices."""

    # Bootstrap entry used to enable UDP autodiscovery; it does not control a fan.
    LOCAL_DISCOVERY = "local_discovery"

    CLOUD = "cloud"
    IR = "ir"
    LOCAL_UDP = "local_udp"


class FanModel(StrEnum):
    """Supported Atomberg fan models for IR control."""

    RENESA_PLUS = "renesa_plus"
    ARIS = "aris"
    ERICA = "erica"
    GORILLA_EFFICIO = "gorilla_efficio"
    EFFICIO_PLUS_400MM_PEDESTAL = "efficio_plus_400mm_pedestal"
    GENERIC = "generic"


FAN_MODEL_NAMES = {
    FanModel.RENESA_PLUS: "Renesa+",
    FanModel.ARIS: "Aris",
    FanModel.ERICA: "Erica",
    FanModel.GORILLA_EFFICIO: "Gorilla Efficio",
    FanModel.EFFICIO_PLUS_400MM_PEDESTAL: "Efficio+ 400mm Pedestal",
    FanModel.GENERIC: "Generic",
}
