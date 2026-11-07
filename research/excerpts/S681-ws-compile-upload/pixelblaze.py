    class messageTypes(IntEnum):
        """Types of binary messages sent and received by a Pixelblaze.  The first byte of a binary frame contains the message type."""
        putSourceCode = 1  # from client to PB
        putByteCode = 3  # from client to PB
        previewImage = 4  # from client to PB
        previewFrame = 5  # from PB to client
        getSourceCode = 6  # from PB to client
        getProgramList = 7  # from client to PB
        putPixelMap = 8  # from client to PB
        ExpanderConfig = 9  # from client to PB *and* PB to client
        # SPECIAL MESSAGE TYPES: These aren't part of the Pixelblaze protocol; they're flags for the state machine.
        specialConfig = -1
        specialStats = -2

    class frameTypes(Flag):
        """Continuation flags for messages sent and received by a Pixelblaze.  The second byte of a binary frame tells whether this packet is part of a set."""
        frameNone = 0
        frameFirst = 1
        frameMiddle = 2
        frameLast = 4
    def compilePattern(self, patternCode: str, allow_cache: bool = False) -> bytes:
        """Compiles pattern sourcecode into a bytecode blob.

        Args:
            patternCode (str): The PBscript sourcecode of the pattern.
            allow_cache (bool): If True, use cached compiler if available. Defaults to False for backwards compatibility.

        Returns:
            bytes: a compiled blob of bytecode, ready to send to the Pixelblaze using `sendPatternToRenderer()`.
        """

        def _get_compiler_cache_dir():
            """Get the compiler cache directory."""
            import sys
            if sys.platform == 'win32':
                cache_dir = pathlib.Path.home() / 'AppData' / 'Local' / 'pixelblaze' / 'compiler_cache'
            else:
                cache_dir = pathlib.Path.home() / '.config' / 'pixelblaze' / 'compiler_cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir

        def _get_cached_compiler(version: str):
            """Get cached compiler code for a specific version."""
            try:
                cache_file = _get_compiler_cache_dir() / f"{version}.js"
                if cache_file.exists():
                    return cache_file.read_text()
            except Exception:
                pass
            return None

        def _cache_compiler(version: str, compiler_code: str):
            """Cache compiler code for future use."""
            try:
                cache_file = _get_compiler_cache_dir() / f"{version}.js"
                cache_file.write_text(compiler_code)
            except Exception:
                pass

        # Firmware-dependent adapters.
        def getSubstring(text: str, startValue: str, endValue: str):
            start = text.index(startValue)
            finish = text.index(endValue, start)
            return text[start:finish]

        def extractCompiler(webUI: str):
            # Search through the script blocks to find the compiler module.
            while len(webUI) > 0:
                before, during, after = webUI.partition("<script>")
                script, during, webUI = after.partition("</script>")
                # Find the compiler.
                if script.find("window.compile") != -1:
                    return script

        def v2Adapter(webUI: str):
            # Extract the model-dependent constants from the webUI.
            components = {}
            components["hardwareVariant"] = ""
            components["extendedOperators"] = getSubstring(webUI, "extendedOperators={", ",constants=")
            components["constants"] = getSubstring(webUI, "constants=", ",lastErrorMarkers=[],")
            components["compiler"] = extractCompiler(webUI)
            return components

        def v3AdapterV1(webUI: str):
            # Extract the model-dependent constants from the webUI.
            components = {}
            components["hardwareVariant"] = getSubstring(webUI, "var hardwareVariant=", ",")
            components["extendedOperators"] = getSubstring(webUI, "extendedOperators={", "var constants;")
            components["constants"] = getSubstring(webUI, "var constants;", "var lastErrorMarkers=[],")
            components["compiler"] = extractCompiler(webUI)
            return components

        def v3AdapterV2(webUI: str):
            # Extract the model-dependent constants from the webUI.
            components = {}
            components["hardwareVariant"] = getSubstring(webUI, "var hardwareVariant=", "$('")
            components["extendedOperators"] = getSubstring(webUI, "extendedOperators={", "var constants;")
            components["constants"] = getSubstring(webUI, "var constants;", "var lastErrorMarkers=[],")
            components["compiler"] = extractCompiler(webUI)
            return components

        ",[])"

        def v3AdapterV3(webUI: str):
            # Extract the model-dependent constants from the webUI.
            components = {}
            components["hardwareVariant"] = "var " + getSubstring(webUI, "hardwareVariant=", ",varWatcherPoller") + ";"
            components["extendedOperators"] = getSubstring(webUI, "extendedOperators={", ",lastErrorMarkers=") + ";"
            components["constants"] = "var constants;" + getSubstring(webUI, '"ESP8266"===hardwareVariant&&',
                                                                      ",[])") + ";"
            components["compiler"] = extractCompiler(webUI) + ";"
            return components

        # Determine which adapter to use based on the firmware version.
        def getAdapter(version: float):
            # print("Version is: ", version)
            if version < 3.0:
                # print("Using v2Adapter")
                return v2Adapter
            elif version <= 3.20:
                # print("Using v3AdapterV1")
                return v3AdapterV1
            elif version <= 3.4:
                # print("Using v3AdapterV2")
                return v3AdapterV2
            else:
                # print("Using v3AdapterV3")
                return v3AdapterV3

        # Try to get compiler from cache first if allowed
        version = self.getVersion()
        compiler = None
        if allow_cache:
            compiler = _get_cached_compiler(version)

        if compiler is None:
            # Download the webUI from the Pixelblaze and extract the pieces we need for compilation.
            webUI = gzip.decompress(self.getFile("/index.html.gz")).decode('utf-8-sig')
            # DEBUG BLOCK -- REMOVE BEFORE COMMITTING
            # print(webUI.encode('utf-8-sig'))
            # quit(0)
            # DEBUG BLOCK -- REMOVE BEFORE COMMITTING
            components = getAdapter(float(version))(webUI)
            # print("Hardware Variant: ", components["hardwareVariant"].encode('utf-8-sig'))
            # print("Constants: ", components["constants"].encode('utf-8'))
            # print("Extended Operators: ", components["extendedOperators"].encode('utf-8'))
            # print("Compiler: ", components["compiler"].encode('utf-8-sig'))

            # Build up the compilation environment from bits and pieces.
            compiler = 'window = {};\nvar predefinedGlobals = ["pixelCount"];\n' + components["hardwareVariant"] + '\n' + \
                       components["constants"] + '\n' + components["extendedOperators"] + '\n' + components[
                           "compiler"] + '\n' + """
            const compilePattern = (src) => {
                try {
                    compilerOptions = { predefinedGlobals: predefinedGlobals, extendedOperators: extendedOperators, constants: constants }
                    program = window.compile(src, compilerOptions);

                    //  Get rid of a few recursive properties that inhibit serialization.
                    delete program.parent; delete program.breaks; delete program.continues; delete program.placeholders; delete program.placeholder;
                    program.blocks.forEach(function (v) { delete v.parent; delete v.breaks; delete v.continues; delete v.placeholders; delete v.placeholder; });
                    program.sourceBits.forEach(function (v) { delete v.short; v.start = {}; v.end = {}; });
                    program.sourceBits.forEach(function (v) { if (v.loc != null) for (const [key, value] of Object.entries(v.loc.start)) { v.start[key] = value; } });
                    program.sourceBits.forEach(function (v) { if (v.loc != null) for (const [key, value] of Object.entries(v.loc.end)) { v.end[key] = value; } });
                    program.sourceBits.forEach(function (v) { delete v.loc; });

                    //  Rearrange a few properties for easier access from Python.
                    function surfaceList(list) { temp = Object.keys(list).reduce(function (r, k) { return r.concat(list[k]); }, []); return temp; }
                    program.exports = surfaceList(program.exports);
                    program.identifiers = surfaceList(program.identifiers);
                    program.blocks.forEach(function (v) { v.identifiers = surfaceList(v.identifiers); })

                    return { "status": "OK", "program": program }
                }
                catch (ex) {
                    return { "status": ex.description + " at line " + ex.lineNumber.toString() + " column " + ex.column.toString(), "program": {} }
                }
            }
            """

            # Cache the compiler for future use if caching is enabled
            if allow_cache:
                _cache_compiler(version, compiler)

        # Load the compiler into the interpreter.
        ctx = MiniRacer()
        ctx.eval(compiler)

        # Use the interpreter to run the compiler to convert the sourcecode into the bytecode.
        # set up MiniRacer to give detailed error messages

        result = ctx.call("compilePattern", patternCode)
        if result["status"] != "OK":
            raise ValueError(f'Compilation error: {result["status"]}')

        # Build the results into a bytecode packet.
        program = result["program"]

        # We first need to build the EXPORTS table to determine its size.
        exportSize = 0
        for symbol in program["exports"]: exportSize += 4 + len(symbol["name"]) + 1

        # First DWORD is the size in bytes of the OPCODES section.
        bytecode = int.to_bytes(4 * len(program["compiled"]), 4, "little")

        # Second DWORD is the size in bytes of the EXPORTS section.
        bytecode += int.to_bytes(exportSize, 4, "little")

        # Then come the OPCODES themselves...
        for opcode in program["compiled"]:
            bytecode += int.to_bytes(opcode, 4, "little", signed=True)

        # ...And finally the EXPORTS.
        for symbol in program["exports"]:
            bytecode += int.to_bytes(symbol["address"], 4, "little")
            bytecode += bytes(symbol["name"], "ascii") + int.to_bytes(0, 1, "little")

        # save flag.  (apparently new with v3.5-ish firmware
        # bytecode += int.to_bytes(0, 1, "little")

        # Return the completed bytecode blob.
        return bytecode

    _pattern_id_chars = "23456789ABCDEFGHJKLMNPQRSTWXYZabcdefghijkmnopqrstuvwxyz"
    def makeId(self):
        # build a 17-character ID consisting of characters from the list above
        return ''.join(random.choice(Pixelblaze._pattern_id_chars) for _ in range(17))
    
    @staticmethod
    def isPatternId(id: str):
        return len(id) == 17 and all(c in Pixelblaze._pattern_id_chars for c in id)

    @staticmethod
    def _compress_to_uint8array(text: str) -> bytes:
        """Compress text and encode as Uint8Array format (matching JavaScript LZString.compressToUint8Array)."""
        compressed_str = lzstring.LZString.compress(text) or ""
        return b''.join(
            (ord(c) >> 8).to_bytes(1, 'big') + (ord(c) & 0xFF).to_bytes(1, 'big')
            for c in compressed_str
        )

    @staticmethod
    def _decompress_from_uint8array(data: bytes) -> str:
        """Decompress from Uint8Array format (matching JavaScript LZString.decompressFromUint8Array)."""
        if data is None or len(data) == 0:
            return ""
        # Convert byte pairs back to 16-bit characters
        compressed_str = ''.join(
            chr((data[i] << 8) | data[i + 1])
            for i in range(0, len(data), 2)
        )
        return lzstring.LZString.decompress(compressed_str) or ""

    def calculate_crc32(self, data):
        return binascii.crc32(data) & 0xffffffff

    def sendPatternToRenderer(self, bytecode: bytes, controls: dict = {}):
        """Sends a blob of bytecode and a JSON dictionary of UI controls to the Renderer. Mimics the actions of the webUI code editor.

        Args:
            bytecode (bytes): A valid blob of bytecode as generated by the Editor tab in the Pixelblaze webUI.
            controls (dict, optional): a dictionary of UI controls exported by the pattern, with controlName as the key and controlValue as the value. Defaults to {}.
        """
        # NOTE: crc may only be needed for v3.5+ firmware, but doesn't seem to hurt other versions
        crcVal = self.calculate_crc32(bytecode)
        self.wsSendJson(
            {"pause": True, "setCode": {"size": len(bytecode), "crc": crcVal, "name": "", "id": self.makeId()}},
            expectedResponse="ack")
        self.wsSendBinary(self.messageTypes.putByteCode, bytecode, expectedResponse="ack")
        time.sleep(0.25)
        self.wsSendJson({"setControls": controls})
        self.wsSendJson({"pause": False}, expectedResponse="ack")
        time.sleep(0.25)
