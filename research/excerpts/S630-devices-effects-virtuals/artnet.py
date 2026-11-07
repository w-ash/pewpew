# Excerpt from LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
# ledfx/devices/artnet.py lines 176-179, verbatim. GPL-3.0; LedFx developers (Austin Hodges et al., per AUTHORS.rst).
# Source entry [S630]. See LICENSE-NOTE.md.
# lines 176-179
        # protect against things being modified during flush
        # just skip a frame if the lock is owned, we have a mutext deadlock between
        # devices and virtuals protections
        if self.lock.acquire(blocking=False):
