# A4. Prior art for fixture, placement, power and controller models (Explore agent, Sonnet, 2026-10-22)

Brief: how GDTF/MVR, Open Fixture Library, xLights, WLED, FastLED, ESPHome, Chromatik and QLC+
model fixtures, placement, wiring, power and controllers, and what separation they settle on.

# Research report: how existing standards and tools model LED fixtures, wiring and controllers (2026-10-22)

Several sources are partial. Gaps are marked "not found". I ran no `fd` or `ast-grep` commands because this was web-only research.

## 1. GDTF and MVR
- **GDTF version.** The spec text I read is "GDTF Version 1.2 Draft 1" on the spec repo's main branch, `<GDTF DataVersion="1.2">`, with no date shown (https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md). A developer page equates GDTF 1.2 with DIN SPEC 15800:2022-02 (https://gdtf-share.com/help/developers/gdtf_1_2/). That makes the standard older than 12 months. I found no 1.3 or newer version, but I did not check gdtf.eu.
- **Fixture type.** `FixtureType` has these children in this order: AttributeDefinitions, Wheels, PhysicalDescriptions, Models, Geometries, DMXModes, Revisions, FTPresets, Protocols ([gdtf-spec.md](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md)).
  - The geometry types include Geometry, Axis, Beam, GeometryReference, Display, WiringObject, Inventory, Structure and Support.
  - `Beam` carries PowerConsumption (default 1000 W) and LuminousFlux.
  - `PhysicalDescriptions` holds Emitters (Name, Color, DominantWaveLength, DiodePart), ColorSpace, Properties (Weight, OperatingTemperature, PowerConsumption) and an obsolete Connectors list.
- **Connectors and power.** The old `Connectors` list is obsolete. `WiringObject` replaces it, with these attributes ([gdtf-spec.md](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md)):
  - `ConnectorType`, `ComponentType` (Input, Output, PowerSource, Consumer, Fuse and network variants), `SignalType`, `PinCount`.
  - Consumer: `ElectricalPayLoad`, `VoltageRangeMin` and `VoltageRangeMax`.
  - PowerSource: `MaxPayLoad` and `Voltage`.
  - Fuse: `FuseCurrent`.
  - `PinPatch` links pins between wiring objects.
