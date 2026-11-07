"""`pewpew.load`: resolving a pattern from a path, a search dir, or the gallery."""

from __future__ import annotations

import inspect
import sys
import textwrap
from pathlib import Path

import pytest

from pewpew import Pattern, Renderer, line, render_sequence
from pewpew.errors import LoadError, scrub, unknown
from pewpew.load import load_file, resolve
from pewpew.patterns import Comet

ONE = '''
import numpy as np
from pewpew import Float, Pattern

class Mine(Pattern):
    level = Float(0.5, 0.0, 1.0, label="Level")

    def render(self, x, y, z, index):
        return np.full((self.n, 3), self.level, dtype=np.float32)
'''


def write(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(textwrap.dedent(body))
    return path


def test_explicit_path_loads_the_single_subclass(tmp_path):
    path = write(tmp_path, "mine.py", ONE)
    loaded = resolve(str(path))
    assert loaded.cls.__name__ == "Mine"
    assert loaded.source == path
    assert loaded.attr is None
    assert loaded.cls.__module__ == "pewpew_user.mine"
    # The class is a real, runnable Pattern on the real engine.
    frames = render_sequence(loaded.cls, line(4), frames=2)
    assert frames.shape == (2, 4, 3)


def test_bare_name_is_the_gallery_never_the_working_directory(tmp_path, monkeypatch):
    write(tmp_path, "comet.py", ONE)
    monkeypatch.chdir(tmp_path)
    assert resolve("comet").cls is Comet
    assert resolve("Comet").cls is Comet  # case-insensitive


def test_gallery_entries_know_their_source_file():
    loaded = resolve("comet")
    assert loaded.source is not None and loaded.source.name == "comet.py"
    assert len(loaded.digest) == 64


def test_search_dir_beats_the_gallery_and_a_path_beats_both(tmp_path):
    write(tmp_path, "comet.py", ONE)
    assert resolve("comet", search_dir=tmp_path).cls.__name__ == "Mine"
    assert resolve("comet").cls is Comet
    (tmp_path / "sub").mkdir()
    other = write(tmp_path / "sub", "x.py", ONE)
    assert resolve(str(other), search_dir=tmp_path).source == other


def test_search_dir_without_a_match_falls_through_to_the_gallery(tmp_path):
    assert resolve("comet", search_dir=tmp_path).cls is Comet


def test_an_unknown_name_lists_the_known_ones_by_their_plural():
    assert unknown("address", "x", ["a"]) == "unknown address 'x'; addresses: a"
    assert unknown("op", "kaleidoscope", ["kaleid"], suggest=True, aliases={"Kaleidoscope": "kaleid"}) == (
        "unknown op 'kaleidoscope' (did you mean 'kaleid'?); ops: kaleid"
    )


def test_unknown_name_lists_the_gallery():
    with pytest.raises(LoadError, match="unknown pattern 'nope'; patterns: colorplasma, comet, fire"):
        resolve("nope")


def test_missing_file_is_a_file_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve(str(tmp_path / "gone.py"))


def test_colon_name_picks_among_several_classes(tmp_path):
    path = write(
        tmp_path,
        "two.py",
        ONE
        + '''
class Other(Mine):
    pass
''',
    )
    with pytest.raises(LoadError, match=r"defines 2 Pattern classes \(Mine, Other\); pick one with :ClassName"):
        resolve(str(path))
    assert resolve(f"{path}:Other").cls.__name__ == "Other"
    assert resolve(f"{path}:Other").attr == "Other"
    with pytest.raises(LoadError, match="'Nope' is not a Pattern subclass"):
        resolve(f"{path}:Nope")


def test_a_base_imported_from_a_sibling_module_is_not_a_candidate(tmp_path):
    write(tmp_path, "mybase.py", ONE)
    path = write(
        tmp_path,
        "child.py",
        '''
from mybase import Mine

class Child(Mine):
    pass
''',
    )
    # One class of the file's own, even though `Mine` is visible in its namespace.
    assert resolve(str(path)).cls.__name__ == "Child"


def test_errors_never_name_the_path(tmp_path):
    path = write(tmp_path, "broken.py", "def (:\n")
    with pytest.raises(LoadError) as exc:
        resolve(str(path))
    text = str(exc.value)
    assert text.startswith("SyntaxError: ")
    assert "(line 1)" in text
    assert "/" not in text and ".py" not in text
    assert exc.value.path == path  # the CLI, and only the CLI, prints it

    path = write(tmp_path, "raises.py", "raise RuntimeError('at import')\n")
    with pytest.raises(LoadError, match="^RuntimeError: at import$"):
        resolve(str(path))
    assert "pewpew_user.raises" not in sys.modules  # a failed exec leaves nothing behind


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
    path = write(tmp_path, "opens.py", f"open({str(missing)!r})\n")
    with pytest.raises(LoadError) as exc:
        resolve(str(path))
    assert str(exc.value) == "FileNotFoundError: No such file or directory"

    class Opens(Pattern):
        def render(self, x, y, z, index):
            open(missing)  # noqa: SIM115  raises before a file opens

    renderer = Renderer(Opens(), line(4))
    renderer.step(1 / 60)
    text = str(renderer.error)
    assert text.endswith("FileNotFoundError: No such file or directory")
    assert str(missing) not in text and "secret" not in text


def test_loading_twice_gives_fresh_classes_under_one_module_entry(tmp_path):
    path = write(tmp_path, "again.py", ONE)
    first = load_file(path, attr=None)
    second = load_file(path, attr=None)
    assert first.cls is not second.cls
    assert first.digest == second.digest
    assert sys.modules["pewpew_user.again"] is not None
    assert [k for k in sys.modules if k.startswith("pewpew_user.again")] == ["pewpew_user.again"]
    # Both generations still resolve their source, which `ParamSet.hint` needs.
    assert inspect.getsourcefile(first.cls) == str(path)
    assert inspect.getsourcefile(second.cls) == str(path)


def test_a_failed_reexec_keeps_the_previous_module_registered(tmp_path):
    path = write(tmp_path, "keep.py", ONE)
    good = load_file(path, attr=None)
    path.write_text("def (:\n")
    with pytest.raises(LoadError):
        load_file(path, attr=None)
    assert sys.modules["pewpew_user.keep"] is sys.modules[good.cls.__module__]


OP = '''
import numpy as np
from pewpew import Float
from pewpew.fx.op import Op
from pewpew.fx.types import Sig, Ty

class Shim(Op, op="shim_test"):
    """A source of one level."""

    sig = Sig.SOURCE
    out = Ty.SCALAR
    {knob} = Float(0.5, 0.0, 1.0)

    def build(self, inputs):
        return lambda c: np.full(len(c.index), 0.5, np.float32)
'''
PROGRAM = '''
from pewpew.fx.expr import shim_test
from pewpew.fx.host import ProgramPattern

class Mine(ProgramPattern):
    program = shim_test(amount=0.3).palette("ember")
'''


@pytest.mark.parametrize("broken", ["not_defined()\n", "# and no pattern of its own\n"])
def test_a_failed_load_puts_back_the_ops_it_defined(tmp_path, broken):
    """An op registers as its class statement runs; a load that fails
    leaves the last good class registered, so a rebind of a layer that
    runs it still finds its knobs (pewpew.fx.op)."""
    from pewpew.fx.op import REGISTRY

    before = dict(REGISTRY)
    path = tmp_path / "shimmer.py"
    try:
        path.write_text(OP.format(knob="amount") + PROGRAM)
        load_file(path, attr=None)
        good = REGISTRY["shim_test"]
        path.write_text(OP.format(knob="depth") + broken)
        with pytest.raises(LoadError):
            load_file(path, attr=None)
        assert REGISTRY["shim_test"] is good
    finally:
        REGISTRY.clear()
        REGISTRY.update(before)


def test_colon_name_works_through_the_search_dir_and_not_on_the_gallery(tmp_path):
    write(tmp_path, "two.py", ONE + "\nclass Other(Mine):\n    pass\n")
    assert resolve("two:Other", search_dir=tmp_path).cls.__name__ == "Other"
    with pytest.raises(LoadError, match="':Comet' only applies to a file"):
        resolve("comet:Comet")


def test_a_missing_search_dir_is_a_clean_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such patterns directory"):
        resolve("comet", search_dir=tmp_path / "nope")


def test_gallery_files_never_touch_sys_path(tmp_path):
    before = list(sys.path)
    loaded = resolve("comet")
    load_file(loaded.source, attr=None)
    assert sys.path == before


def test_interrupts_propagate_and_leave_no_half_module(tmp_path):
    path = write(tmp_path, "slow.py", "raise KeyboardInterrupt\n")
    with pytest.raises(KeyboardInterrupt):
        load_file(path, attr=None)
    assert "pewpew_user.slow" not in sys.modules


def test_a_file_with_only_the_imported_base_defines_no_pattern(tmp_path):
    path = write(tmp_path, "base_only.py", "from pewpew import Pattern\n")
    with pytest.raises(LoadError, match="no Pattern subclass is defined"):
        resolve(str(path))
