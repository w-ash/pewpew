// Excerpt: usermods/audioreactive/audio_reactive.cpp lines 799-812, verbatim, at the pin in LICENSE-NOTE.md.
    // new "V2" audiosync struct - 44 Bytes
    struct __attribute__ ((packed)) audioSyncPacket {  // "packed" ensures that there are no additional gaps
      char    header[6];      //  06 Bytes  offset 0
      uint8_t reserved1[2];   //  02 Bytes, offset 6  - gap required by the compiler - not used yet 
      float   sampleRaw;      //  04 Bytes  offset 8  - either "sampleRaw" or "rawSampleAgc" depending on soundAgc setting
      float   sampleSmth;     //  04 Bytes  offset 12 - either "sampleAvg" or "sampleAgc" depending on soundAgc setting
      uint8_t samplePeak;     //  01 Bytes  offset 16 - 0 no peak; >=1 peak detected. In future, this will also provide peak Magnitude
      uint8_t reserved2;      //  01 Bytes  offset 17 - for future extensions - not used yet
      uint8_t fftResult[16];  //  16 Bytes  offset 18
      uint16_t reserved3;     //  02 Bytes, offset 34 - gap required by the compiler - not used yet
      float  FFT_Magnitude;   //  04 Bytes  offset 36
      float  FFT_MajorPeak;   //  04 Bytes  offset 40
    };

