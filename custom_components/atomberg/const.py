"""Constants for the Atomberg integration."""

from enum import StrEnum

DOMAIN = "atomberg"

UDP_LISTENER = "udp_listener"
ENTRIES = "entries"
PURIFIER_COORDINATORS = "purifier_coordinators"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_USE_CLOUD_CONTROL = "use_cloud_control"
CONF_CONTROL_METHOD = "control_method"
CONF_IR_EMITTER_ENTITY = "ir_emitter_entity"
CONF_FAN_MODEL = "fan_model"
CONF_PURIFIER_POLL_INTERVAL = "purifier_poll_interval"
DEFAULT_PURIFIER_POLL_INTERVAL = 30  # Minutes, 48 API calls a day
MIN_PURIFIER_POLL_INTERVAL = 15
MAX_PURIFIER_POLL_INTERVAL = 240
MANUFACTURER = "Atomberg"


class ControlMethod(StrEnum):
    """Control method for Atomberg devices."""

    CLOUD = "cloud"
    IR = "ir"


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
