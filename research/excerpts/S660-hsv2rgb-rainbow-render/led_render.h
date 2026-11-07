// Render float HSV to LEDs with "Rainbow" color transform from FastLED
uint32_t render_hsv2rgb_rainbow_float(color_hsv_float hsv, color_rgb corr_rgb,
                                      float saturation, float brightness,
                                      uint8_t has_white) {
  uint8_t hue = fmod(hsv.hue, 1.0) * 255.0;
  uint8_t sat = hsv.sat * saturation * 255.0;
  uint8_t val = (hsv.val * hsv.val) * 255;
  if (val > 0 && val < 255) val += 1;
  val = scale_8(val, brightness * 255);
  uint8_t r, g, b, w;

  w = 0;

  uint8_t offset = hue & 0x1F; // 0..31
  uint8_t offset8 = offset << 3;
  uint8_t third = offset8 / 3;

  if (!(hue & 0x80)) {
    if (!(hue & 0x40)) {
      // section 0-1
      if (!(hue & 0x20)) {
        // case 0: // R -> O
        r = 255 - third;
        g = third;
        b = 0;
      } else {
        // case 1: // O -> Y
        r = 171;
        g = 85 + third;
        b = 0;
      }
    } else {
      // section 2-3
      if (!(hue & 0x20)) {
        // case 2: // Y -> G
        r = 171 - third * 2;
        g = 170 + third;
        b = 0;
      } else {
        // case 3: // G -> A
        r = 0;
        g = 255 - third;
        b = third;
      }
    }
  } else {
    // section 4-7
    if (!(hue & 0x40))  {
      if (!(hue & 0x20)) {
        // case 4: // A -> B
        r = 0;
        uint8_t twothirds = third * 2;
        g = 171 - twothirds; // K170?
        b = 85 + twothirds;
      } else {
        // case 5: // B -> P
        r = third;
        g = 0;
        b = 255 - third;
      }
    } else {
      if (!(hue & 0x20)) {
        // case 6: // P -- K
        r = 85 + third;
        g = 0;
        b = 171 - third;
      } else {
        // case 7: // K -> R
        r = 170 + third;
        g = 0;
        b = 85 - third;
      }
    }
  }

  // Scale down colors if we're desaturated at all
  // and add the brightness_floor to r, g, and b.
  if (has_white) {
    if (sat != 255) {
      if (sat == 0) {
        r = 0;
        b = 0;
        g = 0;
        w = 255;
      } else {
        uint8_t desat = 255 - sat;
        desat = scale_8(desat, desat);
        r = scale_8(r, sat);
        g = scale_8(g, sat);
        b = scale_8(b, sat);
        w = desat;
      }
    }
  } else {
    if (sat != 255) {
      if (sat == 0) {
        r = 255;
        b = 255;
        g = 255;
      } else {
        uint8_t desat = 255 - sat;
        desat = scale_8(desat, desat);
        r = scale_8(r, sat) + desat;
        g = scale_8(g, sat) + desat;
        b = scale_8(b, sat) + desat;
      }
    }
    /*
    if (gamma != 1) {
      r = pow((float)r / 255.0, gamma) * 255;
      g = pow((float)g / 255.0, gamma) * 255;
      b = pow((float)b / 255.0, gamma) * 255;
    }
    */
  }

  // Now scale everything down if we're at value < 255.
  if (val != 255) {
    if (val == 0) {
      r = 0;
      g = 0;
      b = 0;
      w = 0;
    } else {
      r = scale_8(r, val);
      g = scale_8(g, val);
      b = scale_8(b, val);
      w = scale_8(w, val);
    }
  }

  r = scale_8(r, corr_rgb.r);
  g = scale_8(g, corr_rgb.g);
  b = scale_8(b, corr_rgb.b);

  if (debug) printf("%d %d %d %d\n", r, g, b, w);
  return pack_rgbw(r, g, b, w);
}
