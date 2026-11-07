// Excerpt from wled/WLED@29b389df1c1aaec6ff53aea742d17063b985906c
// wled00/wled.cpp lines 855-860, verbatim. EUPL-1.2; WLED contributors.
// Source entry [S1250]. See LICENSE-NOTE.md.
// lines 855-860
    MDNS.begin(cmDNS);

    DEBUG_PRINTLN(F("mDNS started"));
    MDNS.addService("http", "tcp", 80);
    MDNS.addService("wled", "tcp", 80);
    MDNS.addServiceTxt("wled", "tcp", "mac", escapedMac.c_str());
