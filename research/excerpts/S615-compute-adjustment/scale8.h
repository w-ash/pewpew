/// Scale one byte by a second one (C implementation)
FL_ALWAYS_INLINE u8 scale8(u8 i, fract8 scale) FL_NO_EXCEPT {
#if (FASTLED_SCALE8_FIXED == 1)
    return (((u16)i) * (1 + (u16)(scale))) >> 8;
#else
    return ((u16)i * (u16)(scale)) >> 8;
#endif
}

constexpr u8 scale8_constexpr(u8 i, fract8 scale) FL_NO_EXCEPT {
    return (((u16)i) * (1 + (u16)(scale))) >> 8;
}

/// The "video" version of scale8() (C implementation)
FL_ALWAYS_INLINE u8 scale8_video(u8 i, fract8 scale) FL_NO_EXCEPT {
    u8 j = (((int)i * (int)scale) >> 8) + ((i && scale) ? 1 : 0);
    return j;
}
