def find_inter_led_distance(leds: list[Union[LED2D, LED3D]]):
    distances = []

    for led in leds:
        next_led = get_next(led, leds)
        if next_led is not None:
            if get_gap(led, next_led) == 1:
                dist = get_distance(led, next_led)
                distances.append(dist)

    return np.median(distances)


def rescale(leds: list[LED3D], target_inter_distance=1.0) -> int:

    inter_led_distance = find_inter_led_distance(leds)
    scale = (1.0 / inter_led_distance) * target_inter_distance
    for led in leds:
        led.point *= scale
        for view in led.views:
            view.position = view.position * scale

    return scale


def recenter(leds: list[LED3D]):

    for led in leds:
        assert len(led.point.position) == 3

    center = np.median([led.point.position for led in leds], axis=0)
    for led in leds:
        led.point.position -= center
        for view in led.views:
            view.position = view.position - center


def fill_gap(start_led: LED3D, end_led: LED3D):

    total_missing_leds = end_led.led_id - start_led.led_id - 1

    new_leds = []
    for led_offset in range(1, total_missing_leds + 1):

        new_led = LED3D(start_led.led_id + led_offset)
        fraction = led_offset / (total_missing_leds + 1)
        p1 = start_led.point * (1 - fraction)
        p2 = end_led.point * fraction
        new_led.point = p1 + p2

        new_led.views = start_led.views + end_led.views

        new_led.interpolated = True
        new_leds.append(new_led)

    return new_leds


def fill_gaps(
    leds: list[LED3D],
    min_distance: float = 0.8,
    max_distance: float = 1.2,
    max_missing=5,
):

    new_leds = []

    for led in leds:

        next_led = get_next(led, leds)

        if next_led is None:
            continue

        gap = get_gap(led, next_led) - 1

        if 1 <= gap <= max_missing:

            distance = get_distance(led, next_led)

            distance_per_led = distance / (gap + 1)

            if (min_distance < distance_per_led < max_distance) and gap <= max_missing:
                new_leds += fill_gap(led, next_led)

    new_led_count = len(new_leds)

    if new_led_count > 0:
        logger.debug(f"filled {new_led_count} LEDs")

    leds += new_leds
