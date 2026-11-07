    # Computing cached values

    def calculate_palette_table(self, key):
        'Calculate and store the palette lookup table for one palette'
        palette = self._palettes[key]
        palette_table = []
        sector_size = 1.0 / (len(palette['colors']) - 1)
        for i in range(self._palette_table_size):
            f = i / self._palette_table_size
            sector = math.floor(f / sector_size)
            f = f % sector_size / sector_size
            c1, c2 = palette['colors'][sector], palette['colors'][sector + 1]
            # Allow full spectrum if extremes are 0 and 1 in any order
            # otherwise pick shortest path between colors
            h1 = c2[0] - c1[0]
            if abs(h1) != 1:
                if h1 < -0.5:
                    h1 += 1
                if h1 > 0.5:
                    h1 -= 1
            palette_table.append((
                f * h1 + c1[0],
                f * (c2[1] - c1[1]) + c1[1],
                f * (c2[2] - c1[2]) + c1[2],
            ))
        self._palette_tables[key] = palette_table
        self._update_needed = True

    def calculate_palette_tables(self):
        'Calculate and store the palette lookup tables for all palettes'
        for key in self._palettes:
            self.calculate_palette_table(key)

    def calculate_color_correction(self):
        'Calculate and store color temperature correction'
        rgb = driver.blackbody_to_rgb(self._settings['global_color_temp'])
        c = [self._settings['global_color_r'] * int(rgb[0] * 255) // 255,
             self._settings['global_color_g'] * int(rgb[1] * 255) // 255,
             self._settings['global_color_b'] * int(rgb[2] * 255) // 255]
        self._correction = (c[0] << 16) | (c[1] << 8) | c[2]

    def calculate_mapping(self):
        'Calculate and store spatial mapping values with current scale'
        for group in self._settings['groups']:
            scale = self._settings['groups'][group]['scale']
            if scale != 0:
                # Calculate scale components to determine animation position
                # scale component = position / scale (pattern length in units)
                # One cycle is a normalized input value's transition from 0 to 1
                self._mappings[group] = [(
                    (self._mapped[i][0] / scale) % 1,
                    (self._mapped[i][1] / scale) % 1,
                    (self._mapped[i][2] / scale) % 1
                ) for i in range(self._led_count)]

            else:
                self._mappings[group] = [(0, 0, 0) for i in range(self._led_count)]
    def update_leds(self):
        'Determine time, render frame, and display'
        last_t = self._time
        self._time = self._timer.last_start - self._start
        delta_t = self._time - last_t

        if self._timer.get_count() % 100 == 0:
            print(f'Execution time: {self._timer.get_perf_avg():0.5f}s, {self._timer.get_rate():05.1f} FPS')

        if self._settings['calibration'] == 1:
            for group, settings in list(self._settings['groups'].items()):
                range_start = settings['range_start']
                range_end = min(self._led_count, settings['range_end'])
                self._led_controller.show_calibration_color(
                    range_end - range_start,
                    self._correction,
                    self._settings['global_brightness'] / 2,
                    settings['render_mode'],
                    settings['render_target']
                )

            return

        if self._update_needed:
            self._update_needed = False
            # Store dict keys as list in case they are changed during iteration
            for group, settings in list(self._settings['groups'].items()):
                try:
                    mapping = self._mappings[group]
                    range_start = settings['range_start']
                    range_end = min(self._led_count, settings['range_end'])

                    # Begin render
                    self._current_palette_table = self._palette_tables[settings['palette']]
                    computed_brightness = self._settings['on'] * self._settings['global_brightness'] * settings['brightness']
                    computed_saturation = self._settings['global_saturation'] * settings['saturation']
                    function_1 = self._functions[settings['function']]

                    # Calculate times
                    # Reset time every week to prevent strange math issues
                    time_fix = self._time % 604800
                    # time component = time (s) * speed (cycle/s)
                    time_1 = time_fix * settings['speed']
                    delta_t_1 = delta_t * settings['speed']

                except KeyError as e: # Ignore if settings haven't been calculated yet
                    continue

                try:
                    if self._settings['sacn'] == 0:
                        # Determine current pattern mode
                        c, mode = function_1(0, 0.1, 0, 0, 0, (0, 0, 0))

                        # Run pattern to determine color
                        state = [function_1(time_1,
                                            delta_t_1,
                                            mapping[i][0],
                                            mapping[i][1],
                                            mapping[i][2],
                                            self._prev_state[i])[0]
                                for i in range(range_start, range_end)]
                        self._prev_state[range_start:range_end] = state

                        self._led_controller.set_range(
                            state,
                            range_start,
                            range_end,
                            self._correction,
                            computed_saturation,
                            computed_brightness,
                            mode,
                            settings['render_mode'],
                            settings['render_target']
                        )

                    else:
                        self._led_controller.set_range(
                            [self._sacn_buffer[i] for i in range(range_start, range_end)],
                            range_start,
                            range_end,
                            self._correction,
                            1.0,
                            self._settings['global_brightness'],
                            animfunctions.ColorMode.rgb,
                            settings['render_mode'],
                            settings['render_target']
                        )

                except Exception as e:
                    msg = traceback.format_exception(type(e), e, e.__traceback__)
                    print(f'Error during animation execution: {msg}')
                    r = 0.1 * driver.wave_pulse(time_fix, 0.5)
                    self._led_controller.set_range(
                        [(r, 0, 0) for i in range(range_end - range_start)],
                        range_start,
                        range_end,
                        self._correction,
                        1.0,
                        1.0,
                        animfunctions.ColorMode.rgb,
                        settings['render_mode'],
                        settings['render_target']
                    )
                    self._led_controller.render()
                    return

                # If displaying a static pattern, brightness is 0, or speed is 0:
                # no update is needed the next frame
                if (not self._update_needed
                    and settings['function'] not in animfunctions.static_function_ids
                    and settings['speed'] != 0
                    and computed_brightness > 0):
                    self._update_needed = True

            self._led_controller.render()
