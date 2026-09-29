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
CONF_STATE_UPDATE_METHOD = "state_update_method"
CONF_POLLING_INTERVAL = "polling_interval"
MANUFACTURER = "Atomberg"

# Polling interval (in seconds) used when state is refreshed via the cloud API.
DEFAULT_POLLING_INTERVAL = 10
MIN_POLLING_INTERVAL = 5
MAX_POLLING_INTERVAL = 300


class ControlMethod(StrEnum):
    """Control method for Atomberg devices."""

    CLOUD = "cloud"
    IR = "ir"


class StateUpdateMethod(StrEnum):
    """How device state is refreshed for cloud-controlled devices."""

    # Listen to local UDP broadcasts/beacons on port 5625 (requires the fans and
    # Home Assistant to be reachable on the same L2 network/VLAN).
    BROADCAST = "broadcast"
    # Poll the Atomberg cloud API on a fixed interval. Works across VLANs since it
    # does not depend on receiving local broadcasts.
    POLLING = "polling"


DEFAULT_STATE_UPDATE_METHOD = StateUpdateMethod.BROADCAST


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
