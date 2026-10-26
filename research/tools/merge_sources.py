#!/usr/bin/env python3
"""Merge research/sources/_fragments/*.md into SOURCES.md.

Entries are grouped into their pre-allocated S-ID block sections and sorted
by ID. Fragments are deleted after a successful merge. Fails loudly on
duplicate IDs or IDs outside every known block.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # research/
SOURCES = ROOT / "SOURCES.md"
FRAGS = ROOT / "sources" / "_fragments"

BLOCKS = [
    (1, 49, "Block S001–S049 — RA-01 Landscape"),
    (50, 99, "Block S050–S099 — RA-02 Color science & high-fidelity output"),
    (100, 149, "Block S100–S149 — RA-03 LED chips & electrical limits"),
    (150, 199, "Block S150–S199 — RA-04 Protocols & transport"),
    (200, 249, "Block S200–S249 — RA-05 Pattern-engine design"),
    (250, 299, "Block S250–S299 — RA-06 Frame pipeline & motion quality"),
    (300, 349, "Block S300–S349 — RA-07 Mapping & topology"),
    (350, 399, "Block S350–S399 — RA-08 Hardware: host-driven tier"),
    (400, 449, "Block S400–S449 — RA-09 Hardware: wearable tier"),
    (450, 499, "Block S450–S499 — RA-10 Audio reactivity"),
    (500, 549, "Block S500–S549 — RA-11 Simulation, preview & dev ergonomics"),
    (550, 599, "Block S550–S599 — RA-12 Prior art & control plane"),
    (600, 699, "Block S600–S699 — Code-reading deep dives"),
    (700, 749, "Block S700–S749 — Code-reading deep dives (Phase 1 additions)"),
    (750, 799, "Block S750–S799 — Synthesis & later additions"),
    (800, 849, "Block S800–S849 — RA-13 ESP-NOW & fleet scaling"),
    (850, 899, "Block S850–S899 — RA-14 Mesh transport alternatives"),
    (900, 949, "Block S900–S949 — RA-15 Decentralized coordination & sync"),
    (950, 999, "Block S950–S999 — RA-16 ESP32-S3 render+radio coexistence"),
    (1000, 1049, "Block S1000–S1049 — RA-17 Fleet ops & mesh gateway"),
    (1050, 1099, "Block S1050–S1099 — RA-18 Wearable bridging"),
    (1100, 1149, "Block S1100–S1149 — RA-19 Embedded test loops (sim/emulation/HIL)"),
    (1150, 1199, "Block S1150–S1199 — RA-20 Agentic feedback loops"),
    (1200, 1249, "Block S1200–S1249 — RA-21 Fleet resilience"),
    (1250, 1299, "Block S1250–S1299 — RA-22 First installation"),
]

ENTRY_RE = re.compile(r"^### \[S(\d+)\]")


def parse(text: str, collect_preamble: bool) -> tuple[str, dict[int, str]]:
    preamble_lines: list[str] = []
    entries: dict[int, list[str]] = {}
    current: list[str] | None = None
    seen_block = False
    for line in text.splitlines():
        m = ENTRY_RE.match(line)
        if m:
            current = entries.setdefault(int(m.group(1)), [])
            if current:
                sys.exit(f"duplicate ID S{m.group(1):>03} within one file")
            current.append(line)
        elif line.startswith("## Block"):
            seen_block = True
            current = None
        elif current is not None:
            current.append(line)
        elif collect_preamble and not seen_block:
            preamble_lines.append(line)
    return (
        "\n".join(preamble_lines).rstrip(),
        {sid: "\n".join(lines).rstrip() for sid, lines in entries.items()},
    )


def main() -> None:
    preamble, entries = parse(SOURCES.read_text(), collect_preamble=True)

    frag_files = sorted(FRAGS.glob("*.md")) if FRAGS.is_dir() else []
    merged_from: list[str] = []
    for frag in frag_files:
        _, frag_entries = parse(frag.read_text(), collect_preamble=False)
        if not frag_entries:
            print(f"warn: {frag.name} contains no entries, skipping")
            continue
        for sid, body in frag_entries.items():
            if sid in entries:
                sys.exit(f"duplicate ID S{sid:03d}: already in SOURCES.md, also in {frag.name}")
            entries[sid] = body
        merged_from.append(f"{frag.name} ({len(frag_entries)})")

    out = [preamble, ""]
    for lo, hi, title in BLOCKS:
        block_ids = sorted(sid for sid in entries if lo <= sid <= hi)
        if not block_ids:
            continue
        out.append(f"## {title}")
        out.append("")
        for sid in block_ids:
            out.append(entries[sid])
            out.append("")
    unplaced = sorted(sid for sid in entries if not any(lo <= sid <= hi for lo, hi, _ in BLOCKS))
    if unplaced:
        sys.exit(f"IDs outside every known block: {unplaced}")

    SOURCES.write_text("\n".join(out).rstrip() + "\n")
    for frag in frag_files:
        frag.unlink()
    print(f"SOURCES.md: {len(entries)} entries total; merged {', '.join(merged_from) or 'nothing'}")


if __name__ == "__main__":
    main()
