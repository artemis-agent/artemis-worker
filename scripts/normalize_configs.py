"""One-off migration that normalizes every `configs/companies/*.yaml` to the
canonical schema. Idempotent — safe to re-run.

Canonical schema (top-level, fixed order):
  name, slug, ats, ats_config, careers_url, verified,
  discovered_from, discovered_jobs, last_verified, evidence_url

ats_config canonical keys (match the scrapers in artemis/scrapers/ats/*.py):
  greenhouse      -> {board_token}
  lever           -> {company}                  (migrate `site` -> `company`)
  ashby           -> {board_token}
  workday         -> {tenant, site_id, wd_version}
  smartrecruiters -> {company_id}               (migrate `company` -> `company_id`)
  eightfold       -> {company, domain}
  icims           -> {careers_url}

Run:  python3 scripts/normalize_configs.py [--dry-run]
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from datetime import datetime, timezone

import yaml


CONFIG_DIR = pathlib.Path("configs/companies")

CANONICAL_ORDER = [
    "name",
    "slug",
    "ats",
    "ats_config",
    "careers_url",
    "verified",
    "discovered_from",
    "discovered_jobs",
    "last_verified",
    "evidence_url",
]

VALID_ATS = {
    "greenhouse",
    "lever",
    "ashby",
    "workday",
    "smartrecruiters",
    "eightfold",
    "icims",
}


def _canonical_ats_config(ats: str, cfg: dict) -> dict:
    """Map per-ATS config to canonical key names. Returns a NEW dict."""
    cfg = dict(cfg or {})
    if ats == "lever":
        # Some old configs used `site`; scraper expects `company`.
        if "site" in cfg and "company" not in cfg:
            cfg["company"] = cfg.pop("site")
        return {"company": cfg.get("company", "")}
    if ats == "smartrecruiters":
        # Some old configs used `company`; scraper expects `company_id`.
        if "company" in cfg and "company_id" not in cfg:
            cfg["company_id"] = cfg.pop("company")
        return {"company_id": cfg.get("company_id", "")}
    if ats == "greenhouse" or ats == "ashby":
        return {"board_token": cfg.get("board_token", "")}
    if ats == "workday":
        return {
            "tenant": cfg.get("tenant", ""),
            "site_id": cfg.get("site_id", "External_Career_Site"),
            "wd_version": str(cfg.get("wd_version", "5")),
        }
    if ats == "eightfold":
        return {
            "company": cfg.get("company", ""),
            "domain": cfg.get("domain", ""),
        }
    if ats == "icims":
        return {"careers_url": cfg.get("careers_url", "")}
    return cfg  # unknown ats — leave untouched


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def normalize(d: dict) -> tuple[dict, list[str]]:
    """Return (canonical_dict, list of changes made)."""
    changes: list[str] = []
    ats = (d.get("ats") or "").lower()
    if ats not in VALID_ATS:
        # Don't fail — flag and pass-through.
        changes.append(f"unknown_ats={ats!r}")

    # Canonicalize ats_config.
    old_cfg = d.get("ats_config") or {}
    new_cfg = _canonical_ats_config(ats, old_cfg)
    if new_cfg != old_cfg:
        changes.append(f"ats_config rekeyed: {sorted(old_cfg)} -> {sorted(new_cfg)}")

    # Backfill missing top-level fields.
    out: dict = {
        "name": d.get("name", ""),
        "slug": d.get("slug", ""),
        "ats": ats,
        "ats_config": new_cfg,
        "careers_url": d.get("careers_url", "") or "",
        "verified": bool(d.get("verified", False)),
        "discovered_from": d.get("discovered_from") or "manual",
        "discovered_jobs": int(d.get("discovered_jobs") or 0),
        "last_verified": d.get("last_verified") or _today_iso(),
        "evidence_url": d.get("evidence_url"),  # may be None
    }

    if "discovered_from" not in d:
        changes.append("added discovered_from=manual")
    if "discovered_jobs" not in d:
        changes.append("added discovered_jobs=0")
    if "last_verified" not in d:
        changes.append(f"added last_verified={out['last_verified']}")
    if "evidence_url" not in d:
        changes.append("added evidence_url=null")

    # Drop any legacy fields not in the canonical schema.
    legacy = sorted(set(d) - set(CANONICAL_ORDER))
    if legacy:
        changes.append(f"dropped legacy fields: {legacy}")

    return out, changes


def _ordered_dump(d: dict) -> str:
    """Dump with stable key order matching CANONICAL_ORDER."""
    ordered = {k: d[k] for k in CANONICAL_ORDER if k in d}
    return yaml.dump(ordered, default_flow_style=False, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report changes but do not write files.")
    parser.add_argument("--dir", default=str(CONFIG_DIR), help="Config directory (default: configs/companies)")
    args = parser.parse_args()

    base = pathlib.Path(args.dir)
    if not base.exists():
        print(f"ERROR: directory not found: {base}", file=sys.stderr)
        return 2

    files = sorted(base.glob("*.yaml"))
    print(f"Found {len(files)} YAMLs in {base}")

    total_changed = 0
    parse_errors = 0
    summary: dict[str, int] = {}

    for p in files:
        try:
            d = yaml.safe_load(open(p))
        except Exception as e:
            parse_errors += 1
            print(f"  PARSE ERROR {p.name}: {e}", file=sys.stderr)
            continue
        if not isinstance(d, dict):
            parse_errors += 1
            continue

        new_d, changes = normalize(d)
        if changes:
            total_changed += 1
            for c in changes:
                summary[c.split(":", 1)[0]] = summary.get(c.split(":", 1)[0], 0) + 1
            if args.dry_run:
                print(f"  WOULD CHANGE {p.name}: {'; '.join(changes)}")
        if not args.dry_run:
            p.write_text(_ordered_dump(new_d))

    print(f"\n{'═' * 60}")
    print(f"  Files seen      : {len(files)}")
    print(f"  Parse errors    : {parse_errors}")
    print(f"  Changed         : {total_changed}")
    print(f"  Unchanged       : {len(files) - total_changed - parse_errors}")
    print(f"  Dry run         : {args.dry_run}")
    if summary:
        print("\nChange categories:")
        for cat, n in sorted(summary.items(), key=lambda x: -x[1]):
            print(f"  {cat:<50} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
