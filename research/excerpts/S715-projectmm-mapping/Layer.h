    /// Cold path, called from onBuildState after physical dimensions are known.
    /// Applies each enabled static modifier to compute the logical box, allocates
    /// the buffer and LUT, and for each logical light asks the modifier chain for
    /// physical destinations. Without a modifier AND with a dense grid in natural
    /// order (no sparse, no serpentine, x-then-y-then-z) it sets an identity mapping
    /// and skips the table entirely (the FPS floor for the common case).
    /// Precondition: physicalWidth_/Height_/Depth_ must be set (call from onBuildState).
    void rebuildLUT() {
        lutSkipped_ = false;
        clearStatus();  // re-evaluated below if a degrade path is taken

        // Fold the box through each enabled STATIC modifier in child order — no fixed
        // chain array (Dynamic over fixed-size, architecture.md): the size pass here and
        // the per-light fold below both iterate the Layer's own (dynamic, heap-grown)
        // child list, filtering for enabled static modifiers inline, the way MoonLight's
        // `for node : nodes` does. modifyLogicalSize mutates the running box AND lets the
        // modifier stash its own output size (MoonLight's modifierSize cache), so in the
        // per-light fold each modifier reads the box at ITS OWN stage from itself.
        // A dynamic modifier (Rotate, hasModifyLive) is excluded — it remaps per frame in
        // Layer::loop's live pass, not baked into the mapping.
        uint8_t staticCount = 0;
        hasLive_ = false;
        Coord3D box{physicalWidth_, physicalHeight_, physicalDepth_};
        for (uint8_t i = 0; i < childCount(); i++) {
            if (child(i)->role() != ModuleRole::Modifier || !child(i)->enabled()) continue;
            auto* m = static_cast<ModifierBase*>(child(i));
            if (m->hasModifyLive()) { hasLive_ = true; continue; }   // dynamic: per-frame, not baked
            m->modifyLogicalSize(box);
            clampLogical(box);
            staticCount++;
        }

        // Final logical box = the running box after the last static modifier.
        Coord3D logical = box;
        width_ = logical.x; height_ = logical.y; depth_ = logical.z;

        const Coord3D phys{physicalWidth_, physicalHeight_, physicalDepth_};
        const nrOfLightsType boxCount    = cellCount(phys);
        const nrOfLightsType logicalCount = cellCount(logical);
        const nrOfLightsType driverCount = physicalLightCount();   // == Layouts::totalLightCount()
        const bool dense = (driverCount == boxCount);

        // Fast path — no static modifiers, dense grid in natural order: box cell i
        // IS driver light i, so the mapping is the identity memcpy. This is the FPS
        // floor for the common case; keep it before any allocation.
        if (staticCount == 0 && dense && isNaturalOrder()) {
            lut_.setIdentity(boxCount);
            allocateBuffer(boxCount);
            return;
        }

        // General build — fold each PHYSICAL light through the static chain to its
        // logical cell, accumulating the physical (driver) index onto that cell.
        // N physical lights folding onto one logical cell IS the fan-out (Multiply),
        // so each physical light contributes at most ONE destination — maxDest is
        // exactly driverCount, no product, no overflow ceiling.
        if (!buildFoldedLUT(logical, logicalCount, driverCount)) {
            // OOM in the fold build — degrade to identity (correct, not crash).
            lutSkipped_ = true;
            setStatus("modifier mapping skipped — not enough memory", Severity::Warning);
            width_ = physicalWidth_; height_ = physicalHeight_; depth_ = physicalDepth_;
            lut_.setIdentity(boxCount);
            allocateBuffer(boxCount);
            return;
        }
        allocateBuffer(logicalCount);
    }

    // Sentinel: a box cell that is not a real light (no driver index).
    static constexpr nrOfLightsType kNoDriver = static_cast<nrOfLightsType>(-1);

    // Does the layout emit lights in natural box order — driver index i == box cell i (x fastest,
    // then y, then z)? Measured, not declared: one allocation-free forEachCoord pass over the same
    // coords the build would walk, so there's a single source of truth (the coords) and no
    // per-layout hint to keep in sync. True → the dense memcpy fast path is valid; false → a
    // reordered grid (serpentine) needs the folded LUT. Only meaningful for a dense layout
    // (boxCount == driverCount); a sparse layout always routes to the folded build.
    bool isNaturalOrder() const {
        struct Ctx { lengthType w, h; bool ok; };
        Ctx ctx{physicalWidth_, physicalHeight_, true};
        layouts_->forEachCoord([](void* c, nrOfLightsType driverIdx, lengthType x, lengthType y, lengthType z) {
            auto* k = static_cast<Ctx*>(c);
            if (!k->ok) return;   // once a mismatch is found the answer is settled; skip the rest
            nrOfLightsType box = static_cast<nrOfLightsType>(z) * k->w * k->h
                               + static_cast<nrOfLightsType>(y) * k->w + x;
            if (driverIdx != box) k->ok = false;
        }, &ctx);
        return ctx.ok;
    }

    // Build the mapping by folding PHYSICAL lights to LOGICAL cells (physical→logical).
    // Our MappingLUT is a CSR keyed by logical index, and setMapping demands sequential
    // in-order writes — but folding scatters onto arbitrary, repeated logical indices.
    // So this is the textbook counting-sort CSR build: pass A counts destinations per
    // logical cell, prefix-sum to offsets, pass B scatters, then replay through
    // setMapping in logical order. Two forEachCoord passes + a counts/dests scratch,
    // all on the cold rebuild path; the hot-path read (forEachDestination) is unchanged.
    // Returns false on OOM (caller degrades to identity).
    bool buildFoldedLUT(const Coord3D& logical,
                        nrOfLightsType logicalCount, nrOfLightsType driverCount) {
        if (logicalCount == 0 || driverCount == 0) { lut_.setIdentity(0); return true; }

        // Scratch: per-logical-cell counts (then reused as the write cursor) and the
        // scattered driver indices. Each physical light yields ≤1 destination, so the
        // dests array is driverCount-sized — the tight, overflow-free ceiling.
        auto* counts = static_cast<nrOfLightsType*>(
            platform::alloc(static_cast<size_t>(logicalCount + 1) * sizeof(nrOfLightsType)));
        auto* dests = static_cast<nrOfLightsType*>(
            platform::alloc(static_cast<size_t>(driverCount) * sizeof(nrOfLightsType)));
        if (!counts || !dests) {
            if (counts) platform::free(counts);
            if (dests) platform::free(dests);
            return false;
        }
        for (nrOfLightsType i = 0; i <= logicalCount; i++) counts[i] = 0;

        // One callback does both passes. It folds the physical coord through the chain
        // (the Layer's own children — enabled static modifiers, in order, no array) to a
        // logical index (or skips it if a modifier rejects it or it lands out of box —
        // guarded, never trusted), then either counts it (pass A) or writes the driver
        // index at the cell's cursor (pass B). Everything travels through the forEachCoord
        // void* ctx, so the lambda captures nothing (it's a function ptr).
        struct FoldCtx {
            Layer* self;   // for the dynamic child list (the modifier chain)
            Coord3D logical; nrOfLightsType logicalCount;  // final box, for the flatten + guard
            nrOfLightsType* counts;   // pass A: per-cell count.  pass B: per-cell write cursor.
            nrOfLightsType* dests;    // pass B only.
            bool scatter;
        } fctx{this, logical, logicalCount, counts, dests, /*scatter=*/false};

        auto onCoord = [](void* c, nrOfLightsType driverIdx, lengthType x, lengthType y, lengthType z) {
            auto* f = static_cast<FoldCtx*>(c);
            Coord3D pos{x, y, z};
            Layer* self = f->self;
            for (uint8_t i = 0; i < self->childCount(); i++) {
                if (self->child(i)->role() != ModuleRole::Modifier || !self->child(i)->enabled()) continue;
                auto* m = static_cast<ModifierBase*>(self->child(i));
                if (m->hasModifyLive()) continue;                 // dynamic: not in the static fold
                if (!m->modifyLogical(pos)) return;               // rejected — no logical source
            }
            if (pos.x < 0 || pos.x >= f->logical.x || pos.y < 0 || pos.y >= f->logical.y ||
                pos.z < 0 || pos.z >= f->logical.z) return;                          // defensive
            const nrOfLightsType li =
                static_cast<nrOfLightsType>(pos.z) * static_cast<nrOfLightsType>(f->logical.x) * static_cast<nrOfLightsType>(f->logical.y) +
                static_cast<nrOfLightsType>(pos.y) * static_cast<nrOfLightsType>(f->logical.x) +
                static_cast<nrOfLightsType>(pos.x);
            if (li >= f->logicalCount) return;                                       // defensive
            if (f->scatter) f->dests[f->counts[li]++] = driverIdx;  // pass B: write at the cursor
            else            f->counts[li]++;                        // pass A: bump the count
        };

        // Pass A — count.
        layouts_->forEachCoord(onCoord, &fctx);

        // Prefix-sum counts → offsets (counts[li] becomes the start of cell li's run).
        nrOfLightsType running = 0;
        for (nrOfLightsType i = 0; i < logicalCount; i++) {
            nrOfLightsType c = counts[i];
            counts[i] = running;
            running += c;
        }
        counts[logicalCount] = running;   // total destinations

        // Pass B — scatter. counts[] is now the per-cell write cursor (offsets advance).
        fctx.scatter = true;
        layouts_->forEachCoord(onCoord, &fctx);

        // Pass B advanced each cell's cursor to the END of its run, so counts[i] now
        // holds the end offset of cell i — which equals the START offset of cell i+1.
        // The run for cell i is therefore [counts[i-1], counts[i]) with counts[-1]=0,
        // i.e. the `start` cursor below. dests[] is already laid out in this exact CSR
        // order, so replaying it through setMapping in logical order is a straight copy.
        if (!lut_.build(logicalCount, running)) {   // running == total destinations
            platform::free(counts);
            platform::free(dests);
            return false;
        }
        nrOfLightsType start = 0;
        for (nrOfLightsType i = 0; i < logicalCount; i++) {
            nrOfLightsType end = counts[i];          // end of cell i's run
            lut_.setMapping(i, &dests[start], static_cast<nrOfLightsType>(end - start));
            start = end;
        }
        lut_.finalize();
        platform::free(counts);
        platform::free(dests);
        return true;
    }
