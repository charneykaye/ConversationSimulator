#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Print a ready-to-paste model-registry entry for a Hugging Face GGUF file.

The registry policy (model-registry/README.md) requires every registry-managed
model to carry a URL pinned to a specific repo commit and a verified SHA-256.
Working those out by hand means downloading gigabytes just to hash them. This
script asks the Hugging Face Hub API instead: the file's Git-LFS object id IS
its SHA-256, and the repo's current commit SHA pins the URL.

Usage::

    python scripts/pin-model.py Qwen/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf \\
        --id qwen3-1.7b-instruct-q4_k_m --role starter \\
        --min-vram 3 --recommended-vram 4

Prints a YAML block for model-registry/registry.yaml. Review the licence,
hardware hints and runtime defaults before committing, then run
``python scripts/validate-registry.py --url-check``.

The demo edition (docs/steam-next-fest-demo.md) installs the registry's
``role: starter`` entry, or whatever CONVSIM_DEMO_MODEL_ID names — so the
evaluation of a smaller/faster Qwen tier for the demo is: pin it with this
script, add the entry, point CONVSIM_DEMO_MODEL_ID at it, and run the demo
quality gate. No code change is needed to switch models.

Exit codes: 0 printed an entry; 1 the file or repo was not found or the file
is not stored in LFS (no verifiable digest).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

_UA = "convsim-pin-model/1.0"
_TIMEOUT = 60


def _get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.load(resp)


def _resolve(repo: str, filename: str, revision: str) -> tuple[str, str, int]:
    """Return (commit_sha, sha256, size_bytes) for ``filename`` in ``repo``."""
    q = urllib.parse.quote
    # /api/models/{repo}/revision/{rev} carries the resolved commit sha and the
    # sibling list; /tree/{rev} carries per-file LFS metadata.
    info = _get_json(f"https://huggingface.co/api/models/{q(repo, safe='/')}/revision/{q(revision)}")
    if not isinstance(info, dict) or "sha" not in info:
        raise SystemExit(f"error: could not resolve revision {revision!r} of {repo}")
    commit = str(info["sha"])

    tree = _get_json(f"https://huggingface.co/api/models/{q(repo, safe='/')}/tree/{commit}")
    if not isinstance(tree, list):
        raise SystemExit(f"error: unexpected tree payload for {repo}@{commit}")
    for entry in tree:
        if isinstance(entry, dict) and entry.get("path") == filename:
            lfs = entry.get("lfs")
            if not isinstance(lfs, dict) or not lfs.get("oid"):
                raise SystemExit(
                    f"error: {filename} is not an LFS object in {repo}@{commit}; "
                    "there is no verifiable SHA-256 to pin"
                )
            return commit, str(lfs["oid"]).lower(), int(lfs.get("size") or entry.get("size") or 0)
    raise SystemExit(f"error: {filename} not found in {repo}@{commit}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="Hugging Face repo, e.g. Qwen/Qwen3-1.7B-GGUF")
    parser.add_argument("filename", help="GGUF file inside the repo, e.g. Qwen3-1.7B-Q4_K_M.gguf")
    parser.add_argument("--revision", default="main", help="branch, tag or commit to pin (default: main)")
    parser.add_argument("--id", dest="model_id", required=True, help="registry id, e.g. qwen3-1.7b-instruct-q4_k_m")
    parser.add_argument("--name", help="display name (default: derived from the filename)")
    parser.add_argument("--family", default="qwen3")
    parser.add_argument("--role", default="starter", choices=["starter", "standard", "high-quality"])
    parser.add_argument("--license", default="Apache-2.0")
    parser.add_argument("--license-url", default="https://www.apache.org/licenses/LICENSE-2.0")
    parser.add_argument("--min-vram", type=float, required=True, help="minimum VRAM in GB")
    parser.add_argument("--recommended-vram", type=float, required=True, help="recommended VRAM in GB")
    parser.add_argument("--context-length", type=int, default=8192)
    args = parser.parse_args()

    try:
        commit, sha256, size = _resolve(args.repo, args.filename, args.revision)
    except urllib.error.HTTPError as exc:
        print(f"error: HTTP {exc.code} from Hugging Face for {args.repo}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"error: cannot reach huggingface.co: {exc.reason}", file=sys.stderr)
        return 1

    name = args.name or args.filename.removesuffix(".gguf").replace("-", " ")
    size_gb = round(size / 1_000_000_000, 1) if size else 0.0
    url = f"https://huggingface.co/{args.repo}/resolve/{commit}/{args.filename}"

    print(f"  - id: {args.model_id}")
    print(f'    name: "{name}"')
    print(f"    family: {args.family}")
    print(f"    role: {args.role}")
    print("    format: gguf")
    print(f"    license: {args.license}")
    print(f'    license_url: "{args.license_url}"')
    print(f"    size_gb: {size_gb}")
    print("    hardware:")
    print(f"      min_vram_gb: {args.min_vram:g}")
    print(f"      recommended_vram_gb: {args.recommended_vram:g}")
    print("    download:")
    print("      provider: huggingface")
    print(f"      # Pinned to commit {commit[:7]} of {args.repo}")
    print(f'      url: "{url}"')
    print(f'      sha256: "{sha256}"')
    print("    runtime:")
    print("      llama_cpp:")
    print(f"        context_length: {args.context_length}")
    print("        temperature_default: 0.75")
    print("        top_p_default: 0.9")
    return 0


if __name__ == "__main__":
    sys.exit(main())
