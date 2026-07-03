    # Functions frontend

    def set_pattern_function(self, key, source):
        'Update and recompile a pattern function'
        def getitem(obj, index):
            if obj is not None and type(obj) in (list, tuple, dict):
                return obj[index]
            raise Exception()

        def getiter(obj):
            return obj

        restricted_globals = {
            '__builtins__': RestrictedPython.Guards.safe_builtins,
            '_print_': RestrictedPython.PrintCollector,
            '_getattr_': RestrictedPython.Guards.safer_getattr,
            '_getitem_': getitem,
            '_getiter_': getiter,
            '_write_': RestrictedPython.Guards.full_write_guard,
            'math': math,
            'random': random,
            'palette': self._get_palette_color,
            'palette_mirrored': self._get_palette_color_mirrored,
            'hsv': animfunctions.ColorMode.hsv,
            'rgb': animfunctions.ColorMode.rgb,
            'clamp': utils.clamp,
            'wave_pulse': driver.wave_pulse,
            'wave_triangle': driver.wave_triangle,
            'wave_sine': driver.wave_sine,
            'wave_cubic': driver.wave_cubic,
            'plasma_sines': driver.plasma_sines,
            'plasma_sines_octave': driver.plasma_sines_octave,
            'perlin_noise_3d': driver.perlin_noise_3d,
            'fbm_noise_3d': driver.fbm_noise_3d,
            'impulse_exp': utils.impulse_exp,
            'fract': utils.fract,
            'blackbody_to_rgb': driver.blackbody_to_rgb,
            'blackbody_correction_rgb': driver.blackbody_correction_rgb,
        }
        restricted_locals = {}
        arg_names = ['t', 'dt', 'x', 'y', 'z', 'prev_state']

        result = RestrictedPython.compile_restricted_exec(source)
        warnings = list(result.warnings)
        for name in result.used_names:
            if name not in restricted_globals and name not in arg_names:
                warnings.append(f'NameError: name \'{name}\' is not defined')

        if result.code:
            exec(result.code, restricted_globals, restricted_locals)

        if len(result.errors) == 0 and 'pattern' in restricted_locals:
            self._functions[key] = restricted_locals['pattern']
            self._check_reset_animation_state()

        self._update_needed = True
        return result.errors, warnings

