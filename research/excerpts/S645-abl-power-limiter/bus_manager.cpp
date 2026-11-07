//The following function attemps to calculate the current LED power usage,
//and will limit the brightness to stay below a set amperage threshold.
//It is NOT a measurement and NOT guaranteed to stay within the ablMilliampsMax margin.
//Stay safe with high amperage and have a reasonable safety margin!
//I am NOT to be held liable for burned down garages or houses!

// note on ABL implementation:
// ABL is set up in finalizeInit()
// scaled color channels are summed in BusDigital::setPixelColor()
// the used current is estimated and limited in BusManager::show()
// if limit is set too low, brightness is limited to 1 to at least show some light
// to disable brightness limiter for a bus, set LED current to 0

void BusDigital::estimateCurrent() {
  uint32_t actualMilliampsPerLed = _milliAmpsPerLed;
  if (_milliAmpsPerLed == 255) {
    // use wacky WS2815 power model, see WLED issue #549
    _colorSum *= 3; // sum is sum of max value for each color, need to multiply by three to account for clrUnitsPerChannel being 3*255
    actualMilliampsPerLed = 12; // from testing an actual strip
  }
  // _colorSum has all the values of color channels summed, max would be getLength()*(3*255 + (255 if hasWhite()): convert to milliAmps
  uint32_t clrUnitsPerChannel = hasWhite() ? 4*255 : 3*255;
  _milliAmpsTotal = ((uint64_t)_colorSum * actualMilliampsPerLed) / clrUnitsPerChannel + getLength(); // add 1mA standby current per LED to total (WS2812: ~0.7mA, WS2815: ~2mA)
}

void BusDigital::applyBriLimit(uint8_t newBri) {
  // a newBri of 0 means calculate per-bus brightness limit
  _NPBbri = 255; // reset, intermediate value is set below, final value is calculated in bus::show()
  if (newBri == 0) {
    if (_milliAmpsLimit == 0 || _milliAmpsTotal == 0) return; // ABL not used for this bus
    newBri = 255;

    if (_milliAmpsLimit > getLength()) { // each LED uses about 1mA in standby
      if (_milliAmpsTotal > _milliAmpsLimit) {
        // scale brightness down to stay in current limit
        newBri = ((uint32_t)_milliAmpsLimit * 255) / _milliAmpsTotal + 1; // +1 to avoid 0 brightness
        _milliAmpsTotal = _milliAmpsLimit;
      }
    } else {
      newBri = 1; // limit too low, set brightness to 1, this will dim down all colors to minimum since we use video scaling
      _milliAmpsTotal = getLength(); // estimate bus current as minimum
    }
  }

  if (newBri < 255) {
    _NPBbri = newBri; // store value so it can be updated in show() (must be updated even if ABL is not used)
    uint16_t wwcw = 0;
    unsigned hwLen = _len;
    if (_type == TYPE_WS2812_1CH_X3) hwLen = NUM_ICS_WS2812_1CH_3X(_len); // only needs a third of "RGB" LEDs for NeoPixelBus
    for (unsigned i = 0; i < hwLen; i++) {
      uint8_t co = _colorOrderMap.getPixelColorOrder(i+_start, _colorOrder); // need to revert color order for correct color scaling and CCT calc in case white is swapped
      uint32_t c = PolyBus::getPixelColor(_busPtr, _iType, i, co); // Note: if ABL would be calculated as a seperate loop (as it was before) it is slower but could use original color, making it more color-accurate
      if (hasCCT()) {
        uint8_t cctWW, cctCW;
        Bus::calculateCCT(c, cctWW, cctCW); // calculate CCT before fade (more accurate) | Note: if using "accurate" white calculation mode, approximateKelvinFromRGB can be very inaccurate (white is subtracted)
        wwcw = ((cctCW + 1) * newBri) & 0xFF00; // apply brightness to CCT (leave it in upper byte for 16bit NeoPixelBus value)
        wwcw |= ((cctWW + 1) * newBri) >> 8;
      }
      c = color_fade(c, newBri, true); // apply additional dimming  note: using inline version is a bit faster but overhead of getPixelColor() dominates the speed impact by far
      PolyBus::setPixelColor(_busPtr, _iType, i, c, co, wwcw); // repaint all pixels with new brightness
    }
  }

  _colorSum = 0; // reset for next frame
}

void BusDigital::show() {
  if (!_valid) return;
  _NPBbri = (_NPBbri * _bri) / 255;      // total applied brightness for use in restoreColorLossy (see applyBriLimit())
  PolyBus::show(_busPtr, _iType, _skip); // faster if buffer consistency is not important (no skipped LEDs)
}

bool BusDigital::canShow() const {
  if (!_valid) return true;
  return PolyBus::canShow(_busPtr, _iType);
}

//If LEDs are skipped, it is possible to use the first as a status LED.
//TODO only show if no new show due in the next 50ms
void BusDigital::setStatusPixel(uint32_t c) {
  if (_valid && _skip) {
    PolyBus::setPixelColor(_busPtr, _iType, 0, c, _colorOrderMap.getPixelColorOrder(_start, _colorOrder));
    if (canShow()) PolyBus::show(_busPtr, _iType);
  }
}

// note: using WLED_O2_ATTR makes this function ~7% faster at the expense of 600 bytes of flash
void IRAM_ATTR BusDigital::setPixelColor(unsigned pix, uint32_t c) {
  if (!_valid) return;
  if (Bus::_cct >= 1900) c = colorBalanceFromKelvin(Bus::_cct, c); //color correction from CCT
  uint8_t cctWW = 0, cctCW = 0;
  uint16_t wwcw = 0;
  if (hasWhite()) c = autoWhiteCalc(c, cctWW, cctCW);
  c = color_fade(c, _bri, true); // apply brightness

  if (hasCCT()) {
    wwcw = ((cctCW + 1) * _bri) & 0xFF00; // apply brightness to CCT (store CW in upper byte)
    wwcw |= ((cctWW + 1) * _bri) >> 8;
    if (_type == TYPE_WS2812_WWA) c = RGBW32(wwcw, wwcw >> 8, 0, W(c)); // ww,cw, 0, w
  }

  if (BusManager::_useABL) {
    // if using ABL, sum all color channels to estimate current and limit brightness in show()
    uint8_t r = R(c), g = G(c), b = B(c);
    if (_milliAmpsPerLed < 255) { // normal ABL
      _colorSum += r + g + b + W(c);
    } else { // wacky WS2815 power model, ignore white channel, use max of RGB (issue #549)
      _colorSum += ((r > g) ? ((r > b) ? r : b) : ((g > b) ? g : b));
    }
  }

  if (_reversed) pix = _len - pix -1;
  pix += _skip;
  const uint8_t co = _colorOrderMap.getPixelColorOrder(pix+_start, _colorOrder);
  if (_type == TYPE_WS2812_1CH_X3) { // map to correct IC, each controls 3 LEDs
    unsigned pOld = pix;
    pix = IC_INDEX_WS2812_1CH_3X(pix);
    uint32_t cOld = PolyBus::getPixelColor(_busPtr, _iType, pix, co);
    switch (pOld % 3) { // change only the single channel (TODO: this can cause loss because of get/set)
      case 0: c = RGBW32(R(cOld), W(c)   , B(cOld), 0); break;
      case 1: c = RGBW32(W(c)   , G(cOld), B(cOld), 0); break;
      case 2: c = RGBW32(R(cOld), G(cOld), W(c)   , 0); break;
    }
  }

  PolyBus::setPixelColor(_busPtr, _iType, pix, c, co, wwcw);
}
