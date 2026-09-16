"""Fail a release when its tag and project metadata disagree."""

from pathlib import Path
import os
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from email_extractor.version import __version__  # noqa: E402


def main() -> int:
    metadata_only = "--metadata-only" in sys.argv[1:]
    tag = os.environ.get("GITHUB_REF_NAME", f"v{__version__}")
    expected_tag = f"v{__version__}"
    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    file_version = re.search(r"StringStruct\('FileVersion', '([^']+)'\)", version_info)
    errors = []
    if not metadata_only and tag != expected_tag:
        errors.append(f"Tag {tag!r} deve ser {expected_tag!r}.")
    if not file_version or file_version.group(1) != __version__:
        errors.append("version_info.txt não corresponde a email_extractor/version.py.")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Versão validada: {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
