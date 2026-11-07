# Third-party excerpts

The files in this folder are not under pewpew's Apache-2.0 licence. Each
`S###-name/` folder holds verbatim lines from an upstream project, kept so
that line-anchored research cites survive upstream changes (archival rule,
`research/README.md`). Each folder stays under its upstream licence, which
its `LICENSE-NOTE.md` names with the upstream copyright notice. ADR-012
rule 1 applies: GPL and EUPL code here is never copied into pewpew.

`LICENSES/` holds the full text of each licence the folders use:

| file | used by | text from |
|---|---|---|
| `Apache-2.0.txt` | S1300, S1777 | apache.org [S1850] |
| `EUPL-1.2.txt` | S645, S1250, S1771 | WLED's `LICENSE` at the pins in S1250 and S645, after its two-line notice |
| `GPL-2.0.txt` | S1301 | gnu.org [S1856] |
| `GPL-3.0.txt` | S630, S670, S715, S1359, S1759 | gnu.org [S1855]; the same as marimapper's and projectMM's `LICENSE` at their pins |
| `MIT.txt` | S600, S615, S660, S681, S682, S683, S700, S716, S1351, S1754, S1756, S1757 | the standard MIT text; each folder's note gives its copyright line |

`S680-pixelblaze-docs/` is the exception: its upstream has no licence, so
it holds only brief quotations, under fair use [S1857].
