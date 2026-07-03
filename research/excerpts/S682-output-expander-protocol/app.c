 *
 * The protocol starts with a magic sequence, channel, and record type
 *
 * These vars and data structures are for reference:
 * const static char MAGIC[] = { "UPXL" }; //starts with 0x55, good for auto baud rate detection
 * frame headers look like this:
 * typedef struct {
 * 	int8_t magic[4]; //"UPXL"
 * 	uint8_t channel;
 * 	uint8_t recordType; //set channel ws2812 opts+data, draw all
 * } PBFrameHeader;
 *
 * following this is a frame of the record type, optional payload data, and finished with a
 * CRC32 of the entire thing (up to and including magic)
 *
 *
 * The protocol allows specifying output data rates, however it would be hard to
 * untangle ws2812 and apa102 as they would be writing to the same port at different times,
 *
 * It would be possible to let apa102 set the speed when used without WS2812, but this is not implemented.
 * Output speed is fixed at 800KHz.
 *
 * for apa102 clock, start bits are cleared, data is zeroed out so when it copies it will toggle clock low (via tim1 data trigger)
 * tim1ch2 has a dma trigger to set clocks high (like start bits, but for clocks) half a period after data is set
 * storing a bunch of zeros is kind of a waste, but each clock channel reserves a position in the bitBuffer anyway.
 *
 * apa102 needs a start and end frame, better to write these in memory and not require it in the protocol, borrowing 2 pixels of data
 *
 *
 */

enum RecordType {
	SET_CHANNEL_WS2812 = 1, DRAW_ALL, SET_CHANNEL_APA102_DATA, SET_CHANNEL_APA102_CLOCK
};

typedef struct {
	uint8_t numElements; //0 to disable channel, usually 3 (RGB) or 4 (RGBW)
	uint8_t or :2, og :2, ob :2, ow :2; //color orders, data on the line assumed to be RGB or RGBW
	uint16_t pixels;
} PBWS2812Channel;

typedef struct {
	uint32_t frequency;
	uint8_t or :2, og :2, ob :2; //color orders, data on the line assumed to be RGBV (global brightness last)
	uint16_t pixels;
} PBAPA102DataChannel;

typedef struct {
	uint32_t frequency;
} PBAPA102ClockChannel;


typedef struct {
	enum RecordType type;
	union {
		PBWS2812Channel ws2812Channel;
		PBAPA102DataChannel apa102DataChannel;
		PBAPA102ClockChannel apa102ClockChannel;
	};
} PBChannel;

PBChannel channels[8];


volatile unsigned long ms;
volatile unsigned long lastDataMs;
volatile unsigned long lastValidChannelMs;
volatile unsigned long lastDrawMs;

uint32_t bitBuffer[BYTES_PER_CHANNEL * 2];

//single byte vars for DMA to GPIO
uint8_t ones = 0xff;
uint8_t ws2812StartBits = 0;
uint8_t apa102ClockBits = 0;

