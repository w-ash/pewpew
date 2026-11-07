<!-- Excerpt from jackw01/led-control@8e3fe1d0456e589213ecdef1dc8ce57aa15142b6
     README.md lines 17-24, verbatim. MIT; jackw01.
     Source entry [S660]. See LICENSE-NOTE.md. -->
<!-- lines 17-24 -->
* Capable of achieving up to 150 FPS on 150 RGBW LEDs on a Raspberry Pi Zero
* Web backend and animation code are written in Python using the [Flask](https://flask.palletsprojects.com/en/2.0.x/) web framework for ease of development and served using [bjoern](https://github.com/jonashaag/bjoern)
* Web frontend UI is implenented using [Vue 3](https://vuejs.org/)
* Color conversions, color correction, and final rendering operations are implemented in a C extension module for maximum performance

#### Framerate Note
The theoretical maximum framerate for 150 RGBW LEDs is 800000 Hz / (8*4) bits / 150 = 166.67 FPS.
All built-in animations run at over 50FPS with 150 LEDs on a Raspberry Pi Zero, the least powerful Raspberry Pi model. The framerate is limited to 60FPS by default to reduce CPU usage.