- **DMX modes.** A mode has Name, Description and Geometry, plus `DMXChannels` (each with `DMXBreak`, `Offset` and `Geometry`), optional `Relations` and optional `FTMacros` ([gdtf-spec.md](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md)).
- **Pixel bar.** The spec's Listing 1 puts a `Pixel` geometry in the mode, with channels `ColorAdd_R`, `ColorAdd_G` and `ColorAdd_B` at offsets 1 to 3 and `DMXBreak="Overwrite"`. `GeometryReference` repeats that geometry, with one Break child per distinct DMX break ([gdtf-spec.md](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md)).
  - Inference: a 64-pixel bar would be one referenced Pixel geometry repeated 64 times with an offset each. I did not see a complete example in the text I read.
  - GDTF has no pixel-protocol or chipset concept. It is DMX-only, though 1.2 reportedly adds OSC support (https://alia.com.au/?p=48994).
- **MVR 1.6** (DIN SPEC 15801, undated; https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md). It is a zip containing `GeneralSceneDescription.xml` plus the referenced GDTF files.
  - A Fixture node has `GDTFSpec`, `GDTFMode`, `Matrix` (right-handed, Z-up, 1 unit = 1 mm) and `Addresses`.
  - Addresses are keyed by break, as an absolute integer or `Universe.Address`.
  - A fixture also has `FixtureID`, `UnitNumber`, `Position` (a grouping), `Protocols` and `Network` (ip, hostname), and `multipatch`.
  - Layers are containers. A layer matrix may only translate vertically.
  - Geometry is not stored on the instance; it comes from the GDTF file.

## 2. Open Fixture Library
Source: schemas at https://github.com/OpenLightingProject/open-fixture-library/tree/cfcb0c5b0cbb4aa0b058492a4d8586c53503b2ff/schemas/ (fixture.json is v12.6.0).
- `physical` exists at the top level and per mode. Fields: `dimensions` ([w,h,d] in mm), `weight` (kg), `power` (W), `powerConnectors` (each "input only", "output only" or "input and output"), `DMXconnector` (enum), `bulb`, `lens` and `matrixPixels` (dimensions and spacing).
- A mode has `name`, `channels` and an optional `physical`.
- The `matrix` object takes `pixelCount` or `pixelKeys` (nested arrays in Z, Y, X order), plus optional `pixelGroups` constrained by x, y, z or name.
- A mode's channel list can contain a block `{insert: "matrixChannels", repeatFor: eachPixelABC | eachPixelGroup | [keys], channelOrder: perPixel | perChannel, templateChannels: [...]}`.
- Template channel names contain `$pixelKey`.
- There is no chipset or protocol concept. Power connectors are mains types (IEC, powerCON), not low-voltage LED connectors. Electrical fields are only `power` (W) and the connectors; voltage and current are not found.

## 3. xLights
- **Model types.** The layout toolbar lists Single Line, Poly Line, Matrix, Tree and others, plus Custom (https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models). Single Line is a two-point model. How nodes are laid out along it is not described, and Poly Line and Custom are not explained either.
- **Strings and nodes.** The settings are `# of Strings`, `Nodes/String` and `Lights/Node`. String types include RGB Nodes (3 channels per node), WRGB Nodes (4) and RGBWW Nodes (5) (https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/model-attribute.md; no date).
- **Connection properties.** `Protocol`, `Port`, `Null Pixels`, `Brightness`, `Gamma` and `Color Order` are documented in the same page, each as an optional override of the controller setting. `Smart Remote`, `Reverse` and `Group Count` are not covered there, and I found no other source for them (not found).
- **Start channel.** It can be absolute, universe-based, relative to another model, or generated from the controller, port and chaining.
- **Controller properties.** Type (USB, Ethernet or Null), Name, Id, Active, and Vendor, Controller and Variant (https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks). Vendor, Controller and Variant determine the supported protocols and the maximum universes or channels. Config is saved in `xlights_networks.xml`.
- **Capability definitions.** No schema or file found. A GitHub issue mentions `MaxPixelPortChannels` and `MaxSerialPortChannels` as separate fields and says a per-port max list cannot be expressed (https://github.com/xLightsSequencer/xLights/issues/6987, closed 2026-09-21). `SupportedProtocols` and port counts were not found.

## 4. WLED
- **Sources.** Read from source, not the docs: the kno.wled.ge remote-config page returned a 404. Files: https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/cfg.cpp, [`bus_manager.h`](https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/bus_manager.h) and [`const.h`](https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/const.h).
- **Per-bus keys in `hw.led.ins[]`:**

| Key | Default | Notes |
|---|---|---|
| `pin` | none | array of up to 5 GPIOs |
| `len` | 1 | |
| `start` | 0 | |
| `order` | 0 | upper nibble holds the white swap |
| `skip` | 0 | |
| `type` | WS2812_RGB | |
| `rev` | false | |
| `ref` | false | stored in bit 7 of `type` |
| `freq` | 0 | |
| `rgbwm` | manual only | |
| `ledma` | `LED_MILLIAMPS_DEFAULT` | per-LED current |
| `maxpwr` | derived from the global limit | per-bus current cap |
| `drv` | 0 | 0 = RMT, 1 = I2S |
| `text` | empty | |

- **Top-level keys in `hw.led`:** `total`, `maxpwr`, `rgbwm`, `cct`, `cr`, `cb`, `fps`. `ledma` is not read at the top level.
- **Type table.** Types are numeric codes in ranges: digital 16 to 39, analog 41 to 47, 2-pin 48 to 63, HUB75 64 to 71, network 80 to 95 ([`const.h`](https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/const.h)).
  - SK6812_RGBW is 30. UCS8903 (26) and UCS8904 (29) exist.
  - Channels per pixel are computed as `hasWhite + 3*hasRGB + hasCCT`. `is16bit()` covers UCS8903, UCS8904 and SM16825.
  - Inference: a UCS1903 tube would probably map to a generic RGB type such as WS2812_RGB, but I did not confirm that.
  - Default `LED_MILLIAMPS_DEFAULT` value: not found.

## 5. Other chipset descriptions
- **FastLED** (https://github.com/FastLED/FastLED/blob/2381daee98d53e04e7a4e57634b719be768ead90/src/chipsets.h):
  - Timing is three nanosecond values, T1, T2 and T3, in named presets. SK6812 is (300, 600, 300) and `TIMING_UCS1903B_800KHZ` is (400, 450, 450).
  - Reset or wait is a separate template argument. Color order (`EOrder`) is a template parameter.
  - RGBW is a wrapper (`RGBWEmulatedController`) that packs 4 bytes into 3, with `Rgbw` modes. WS2814 and LC8816E are fixed-RGBW chipsets.
- **ESPHome** (https://esphome.io/components/light/esp32_rmt_led_strip/, undated, site version 2026.10.0): options are `pin`, `num_leds`, `chipset` (WS2811, WS2812, SK6812, APA106, SM16703), `channel_colors` (a W in the string means RGBW), `bit0_high`, `bit0_low`, `bit1_high`, `bit1_low`, `reset_high` and `reset_low`. `rgb_order` and `is_rgbw` do not appear on this page.
- **Chromatik `.lxf`** (https://chromatik.co/guide/custom-fixtures, undated, appears to match Chromatik 1.1.0):
  - Top-level keys: `label`, `tags`, `transforms`, `parameters`, `components`, `outputs`, `meta`.
  - Components are `point`, `points`, `strip` (numPoints, spacing, yaw, pitch, roll), `arc`, a `class` reference, or a nested fixture.
  - Transforms apply in order. Outputs have `protocol`, `host`, `universe`, `channel`, `byteOrder`, `start`, `num`, `stride`, `reverse` and `segments`.
  - Fixtures bundle geometry, wiring and output in one file.
- **QLC+** (https://github.com/mcallegari/qlcplus/blob/a706b2adfe9273b167b3ea04e6a0d53e9641bf67/resources/schemas/fixture.xsd): `Physical` holds `Bulb`, `Dimensions` (units unspecified), `Lens`, `Focus`, `Layout` and `Technical`. `Technical` has `PowerConsumption` (integer, no units given) and `DmxConnector`.

## 6. Electrical prior art
- GDTF 1.2 `WiringObject` is the only standard I found with first-class electrical objects: power source with voltage and max payload, consumer with payload and voltage range, fuse, and pin-level patching ([gdtf-spec.md](https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md#L1612-L1646), 2022). It has no cable conductor size or length.
- Voltage-drop and injection calculators exist, but they are web calculators, not formats. They take strip length, W/m, wire gauge and feed style (https://www.diysmarthomehub.com/?p=18747, snippet only, unopened). Spiker Lights' power calculator is also cited (unverified).
- WLED models only current: per-LED mA and a per-bus limit (section 4).
- A format with power supplies, injection points, connectors with current ratings or cable gauge and length as objects: not found.

## 7. Synthesis
- **Recurring entities.**
  - Fixture type and fixture instance (GDTF/MVR, OFL, QLC+, `.lxf` as a template).
  - Geometry, emitter and pixel (GDTF Beam, OFL pixelKeys, xLights node and string, `.lxf` points).
  - Chipset or protocol (WLED type, FastLED timing, ESPHome chipset, xLights protocol).
  - Connector (GDTF WiringObject, OFL).
  - Controller and output port (xLights, WLED bus, `.lxf` outputs).
  - Power supply (GDTF PowerSource only).
- **Catalog versus scene.** GDTF and MVR separate them most cleanly. GDTF is the catalog: geometry, modes, electrical and connector data. MVR is the scene: placement matrix, address and network. OFL and QLC+ are catalog only. xLights puts both in its show directory ([xLights manual](https://manual.xlights.org/xlights/chapters/chapter-two-quick-start-guide/defining-the-show-directory)): model definitions, layout, and port assignments to a controller that is chosen by vendor and variant. WLED `cfg.json` is purely a controller-side wiring record. `.lxf` mixes both in one file.
- **Inference: patterns to reuse.**
  - Keep three layers: fixture type (pixel count, chipset, bytes per pixel, voltage, watts, connectors); placement (a transform plus the type, as in MVR); and a wiring graph.
  - In that graph, controller outputs, chains and supplies are nodes, and connector-to-connector links are edges. Every format here puts the port, start, count, order and reverse fields on that link, not on the fixture.
  - Pixel format (chipset, bytes per pixel, color order, timing) can be a separate small catalog, as WLED's type table and FastLED's timing traits are.
  - Electrical data (supply, injection, cable gauge and length) is unmodeled elsewhere, so this part of the model is original design work.

## Sources

- https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md
- https://gdtf-share.com/help/developers/gdtf_1_2/
- https://alia.com.au/?p=48994
- https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/mvr-spec.md
- https://github.com/OpenLightingProject/open-fixture-library/tree/cfcb0c5b0cbb4aa0b058492a4d8586c53503b2ff/schemas/
- https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models
- https://manual.xlights.org/xlights/chapters/chapter-four-tabs/models/model-attribute.md
- https://manual.xlights.org/xlights/chapters/chapter-four-set-up/lighting-networks
- https://github.com/xLightsSequencer/xLights/issues/6987
- https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/cfg.cpp
- https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/bus_manager.h
- https://github.com/wled/WLED/blob/3cdb5108b924ec26dec81d2c92962b70b185bd01/wled00/const.h
- https://github.com/FastLED/FastLED/blob/2381daee98d53e04e7a4e57634b719be768ead90/src/chipsets.h
- https://esphome.io/components/light/esp32_rmt_led_strip/
- https://chromatik.co/guide/custom-fixtures
- https://github.com/mcallegari/qlcplus/blob/a706b2adfe9273b167b3ea04e6a0d53e9641bf67/resources/schemas/fixture.xsd
- https://github.com/mvrdevelopment/spec/blob/098d3791f77f0895bd859adf01864b4826e2006f/gdtf-spec.md#L1612-L1646
- https://www.diysmarthomehub.com/?p=18747
