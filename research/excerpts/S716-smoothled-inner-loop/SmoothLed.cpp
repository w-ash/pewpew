// Values in this table are inverted and the CCL LUT will flip them back.
const uint16_t SmoothLed::Gamma25[Gamma25Size] =
{
    0xff00, 0xfef4, 0xfebb, 0xfe42, 0xfd79, 0xfc56, 0xfacc, 0xf8d2,
    0xf65f, 0xf36a, 0xefed, 0xebde, 0xe738, 0xe1f3, 0xdc0a, 0xd575,
    0xce2f, 0xc632, 0xbd78, 0xb3fc, 0xa9b8, 0x9ea8, 0x92c6, 0x860e,
    0x787a, 0x6a06, 0x5aad, 0x4a6a, 0x393a, 0x2718, 0x13ff, 0xffeb,
};
void SmoothLed::beginFade(uint16_t numFrames)
{
    m_Time = 0;
    m_DeltaTime = uint16_t(0x8000) / numFrames;
}
void SmoothLed::setFadePosition(uint16_t time)
{
    m_Time = time;
}
void SmoothLed::setFadeRate(uint16_t speed)
{
    m_DeltaTime = speed;
}
uint8_t SmoothLed::updateTime()
{
    uint8_t lastT = highByte(m_Time);
    if (lastT >= 0x80)
        return 0;
    m_Time += m_DeltaTime;
    return highByte(m_Time) - lastT;
}
uint8_t SmoothLed::Interpolator::update(uint8_t dt, const uint16_t* lut, uint16_t maxvalue, uint8_t ditherMask)
{    
    value = fmac(value, step, dt); //value += (step * dt) >> 7;
    if (highByte(maxvalue) < highByte(value))
        value = value < 0 ? 0 : maxvalue;
    lut += highByte(value);
    uint16_t corrected = lerp(lut[0], lut[1], lowByte(value)) + dither;
    dither = lowByte(corrected) & ditherMask;
    return highByte(corrected);
}
