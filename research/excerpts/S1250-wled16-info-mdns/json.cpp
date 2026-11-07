// Excerpt from wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c
// wled00/json.cpp lines 762-778, 869, 910, verbatim. EUPL-1.2; WLED contributors.
// Source entry [S1250]. See LICENSE-NOTE.md.
// lines 762-778
  root["live"] = (bool)realtimeMode;
  root[F("liveseg")] = useMainSegmentOnly ? strip.getMainSegmentId() : -1;  // if using main segment only for live

  switch (realtimeMode) {
    case REALTIME_MODE_INACTIVE: root["lm"] = ""; break;
    case REALTIME_MODE_GENERIC:  root["lm"] = ""; break;
    case REALTIME_MODE_UDP:      root["lm"] = F("UDP"); break;
    case REALTIME_MODE_HYPERION: root["lm"] = F("Hyperion"); break;
    case REALTIME_MODE_E131:     root["lm"] = F("E1.31"); break;
    case REALTIME_MODE_ADALIGHT: root["lm"] = F("USB Adalight/TPM2"); break;
    case REALTIME_MODE_ARTNET:   root["lm"] = F("Art-Net"); break;
    case REALTIME_MODE_TPM2NET:  root["lm"] = F("tpm2.net"); break;
    case REALTIME_MODE_DDP:      root["lm"] = F("DDP"); break;
    case REALTIME_MODE_DMX:      root["lm"] = F("DMX"); break;
  }

  root[F("lip")] = realtimeIP[0] == 0 ? "" : realtimeIP.toString();
// line 869
  root[F("uptime")] = millis()/1000 + rolloverMillis*4294967;
// line 910
  root["mac"] = escapedMac;