static inline void handleIncomming() {
	uartResetCrc();
	//look for the 4 byte magic header sequence
	if (uartGetc() == 'U' && uartGetc() == 'P' && uartGetc() == 'X' && uartGetc() == 'L') {
		uint8_t channel = uartGetc();
		uint8_t recordType = uartGetc();
		lastDataMs = ms; //notice that we see some data
		switch (recordType) {
		case SET_CHANNEL_WS2812: {
			//read in the header
			PBWS2812Channel ch;
			uartRead(&ch, sizeof(PBWS2812Channel));

			if (ch.numElements < 3 || ch.numElements > 4)
				return;
			if (ch.pixels * ch.numElements > BYTES_PER_CHANNEL)
				return;

			//check that it's addressed to us and remap
			channel = remapFrameChannel(channel);

			uint8_t or = ch.or;
			uint8_t og = ch.og;
			uint8_t ob = ch.ob;
			uint8_t ow = ch.ow;

			uint8_t elements[4];

			uint32_t * dst = bitBuffer;
			int stride = 2*ch.numElements;
			for (int i = 0; i < ch.pixels; i++) {
				elements[or] = uartGetc();
				elements[og] = uartGetc();
				elements[ob] = uartGetc();
				if (ch.numElements == 4) {
					elements[ow] = uartGetc();
				}
				//this will ignore channel > 7
				bitConverter(dst, channel, elements, ch.numElements);
				dst += stride;
			}

			volatile uint32_t crcExpected = uartGetCrc();
			volatile uint32_t crcRead;
			uartRead((void *) &crcRead, sizeof(crcRead));

			if (channel < 8) { //check that it was addressed to us (not 0xff)
				int blocksToZero;
				if (crcExpected == crcRead) {
					if (channels[channel].type == SET_CHANNEL_WS2812
							&& (ch.pixels * ch.numElements >=
									channels[channel].ws2812Channel.pixels * channels[channel].ws2812Channel.numElements)
						) {
						blocksToZero = 0;
					} else {
						//we need to zero out previous data if the data received was less than last time
						blocksToZero = BYTES_PER_CHANNEL - ch.numElements * ch.pixels;
					}

					channels[channel].type = SET_CHANNEL_WS2812;
					channels[channel].ws2812Channel = ch;

					lastValidChannelMs = ms;
				} else {
					//garbage data, disable the channel, zero everything.
					//its better to let the LEDs keep the previous values than draw garbage.
					debugStats.crcErrors++;
					channels[channel].type = SET_CHANNEL_WS2812;
					memset(&channels[channel].ws2812Channel, 0, sizeof(channels[0].ws2812Channel));
					blocksToZero = BYTES_PER_CHANNEL;
				}
				//zero out any remaining data in the buffer for this channel
				if (blocksToZero > 0)
					bitSetZeros(bitBuffer + (BYTES_PER_CHANNEL - blocksToZero)*2, channel, blocksToZero);
			}
			break;
		}
		case DRAW_ALL: {
			uint32_t crcExpected = uartGetCrc();
			uint32_t crcRead;
			uartRead(&crcRead, sizeof(crcRead));
			if (crcExpected == crcRead) {
				startDrawingChannles();
			} else {
				debugStats.crcErrors++;
			}
			break;
		}
		case SET_CHANNEL_APA102_DATA: {
			//read in the header
			PBAPA102DataChannel ch;
			uartRead(&ch, sizeof(ch));
			if (ch.frequency == 0)
				return;
			//make sure we're not getting more data than we can handle
			if ((ch.pixels+2) * 4 > BYTES_PER_CHANNEL)
				return;

			//check that it's addressed to us and remap
			channel = remapFrameChannel(channel);

			uint8_t or = ch.or;
			uint8_t og = ch.og;
			uint8_t ob = ch.ob;

			uint8_t elements[4] = {0,0,0,0};
			uint32_t * dst = bitBuffer;

			//start frame
			bitConverter(dst, channel, elements, 4);
			dst += 8;

			for (int i = 0; i < ch.pixels; i++) {
				elements[or+1] = uartGetc();
				elements[og+1] = uartGetc();
				elements[ob+1] = uartGetc();
				elements[0] = uartGetc() | 0xe0;
				bitConverter(dst, channel, elements, 4);
				dst += 8;
			}

			//end frame
			elements[0] = 0xff;
			elements[1] = elements[2] = elements[3] = 0;
			bitConverter(dst, channel, elements, 4);

			volatile uint32_t crcExpected = uartGetCrc();
			volatile uint32_t crcRead;
			uartRead((void *) &crcRead, sizeof(crcRead));

			if (channel < 8) { //check that it was addressed to us (not 0xff)
				int blocksToZero;
				if (crcExpected == crcRead) {
					if (channels[channel].type == SET_CHANNEL_APA102_DATA
							&& (ch.pixels >= channels[channel].apa102DataChannel.pixels)
						) {
						blocksToZero = 0;
					} else {
						//we need to zero out previous data if the data received was less than last time
						blocksToZero = BYTES_PER_CHANNEL - ch.pixels * 4;
					}

					channels[channel].type = SET_CHANNEL_APA102_DATA;
					channels[channel].apa102DataChannel = ch;

					lastValidChannelMs = ms;
				} else {
					//garbage data, disable the channel, zero everything.
					//its better to let the LEDs keep the previous values than draw garbage.
					debugStats.crcErrors++;
					channels[channel].type = SET_CHANNEL_APA102_DATA;
					memset(&channels[channel].apa102DataChannel, 0, sizeof(channels[0].apa102DataChannel));
					blocksToZero = BYTES_PER_CHANNEL;
				}
				//zero out any remaining data in the buffer for this channel
				//TODO FIXME apa102 zeros will cause a start frame or maybe draw black? might not be what we want. set to all ones instead?
				if (blocksToZero > 0)
					bitSetZeros(bitBuffer + (BYTES_PER_CHANNEL - blocksToZero)*2, channel, blocksToZero);
			}
			break;
		}
		case SET_CHANNEL_APA102_CLOCK: {
			//read in the header
			PBAPA102ClockChannel ch;
			uartRead(&ch, sizeof(ch));
			if (ch.frequency == 0)
				return;

			//check that it's addressed to us and remap
			channel = remapFrameChannel(channel);

			volatile uint32_t crcExpected = uartGetCrc();
			volatile uint32_t crcRead;
			uartRead((void *) &crcRead, sizeof(crcRead));

			if (channel < 8) { //check that it was addressed to us (not 0xff)
				int blocksToZero;
				if (crcExpected == crcRead) {
					if (channels[channel].type == SET_CHANNEL_APA102_CLOCK) {
						blocksToZero = 0;
					} else {
						//we need to zero out previous data
						blocksToZero = BYTES_PER_CHANNEL;
					}

					channels[channel].type = SET_CHANNEL_APA102_CLOCK;
					channels[channel].apa102ClockChannel = ch;

					lastValidChannelMs = ms;
				} else {
					//garbage data, disable the channel, zero everything. Some apa102 channels could be without clock, so should remain unchanged
					debugStats.crcErrors++;
					channels[channel].type = SET_CHANNEL_APA102_CLOCK;
					memset(&channels[channel].apa102ClockChannel, 0, sizeof(channels[0].apa102ClockChannel));
					blocksToZero = BYTES_PER_CHANNEL;
				}
				//zero out any remaining data in the buffer for this channel
				if (blocksToZero > 0)
					bitSetZeros(bitBuffer + (BYTES_PER_CHANNEL - blocksToZero)*2, channel, blocksToZero);
			}
			break;
		}
		default:
			//unsupported frame type or garbage frame, just wait for the next one
			break;
		}

	} else {
		debugStats.frameMisses++;
	}
}
void loop() {
	for (;;) {
		if (uartAvailable() > 0) {
			handleIncomming();
		}
	}
}
