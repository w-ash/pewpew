// Excerpt from PimentNoir/fadecandy@36f616158f195a327f8486474af2956dad52881d
// server/src/fcdevice.cpp lines 235-360, 362-382, verbatim. MIT; Copyright (c) 2013 Micah Elizabeth Scott.
// Source entry [S600]. See LICENSE-NOTE.md.
// lines 235-360
void FCDevice::writeColorCorrection(const Value &color)
{
    /*
     * Populate the color correction table based on a JSON configuration object,
     * and send the new color LUT out over USB.
     *
     * 'color' may be 'null' to load an identity-mapped LUT, or it may be
     * a dictionary of options including 'gamma' and 'whitepoint'.
     *
     * This calculates a compound curve with a linear section and a nonlinear
     * section. The linear section, near zero, avoids creating very low output
     * values that will cause distracting flicker when dithered. This isn't a problem
     * when the LEDs are viewed indirectly such that the flicker is below the threshold
     * of perception, but in cases where the flicker is a problem this linear section can
     * eliminate it entierly at the cost of some dynamic range.
     *
     * By default, the linear section is disabled (linearCutoff is zero). To enable the
     * linear section, set linearCutoff to some nonzero value. A good starting point is
     * 1/256.0, correspnding to the lowest 8-bit PWM level.
     */

    // Default color LUT parameters
    double gamma = 1.0;                         // Power for nonlinear portion of curve
    double whitepoint[3] = {1.0, 1.0, 1.0};     // White-point RGB value (also, global brightness)
    double linearSlope = 1.0;                   // Slope (output / input) of linear section of the curve, near zero
    double linearCutoff = 0.0;                  // Y (output) coordinate of intersection of linear and nonlinear curves

    /*
     * Parse the JSON object
     */

    if (color.IsObject()) {
        const Value &vGamma = color["gamma"];
        const Value &vWhitepoint = color["whitepoint"];
        const Value &vLinearSlope = color["linearSlope"];
        const Value &vLinearCutoff = color["linearCutoff"];

        if (vGamma.IsNumber()) {
            gamma = vGamma.GetDouble();
        } else if (!vGamma.IsNull() && mVerbose) {
            std::clog << "Gamma value must be a number.\n";
        }

        if (vLinearSlope.IsNumber()) {
            linearSlope = vLinearSlope.GetDouble();
        } else if (!vLinearSlope.IsNull() && mVerbose) {
            std::clog << "Linear slope value must be a number.\n";
        }

        if (vLinearCutoff.IsNumber()) {
            linearCutoff = vLinearCutoff.GetDouble();
        } else if (!vLinearCutoff.IsNull() && mVerbose) {
            std::clog << "Linear slope value must be a number.\n";
        }

        if (vWhitepoint.IsArray() &&
            vWhitepoint.Size() == 3 &&
            vWhitepoint[0u].IsNumber() &&
            vWhitepoint[1].IsNumber() &&
            vWhitepoint[2].IsNumber()) {
            whitepoint[0] = vWhitepoint[0u].GetDouble();
            whitepoint[1] = vWhitepoint[1].GetDouble();
            whitepoint[2] = vWhitepoint[2].GetDouble();
        } else if (!vWhitepoint.IsNull() && mVerbose) {
            std::clog << "Whitepoint value must be a list of 3 numbers.\n";
        }

    } else if (!color.IsNull() && mVerbose) {
        std::clog << "Color correction value must be a JSON dictionary object.\n";
    }

    /*
     * Calculate the color LUT, stowing the result in an array of USB packets.
     */

    Packet *packet = mColorLUT;
    const unsigned firstByteOffset = 1;  // Skip padding byte
    unsigned byteOffset = firstByteOffset;

    for (unsigned channel = 0; channel < 3; channel++) {
        for (unsigned entry = 0; entry < LUT_ENTRIES; entry++) {
            double output;

            /*
             * Normalized input value corresponding to this LUT entry.
             * Ranges from 0 to slightly higher than 1. (The last LUT entry
             * can't quite be reached.)
             */
            double input = (entry << 8) / 65535.0;

            // Scale by whitepoint before anything else
            input *= whitepoint[channel];

            // Is this entry part of the linear section still?
            if (input * linearSlope <= linearCutoff) {

                // Output value is below linearCutoff. We're still in the linear portion of the curve
                output = input * linearSlope;

            } else {

                // Nonlinear portion of the curve. This starts right where the linear portion leaves
                // off. We need to avoid any discontinuity.

                double nonlinearInput = input - (linearSlope * linearCutoff);
                double scale = 1.0 - linearCutoff;
                output = linearCutoff + pow(nonlinearInput / scale, gamma) * scale;
            }

            // Round to the nearest integer, and clamp. Overflow-safe.
            int64_t longValue = (output * 0xFFFF) + 0.5;
            int intValue = std::max<int64_t>(0, std::min<int64_t>(0xFFFF, longValue));

            // Store LUT entry, little-endian order.
            packet->data[byteOffset++] = uint8_t(intValue);
            packet->data[byteOffset++] = uint8_t(intValue >> 8);
            if (byteOffset >= sizeof packet->data) {
                byteOffset = firstByteOffset;
                packet++;
            }
        }
    }

    // Start asynchronously sending the LUT.
    submitTransfer(new Transfer(this, &mColorLUT, sizeof mColorLUT));
}
// lines 362-382
void FCDevice::writeFramebuffer()
{
    /*
     * Asynchronously write the current framebuffer.
     *
     * TODO: Currently if this gets ahead of what the USB device is capable of,
     *       we always drop frames. Alternatively, it would be nice to have end-to-end
     *       flow control so that the client can produce frames slower.
     */

    if (mNumFramesPending >= MAX_FRAMES_PENDING) {
        // Too many outstanding frames. Wait to submit until a previous frame completes.
        mFrameWaitingForSubmit = true;
        return;
    }

    if (submitTransfer(new Transfer(this, &mFramebuffer, sizeof mFramebuffer, FRAME))) {
        mFrameWaitingForSubmit = false;
        mNumFramesPending++;
    }
}
