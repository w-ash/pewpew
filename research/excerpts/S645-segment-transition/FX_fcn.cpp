// Excerpt from wled/WLED@14709dd3ea9fca9e5164509772f6c75185e3ab63
// wled00/FX_fcn.cpp lines 1330-1367 (WS2812FX::service: during a transition the old segment copy runs its own mode)
// EUPL v1.2 or later, (c) 2016 Harm Aldick and WLED contributors. Source entry [S645].
  for (size_t i = 0; i < _segments.size(); i++) {
    Segment &seg = _segments[i];
    _segment_index = i;
    if (_suspend) break; // abort processing segments if suspend requested during service()

    // process transition (also pre-calculates progress value)
    seg.handleTransition();
    // reset the segment runtime data if needed
    seg.resetIfRequired();

    if (seg.isActive()) {
      // current segment is active -> re-run effect, and remember that show() call is necessary
      // if we arrive here, its always showtime (timeToShow == true)
      doShow = true;
      if (!seg.freeze) { //only run effect function if not frozen
        // Effect blending
        uint16_t prog = seg.progress();
        seg.beginDraw(prog);                // set up parameters for get/setPixelColor() (will also blend colors and palette if blend style is FADE)
        _currentSegment = &seg;             // set current segment for effect functions (SEGMENT & SEGENV)
        // workaround for on/off transition to respect blending style
        _mode[seg.mode]();                  // run new/current mode (needed for bri workaround)
        seg.call++;
        // if segment is in transition and no old segment exists we don't need to run the old mode
        // (blendSegments() takes care of On/Off transitions and clipping)
        Segment *segO = seg.getOldSegment();
        if (segO && segO->isActive() && (seg.mode != segO->mode || blendingStyle != TRANSITION_FADE ||
            (segO->name != seg.name && segO->name && seg.name && strncmp(segO->name, seg.name, WLED_MAX_SEGNAME_LEN) != 0))) {
          Segment::modeBlend(true);         // set flag for beginDraw() to blend colors and palette
          segO->beginDraw(prog);            // set up palette & colors (also sets draw dimensions), parent segment has transition progress
          _currentSegment = segO;           // set current segment
          // workaround for on/off transition to respect blending style
          _mode[segO->mode]();              // run old mode (needed for bri workaround; semaphore!!)
          segO->call++;                     // increment old mode run counter
          Segment::modeBlend(false);        // unset flag
        }
      }
    }
  }
// ...
// line 1781 (WS2812FX::show: gamma applied to the 8-bit pixel after brightness)
      c = gamma32(c); // apply gamma correction if enabled note: applying gamma after brightness has too much color loss
