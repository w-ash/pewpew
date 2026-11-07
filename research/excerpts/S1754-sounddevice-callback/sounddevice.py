# Excerpt: src/sounddevice.py lines 840-850, verbatim, at the pin in LICENSE-NOTE.md.
            if kind == 'input':
                iparameters = parameters
            elif kind == 'output':
                oparameters = parameters

        ffi_callback = _ffi.callback('PaStreamCallback', error=_lib.paAbort)

        if callback is None:
            callback_ptr = _ffi.NULL
        elif kind == 'input' and wrap_callback == 'buffer':

