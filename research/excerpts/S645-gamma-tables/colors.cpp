// gamma lookup tables used for color correction (filled on 1st use (cfg.cpp & set.cpp))
uint8_t NeoGammaWLEDMethod::gammaT[256];
uint8_t NeoGammaWLEDMethod::gammaT_inv[256];

// re-calculates & fills gamma tables
void NeoGammaWLEDMethod::calcGammaTable(float gamma)
{
  float gamma_inv = 1.0f / gamma; // inverse gamma
  for (size_t i = 1; i < 256; i++) {
    gammaT[i] = (int)(powf((float)i / 255.0f, gamma) * 255.0f + 0.5f);
    gammaT_inv[i] = (int)(powf(((float)i - 0.5f) / 255.0f, gamma_inv) * 255.0f + 0.5f);
    //DEBUG_PRINTF_P(PSTR("gammaT[%d] = %d gammaT_inv[%d] = %d\n"), i, gammaT[i], i, gammaT_inv[i]);
  }
  gammaT[0] = 0;
  gammaT_inv[0] = 0;
}

uint8_t NeoGammaWLEDMethod::Correct(uint8_t value)
{
  if (!gammaCorrectCol) return value;
  return gammaT[value];
}

uint32_t NeoGammaWLEDMethod::inverseGamma32(uint32_t color)
{
  if (!gammaCorrectCol) return color;
  uint8_t w = W(color);
  uint8_t r = R(color);
  uint8_t g = G(color);
  uint8_t b = B(color);
  w = gammaT_inv[w];
  r = gammaT_inv[r];
  g = gammaT_inv[g];
  b = gammaT_inv[b];
  return RGBW32(r, g, b, w);
}
