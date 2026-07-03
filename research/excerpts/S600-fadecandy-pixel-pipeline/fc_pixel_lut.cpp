/*
 * EXCERPT — see LICENSE-NOTE.md. Function lutInterpolate() from
 * firmware/fc_pixel_lut.cpp at
 * PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d, lines 26-86.
 * The LUT is 257 uint16 entries per channel, each pre-shifted right by 1
 * (15-bit) at upload time (fc_usb.cpp finalizeLUT, L127-L140) so the pair
 * multiply fits the signed SMUAD path.
 */

ALWAYS_INLINE static inline
uint32_t FCP_FN(lutInterpolate)(const uint16_t *lut, uint32_t arg)
{
    /*
     * Using our color LUT for the indicated channel, convert the
     * 16-bit intensity "arg" in our input colorspace to a corresponding
     * 16-bit intensity in the device colorspace.
     *
     * Remember that our LUT is 257 entries long. The final entry corresponds to an
     * input of 0x10000, which can't quite be reached.
     *
     * 'arg' is in the range [0, 0xFFFF]
     *
     * This operation is equivalent to the following:
     *
     *      unsigned index = arg >> 8;          // Range [0, 0xFF]
     *      unsigned alpha = arg & 0xFF;        // Range [0, 0xFF]
     *      unsigned invAlpha = 0x100 - alpha;  // Range [1, 0x100]
     *
     *      // Result in range [0, 0xFFFF]
     *      return (lut[index] * invAlpha + lut[index + 1] * alpha) >> 8;
     *
     * This is easy to understand, but it turns out to be a serious bottleneck
     * in terms of speed and memory bandwidth, as well as register pressure that
     * affects the compilation of updatePixel().
     *
     * To speed this up, we try and do the lut[index] and lut[index+1] portions
     * in parallel using the SMUAD instruction. This is a pair of 16x16 multiplies,
     * and the results are added together. We can combine this with an unaligned load
     * to grab two adjacent entries from the LUT. The remaining complications are:
     *
     *   1. We wanted unsigned, not signed
     *   2. We still need to generate the input values efficiently.
     *
     * (1) is easy to solve if we're okay with 15-bit precision for the LUT instead
     * of 16-bit, which is fine. During LUT preparation, we right-shift each entry
     * by 1, keeping them within the positive range of a signed 16-bit int.
     *
     * For (2), we need to quickly put 'alpha' in the high halfword and invAlpha in
     * the low halfword, or vice versa. One fast way to do this is (0x01000000 + x - (x << 16).
     */

#if FCP_INTERPOLATION

    uint32_t index = arg >> 8;          // Range [0, 0xFF]

    // Load lut[index] into low halfword, lut[index+1] into high halfword.
    uint32_t pair = *(const uint32_t*)(lut + index);

    unsigned alpha = arg & 0xFF;        // Range [0, 0xFF]

    // Reversed halfword order
    uint32_t pairAlpha = (0x01000000 + alpha - (alpha << 16));

    return __SMUADX(pairAlpha, pair) >> 7;

#else
    // Simpler non-interpolated version
    return lut[arg >> 8] << 1;
#endif
}
