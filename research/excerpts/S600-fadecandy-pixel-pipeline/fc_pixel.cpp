/*
 * EXCERPT — see LICENSE-NOTE.md. Function updatePixel() from firmware/fc_pixel.cpp
 * at PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d, lines 25-89.
 * Compiled 4x with FCP_INTERPOLATION/FCP_DITHERING = 0/1; FCP_FN suffixes the name.
 * residual_t is int16_t (fadecandy.cpp L45); pResidual points at this pixel's
 * 3 channels of the 1536-entry residual array.
 */

static uint32_t FCP_FN(updatePixel)(uint32_t icPrev, uint32_t icNext,
    const uint8_t *pixelPrev, const uint8_t *pixelNext, residual_t *pResidual)
{
    /*
     * Update pipeline for one pixel:
     *
     *    1. Interpolate framebuffer
     *    2. Interpolate LUT
     *    3. Dithering
     *
     * icPrev in range [0, 0x1010000]
     * icNext in range [0, 0x1010000]
     * icPrev + icNext = 0x1010000
     */

#if FCP_INTERPOLATION
    // Per-channel linear interpolation and conversion to 16-bit color.
    // Result range: [0, 0xFFFF]
    int iR = (pixelPrev[0] * icPrev + pixelNext[0] * icNext) >> 16;
    int iG = (pixelPrev[1] * icPrev + pixelNext[1] * icNext) >> 16;
    int iB = (pixelPrev[2] * icPrev + pixelNext[2] * icNext) >> 16;
#else
    int iR = pixelNext[0] * 0x101;
    int iG = pixelNext[1] * 0x101;
    int iB = pixelNext[2] * 0x101;
#endif

    // Pass through our color LUT
    // Result range: [0, 0xFFFF]
    iR = FCP_FN(lutInterpolate)(buffers.lutCurrent.r, iR);
    iG = FCP_FN(lutInterpolate)(buffers.lutCurrent.g, iG);
    iB = FCP_FN(lutInterpolate)(buffers.lutCurrent.b, iB);

#if FCP_DITHERING
    // Incorporate the residual from last frame
    iR += pResidual[0];
    iG += pResidual[1];
    iB += pResidual[2];
#endif

    /*
     * Round to the nearest 8-bit value. Clamping is necessary!
     * This value might be as low as -128 prior to adding 0x80
     * for rounding. After this addition, the result is guaranteed
     * to be >= 0, but it may be over 0xffff.
     *
     * This rules out clamping using the UQADD16 instruction,
     * since the addition itself needs to allow overflow. Instead,
     * we clamp using a separate USAT instruction.
     */

    int r8 = __USAT(iR + 0x80, 16) >> 8;
    int g8 = __USAT(iG + 0x80, 16) >> 8;
    int b8 = __USAT(iB + 0x80, 16) >> 8;

#if FCP_DITHERING
    // Compute the error, after expanding the 8-bit value back to 16-bit.
    pResidual[0] = iR - (r8 * 257);
    pResidual[1] = iG - (g8 * 257);
    pResidual[2] = iB - (b8 * 257);
#endif

    // Pack the result, in GRB order.
    return (g8 << 16) | (r8 << 8) | b8;
}
