"""Fetch the latest story archive (zh_CN.zip) from GitHub Releases into data/.

Companion to ``fetch_gamedata.py``. The excel/levels archives are extracted
trees on disk, but the story archive is consumed by the server as a **zip**
(see ``_BUNDLED_STORYJSON_ZIP`` / ``STORYJSON_PATH`` in ``prts_mcp/config.py``),
so this script downloads the asset as-is instead of extracting it.

Used by the repository-root ``Dockerfile`` to bake a complete offline baseline
into the image. Can also be run manually during local development.

Usage:
    python scripts/fetch_storyjson.py [--force]

Options:
    --force   Ignore the cached release metadata and check upstream unconditionally.

Exit codes:
    0   Story archive fetched, already up to date, or network failed with a
        valid cached zip.
    1   Download failed and no usable zip is available.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make the src/ package importable when running this script directly.
_PYTHON_DIR = Path(__file__).resolve().parents[1]   # python/
_REPO_ROOT = _PYTHON_DIR.parent                     # repo root
_SRC_DIR = _PYTHON_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from prts_mcp.data.datasets import STORY_ZH_CN  # noqa: E402
from prts_mcp.data.sync import SyncResult, sync_release  # noqa: E402

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
_logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the latest story archive (zh_CN.zip) from GitHub Releases."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the cached release metadata and check upstream unconditionally.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT / "data" / "storyjson",
        help="Local directory for the story zip. Default: data/storyjson",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    story_root = args.output.resolve()
    zip_path = story_root / "zh_CN.zip"
    spec = STORY_ZH_CN.release_spec(local_zip=zip_path)

    if args.force:
        cache_path = zip_path.parent / "release_meta.json"
        if cache_path.exists():
            cache_path.unlink()
            _logger.info("--force: removed %s to trigger an upstream check.", cache_path)

    _logger.info(
        "Syncing %s/%s:%s → %s", spec.owner, spec.repo, spec.asset_name, zip_path
    )
    result: SyncResult = sync_release(spec, force_check=args.force)

    sha_short = result.commit_sha[:8] if result.commit_sha else "unknown"

    if result.status == "updated":
        _logger.info("Done. Story archive updated to %s @ %s.", spec.repo, sha_short)
        return 0
    if result.status == "up_to_date":
        _logger.info("Story archive is already up to date (%s @ %s).", spec.repo, sha_short)
        return 0
    if result.status == "offline_fallback":
        _logger.warning(
            "Network error; using existing cached story archive (%s @ %s). Error: %s",
            spec.repo,
            sha_short,
            result.error,
        )
        return 0

    _logger.error(
        "Failed to obtain %s:%s. No usable archive available. Error: %s",
        spec.repo,
        spec.asset_name,
        result.error,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
