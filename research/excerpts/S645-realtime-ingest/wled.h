// Excerpt from wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63
// wled00/wled.h lines 453-454, verbatim. EUPL v1.2 or later; Copyright (c) 2016 Harm Aldick; (c) 2016-present Christian Schwinne and individual WLED contributors.
// Source entry [S645]. See LICENSE-NOTE.md.
// lines 453-454
WLED_GLOBAL bool arlsDisableGammaCorrection _INIT(true);          // activate if gamma correction is handled by the source
WLED_GLOBAL bool arlsForceMaxBri _INIT(false);                    // enable to force max brightness if source has very dark colors that would be black
