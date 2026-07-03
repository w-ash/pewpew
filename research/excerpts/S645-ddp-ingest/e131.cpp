#include "wled.h"

#define MAX_3_CH_LEDS_PER_UNIVERSE 170
#define MAX_4_CH_LEDS_PER_UNIVERSE 128
#define MAX_CHANNELS_PER_UNIVERSE 512

// forward declarations
static void handleDDPPacket(e131_packet_t* p, size_t packetLen);
static void handleArtnetPollReply(IPAddress ipAddress);
static void prepareArtnetPollReply(ArtPollReply *reply);
static void sendArtnetPollReply(ArtPollReply *reply, IPAddress ipAddress, uint16_t portAddress);


/*
 * E1.31 handler
 */

//DDP protocol support, called by handleE131Packet
//handles RGB data only
static void handleDDPPacket(e131_packet_t* p, size_t packetLen) {
  static bool ddpSeenPush = false;  // have we seen a push yet?
  int lastPushSeq = e131LastSequenceNumber[0];

  if (packetLen < DDP_HEADER_LEN) return; // too short to safely read any DDP header fields

  // reject unsupported color data types (only RGB and RGBW are supported)
  //uint8_t maskedType = p->dataType & 0x3F; // mask out custom and reserved flags, only type bits are relevant
  //if (maskedType != DDP_TYPE_RGB24 && maskedType != DDP_TYPE_RGBW32) return;

  // note: for maximum compatibility we do not reject unknonw or malformed data types but simply default to RGB24 and check there is enough data available in the packet to do so
  //       also we assume 8bit per channel and currently do not support other bit depths

  // reject control, status and config packets (not implemented)
  if (p->destination == DDP_ID_CONTROL || p->destination == DDP_ID_STATUS || p->destination == DDP_ID_CONFIG) return;

  // reject query and response packets (not implemented)
  if (p->flags & (DDP_FLAGS_QUERY | DDP_FLAGS_REPLY)) return;

  bool push = p->flags & DDP_FLAGS_PUSH; // push flag means "render now"
  if (!push && (p->flags & DDP_FLAGS_STORAGE)) return; // reject "from storage" flag but still let the push flag pass if set along with it

  //reject late packets belonging to previous frame (assuming 4 packets max. before push, if more are used and packets are very late, they are still accepted)
  if (e131SkipOutOfSequence && lastPushSeq) {
    int sn = p->sequenceNum & 0xF; // sequence number is 4 bits, 1-15, 0 means unused
    if (sn) {
      if (lastPushSeq > 5) {
        if (sn > (lastPushSeq -5) && sn < lastPushSeq) return;
      } else {
        if (sn > (10 + lastPushSeq) || sn < lastPushSeq) return;
      }
    }
  }

  unsigned ddpChannelsPerLed = 3; // default to RGB
  if ((p->dataType & 0b00111000)>>3 == 0b011) ddpChannelsPerLed = 4; // RGBW data type (see DDP protocol definition)

  uint32_t start =  htonl(p->channelOffset) / ddpChannelsPerLed;
  start += DMXAddress / ddpChannelsPerLed;
  uint16_t dataLen = htons(p->dataLen);
  unsigned stop = start + dataLen / ddpChannelsPerLed;
  uint8_t* data = p->data;
  unsigned c = 0;
  if (p->flags & DDP_FLAGS_TIME) c = 4; //packet has timecode flag, we do not support it, but data starts 4 bytes later

  // ensure the received packet is at least as long as the header claims
  if (packetLen < DDP_HEADER_LEN + c + dataLen) {
    DEBUG_PRINTLN(F("DDP packet incomplete"));
    return;
  }

  unsigned numLeds = stop - start; // stop >= start is guaranteed
  unsigned maxDataIndex = numLeds * ddpChannelsPerLed; // validate bounds before accessing data array
  if (maxDataIndex > dataLen) {
    DEBUG_PRINTLN(F("DDP packet data bounds exceeded, rejecting."));
    return;
  }

  if (realtimeMode != REALTIME_MODE_DDP) ddpSeenPush = false; // just starting, no push yet
  realtimeLock(realtimeTimeoutMs, REALTIME_MODE_DDP);

  if (!realtimeOverride) {
    for (unsigned i = start; i < stop; i++, c += ddpChannelsPerLed) {
      setRealtimePixel(i, data[c], data[c+1], data[c+2], ddpChannelsPerLed >3 ? data[c+3] : 0);
    }
  }

  ddpSeenPush |= push;
  if (!ddpSeenPush || push) { // if we've never seen a push, or this is one, render display
    e131NewData = true;
    int sn = p->sequenceNum & 0xF;
    if (sn) e131LastSequenceNumber[0] = sn;
  }
}
