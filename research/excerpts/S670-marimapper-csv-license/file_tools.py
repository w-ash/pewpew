# Excerpt from TheMariday/marimapper@7dc5f799a1b7c180573c2632f6d12a3be0cbf4fa
# marimapper/file_tools.py lines 68-85, verbatim. GPL-3.0; TheMariday (Mari D) and contributors.
# Source entry [S670]. See LICENSE-NOTE.md.
# lines 68-85
def write_3d_leds_to_file(leds: list[LED3D], filename: Path):

    lines = ["index,x,y,z,xn,yn,zn,error"]

    for led in sorted(leds, key=lambda led_t: led_t.led_id):
        lines.append(
            f"{led.led_id},"
            f"{led.point.position[0]:f},"
            f"{led.point.position[1]:f},"
            f"{led.point.position[2]:f},"
            f"{led.point.normal[0]:f},"
            f"{led.point.normal[1]:f},"
            f"{led.point.normal[2]:f},"
            f"{led.point.error:f}"
        )

    with open(filename, "w") as f:
        f.write("\n".join(lines))
