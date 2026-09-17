#!/usr/bin/env python3
"""Extract the cited provisions from data/raw/legal/ into data/build/legal.json (SPEC §4, §10.1).

    python scripts/build_legal.py            # write data/build/legal.json and data/build/LEGAL.md
    python scripts/build_legal.py --check    # also fail if any provision in PROVISIONS could not be extracted

Every entry in PROVISIONS names one citation `source` string exactly as build_zones.py cites it
(SPEC §4.1 short forms), the fetched document it comes from and the selector inside it. The
`quote` is the wording of that document, unchanged except for whitespace and the removal of
Lovdata's amendment notes and footnote markers; where parts of a provision are omitted this is
shown by a "[…]" line. Nothing here is typed from memory: if the selector is not found in the
fetched file the entry is reported and, with --check, the build fails.

data/build/LEGAL.md is the review document for the owner (Phase 3 exit criterion: the
zone/citation mapping has been reviewed).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repository root (scripts live in code/scripts/)
RAW = ROOT / "data/raw/legal"
OUT = ROOT / "data/build/legal.json"
REVIEW = ROOT / "data/build/LEGAL.md"
ELLIPSIS = "[…]"

# --------------------------------------------------------------------------- what to extract
# kind=lovdata: doc = DokID; articles = data-name values ("§4"); sections = data-name of sections
#               ("kap1", for regulations whose provisions are numbered sections); items = list
#               markers to keep from a definitions list ("l."), the rest replaced by [...].
# kind=unclos:  articles = list of (article, paragraph|None, item|None): (2, None, None) = whole
#               article, (2, 2, None) = paragraph 2, (87, 1, "b") = paragraph 1 chapeau + item (b).
# kind=hr:      paragraphs = numbered paragraphs of the judgment; pinpoint distinguishes several
#               citations of the same judgment.
# selectionNote: where SPEC §4.1 names an instrument without a provision, or the provision has
#               parts, this records what was chosen — for the owner's review (LEGAL.md).
PROVISIONS = [
    {"source": "territorialfarvannsloven §§ 1–2", "kind": "lovdata", "doc": "NL/lov/2003-06-27-57", "articles": ["§1", "§2"]},
    {"source": "territorialfarvannsloven § 3", "kind": "lovdata", "doc": "NL/lov/2003-06-27-57", "articles": ["§3"]},
    {"source": "territorialfarvannsloven § 4", "kind": "lovdata", "doc": "NL/lov/2003-06-27-57", "articles": ["§4"]},
    {"source": "lov om Norges økonomiske sone § 1", "kind": "lovdata", "doc": "NL/lov/1976-12-17-91", "articles": ["§1"]},
    {"source": "kontinentalsokkelloven", "kind": "lovdata", "doc": "NL/lov/2021-06-18-89", "articles": ["§1"],
     "selectionNote": "SPEC §4.1 says 'kontinentalsokkelloven' without a provision. Lovdata's current-acts package holds two acts on "
                      "the shelf: lov 18. juni 2021 nr. 89 om Norges kontinentalsokkel (short title on Lovdata: 'Lov om Norges "
                      "kontinentalsokkel'), whose § 1 defines the shelf, and lov 21. juni 1963 nr. 12 (scientific research and "
                      "exploitation of other subsea natural resources), whose § 1 now refers to the 2021 act for the definition. "
                      "§ 1 of the 2021 act is quoted; the 1963 act is fetched (data/raw/legal/lovdata/nl-19630621-012.xml) but not cited."},
    {"source": "luftfartsloven § 1-1", "kind": "lovdata", "doc": "NL/lov/1993-06-11-101", "articles": ["§1-1"]},
    {"source": "forskrift 3. juni 1977 nr. 6", "kind": "lovdata", "doc": "SF/forskrift/1977-06-03-6",
     "articles": ["§1", "§2", "§3", "§4", "§5"],
     "selectionNote": "Quoted in full (§§ 1–5); owner instruction 2026-09-17."},
    {"source": "forskrift 23. mai 1980 nr. 4", "kind": "lovdata", "doc": "SF/forskrift/1980-05-23-4",
     "sections": ["kap1", "kap2", "kap3", "kap4", "kap5"],
     "selectionNote": "Quoted in full (its five provisions are numbered 1–5 without §); owner instruction 2026-09-17."},

    {"source": "UNCLOS art. 1(1)(1)", "kind": "unclos", "articles": [(1, 1, "1")]},
    {"source": "UNCLOS art. 2", "kind": "unclos", "articles": [(2, None, None)]},
    {"source": "UNCLOS art. 2(2)", "kind": "unclos", "articles": [(2, 2, None)]},
    {"source": "UNCLOS art. 3", "kind": "unclos", "articles": [(3, None, None)]},
    {"source": "UNCLOS art. 8", "kind": "unclos", "articles": [(8, None, None)]},
    {"source": "UNCLOS art. 17", "kind": "unclos", "articles": [(17, None, None)]},
    {"source": "UNCLOS art. 33", "kind": "unclos", "articles": [(33, None, None)]},
    {"source": "UNCLOS arts 55–58", "kind": "unclos", "articles": [(55, None, None), (56, None, None), (57, None, None), (58, None, None)]},
    {"source": "UNCLOS art. 58(1)", "kind": "unclos", "articles": [(58, 1, None)]},
    {"source": "UNCLOS arts 76–79", "kind": "unclos", "articles": [(76, None, None), (77, None, None), (78, None, None), (79, None, None)]},
    {"source": "UNCLOS art. 86", "kind": "unclos", "articles": [(86, None, None)]},
    {"source": "UNCLOS art. 87", "kind": "unclos", "articles": [(87, None, None)]},
    {"source": "UNCLOS art. 87(1)(b)", "kind": "unclos", "articles": [(87, 1, "b")]},
    {"source": "UNCLOS arts 136–137", "kind": "unclos", "articles": [(136, None, None), (137, None, None)]},
    {"source": "UNCLOS art. 303", "kind": "unclos", "articles": [(303, None, None)]},

    {"source": "HR-2023-491-P (Snøkrabbe II)", "pinpoint": "avsnitt 16", "kind": "hr", "paragraphs": [16],
     "selectionNote": "Cited on svalbard-fpz. Paragraph 16 (the Court's account of how the fisheries protection zone was "
                      "established and why it is called non-discriminatory) is proposed; paragraph 17 states the parties' "
                      "positions on the Treaty's application in the zone and is NOT quoted (SPEC §10.5: no characterising text). "
                      "Owner to confirm."},
    {"source": "HR-2023-491-P (Snøkrabbe II)", "pinpoint": "avsnitt 220", "kind": "hr", "paragraphs": [220],
     "selectionNote": "Cited on continental-shelf. Paragraph 220 (the Court's conclusion on Article 2 of the Treaty and "
                      "Article 77 of UNCLOS) is proposed; 227 is the overall conclusion. Owner to confirm."},
]

UNCLOS_PART_OF = {}   # article number → part file, filled from the fetched table of contents order below
UNCLOS_FILES = ("part1.htm", "part2.htm", "part5.htm", "part6.htm", "part7.htm", "part11-2.htm", "part16.htm")
UNCLOS_URL = "https://www.un.org/depts/los/convention_agreements/texts/unclos/"
UNCLOS_TITLE = "United Nations Convention on the Law of the Sea"
NO_MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]


# --------------------------------------------------------------------------- Lovdata XHTML → lines
class LovdataText(HTMLParser):
    """Turn a Lovdata article/section element into lines: heading, ledd, list items (with their
    marker). Amendment notes (article.changesToParent), footnotes and footnote markers are dropped."""

    SKIP = {("article", "changesToParent"), ("footer", "footnotes"), ("sup", "footnotereference")}
    BLOCK = {"article", "h1", "h2", "h3", "h4", "h5", "p", "li", "section", "div", "ol", "ul"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[list] = []        # [kind, marker, text]
        self._buf: list[str] = []
        self._kind = "text"
        self._marker = ""
        self._skip = 0
        self._stack: list[tuple] = []
        self._pending_marker = ""

    def _flush(self):
        t = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if t:
            self.lines.append([self._kind, self._marker, t])
        self._buf, self._kind, self._marker = [], "text", ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        key = (tag, cls.split()[0] if cls else "")
        self._stack.append(key)
        if self._skip or key in self.SKIP:
            self._skip += 1
            return
        if tag in self.BLOCK:
            self._flush()
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            self._kind = "heading"
        elif tag == "li" and a.get("data-name"):
            self._pending_marker = a["data-name"]
        elif tag == "article" and cls.startswith("legalP"):
            self._kind, self._marker = "ledd", self._pending_marker
            self._pending_marker = ""

    def handle_endtag(self, tag):
        key = self._stack.pop() if self._stack else (tag, "")
        if self._skip:
            self._skip -= 1
            return
        if tag in self.BLOCK:
            self._flush()

    def handle_data(self, data):
        if not self._skip:
            self._buf.append(data)


def lovdata_lines(chunk: str) -> list[list]:
    p = LovdataText()
    p.feed(chunk)
    p._flush()
    return p.lines


def _element(content: str, start: int, tag: str) -> str:
    depth = 0
    for m in re.finditer(rf"<{tag}\b[^>]*>|</{tag}>", content[start:]):
        depth += -1 if m.group(0).startswith("</") else 1
        if depth == 0:
            return content[start:start + m.end()]
    return content[start:]


def lovdata_provision(doc: dict, spec: dict) -> tuple[str, dict]:
    content = doc["content"]
    out_lines: list[str] = []
    selectors = [("article", a) for a in spec.get("articles", [])] + [("section", s) for s in spec.get("sections", [])]
    urls = []
    for tag, name in selectors:
        m = re.search(rf'<{tag}[^>]*data-name="{re.escape(name)}"', content)
        if not m:
            raise LookupError(f"{doc['dokid']}: {tag} {name} not found")
        el = _element(content, m.start(), tag)
        u = re.search(r'data-lovdata-URL="([^"]+)"', el[:400])
        urls.append("https://lovdata.no/dokument/" + u.group(1) if u else None)
        lines = lovdata_lines(el)
        if spec.get("items"):
            keep, omitted = [], False
            for kind, marker, text in lines:
                if kind == "heading" or (kind == "ledd" and not marker) or marker in spec["items"]:
                    if omitted:
                        keep.append(["text", "", ELLIPSIS]); omitted = False
                    keep.append([kind, marker, text])
                else:
                    omitted = True
            if omitted:
                keep.append(["text", "", ELLIPSIS])
            lines = keep
        for kind, marker, text in lines:
            out_lines.append(f"{marker} {text}".strip() if marker else text)
    return "\n".join(out_lines), {"url": urls[0], "urls": urls}


# --------------------------------------------------------------------------- UNCLOS HTML → articles
def unclos_articles(content: str) -> dict[int, dict]:
    """Parse one DOALOS part file into {article: {"title": str, "lines": [(para, item, text)]}}."""
    # the text sits between the first <HR> (after the Part heading) and the last (navigation footer)
    hrs = [m.start() for m in re.finditer(r"<HR\b", content, re.I)]
    if len(hrs) >= 2:
        content = content[hrs[0]:hrs[-1]]
    paras = []
    for m in re.finditer(r"<P\b([^>]*)>(.*?)(?=<P\b|</BODY|</HTML|$)", content, re.S | re.I):
        attrs, body = m.group(1), m.group(2)
        text = html.unescape(re.sub(r"<[^>]+>", "", body)).replace("\xa0", " ")
        text = re.sub(r"[ \t\r\n]+", " ", text).strip()
        if text:
            paras.append(("center" in attrs.lower(), text))
    articles: dict[int, dict] = {}
    cur = None
    in_title = False
    for centered, text in paras:
        am = re.fullmatch(r"Article\s*(\d+)", text)
        if am:
            cur = articles[int(am.group(1))] = {"title": "", "lines": []}
            in_title = True
            continue
        if cur is None:
            continue
        if in_title and (centered or not cur["title"]) and not re.match(r"^(\d+\.|\()", text):
            cur["title"] = (cur["title"] + " " + text).strip()
            continue
        in_title = False
        if centered:      # section headings between articles
            if re.match(r"^(SECTION|PART|SUBSECTION)\b", text):
                cur = None
            continue
        pm = re.match(r"^(\d+)\.\s+(.*)$", text)
        para = int(pm.group(1)) if pm else (cur["lines"][-1][0] if cur["lines"] else None)
        rest = pm.group(2) if pm else text
        im = re.match(r"^\(([a-z]+|\d+)\)\s+(.*)$", rest)
        item = im.group(1) if im else None
        cur["lines"].append((para, item, text))
    return articles


def load_unclos() -> dict[int, tuple[str, dict]]:
    arts = {}
    for f in UNCLOS_FILES:
        content = (RAW / "unclos" / f).read_text(encoding="utf-8", errors="replace")
        for n, a in unclos_articles(content).items():
            arts[n] = (f, a)
    return arts


def unclos_provision(arts: dict, spec: dict) -> tuple[str, dict]:
    out, files = [], []
    for n, para, item in spec["articles"]:
        if n not in arts:
            raise LookupError(f"UNCLOS article {n} not in the fetched parts")
        f, a = arts[n]
        files.append(f)
        if out:
            out.append("")
        out.append(f"Article {n} {a['title']}")
        lines = a["lines"]
        if para is not None:
            sel = [(p, i, t) for p, i, t in lines if p == para and (item is None or i is None or i == item)]
            if not sel:
                raise LookupError(f"UNCLOS art. {n}({para}) not found")
            # mark omitted lines between kept ones, and after, so a partial quote never reads as complete
            idx = [lines.index(s) for s in sel]
            prev = None
            for k, s in zip(idx, sel):
                if prev is not None and k != prev + 1:
                    out.append(ELLIPSIS)
                out.append(s[2]); prev = k
            if idx[-1] != len(lines) - 1:
                out.append(ELLIPSIS)
            if item is not None and not any(i == item for _, i, _ in sel):
                raise LookupError(f"UNCLOS art. {n}({para})({item}) not found")
        else:
            out.extend(t for _, _, t in lines)
    urls = sorted(set(UNCLOS_URL + f for f in files))
    return "\n".join(out), {"url": urls[0], "urls": urls}


# --------------------------------------------------------------------------- Høyesterett PDF → paragraphs
def hr_paragraphs(pdf: Path) -> dict[int, str]:
    import pypdf   # optional dependency (code/scripts/requirements.txt); pure Python
    text = "\n".join(p.extract_text() for p in pypdf.PdfReader(str(pdf)).pages)
    # page furniture: a page number on its own line followed by the case-number header
    text = re.sub(r"\n\s*\d+\s*\n\s*\n?HR-2023-491-P, \((sak|case) n[or]\.? [^\n]*\n", "\n", text)
    paras = {}
    for m in re.finditer(r"(?m)^\((\d+)\)\s(.*?)(?=^\(\d+\)\s|\Z)", text, re.S):
        body = m.group(2)
        body = re.split(r"\n\s*\n\s*\n", body, maxsplit=1)[0]     # a heading follows after blank lines
        paras[int(m.group(1))] = re.sub(r"\s+", " ", body).strip()
    return paras


def hr_provision(no: dict, en: dict, spec: dict) -> tuple[str, dict]:
    out, tr = [], []
    for n in spec["paragraphs"]:
        if n not in no:
            raise LookupError(f"HR-2023-491-P paragraph ({n}) not found in the PDF")
        out.append(f"({n}) {no[n]}")
        if n in en:
            tr.append(f"({n}) {en[n]}")
    return "\n".join(out), {"translation": "\n".join(tr)}


# --------------------------------------------------------------------------- build
def load_lovdata() -> dict[str, dict]:
    log = json.loads((RAW / "lovdata/FETCH_LOG.json").read_text(encoding="utf-8"))
    docs = {}
    for fname, meta in log["files"].items():
        content = (RAW / "lovdata" / fname).read_text(encoding="utf-8")
        legacy = meta["legacyID"]                        # e.g. LOV-2003-06-27-57 / FOR-1977-06-03-6
        kind, y, mo, d, *nr = legacy.split("-")
        cited = f"{'lov' if kind == 'LOV' else 'forskrift'} {int(d)}. {NO_MONTHS[int(mo) - 1]} {y}" + (f" nr. {nr[0]}" if nr else "")
        docs[meta["dokid"]] = {**meta, "file": fname, "content": content, "citedAs": cited,
                               "packageLastModified": log["packages"][meta["package"]]["lastModified"]}
    return docs


def build() -> tuple[dict, list[str]]:
    lovdata = load_lovdata()
    unclos = load_unclos()
    unclos_log = json.loads((RAW / "unclos/FETCH_LOG.json").read_text(encoding="utf-8"))
    hr_log = json.loads((RAW / "hr/FETCH_LOG.json").read_text(encoding="utf-8"))
    hr_no = hr_paragraphs(RAW / "hr/hr-2023-491-p.pdf")
    hr_en = hr_paragraphs(RAW / "hr/hr-2023-491-p-eng.pdf")
    provisions, problems = [], []
    for spec in PROVISIONS:
        rec = {"source": spec["source"]}
        if spec.get("pinpoint"):
            rec["pinpoint"] = spec["pinpoint"]
        try:
            if spec["kind"] == "lovdata":
                doc = lovdata[spec["doc"]]
                quote, extra = lovdata_provision(doc, spec)
                rec.update({"title": doc["title"], "citedAs": doc["citedAs"], "quote": quote, "quoteLang": "no", "url": extra["url"],
                            "provenance": {"publisher": "Lovdata", "dokid": doc["dokid"], "file": f"data/raw/legal/lovdata/{doc['file']}",
                                           "sha256": doc["sha256"], "lastChangeInForce": doc["lastChangeInForce"],
                                           "package": doc["package"], "packageLastModified": doc["packageLastModified"],
                                           "selector": spec.get("articles") or spec.get("sections"), "items": spec.get("items")}})
            elif spec["kind"] == "unclos":
                quote, extra = unclos_provision(unclos, spec)
                files = [u.rsplit("/", 1)[1] for u in extra["urls"]]
                rec.update({"title": UNCLOS_TITLE, "citedAs": spec["source"], "quote": quote, "quoteLang": "en", "url": extra["url"],
                            "provenance": {"publisher": "UN DOALOS", "files": [f"data/raw/legal/unclos/{f}" for f in files],
                                           "sha256": [unclos_log["files"][f]["sha256"] for f in files],
                                           "selector": [list(a) for a in spec["articles"]]}})
            elif spec["kind"] == "hr":
                quote, extra = hr_provision(hr_no, hr_en, spec)
                rec.update({"title": "Høyesteretts dom 20. mars 2023, HR-2023-491-P (Snøkrabbe II)", "citedAs": f"HR-2023-491-P {spec['pinpoint']}",
                            "quote": quote, "quoteLang": "no", "url": hr_log["files"]["hr-2023-491-p.pdf"]["url"],
                            "translation": extra["translation"], "translationUrl": hr_log["files"]["hr-2023-491-p-eng.pdf"]["url"],
                            "translationNote": "the Supreme Court's own English translation, 'provided for information purposes only'",
                            "provenance": {"publisher": "Norges Høyesterett", "files": ["data/raw/legal/hr/hr-2023-491-p.pdf", "data/raw/legal/hr/hr-2023-491-p-eng.pdf"],
                                           "sha256": [hr_log["files"]["hr-2023-491-p.pdf"]["sha256"], hr_log["files"]["hr-2023-491-p-eng.pdf"]["sha256"]],
                                           "selector": spec["paragraphs"]}})
        except LookupError as e:
            problems.append(f"{spec['source']}: {e}")
            rec.update({"quote": "", "error": str(e)})
        if spec.get("selectionNote"):
            rec["selectionNote"] = spec["selectionNote"]
        provisions.append(rec)
    meta = {"built_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "sources": {"lovdata": json.loads((RAW / "lovdata/FETCH_LOG.json").read_text(encoding="utf-8"))["fetched_at_utc"],
                        "unclos": unclos_log["fetched_at_utc"], "hr": hr_log["fetched_at_utc"]},
            "rule": "SPEC §10.1 — every quote is extracted by this script from the files under data/raw/legal/; none is typed from memory"}
    return {"meta": meta, "provisions": provisions}, problems


def key(rec: dict) -> str:
    return rec["source"] + (f" | {rec['pinpoint']}" if rec.get("pinpoint") else "")


def review_md(data: dict, problems: list[str]) -> str:
    L = ["# Legal provisions — review copy", "",
         f"_Generated by `code/scripts/build_legal.py` at {data['meta']['built_at_utc']} from `data/raw/legal/` "
         f"(fetched: Lovdata {data['meta']['sources']['lovdata']}, DOALOS {data['meta']['sources']['unclos']}, "
         f"Høyesterett {data['meta']['sources']['hr']}). Do not edit: change `PROVISIONS` in the script or the zone registry in "
         f"`build_zones.py` and rebuild._", "",
         "Each block is one citation `source` as `build_zones.py` uses it, with the wording extracted from the fetched document. "
         "`[…]` marks omitted parts. Notes headed **Selection** record choices made where SPEC §4.1 leaves room; they are for the "
         "owner to confirm or change.", ""]
    if problems:
        L += ["## Problems", ""] + [f"- {p}" for p in problems] + [""]
    for rec in data["provisions"]:
        L.append(f"## {key(rec)}")
        L.append("")
        if rec.get("error"):
            L += [f"**NOT EXTRACTED:** {rec['error']}", ""]
            continue
        L.append(f"**{rec['title']}** — cited as *{rec['citedAs']}* · quote language `{rec['quoteLang']}` · <{rec['url']}>")
        prov = rec["provenance"]
        src = prov.get("file") or ", ".join(prov["files"])
        L.append(f"Source file: `{src}`" + (f" · in force as amended {prov['lastChangeInForce']}" if prov.get("lastChangeInForce") else ""))
        if rec.get("selectionNote"):
            L.append(f"**Selection:** {rec['selectionNote']}")
        L.append("")
        L += ["> " + line for line in rec["quote"].split("\n")]
        if rec.get("translation"):
            L += ["", f"_{rec['translationNote']}_ (<{rec['translationUrl']}>):", ""] + ["> " + line for line in rec["translation"].split("\n")]
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    data, problems = build()
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    REVIEW.write_text(review_md(data, problems), encoding="utf-8", newline="\n")
    n = sum(1 for r in data["provisions"] if r.get("quote"))
    print(f"{OUT.relative_to(ROOT)}: {n}/{len(data['provisions'])} provisions extracted, "
          f"{sum(len(r.get('quote', '')) for r in data['provisions'])} chars; review copy {REVIEW.relative_to(ROOT)}")
    for p in problems:
        print("  PROBLEM:", p)
    if args.check and problems:
        print("RESULT: FAIL")
        return 1
    print("RESULT: OK" if not problems else "RESULT: PROBLEMS")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
