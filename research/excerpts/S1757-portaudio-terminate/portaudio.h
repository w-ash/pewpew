// Excerpt: include/portaudio.h lines 185-194, verbatim, at the pin in LICENSE-NOTE.md.


/** Library termination function - call this when finished using PortAudio.
 This function deallocates all resources allocated by PortAudio since it was
 initialized by a call to Pa_Initialize(). In cases where Pa_Initialise() has
 been called multiple times, each call must be matched with a corresponding call
 to Pa_Terminate(). The final matching call to Pa_Terminate() will automatically
 close any PortAudio streams that are still open.

 Pa_Terminate() MUST be called before exiting a program which uses PortAudio.
