"""Compare local BibTeX fields with the Crossref REST API (api.crossref.org/works/{doi})."""
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")


def parse_bibtex(text):
    entries = []
    for m in _ENTRY.finditer(text):
        if m.group(1).lower() in ("comment", "string", "preamble"):
            continue
        i, depth = text.index("{", m.start()), 0
        for j in range(i, len(text)):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                break
        body = text[m.end():j]
        fields = {}
        for fm in re.finditer(r"([\w-]+)\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}|\"[^\"]*\"|\d+)", body):
            v = fm.group(2)
            fields[fm.group(1).lower()] = " ".join((v[1:-1] if v[0] in "{\"" else v).split())
        entries.append({"type": m.group(1).lower(), "key": m.group(2), "fields": fields})
    return entries


def _norm(s):
    s = re.sub(r"\\[a-zA-Z]+|[{}]", "", s or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"<[^>]+>", "", s)  # Crossref titles may contain JATS/MathML tags
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def title_similarity(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def crossref_fetch(doi, mailto=None, timeout=20):
    """Fetch the Crossref 'message' for a DOI; returns None if Crossref does not know it."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    ua = "crossref-validator/0.1" + (" (mailto:%s)" % mailto if mailto else "")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=timeout) as r:
            return json.load(r)["message"]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _cr_year(msg):
    for k in ("published-print", "published-online", "issued", "created"):
        parts = (msg.get(k) or {}).get("date-parts") or [[None]]
        if parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def _first_family(author_field):
    first = author_field.split(" and ")[0].strip()
    name = first.split(",")[0] if "," in first else (first.split() or [""])[-1]
    return _norm(name)


def compare(entry, msg, title_threshold=0.9):
    """Return a list of (field, local, crossref, severity) discrepancies for one entry."""
    f = entry["fields"]
    issues = []
    cr_title = (msg.get("title") or [""])[0]
    if f.get("title") and cr_title and title_similarity(f["title"], cr_title) < title_threshold:
        issues.append(("title", f["title"], cr_title, "error"))
    cr_year = _cr_year(msg)
    if f.get("year") and cr_year and f["year"][:4] != cr_year:
        # online-first vs print years often differ by one; flag as warning only
        sev = "warning" if abs(int(f["year"][:4]) - int(cr_year)) == 1 else "error"
        issues.append(("year", f["year"], cr_year, sev))
    venue = f.get("journal") or f.get("booktitle")
    cr_venue = (msg.get("container-title") or [""])[0]
    short = (msg.get("short-container-title") or [""])[0]
    if venue and cr_venue and max(title_similarity(venue, cr_venue), title_similarity(venue, short)) < 0.8:
        issues.append(("journal", venue, cr_venue, "warning"))
    authors = msg.get("author") or []
    if f.get("author") and authors and authors[0].get("family"):
        if _first_family(f["author"]) != _norm(authors[0]["family"]):
            issues.append(("author", f["author"].split(" and ")[0], authors[0]["family"], "error"))
    for field, key in (("volume", "volume"), ("number", "issue"), ("pages", "page")):
        local, remote = f.get(field), msg.get(key)
        if local and remote and re.sub(r"\D+", "-", local).strip("-") != re.sub(r"\D+", "-", str(remote)).strip("-"):
            issues.append((field, local, str(remote), "warning"))
    if msg.get("type") == "retraction" or any(u.get("type") == "retraction" for u in msg.get("update-to") or []):
        issues.append(("status", "", "retraction notice", "error"))
    return issues


def validate(entries, fetch, title_threshold=0.9):
    """Validate all entries that have a DOI. Returns list of result dicts."""
    results = []
    for e in entries:
        doi = e["fields"].get("doi", "")
        doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
        if not doi:
            results.append({"key": e["key"], "status": "no-doi", "issues": []})
            continue
        msg = fetch(doi)
        if msg is None:
            results.append({"key": e["key"], "status": "doi-not-found", "issues": []})
            continue
        issues = compare(e, msg, title_threshold)
        results.append({"key": e["key"], "status": "mismatch" if issues else "ok", "issues": issues})
    return results
