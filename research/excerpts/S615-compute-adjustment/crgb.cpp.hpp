CRGB CRGB::computeAdjustment(fl::u8 scale, const CRGB &colorCorrection,
                             const CRGB &colorTemperature) {
#if defined(NO_CORRECTION) && (NO_CORRECTION == 1)
    return CRGB(scale, scale, scale);
#else
    CRGB adj(0, 0, 0);
    if (scale > 0) {
        for (fl::u8 i = 0; i < 3; ++i) {
            fl::u8 cc = colorCorrection.raw[i];
            fl::u8 ct = colorTemperature.raw[i];
            if (cc > 0 && ct > 0) {
                // Optimized for AVR size. This function is only called very
                // infrequently so size matters more than speed.
                fl::u32 work = (((fl::u16)cc) + 1);
                work *= (((fl::u16)ct) + 1);
                work *= scale;
                work /= 0x10000L;
                adj.raw[i] = work & 0xFF;
            }
        }
    }
    return adj;
#endif
}
