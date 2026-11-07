# Excerpt from LedFx/LedFx@566de0fb6d32231022d7efa7684298f3af615792
# ledfx/effects/__init__.py lines 273-340, 479-547, verbatim. GPL-3.0; LedFx developers (Austin Hodges et al., per AUTHORS.rst).
# Source entry [S630]. See LICENSE-NOTE.md.
# lines 273-340
@BaseRegistry.no_registration
class Effect(BaseRegistry):
    """
    Manages an effect
    """

    NAME = ""
    # over ride in effect children to hide existing keys from UI
    HIDDEN_KEYS = None
    # extend in effect children
    ADVANCED_KEYS = ["diag"]
    # over ride in effect children to allow edit and show others
    PERMITTED_KEYS = None
    _config = None
    _active = False
    _virtual = None

    # Basic effect properties that can be applied to all effects
    CONFIG_SCHEMA = vol.Schema(
        {
            vol.Optional(
                "blur",
                description="Amount to blur the effect",
                default=0.0,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10)),
            vol.Optional(
                "flip", description="Flip the effect", default=False
            ): bool,
            vol.Optional(
                "mirror",
                description="Mirror the effect",
                default=False,
            ): bool,
            vol.Optional(
                "brightness",
                description="Brightness of strip",
                default=1.0,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                "background_color",
                description="Apply a background color",
                default="#000000",
            ): validate_color,
            vol.Optional(
                "background_brightness",
                description="Brightness of the background color",
                default=1.0,
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                "diag", description="Enable diagnostic logging", default=False
            ): bool,
            vol.Optional(
                "advanced",
                description=False,
            ): bool,
        }
    )

    def __init__(self, ledfx, config):
        self._ledfx = ledfx
        self._config = {}
        self.lock = threading.Lock()
        self.logsec = LogSecHelper(self)
        self.passed = 0.0
        self._last_frame_time = timeit.default_timer()
        self.now = self._last_frame_time
        self.background_mode = "additive"
        self.update_config(config)
# lines 479-547
    def get_pixels(self):
        """
        Get the current pixels for the effect and apply flip, mirror, blur, brightness and background color transformations

        Returns:
            numpy.ndarray: The modified pixel array.
        """
        with self.lock:
            pixels = None
            if hasattr(self, "pixels"):
                if self.pixels is not None:
                    pixels = np.copy(self.pixels)
                    # Grab the config and store it here for use in the function - we use it a lot
                    config = self._config

                    # Apply some of the base output filters if necessary
                    if self.flip:
                        pixels = np.flipud(pixels)

                    if self.mirror:
                        # concatenate the pixels for mirror, then take the max of adjacent pixels
                        # prevents average dimming and is best compromise, removes flicker
                        # inherently symetrical
                        mirrored_pixels = np.concatenate(
                            (pixels[::-1], pixels)
                        )
                        pixels = np.maximum(
                            mirrored_pixels[::2], mirrored_pixels[1::2]
                        )

                    if (
                        self.bg_color_use
                        and self.background_mode == "additive"
                    ):
                        pixels += self._bg_color

                    if self.brightness is not None:
                        np.multiply(
                            pixels,
                            self.brightness,
                            out=pixels,
                            casting="unsafe",
                        )

                    # If the configured blur is greater than 0 and pixel_count > 3, apply blur
                    # The matrix math requires > 3 pixels to work properly
                    # And blurring with a less than 3 pixels seems... redundant
                    # TODO: Handle RGBW properly
                    if config["blur"] != 0.0 and self.pixel_count > 3:
                        kernel = _gaussian_kernel1d(
                            config["blur"], 0, len(pixels)
                        )

                        # Blur the R,G,B portions of the pixel array
                        # Lots of attempts at vectorisation/performance improvements here
                        # This appears to be optimal from a readability/performance point of view
                        # TODO: If we ever move to RGBW pixel arrays, uncomment the last line to operate on the W portion

                        pixels[:, 0] = np.convolve(
                            pixels[:, 0], kernel, mode="same"
                        )  # R
                        pixels[:, 1] = np.convolve(
                            pixels[:, 1], kernel, mode="same"
                        )  # G
                        pixels[:, 2] = np.convolve(
                            pixels[:, 2], kernel, mode="same"
                        )  # B
                        # pixels[:, 3] = np.convolve(pixels[:, 3], kernel, mode="same") # W
                return pixels
