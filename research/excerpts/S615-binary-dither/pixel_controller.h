// ============================================================================
// TEMPORAL DITHERING OVERVIEW
// ============================================================================
//
// Temporal dithering recovers fractional brightness precision lost to integer
// quantization by varying pixel values across frames. At refresh rates above
// ~50Hz, human vision integrates these variations, perceiving the true
// fractional brightness.
//
// THE PROBLEM:
//   Integer scaling causes color shifts at low brightness. For example:
//     CRGB(100, 60, 20) at 20% brightness â†’ RGB(19, 11, 3)
//   Each channel loses different fractional precision, distorting the color.
//
// THE SOLUTION:
//   Add frame-varying noise BEFORE scaling, causing different rounding outcomes:
//     Frame 1: scale8(100+0, 51) = 19
//     Frame 2: scale8(100+3, 51) = 20  â† noise pushed over threshold
//   Your eye averages these to perceive the correct fractional brightness.
//
// THE ALGORITHM:
//   1. Frame counter R cycles 0-7, creating an 8-frame pattern
//   2. Bit-reverse R to Q (0â†’0, 1â†’128, 2â†’64...) to distribute pattern temporally
//   3. Center pattern: Q += 16
//   4. Scale per channel: e[i] = 256/brightness, d[i] = scale8(Q, e[i])
//      Lower brightness needs BIGGER dither to compensate for larger % error
//   5. Toggle between pixels: d[i] = e[i] - d[i] (spatial distribution)
//   6. Apply: pixel = scale8(qadd8(pixel, d[i]), brightness)
//
// VIRTUAL BITS:
//   8-frame cycle at 400Hz = 50Hz complete cycle â†’ +3 "virtual" bits
//   Result: 8-bit hardware provides 11-bit perceived precision (0-2047 levels)
//
// DISABLE FOR:
//   - Cameras/photography (captures individual frames, sees flicker)
//   - Slow refresh <50Hz (visible flickering)
//   - Video recording (frame rate mismatches create artifacts)
//   Use: FastLED.setDither(DISABLE_DITHER)
//
// NOTE: This is NOT gamma correction. Dithering is pure temporal averaging
// to recover quantization precision. See init_binary_dithering() below.
//
// ============================================================================

#if !defined(NO_DITHERING) || (NO_DITHERING != 1)

/// Predicted max update rate, in Hertz
#define MAX_LIKELY_UPDATE_RATE_HZ     400

/// Minimum acceptable dithering rate, in Hertz
#define MIN_ACCEPTABLE_DITHER_RATE_HZ  50

/// The number of updates in a single dither cycle
#define UPDATES_PER_FULL_DITHER_CYCLE (MAX_LIKELY_UPDATE_RATE_HZ / MIN_ACCEPTABLE_DITHER_RATE_HZ)

/// Set "virtual bits" of dithering to the highest level
/// that is not likely to cause excessive flickering at
/// low brightness levels + low update rates. 
/// These pre-set values are a little ambitious, since
/// a 400Hz update rate for WS2811-family LEDs is only
/// possible with 85 pixels or fewer.
/// Once we have a "number of milliseconds since last update"
/// value available here, we can quickly calculate the correct
/// number of "virtual bits" on the fly with a couple of "if"
/// statements -- no division required.  At this point,
/// the division is done at compile time, so there's no runtime
/// cost, but the values are still hard-coded.
/// @todo Can these macros be replaced with constants scoped to PixelController::init_binary_dithering()?
#define RECOMMENDED_VIRTUAL_BITS ((UPDATES_PER_FULL_DITHER_CYCLE>1) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>2) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>4) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>8) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>16) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>32) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>64) + \
                                  (UPDATES_PER_FULL_DITHER_CYCLE>128) )

/// Alias for RECOMMENDED_VIRTUAL_BITS
#define VIRTUAL_BITS RECOMMENDED_VIRTUAL_BITS

