// Excerpt from FastLED/FastLED@8df8258c86200112b2c9e917b4b3fec5d19a946e
// src/fl/chipsets/hd108.h lines 59-88, verbatim. MIT; FastLED contributors (Daniel Garcia, Mark Kriegsman, Zach Vorhies et al.).
// Source entry [S615]. See LICENSE-NOTE.md.
// lines 59-88
    while (pixels.has(1)) {
        // Load and scale pixel data in OUTPUT order (respects RGB_ORDER template parameter)
        fl::u8 c0_8, c1_8, c2_8;
        pixels.loadAndScaleRGB(&c0_8, &c1_8, &c2_8);

        // Apply gamma correction (2.8) to convert 8-bit to 16-bit for HD108
        // This provides smooth perceptual brightness transitions across the full 65K range
        // Note: Brightness scaling is applied by loadAndScaleRGB() before gamma correction
        fl::u16 c0_16 = fl::gamma_2_8(c0_8);
        fl::u16 c1_16 = fl::gamma_2_8(c1_8);
        fl::u16 c2_16 = fl::gamma_2_8(c2_8);

        // Header bytes: HD108 per-channel gain control encoding
        // f0: [1][RRRRR][GG] - marker bit, 5-bit R gain, 2 MSBs of G gain
        // f1: [GGG][BBBBB]   - 3 LSBs of G gain, 5-bit B gain
        // Use maximum gain (31) for all channels to maximize precision
        // Brightness control via 16-bit PWM values (already applied via loadAndScaleRGB)
        constexpr fl::u8 r_gain = 31, g_gain = 31, b_gain = 31;
        constexpr fl::u8 f0 = fl::u8(0x80 | ((r_gain & 0x1F) << 2) | ((g_gain >> 3) & 0x03));
        constexpr fl::u8 f1 = fl::u8(((g_gain & 0x07) << 5) | (b_gain & 0x1F));

        // Transmit LED frame: 2 header bytes + 6 color bytes (16-bit, big-endian, in RGB_ORDER)
        mSPI.writeByte(f0);
        mSPI.writeByte(f1);
        mSPI.writeByte(fl::u8(c0_16 >> 8)); mSPI.writeByte(fl::u8(c0_16 & 0xFF));  // Channel 0 MSB, LSB
        mSPI.writeByte(fl::u8(c1_16 >> 8)); mSPI.writeByte(fl::u8(c1_16 & 0xFF));  // Channel 1 MSB, LSB
        mSPI.writeByte(fl::u8(c2_16 >> 8)); mSPI.writeByte(fl::u8(c2_16 & 0xFF));  // Channel 2 MSB, LSB

        pixels.stepDithering();
        pixels.advanceData();
