// Excerpt from wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63
// wled00/udp.cpp lines 410-456, verbatim. EUPL v1.2 or later; Copyright (c) 2016 Harm Aldick; (c) 2016-present Christian Schwinne and individual WLED contributors.
// Source entry [S645]. See LICENSE-NOTE.md.
// lines 410-456
// realtimeLock() is called from UDP notifications, JSON API or serial Ada
void realtimeLock(uint32_t timeoutMs, byte md)
{
  if (!realtimeMode && !realtimeOverride) {
    if (useMainSegmentOnly) {
      Segment& mainseg = strip.getMainSegment();
      mainseg.clear(); // clear entire segment (in case sender transmits less pixels)
      mainseg.freeze = true;
      // if WLED was off and using main segment only, freeze non-main segments so they stay off
      if (bri == 0) {
        for (size_t s = 0; s < strip.getSegmentsNum(); s++) strip.getSegment(s).freeze = true;
      }
    } else {
      // clear entire strip
      strip.fill(BLACK);
    }
    // if strip is off (bri==0) and not already in RTM
    if (briT == 0) {
      strip.setBrightness(briLast, true);
    }
  }

  if (realtimeTimeout != UINT32_MAX) {
    realtimeTimeout = (timeoutMs == 255001 || timeoutMs == 65000) ? UINT32_MAX : millis() + timeoutMs;
  }
  realtimeMode = md;

  if (realtimeOverride) return;
  if (arlsForceMaxBri) strip.setBrightness(255, true);
  if (briT > 0 && md == REALTIME_MODE_GENERIC) strip.show();
}

void exitRealtime() {
  if (!realtimeMode) return;
  if (realtimeOverride == REALTIME_OVERRIDE_ONCE) realtimeOverride = REALTIME_OVERRIDE_NONE;
  strip.setBrightness(bri, true);
  realtimeTimeout = 0; // cancel realtime mode immediately
  realtimeMode = REALTIME_MODE_INACTIVE; // inform UI immediately
  realtimeIP[0] = 0;
  if (useMainSegmentOnly) { // unfreeze live segment again
    strip.getMainSegment().freeze = false;
    strip.trigger();
  } else {
    strip.show(); // possible fix for #3589
  }
  updateInterfaces(CALL_MODE_WS_SEND);
}
