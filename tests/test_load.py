"""`pewpew.load`: a pattern by its gallery name, never by file; and the
path-free wording of a refusal."""

from __future__ import annotations

from pathlib import Path

import pytest

from fakes import Solid
from pewpew import Pattern, Renderer, line
from pewpew.errors import LoadError, scrub, unknown
from pewpew.load import Catalog, gallery, resolve
from pewpew.patterns import Comet


def test_a_name_is_the_gallery_never_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "comet.py").write_text("raise SystemExit('a file ran')\n")
    monkeypatch.chdir(tmp_path)
    assert resolve("comet") is Comet
    assert list(gallery())[:2] == ["plasma", "comet"]  # the gallery's order


@pytest.mark.parametrize("spec", ["Comet", "comet.py", "effects/comet.py", "comet.py:Comet", "nope"])
def test_anything_but_a_gallery_name_is_unknown(spec):
    with pytest.raises(LoadError, match=r"^unknown pattern .*; patterns: colorplasma, comet, fire"):
        resolve(spec)


def test_a_catalog_of_classes_holds_those_names_alone():
    catalog = Catalog({"solid": Solid})
    assert catalog.names == ["solid"] and catalog.resolve("solid") is Solid
    with pytest.raises(LoadError, match="^unknown pattern 'comet'; patterns: solid$"):
        catalog.resolve("comet")
    assert Catalog().names == sorted(gallery())


def test_an_unknown_name_lists_the_known_ones_by_their_plural():
    assert unknown("address", "x", ["a"]) == "unknown address 'x'; addresses: a"
    assert unknown("op", "kaleidoscope", ["kaleid"], suggest=True, aliases={"Kaleidoscope": "kaleid"}) == (
        "unknown op 'kaleidoscope' (did you mean 'kaleid'?); ops: kaleid"
    )


HOME = str(Path.home())


@pytest.mark.parametrize("text, scrubbed", [
    (f"cannot import name 'Param' from 'pewpew' ({HOME}/src/pewpew/__init__.py)",
     "cannot import name 'Param' from 'pewpew'"),
    ("cannot import name 'A' from partially initialized module 'b' (most likely due to a circular import) (/x/b.py)",
     "cannot import name 'A' from partially initialized module 'b' (most likely due to a circular import)"),
    ("no table in /private/var/folders/table.bin, so none", "no table in …, so none"),
    (f"cannot write {HOME}", "cannot write ~"),
    ("'/etc/passwd' is not a pattern", "'…' is not a pattern"),
    ("from 'mod' (/Volumes/Light Drive/My Patterns/mod.py)", "from 'mod'"),
    ("no table in /Volumes/Light Drive/table.bin, so none", "no table in …, so none"),
    ("40/60 fps from 10.0.0.0/24 at http://10.0.0.11/json/info, 0.0..1.0", None),
    ("effects/mine.py: /24", None),
])
def test_scrub_drops_every_absolute_path_and_keeps_the_rest(text, scrubbed):
    assert scrub(text) == (text if scrubbed is None else scrubbed)


def test_an_os_error_is_described_without_its_path(tmp_path):
    """An OSError's text carries its filename; the description that reaches
    the preview socket keeps only the reason."""
    missing = tmp_path / "secret" / "table.bin"

    class Opens(Pattern):
        def render(self, x, y, z, index):
            open(missing)  # noqa: SIM115  raises before a file opens

    renderer = Renderer(Opens(), line(4))
    renderer.step(1 / 60)
    text = str(renderer.error)
    assert text.endswith("FileNotFoundError: No such file or directory")
    assert str(missing) not in text and "secret" not in text
