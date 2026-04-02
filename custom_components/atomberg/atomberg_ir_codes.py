"""Atomberg IR NEC command definitions."""

from infrared_protocols import Command as InfraredCommand
from infrared_protocols.protocols.nec import NECCommand

ATOMBERG_IR_ADDRESS = 0xF300
ATOMBERG_IR_MODULATION = 38000


class AtombergIRCommand:
    """NEC command codes for Atomberg fans."""

    POWER = 0x6E91
    SPEED_1 = 0x748B
    SPEED_2 = 0x6F90
    SPEED_3 = 0x758A
    SPEED_4 = 0x6C93
    SPEED_5 = 0x7788
    BOOST = 0x708F
    SLEEP = 0x718E
    LED = 0xE916
    TIMER = 0x6996
    TIMER_1H = 0xA15E
    TIMER_2H = 0x619E
    TIMER_3H = 0x49B6
    TIMER_6H = 0x31CE


SPEED_MAP = {
    1: AtombergIRCommand.SPEED_1,
    2: AtombergIRCommand.SPEED_2,
    3: AtombergIRCommand.SPEED_3,
    4: AtombergIRCommand.SPEED_4,
    5: AtombergIRCommand.SPEED_5,
    6: AtombergIRCommand.BOOST,
}


def make_atomberg_command(command: int) -> InfraredCommand:
    """Create an InfraredCommand from an Atomberg NEC command code."""
    return NECCommand(
        address=ATOMBERG_IR_ADDRESS,
        command=command,
        modulation=ATOMBERG_IR_MODULATION,
    )
