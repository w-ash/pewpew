# Excerpt from LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
# ledfx/devices/ddp.py lines 25-36, verbatim. GPL-3.0; LedFx developers (Austin Hodges et al., per AUTHORS.rst).
# Source entry [S630]. See LICENSE-NOTE.md.
# lines 25-36
    MAX_PIXELS = 480
    MAX_DATALEN = MAX_PIXELS * 3  # fits nicely in an ethernet packet

    VER = 0xC0  # version mask
    VER1 = 0x40  # version=1
    PUSH = 0x01
    QUERY = 0x02
    REPLY = 0x04
    STORAGE = 0x08
    TIME = 0x10
    DATATYPE = 0x0B  # RGB (type=001), 8-bit (size=011)
    SOURCE = 0x01