#endif
    /// Set up the values for binary dithering
    /// @see "TEMPORAL DITHERING: THE COMPLETE GUIDE" section above (line 195)
    void init_binary_dithering() {
#if !defined(NO_DITHERING) || (NO_DITHERING != 1)
        // STEP 1: Increment frame counter (creates temporal variation)
        static fl::u8 R = 0; // okay static in header
        ++R;

        // STEP 2: Wrap counter at 2^ditherBits (creates 8-frame cycle: 0,1,2,3,4,5,6,7,0...)
        fl::u8 ditherBits = VIRTUAL_BITS;
        R &= (0x01 << ditherBits) - 1;

        // STEP 3: Bit-reverse R to create maximally-spaced pattern Q
        // Why? Prevents visible ramping patterns. Turns 0,1,2,3,4,5,6,7 â†’ 0,128,64,192,32,160,96,224
        fl::u8 Q = 0;

        // Bit reversal magic: mirrors bit positions (bit 0 â†” bit 7, bit 1 â†” bit 6, etc.)
        {
            if(R & 0x01) { Q |= 0x80; }
            if(R & 0x02) { Q |= 0x40; }
            if(R & 0x04) { Q |= 0x20; }
            if(R & 0x08) { Q |= 0x10; }
            if(R & 0x10) { Q |= 0x08; }
            if(R & 0x20) { Q |= 0x04; }
            if(R & 0x40) { Q |= 0x02; }
            if(R & 0x80) { Q |= 0x01; }
        }

        // STEP 4: Center the pattern (shifts values to middle of quantization bins)
        // Example: 0,128,64,192 becomes 16,144,80,208 (adds 16 when ditherBits=3)
        if( ditherBits < 8) {
            Q += 0x01 << (7 - ditherBits);
        }

        // STEP 5: Scale per-channel based on brightness
        // Key insight: Lower brightness needs BIGGER dithering offsets!
        // e[i] = max dither range (inversely proportional to brightness)
        // d[i] = current dither offset (Q scaled by e[i])
        for(int i = 0; i < 3; ++i) {
                fl::u8 s = mColorAdjustment.premixed.raw[i];  // Brightness scale factor

                // Calculate max dither range: e = 256/brightness
                // At 100% (255): eâ‰ˆ1 (tiny range), At 20% (51): eâ‰ˆ5 (large range)
                e[i] = s ? (256/s) + 1 : 0;

                // Scale Q by the dither range to get current offset
                d[i] = fl::scale8(Q, e[i]);

#if (FASTLED_SCALE8_FIXED == 1)
                // Adjust for scale8 implementation quirk
                if(d[i]) (--d[i]);
#endif
                // Finalize e[i] value for later toggling
                if(e[i]) --e[i];
        }
#endif
    }
    /// Step the dithering forward - creates triangular wave that toggles between pixels
    /// @note If updating here, be sure to update the asm version in clockless_avr.h!
    FASTLED_FORCE_INLINE void stepDithering() {
            // Toggles d between two values: if d=2 and e=5, becomes 3, then back to 2, etc.
            // This spreads dithering spatially along the strip, preventing visible patterns
            d[0] = e[0] - d[0];
            d[1] = e[1] - d[1];
            d[2] = e[2] - d[2];
    }

    /// Some chipsets pre-cycle the first byte, which means we want to cycle byte 0's dithering separately
    FASTLED_FORCE_INLINE void preStepFirstByteDithering() {
        d[RO(0)] = e[RO(0)] - d[RO(0)];
    }
    /// Add dither offset to pixel value (BEFORE scaling). Black pixels not dithered.
    /// @tparam SLOT The data slot in the output stream
    /// @param pc reference to the pixel controller
    /// @param b the color byte to dither
    /// @returns b + dither offset, clamped to 255
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 dither(PixelController & pc, fl::u8 b) { return b ? fl::qadd8(b, pc.d[RO(SLOT)]) : 0; }

    /// Add explicit dither offset to pixel value (BEFORE scaling). Black pixels not dithered.
    /// @tparam SLOT The data slot in the output stream
    /// @param b the color byte to dither
    /// @param d dither offset to add
    /// @returns b + d, clamped to 255
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 dither(PixelController & , fl::u8 b, fl::u8 d) { return b ? fl::qadd8(b,d) : 0; }

    /// Scale a value using the per-channel scale data
    /// @tparam SLOT The data slot in the output stream. This is used to select which byte of the output stream is being processed.
    /// @param pc reference to the pixel controller
    /// @param b the color byte to scale
    /// @see PixelController::mScale
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 scale(PixelController & pc, fl::u8 b) { return fl::scale8(b, pc.mColorAdjustment.premixed.raw[RO(SLOT)]); }
    
    /// Scale a value
    /// @tparam SLOT The data slot in the output stream. This is used to select which byte of the output stream is being processed.
    /// @param b the byte to scale
    /// @param scale the scale value
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 scale(PixelController & , fl::u8 b, fl::u8 scale) { return fl::scale8(b, scale); }

    /// @name Composite shortcut functions for loading, dithering, and scaling
    /// These composite functions will load color data, dither it, and scale it
    /// all at once so that it's ready for the output controller to send to the
    /// LEDs.
    /// @{


    /// Complete pipeline: load â†’ dither â†’ scale (THE MAGIC HAPPENS HERE!)
    /// Order is critical: pixel + dither FIRST, then scale by brightness
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 loadAndScale(PixelController & pc) {
        return scale<SLOT>(pc, pc.dither<SLOT>(pc, pc.loadByte<SLOT>(pc)));
    }

    /// Complete pipeline: load â†’ dither â†’ scale (parallel output version)
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 loadAndScale(PixelController & pc, int lane) {
        return scale<SLOT>(pc, pc.dither<SLOT>(pc, pc.loadByte<SLOT>(pc, lane)));
    }

    /// Complete pipeline: load â†’ dither â†’ scale (explicit dither/scale values)
    template<int SLOT>  FASTLED_FORCE_INLINE static fl::u8 loadAndScale(PixelController & pc, int lane, fl::u8 d, fl::u8 scale) {
        return fl::scale8(pc.dither<SLOT>(pc, pc.loadByte<SLOT>(pc, lane), d), scale);
    }
