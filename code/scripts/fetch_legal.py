#!/usr/bin/env python3
"""Fetch the legal source documents behind every citation (SPEC §4.1, §6.1 step 4, §10.1).

    python scripts/fetch_legal.py                 # fetch everything into data/raw/legal/
    python scripts/fetch_legal.py --only lovdata   # one source: lovdata | unclos | hr
    python scripts/fetch_legal.py --compare        # re-fetch to a temp dir, report byte differences, write nothing

Three sources, each written verbatim with a FETCH_LOG.json (URL, size, SHA-256, time):

  lovdata/   Lovdata's free data packages (https://api.lovdata.no/v1/publicData/, NLOD 2.0): the
             two archives `gjeldende-lover` (NL) and `gjeldende-sentrale-forskrifter` (SF) are
             downloaded whole (≈ 6 + 21 MB, refreshed daily) and only the documents in LOVDATA_DOCS
             are kept, byte for byte, as Lovdata's XHTML. The archives themselves are not kept.
  unclos/    The Convention text as published by the UN Division for Ocean Affairs and the Law of
             the Sea (DOALOS), one HTML file per Part / Section, for the Parts that contain a cited
             article (UNCLOS_PARTS).
  hr/        HR-2023-491-P (Snøkrabbe II) as the Supreme Court publishes it on domstol.no: the
             Norwegian judgment and the Court's English translation, both PDF.

Nothing is quoted here; build_legal.py extracts the cited provisions from these files.
Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import io
import json
import re
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)
OUT = ROOT / "data/raw/legal"
USER_AGENT = "norway-jurisdiction/0.1 (teaching model, UiO)"

# ---- Lovdata ------------------------------------------------------------------------------
LOVDATA_API = "https://api.lovdata.no/v1/publicData"
LOVDATA_PACKAGES = ("gjeldende-lover.tar.bz2", "gjeldende-sentrale-forskrifter.tar.bz2")
# DokIDs found by searching the titles in the fetched packages on 2026-09-17 (not from memory):
# "territorialfarvann", "økonomiske sone", "kontinentalsokkel", "luftfart", "fiskevernsone",
# "fiskerisone". The label is a reading aid only; the title that ships comes from the document
# itself. (petroleumsloven was fetched at first and dropped by the owner, 2026-09-17.)
LOVDATA_DOCS = {
    "NL/lov/2003-06-27-57": "territorialfarvannsloven",
    "NL/lov/1976-12-17-91": "økonomiske soneloven",
    "NL/lov/2021-06-18-89": "lov om Norges kontinentalsokkel",
    "NL/lov/1963-06-21-12": "lov om undersjøiske naturforekomster (1963)",
    "NL/lov/1993-06-11-101": "luftfartsloven",
    "SF/forskrift/1977-06-03-6": "forskrift om fiskevernsone ved Svalbard",
    "SF/forskrift/1980-05-23-4": "forskrift om opprettelse av fiskerisone ved Jan Mayen",
}

# ---- UNCLOS -------------------------------------------------------------------------------
UNCLOS_BASE = "https://www.un.org/depts/los/convention_agreements/texts/unclos/"
# Part files that contain the articles cited in SPEC §4.1 (art. 1; 2, 3, 8, 17, 33; 55–58;
# 76–79; 86, 87; 136, 137; 303) plus the table of contents.
UNCLOS_PARTS = ("UNCLOS-TOC.htm", "part1.htm", "part2.htm", "part5.htm", "part6.htm", "part7.htm",
                "part11-2.htm", "part16.htm")

# ---- Høyesterett --------------------------------------------------------------------------
HR_DOCS = {
    "hr-2023-491-p.pdf": {
        "url": "https://www.domstol.no/globalassets/upload/hret/avgjorelser/2023/mars/hr-2023-491-p.pdf",
        "page": "https://www.domstol.no/no/hoyesterett/avgjorelser/2023/hoyesterett-sivil/hr-2023-491-p/",
        "lang": "no", "note": "the judgment as published by the Supreme Court of Norway"},
    "hr-2023-491-p-eng.pdf": {
        "url": "https://www.domstol.no/globalassets/upload/hret/translated-rulings/2023/hr-2023-491-p.pdf",
        "page": "https://www.domstol.no/en/supremecourt/rulings/2023/supreme-court-civil-cases/hr-2023-491-p/",
        "lang": "en", "note": "the Supreme Court's own English translation"},
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get(url: str, timeout: int = 300) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        hdr = {k: v for k, v in r.headers.items() if k.lower() in ("content-type", "last-modified", "etag")}
    return body, hdr


def write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def write_log(path: Path, log: dict) -> None:
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _dd(head: str, cls: str) -> str:
    m = re.search(rf'<dd class="{cls}">(.*?)</dd>', head, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def fetch_lovdata(out: Path) -> dict:
    listing, _ = get(f"{LOVDATA_API}/list", timeout=60)
    packages = {p["filename"]: p for p in json.loads(listing)}
    write(out / "publicData-list.json", listing)
    log = {"fetched_at_utc": now(), "api": f"{LOVDATA_API}/list",
           "licence": "NLOD 2.0 (Lovdata: 'Deling av datasett via API ... under en NLOD 2.0-lisens', lovdata.no/info/api)",
           "packages": {}, "files": {}}
    wanted = dict(LOVDATA_DOCS)
    for name in LOVDATA_PACKAGES:
        meta = packages[name]
        print(f"  {name}: {int(meta['sizeBytes']) // 1024} KB, lastModified {meta['lastModified']} ...", flush=True)
        body, _ = get(f"{LOVDATA_API}/get/{name}", timeout=900)
        log["packages"][name] = {"lastModified": meta["lastModified"], "sizeBytes": len(body), "sha256": sha256(body),
                                 "description": meta.get("description", "")}
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:bz2") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                data = tf.extractfile(m).read()
                head = data[:12000].decode("utf-8", "replace")
                dokid = _dd(head, "dokid")
                if dokid not in wanted:
                    continue
                fname = Path(m.name).name
                write(out / fname, data)
                log["files"][fname] = {"dokid": dokid, "package": name, "member": m.name, "bytes": len(data),
                                       "sha256": sha256(data), "title": _dd(head, "title"),
                                       "legacyID": _dd(head, "legacyID"), "lastChangeInForce": _dd(head, "lastChangeInForce"),
                                       "label": wanted.pop(dokid)}
                print(f"    {fname}  {dokid}  {len(data)} B  {log['files'][fname]['title'][:70]}")
    if wanted:
        raise SystemExit(f"not found in the packages: {sorted(wanted)}")
    write_log(out / "FETCH_LOG.json", log)
    return log


def fetch_unclos(out: Path) -> dict:
    log = {"fetched_at_utc": now(), "base": UNCLOS_BASE,
           "source": "United Nations Convention on the Law of the Sea, text as published by the UN Division for "
                     "Ocean Affairs and the Law of the Sea (DOALOS), un.org/depts/los",
           "files": {}}
    for name in UNCLOS_PARTS:
        body, hdr = get(UNCLOS_BASE + name, timeout=120)
        write(out / name, body)
        log["files"][name] = {"url": UNCLOS_BASE + name, "bytes": len(body), "sha256": sha256(body), "headers": hdr}
        print(f"    {name}  {len(body)} B")
    write_log(out / "FETCH_LOG.json", log)
    return log


def fetch_hr(out: Path) -> dict:
    log = {"fetched_at_utc": now(), "source": "Norges Høyesterett (Supreme Court of Norway), domstol.no",
           "case": "HR-2023-491-P (sak nr. 22-134375SIV-HRET), dom 20. mars 2023", "files": {}}
    for name, d in HR_DOCS.items():
        body, hdr = get(d["url"], timeout=300)
        if not body.startswith(b"%PDF"):
            raise SystemExit(f"{d['url']}: not a PDF")
        write(out / name, body)
        log["files"][name] = {**d, "bytes": len(body), "sha256": sha256(body), "headers": hdr}
        print(f"    {name}  {len(body)} B")
    write_log(out / "FETCH_LOG.json", log)
    return log


FETCHERS = {"lovdata": fetch_lovdata, "unclos": fetch_unclos, "hr": fetch_hr}


def compare(a: Path, b: Path) -> int:
    """Report files that differ between two trees (FETCH_LOG.json excluded: it carries the fetch time)."""
    diffs = 0
    for pa in sorted(p for p in a.rglob("*") if p.is_file() and p.name != "FETCH_LOG.json"):
        pb = b / pa.relative_to(a)
        if not pb.exists():
            print(f"  only in {a.name}: {pa.relative_to(a)}"); diffs += 1
        elif pa.name == "publicData-list.json":     # the API lists the packages in varying order
            key = lambda p: sorted(json.loads(p.read_text(encoding="utf-8")), key=lambda e: e["filename"])
            if key(pa) != key(pb):
                print(f"  DIFFERENT (package list): {pa.relative_to(a)}"); diffs += 1
        elif pa.read_bytes() != pb.read_bytes():
            print(f"  DIFFERENT: {pa.relative_to(a)}"); diffs += 1
    for pb in sorted(p for p in b.rglob("*") if p.is_file() and p.name != "FETCH_LOG.json"):
        if not (a / pb.relative_to(b)).exists():
            print(f"  new: {pb.relative_to(b)}"); diffs += 1
    return diffs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=sorted(FETCHERS), action="append", help="fetch only this source (repeatable)")
    ap.add_argument("--compare", action="store_true", help="fetch to a temp dir and compare with data/raw/legal")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    sources = args.only or sorted(FETCHERS)
    if args.compare:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            for s in sources:
                print(f"{s}:"); FETCHERS[s](tmp / s)
            diffs = sum(compare(args.out / s, tmp / s) for s in sources)
        print("all files byte-identical" if diffs == 0 else f"{diffs} file(s) differ")
        return 1 if diffs else 0
    for s in sources:
        print(f"{s}:"); FETCHERS[s](args.out / s)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
