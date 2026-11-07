# Excerpt from LedFx ledfx/effects/audio.py @ 566de0fb6d32231022d7efa7684298f3af615792
# See LICENSE-NOTE.md. Functions excerpted: AudioAnalysisSource.volume_beat_now,
# bar_oscillator, beat_oscillator (custom beat features layered on aubio.tempo).

# --- init constants (from initialise_analysis, L1333-L1339) ---
        self.beat_min_percent_diff = 0.5
        self.beat_min_time_since = 0.1
        self.beat_min_amplitude = 0.5
        self.beat_power_history_len = int(self._config["sample_rate"] * 0.2)

        self.beat_prev_time = time.time()
        self.beat_power_history = deque(maxlen=self.beat_power_history_len)

# --- volume_beat_now (L1384-L1419) ---
    @lru_cache(maxsize=None)
    def volume_beat_now(self):
        """
        Returns True if a beat is expected now based on volume of the beat freq region
        This algorithm is a bit weird, but works quite nicely.
        I've tried my best to optimise it from the original
        implementation in systematic_leds
        """

        time_now = time.time()
        melbank = self.melbanks.melbanks[0][: self.beat_max_mel_index]
        beat_power = np.sum(melbank)
        melbank_max = np.max(melbank)

        # calculates the % difference of the first value of the channel to the average for the channel
        if sum(self.beat_power_history) > 0:
            difference = (
                beat_power
                * self.beat_power_history_len
                / sum(self.beat_power_history)
                - 1
            )
        else:
            difference = 0

        self.beat_power_history.appendleft(beat_power)

        if (
            difference >= self.beat_min_percent_diff
            and melbank_max >= self.beat_min_amplitude
            and time_now - self.beat_prev_time > self.beat_min_time_since
        ):
            self.beat_prev_time = time_now
            return True
        else:
            return False

# --- bar_oscillator (L1482-L1517) ---
    @lru_cache(maxsize=None)
    def bar_oscillator(self):
        """
        Returns a float (0<=x<4) corresponding to the position of the beat
        tracker in the musical bar (4 beats)
        This is synced and quantized to the bpm of whatever is playing.
        While the beat number might not necessarily be accurate, the
        relative position of the tracker between beats will be quite accurate.

        NOTE: currently this makes no attempt to guess which beat is the first
        in the bar. It simple counts to four with each beat that is detected.
        The actual value of the current beat in the bar is completely arbitrary,
        but in time with each beat.

        0           1           2           3
        {----------time for one bar---------}
               ^    -->      -->      -->
            value of
        beat grid pointer
        """
        # update tempo and oscillator
        if self.bpm_beat_now():
            self.beat_counter = (self.beat_counter + 1) % 4
            self.beat_period = self._tempo.get_period_s()
            self.beat_timestamp = time.time()
            oscillator = self.beat_counter
        else:
            time_since_beat = time.time() - self.beat_timestamp
            oscillator = (
                1 - (self.beat_period - time_since_beat) / self.beat_period
            ) + self.beat_counter
            # ensure it's between [0 and 4). useful when audio cuts
            oscillator = oscillator % 4
        return oscillator

# --- beat_oscillator (L1519-L1530) ---
    def beat_oscillator(self):
        """
        returns a float (0<=x<1) corresponding to the relative position of the
        bar oscillator in the current beat.

        0                0.5                 <1
        {----------time for one beat---------}
               ^    -->      -->      -->
            value of
           oscillator
        """
        return self.bar_oscillator() % 1
