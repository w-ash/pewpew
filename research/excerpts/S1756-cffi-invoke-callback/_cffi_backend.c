// Excerpt: src/c/_cffi_backend.c lines 6278-6290, verbatim, at the pin in LICENSE-NOTE.md.
}

static void invoke_callback(ffi_cif *cif, void *result, void **args,
                            void *userdata)
{
    save_errno();
    {
        PyGILState_STATE state = gil_ensure();
        general_invoke_callback(1, result, (char *)args, userdata);
        gil_release(state);
    }
    restore_errno();
}
