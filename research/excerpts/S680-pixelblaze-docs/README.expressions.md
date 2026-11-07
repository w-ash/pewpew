# Brief quotations from `README.expressions.md` [S680]

Upstream: `README.expressions.md` at
`simap/pixelblaze@20d169f30f7912b2245c57ab9bd721436324bf04` (v3 branch).
Each line below is a short verbatim quotation with its upstream line
number; the file itself is not copied here. See LICENSE-NOTE.md.

- L19: “The exported `render(index)` function is called for each pixel in the strip.”
- L21: “Alternative render functions `render2D(index, x, y)` and `render3D(index, x, y, z)` can also be specified to use when a 2D or 3D pixel map is available.”
- L23: “The exported `beforeRender(delta)` function is called before it is going to render a new frame of pixels to the strip.”
- L23: “You can use `delta` to create animations that run at the same speed regardless of the frame rate.”
- L25: “All numbers in Pixelblaze are a 16.16 fixed-point numbers.”
- L35: “If you export a global variable that is modified inside `render()` normally only the last value will be shown.”
- L43: “To create a slider, export a function that starts with the key word `slider` followed by the name of the slider.”
- L47: “It will also be called with a saved value when the pattern is switched to before rendering occurs.”
- L86: “Create arrays using the `array(size)` function”
- L93: “Arrays are currently the only dynamically allocated memory, and you can't (yet) free them once created.”
- L153: “A sawtooth waveform between 0.0 and 1.0 that loops about every 65.536*`interval` seconds.”
- L159: “Converts a sawtooth waveform `v` between 0.0 and 1.0 to a sinusoidal waveform between 0.0 to 1.0.”
