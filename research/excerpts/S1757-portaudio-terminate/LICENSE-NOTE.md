# Excerpt provenance — S1757 Pa_Terminate closes every open stream

- project: PortAudio
- license: MIT-style (upstream LICENSE.txt)
- pinned: PortAudio/portaudio@0dce0e9cf5c2235f04f2caeb2ca09db358cb8a6e
- paths / contents:
  - `include/portaudio.h` lines 185–194 (fetched at the pin on 2026-11-06): the `Pa_Terminate`
    comment, L187–192, ending "The final matching call to Pa_Terminate() will automatically close
    any PortAudio streams that are still open."
- why excerpted: ADR-009's 2026-11-06 amendment "live input" re-enumerates devices only with no
  stream open.

Licence text: `../LICENSES/MIT.txt`, with the upstream notice "Copyright (c)
1999-2002 Ross Bencina and Phil Burk" (the header of `include/portaudio.h` at
the pin). The same header adds non-binding requests, kept here as it asks:
"Any person wishing to distribute modifications to the Software is requested
to send the modifications to the original developer so that they can be
incorporated into the canonical version. It is also requested that these
non-binding requests be included along with the license above."
