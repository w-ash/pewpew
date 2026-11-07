# Excerpt from LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
# ledfx/virtuals.py lines 409-495, 746-779, 864-877, verbatim. GPL-3.0; LedFx developers (Austin Hodges et al., per AUTHORS.rst).
# Source entry [S630]. See LICENSE-NOTE.md.
# lines 409-495
    def _compile_device_remap(self):
        """
        Precompile device remap structure for fast pixel mapping in flush().
        Only active when complex_segments is enabled.
        Builds src (virtual indices) and dst (device indices) arrays per device.
        """
        device_remap = {}

        if not self.complex_segments:
            # Complex segments disabled - skip compilation
            self._device_remap = {}
            return

        if self._config["mapping"] != "span":
            # Only compile for span mode - copy mode needs different handling
            self._device_remap = {}
            return

        _LOGGER.info(
            "Virtual %s: compiling device remap for complex segments", self.id
        )

        # Group segments by device and build index arrays
        device_buffers = {}  # {device_id: {"src": list, "dst": list}}
        virtual_offset = 0

        for device_id, device_start, device_end, reverse in self._segments:
            segment_width = device_end - device_start + 1

            # Skip gap devices - they are placeholders for empty space
            # But still advance virtual_offset to consume those pixels from the virtual's buffer
            device = self._ledfx.devices.get(device_id)
            if is_gap_device(device):
                virtual_offset += segment_width
                continue

            # Skip segments with invalid width
            if segment_width <= 0:
                continue

            # Build virtual indices for this segment
            virtual_indices = np.arange(
                virtual_offset, virtual_offset + segment_width, dtype=np.int32
            )

            # Build device indices for this segment
            device_indices = np.arange(
                device_start, device_end + 1, dtype=np.int32
            )

            # Handle reverse flag by reversing virtual indices
            if reverse:
                virtual_indices = virtual_indices[::-1]

            # Initialize device buffer if needed
            if device_id not in device_buffers:
                device_buffers[device_id] = {"src": [], "dst": []}

            # Append indices to device buffers
            device_buffers[device_id]["src"].append(virtual_indices)
            device_buffers[device_id]["dst"].append(device_indices)

            virtual_offset += segment_width

        # Convert lists to numpy arrays
        for device_id, buffers in device_buffers.items():
            device_remap[device_id] = {
                "src": (
                    np.concatenate(buffers["src"])
                    if buffers["src"]
                    else np.array([], dtype=np.int32)
                ),
                "dst": (
                    np.concatenate(buffers["dst"])
                    if buffers["dst"]
                    else np.array([], dtype=np.int32)
                ),
            }

        # Filter out devices that don't exist (like gap-mapping)
        device_remap = {
            device_id: remap
            for device_id, remap in device_remap.items()
            if self._ledfx.devices.get(device_id) is not None
        }

        self._device_remap = device_remap
# lines 746-779
    def clear_frame(self):
        """
        Clears the frame by performing the following steps:
        1. Clears the active effect.
        2. Clears the transition effect.
        3. If the virtual device is active:
           - Clears all the pixel data by setting it to zeros.
           - Flushes the assembled frame to the device.
           - Fires a VirtualUpdateEvent to notify listeners of the updated frame.
           - Releases the lock.
           - Deactivates the virtual device.
        """
        # Little tricky logic here - we need to clear the active effect and
        # transition effect before we flush the frame, but we need to flush
        # the frame before we deactivate the virtual device. We also need to
        # make sure that we don't clear the frame if the virtual device is
        # not active.
        # All of this requires thread lock management that's a bit unwieldy

        assembled_frame = None
        with self.lock:
            self.clear_active_effect()
            self.clear_transition_effect()
            if self._active:
                assembled_frame = np.zeros((self.pixel_count, 3))
                self.flush(assembled_frame)
                self._fire_update_event(assembled_frame)

        # Deactivate the device - this requires the thread lock
        # Hence why we do it outside of the lock and after the frame is cleared
        # This is because the deactivate method will join the thread
        # and we don't want to call join while holding the lock
        if assembled_frame is not None:
            self.deactivate()
# lines 864-877
            # adjust for the frame assemble time, min allowed sleep 1 ms
            # this will be more frame accurate on high res sleep systems
            run_time = time.perf_counter() - start_time
            sleep_time = max(
                0.001, fps_to_sleep_interval(self.refresh_rate) - run_time
            )
            time.sleep(sleep_time)

            # use an aggressive check for did we sleep against expected min clk
            # for all high res scenarios this will be passive
            # for unexpected high res sleep on windows scenarios it will adapt
            pass_time = time.perf_counter() - start_time
            if pass_time < (self._min_time / 2):
                time.sleep(max(0.001, self._min_time - pass_time))
