/*
 * EXCERPT — see LICENSE-NOTE.md. Function calculateInterpCoefficient() from
 * firmware/fadecandy.cpp at
 * PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d, lines 97-120.
 * Timestamps are millis() values stamped when a keyframe's final USB packet
 * was finalized (fc_usb.cpp finalizeFramebuffer, L117-L125).
 */

static inline uint32_t calculateInterpCoefficient()
{
    /*
     * Calculate our interpolation coefficient. This is a value between
     * 0x0000 and 0x10000, representing some point in between fbPrev and fbNext.
     *
     * We timestamp each frame at the moment its final packet has been received.
     * In other words, fbNew has no valid timestamp yet, and fbPrev/fbNext both
     * have timestamps in the recent past.
     *
     * fbNext's timestamp indicates when both fbPrev and fbNext entered their current
     * position in the keyframe queue. The difference between fbPrev and fbNext indicate
     * how long the interpolation between those keyframes should take.
     */

    uint32_t now = millis();
    uint32_t tsPrev = buffers.fbPrev->timestamp;
    uint32_t tsNext = buffers.fbNext->timestamp;
    uint32_t tsDiff = tsNext - tsPrev;
    uint32_t tsElapsed = now - tsNext;

    // Careful to avoid overflows if the frames stop coming...
    return (std::min<uint32_t>(tsElapsed, tsDiff) << 16) / tsDiff;
}
