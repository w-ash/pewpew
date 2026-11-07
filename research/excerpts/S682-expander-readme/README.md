<!-- Excerpt from simap/pixelblaze_output_expander@7a6295b12056db35be3dfd2629783050020db7ae
     README.md lines 13-78, verbatim. MIT; Copyright (c) 2018 Ben Hencke.
     Source entry [S682]. See LICENSE-NOTE.md. -->
<!-- lines 13-78 -->
Frames start with a magic 4-byte sequence, followed by the channel ID (8 bits), then the command type (8 bits). Some commands have additional header/structs and payloads, finally every frame is ended with a 32-bit CRC that covers the entire frame (from magic to the last byte before CRC).

```c
typedef struct {
	int8_t magic[4]; //"UPXL"
	uint8_t channel;
	uint8_t recordType; //set channel ws2812 opts+data, draw all
} PBFrameHeader;
```

Two commands are implemented, one sets a channel's configuration and buffer data, and the other draws all channels:

```c
enum {
	SET_CHANNEL_WS2812 = 1, DRAW_ALL
} RecordType;
```

### `SET_CHANNEL_WS2812`

The channel ID is part of the PBFrameHeader. Each board supports 8 channels, and has an additional 3 bits of address configured by cuttable jumpers on the underside of the board. Up to 64 channels can be on the same bus (8 boards w/ 8 channels each).

The `SET_CHANNEL_WS2812` command frame header is immediately followed by a structure defining the configuration for that channel, and then followed by RGB or RGBW pixel data:

```c
typedef struct {
	uint8_t numElements; //0 to disable channel, usually 3 (RGB) or 4 (RGBW)
	uint8_t redIndex :2, greenIndex :2, blueIndex :2, whiteIndex :2; //color orders, data on the line assumed to be RGB or RGBW
	uint16_t pixels;
} PBChannel;
```

In total:

```
PBFrameHeader + PBChannel + bytes[numElements * pixels] + CRC
```

### `DRAW_ALL`

The `DRAW_ALL` command ignores the channel from the frame header, though it must still be followed by a CRC. All channels on the bus are drawn simultaneously when this command is received. This command ignores channel ID.

In total:

```
PBFrameHeader + CRC
```

Error Handling
-------------------

The firmware is designed to tolerate noise and data errors. There isn't enough memory to double-buffer the channel data, but any channel data received is zeroed out in case the CRC does not match.

The magic header provides a way to align frames in case of continuous transmission.

It's assumed that data will be more or less continuously flowing, and the reception code doesn't timeout if the input goes idle.

If part of a frame is received, it will wait for enough data to complete that frame, and eventually throw that out if the CRC doesn't match. If that is in the middle of another frame, it will discard data until the magic frame start sequence is found. 

Timing Considerations
-------------------

There isn't enough memory to double-buffer the channel data, so its possible to send a draw command, and then immediately follow with channel data that will update the buffer as it is being drawn. Usually this is not a problem, but if corrupted data or pixels are very different, it might cause a momentary display glitch until the next frame is drawn.

To avoid any potential issues, you can delay sending the next channel data until drawing is completed. Drawing takes 5760 bit times at 800Khz, or 7.2ms. Given that the input data rate is 2Mbps (and that includes start/stop bits, so effectively 1.6Mbps of data), its possible to delay for less than this as input would be updating buffer area that has already been drawn. Waiting for 3.6ms would give the drawing operation enough of a head start that an `SET_CHANNEL_WS2812` frame won't overtake it. Even if corrupted data is written, it won't get displayed as the CRC mismatch will cause the buffer to be cleared and the channel to be disabled until valid data is sent.

