"""Constants for the Atomberg integration."""

from enum import StrEnum

DOMAIN = "atomberg"

UDP_LISTENER = "udp_listener"
ENTRIES = "entries"

CONF_REFRESH_TOKEN = "refresh_token"
CONF_USE_CLOUD_CONTROL = "use_cloud_control"
CONF_CONTROL_METHOD = "control_method"
CONF_IR_EMITTER_ENTITY = "ir_emitter_entity"
CONF_FAN_MODEL = "fan_model"
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
    GENERIC = "generic"


FAN_MODEL_NAMES = {
    FanModel.RENESA_PLUS: "Renesa+",
    FanModel.ARIS: "Aris",
    FanModel.ERICA: "Erica",
    FanModel.GORILLA_EFFICIO: "Gorilla Efficio",
    FanModel.GENERIC: "Generic",
}
