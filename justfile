# Checks for pewpew. CI (.github/workflows/ci.yml) runs `just check`.

# Every gate CI runs.
check: lint sources typecheck web studio test

lint:
    uv run ruff check .

# Every cite resolves and ADR evidence follows the archival rule (research/README.md).
sources:
    python3 research/tools/merge_sources.py --check

typecheck:
    uv run basedpyright

# The preview page: install from the lockfile, type-check and test the source
# in web/, then build it into src/pewpew/sinks/web/index.html.
web:
    pnpm -C web install --frozen-lockfile
    pnpm -C web check
    pnpm -C web test
    pnpm -C web build

# The page's Martian font subsets, from their pinned upstream files (tools/fonts.py).
# Run only when the fonts change; fontTools and brotli are for this run alone.
fonts:
    uv run --no-project --with fonttools==4.68.0 --with brotli==1.2.1 python tools/fonts.py

# The studio frontend: install from the lockfile, then biome, tsc and the build
# (`check`) and the unit tests. E2E (`pnpm -C studio-web e2e`) is not in the gate.
studio:
    pnpm -C studio-web install --frozen-lockfile
    pnpm -C studio-web check
    pnpm -C studio-web test

# The L1 suite. Extra arguments go to pytest, e.g. `just test -k "health or room"`.
[positional-arguments]
test *args:
    uv run pytest "$@"

# The L1 suite with more examples a property: the "thorough" Hypothesis
# profile (tests/conftest.py).
[positional-arguments]
test-thorough *args:
    uv run pytest --hypothesis-profile=thorough "$@"

# Before a merge: the gate, the changelog check, and open work.
# The base branch defaults to main; `just ready fx` and `just ready base=fx`
# both set it (just passes `base=fx` through as a plain positional argument).
ready base="main": check && branches
    scripts/check_changelog.sh {{trim_start_match(base, "base=")}}

# The capture node's firmware (firmware/audio-node), built in the pinned
# ESP-IDF image, as CI's firmware job builds it; extra arguments go to
# idf.py, e.g. `just firmware size`. Needs Docker. Flashing is tier 1 and
# attended (docs/audio.md §8): run `idf.py flash` from an ESP-IDF install.
idf := "espressif/idf:v6.1@sha256:81893c71bb5e570088901f21def8684c25cd2a9020281bd01b843a7655edb18c"

[positional-arguments]
firmware *args:
    docker run --rm -v "$PWD/firmware/audio-node:/project" -w /project {{idf}} idf.py build "$@"

# Unmerged branches, worktrees, uncommitted work, and stashes.
branches:
    python3 scripts/branches.py
