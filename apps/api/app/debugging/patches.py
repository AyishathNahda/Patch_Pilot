"""Strict single-file unified diff application: no shell, fuzzy matches or test edits."""

import ast
import difflib
from pathlib import Path
import re
from patchpilot_sandbox.fixtures import FIXTURES

SOURCE_PATH = "checkout/__init__.py"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")


class PatchError(ValueError):
    pass


def canonicalize_diff(diff: str, source: str, source_path: str = SOURCE_PATH) -> str:
    """Convert one coordinate-free model hunk only with an exact unique match."""
    lines = diff.splitlines(keepends=True)
    if len(lines) < 4 or lines[2].rstrip("\r\n") != "@@":
        return diff  # Numbered diffs still go through the original strict validator.
    if len(diff.encode()) > 16000 or [line.rstrip("\r\n") for line in lines[:2]] != [
        "--- a/" + source_path, "+++ b/" + source_path,
    ]:
        raise PatchError("Unapproved model diff")
    old, new = [], []
    for line in lines[3:]:
        if line[:1] not in (" ", "+", "-") or not line.endswith("\n"):
            raise PatchError("Unsupported coordinate-free hunk")
        if line[0] in (" ", "-"):
            old.append(line[1:])
        if line[0] in (" ", "+"):
            new.append(line[1:])
    original = source.splitlines(keepends=True)
    matches = [i for i in range(len(original) - len(old) + 1)
               if original[i:i + len(old)] == old] if old else []
    if len(matches) != 1:
        raise PatchError("Model hunk must match source exactly once")
    index = matches[0]
    updated = original[:index] + new + original[index + len(old):]
    return "".join(difflib.unified_diff(original, updated,
                   fromfile="a/" + source_path, tofile="b/" + source_path))


def apply_candidate(workspace: Path, diff: str, source_path: str = SOURCE_PATH) -> None:
    if source_path not in {fixture.source_path for fixture in FIXTURES.values()}:
        raise PatchError("Unapproved patch target")
    if len(diff.encode("utf-8")) > 16000:
        raise PatchError("Patch too large")
    lines = diff.splitlines(keepends=True)
    # Exact headers reject traversal, absolute paths, renames, extra files and test edits.
    if len(lines) < 4 or [line.rstrip("\r\n") for line in lines[:2]] != [
        "--- a/" + source_path, "+++ b/" + source_path,
    ]:
        raise PatchError("Only the approved source file may be changed")
    target = workspace / source_path
    if workspace.resolve() != workspace or target.resolve() != target or not target.is_file():
        raise PatchError("Linked or missing patch target")
    original = target.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    position = 0
    index = 2
    changed = False
    while index < len(lines):
        match = HUNK.fullmatch(lines[index].rstrip("\r\n"))
        if not match:
            raise PatchError("Invalid unified diff hunk")
        old_start, old_count, new_start, new_count = (
            int(value) if value is not None else 1 for value in match.groups()
        )
        start = old_start - 1 if old_count else old_start
        if start < position or start > len(original):
            raise PatchError("Overlapping or out-of-range hunk")
        output.extend(original[position:start])
        position = start
        if new_start != len(output) + (1 if new_count else 0):
            raise PatchError("Incorrect new hunk position")
        index += 1
        removed = added = 0
        while index < len(lines) and not lines[index].startswith("@@"):
            line = lines[index]
            prefix, content = line[:1], line[1:]
            if prefix not in (" ", "+", "-"):
                raise PatchError("Unsupported patch syntax")
            if prefix in (" ", "-"):
                if position >= len(original) or original[position] != content:
                    raise PatchError("Patch context does not match source")
                position += 1
                removed += 1
            if prefix in (" ", "+"):
                output.append(content)
                added += 1
            changed |= prefix in ("+", "-")
            index += 1
        if (removed, added) != (old_count, new_count):
            raise PatchError("Hunk counts do not match patch contents")
    output.extend(original[position:])
    updated = "".join(output)
    if not changed or updated == "".join(original) or len(updated.encode()) > 16000:
        raise PatchError("Patch must make a bounded source change")
    try:
        ast.parse(updated)  # Syntax only: never imports or executes candidate code.
    except SyntaxError:
        raise PatchError("Candidate has invalid Python syntax") from None
    target.write_text(updated, encoding="utf-8", newline="\n")
