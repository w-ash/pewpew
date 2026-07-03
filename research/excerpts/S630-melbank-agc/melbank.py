# Excerpt from LedFx ledfx/effects/melbank.py @ 566de0fb6d32231022d7efa7684298f3af615792
# See LICENSE-NOTE.md. Functions excerpted: matt_mel coefficient setup,
# Melbank.__call__ (peak-isolation power + AGC + smoothing + transient filter).

# --- module constants (L26-L32) ---
# these parameters are hard coded and will break configs if changed
FFT_SIZE = 4096
MIC_RATE = 30000
MAX_FREQ = MIC_RATE // 2
MIN_FREQ = 20
MEL_MAX_FREQS = [350, 2000, MAX_FREQ]

# --- from Melbank.__init__ (L100-L108): peak-isolation exponent ---
        # adjustable power (peak isolation) based on parameter a (0-1)
        # a=0    -> linear response (filter bank value maps to itself)
        # a=0.4  -> roughly equivalent to filter_banks ** 2.0
        # a=0.6  -> roughly equivalent to filter_banks ** 3.0
        # a=1    -> no response (infinite power as filter bank value approaches 1)
        # https://www.desmos.com/calculator/xxa2l9radu
        self.power_factor = np.tan(
            0.5 * np.pi * (self._config["peak_isolation"] + 1) / 2
        )

# --- from Melbank.__init__ (L264-L287): default "matt_mel" frequency warp ---
        if self._config["coeffs_type"] == "matt_mel":

            def hertz_to_matt(freq):
                return 3700.0 * log(1 + (freq / 230.0), 12)

            def matt_to_hertz(matt):
                return 230.0 * (12 ** (matt / 3700.0)) - 230.0

            melbank_matt = np.linspace(
                hertz_to_matt(self._config["min_frequency"]),
                hertz_to_matt(self._config["max_frequency"]),
                self._config["samples"] + 2,
            )
            self.melbank_frequencies = np.array(
                [matt_to_hertz(matt) for matt in melbank_matt]
            ).astype(np.float32)

            self.filterbank = aubio.filterbank(
                self._config["samples"], FFT_SIZE
            )
            self.filterbank.set_triangle_bands(
                self.melbank_frequencies, MIC_RATE
            )
            self.melbank_frequencies = self.melbank_frequencies[1:-1]

# --- from Melbank.__init__ (L374-L378): the shared ExpFilters ---
        # Build up some of the common filters
        self.mel_gain = ExpFilter(alpha_decay=0.01, alpha_rise=0.99)
        self.mel_smoothing = ExpFilter(alpha_decay=0.7, alpha_rise=0.99)
        self.common_filter = ExpFilter(alpha_decay=0.99, alpha_rise=0.01)
        self.diff_filter = ExpFilter(alpha_decay=0.15, alpha_rise=0.99)

# --- Melbank.__call__ (L380-L403) ---
    def __call__(self, frequency_domain, filter_banks, filter_banks_filtered):
        """
        computes the melbank curve for frequency domain .
        this function has been modified a bit to make sure all operations
        are applied to filter_banks in place
        """

        # Compute the filterbank from the frequency information.
        filter_banks[:] = self.filterbank(frequency_domain)

        np.power(
            filter_banks,
            self.power_factor,
            out=filter_banks,
        )

        self.mel_gain.update(np.max(fast_blur_array(filter_banks, sigma=1.0)))
        filter_banks /= self.mel_gain.value
        filter_banks[:] = self.mel_smoothing.update(filter_banks)

        self.common_filter.update(filter_banks)
        filter_banks_filtered[:] = self.diff_filter.update(
            filter_banks - self.common_filter.value
        )
