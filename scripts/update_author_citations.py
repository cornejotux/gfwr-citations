"""Build a provenance-preserving citation page for Jorge Cornejo-Donoso.

The public ORCID record supplies the list of works and OpenAlex supplies the
works that cite each DOI. Google Scholar is linked as a profile-level source
and is deliberately not scraped: it has no supported bulk API.
"""
import csv
import html
import io
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ORCID = "0000-0002-4244-2865"
ORCID_URL = f"https://orcid.org/{ORCID}"
SCHOLAR_URL = "https://scholar.google.com/citations?user=4mnGFJcAAAAJ&hl=en"
OPENALEX = "https://api.openalex.org"
TODAY = date.today().isoformat()
SCHOLAR_SNAPSHOT = {"observed_at": "2026-09-30", "citations": 472, "h_index": 8, "i10_index": 8}
# Correct a malformed DOI in the public ORCID record while retaining its source.
DOI_OVERRIDES = {"10.1111/j.december 20091439-0485.2010.00372.x": "10.1111/j.1439-0485.2010.00372.x"}


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")


def get_json(url, accept="application/json"):
    request = Request(url, headers={"Accept": accept, "User-Agent": "gfwr-citations/1.0 (citation tracker)"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def doi_key(value):
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value or "", flags=re.I).strip().lower()
    return DOI_OVERRIDES.get(value, value)


def orcid_works(payload):
    works = []
    for group in payload.get("group", []):
        summary = group.get("work-summary", [{}])[0]
        ids = summary.get("external-ids", {}).get("external-id", [])
        doi = next((doi_key(i.get("external-id-value")) for i in ids if i.get("external-id-type") == "doi"), "")
        title = summary.get("title", {}).get("title", {}).get("value", "Untitled work")
        year = summary.get("publication-date", {}).get("year", {}).get("value", "")
        works.append({"put_code": str(summary.get("put-code", "")), "title": title, "year": year, "doi": doi,
                      "orcid_url": f"{ORCID_URL}/{summary.get('put-code')}"})
    return sorted(works, key=lambda w: (w["year"] or "", w["title"]), reverse=True)


def openalex_work(doi):
    return get_json(f"{OPENALEX}/works/https://doi.org/{quote(doi, safe='/')}")


def citing_works(work):
    records, cursor = [], "*"
    while cursor:
        # OpenAlex v2 work records no longer include cited_by_api_url.
        url = OPENALEX + "/works?" + urlencode({"filter": "cites:" + work["id"].rsplit("/", 1)[-1], "per-page": 200, "cursor": cursor})
        page = get_json(url)
        records.extend(page.get("results", []))
        cursor = page.get("meta", {}).get("next_cursor")
    return records


def authorship(work):
    return "; ".join(a.get("author", {}).get("display_name", "") for a in work.get("authorships", []) if a.get("author", {}).get("display_name"))


def citation_row(work, cited_doi):
    doi = doi_key(work.get("doi", ""))
    return {"id": work["id"].rsplit("/", 1)[-1], "title": work.get("display_name", "Untitled work"),
            "year": work.get("publication_year") or "", "authors": authorship(work), "doi": doi,
            "url": work.get("doi") or work["id"], "cites_dois": [cited_doi],
            "source": "OpenAlex", "source_url": work["id"]}


def collect():
    works = orcid_works(get_json(f"https://pub.orcid.org/v3.0/{ORCID}/works"))
    citations = {}
    for publication in works:
        if not publication["doi"]:
            publication["openalex_status"] = "no_doi"
            continue
        result = openalex_work(publication["doi"])
        publication["openalex_id"] = result["id"]
        publication["openalex_status"] = "complete"
        for citing in citing_works(result):
            row = citation_row(citing, publication["doi"])
            key = "doi:" + row["doi"] if row["doi"] else "id:" + row["id"]
            if key in citations:
                citations[key]["cites_dois"] = sorted(set(citations[key]["cites_dois"] + row["cites_dois"]))
            else:
                citations[key] = row
    return works, sorted(citations.values(), key=lambda r: (str(r["year"]), r["title"]), reverse=True)


def csv_text(rows, fields):
    stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value for key, value in row.items()})
    return stream.getvalue()


def render(works, citations):
    h = html.escape
    def publication(row):
        link = "https://doi.org/" + row["doi"] if row["doi"] else row["orcid_url"]
        doi = f' · <a href="https://doi.org/{h(row["doi"], quote=True)}">DOI</a>' if row["doi"] else " · No DOI in ORCID"
        return f'<li><a href="{h(link, quote=True)}">{h(row["title"])}</a> ({h(str(row["year"]))}){doi}</li>'
    def citation(row):
        doi = f' · <a href="https://doi.org/{h(row["doi"], quote=True)}">DOI</a>' if row["doi"] else ""
        cited = ", ".join(row["cites_dois"])
        return f'<li><a href="{h(row["url"], quote=True)}">{h(row["title"])}</a> ({h(str(row["year"]))})<br><small>{h(row["authors"])}</small><p class="tags">Source: <a href="{h(row["source_url"], quote=True)}">OpenAlex</a> · cites: {h(cited)}{doi}</p></li>'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Jorge Cornejo-Donoso · Citation tracker</title>
<style>body{{font:17px/1.6 system-ui;max-width:1050px;margin:40px auto;padding:0 24px;color:#173343;background:#f5f9fa}}a{{color:#006b79;overflow-wrap:anywhere}}li{{margin:0 0 18px}}small{{color:#485b65}}.tags{{font-size:14px;margin:6px 0;color:#006b79}}nav a{{margin-right:18px}}h2{{margin-top:42px}}.intro{{border-left:4px solid #006b79;padding-left:20px}}.card{{background:white;padding:14px 18px;border-radius:8px}}</style>
<main><nav><a href="index.html">gfwr tracker</a><a href="#works">My publications</a><a href="#citations">Citing publications</a><a href="#sources">Sources</a></nav><h1>Jorge Cornejo-Donoso · Citation tracker</h1>
<p class="intro">A deduplicated list of publications that cite works associated with this ORCID record. It is refreshed monthly and records the source of each result.</p>
<p class="card"><strong>{len(citations)}</strong> distinct citing publications found by OpenAlex for <strong>{len(works)}</strong> works in ORCID. Last successful refresh: {TODAY}.</p>
<h2 id="sources">Sources and coverage</h2><ul><li><a href="{ORCID_URL}">ORCID</a>: public list of works and DOIs; refreshed automatically.</li><li><a href="https://openalex.org">OpenAlex</a>: citing publications for the ORCID DOIs; refreshed automatically.</li><li><a href="{SCHOLAR_URL}">Google Scholar profile</a>: author-profile cross-check. Manual snapshot on {SCHOLAR_SNAPSHOT["observed_at"]}: {SCHOLAR_SNAPSHOT["citations"]} citations, h-index {SCHOLAR_SNAPSHOT["h_index"]}, i10-index {SCHOLAR_SNAPSHOT["i10_index"]}. It is not scraped or used as an automated record source.</li></ul>
<p>Coverage depends on the identifiers in ORCID and on OpenAlex indexing. A work without a DOI is retained in the works list but cannot yet be queried for citations.</p>
<h2 id="works">Works in ORCID ({len(works)})</h2><ol>{''.join(publication(w) for w in works)}</ol>
<h2 id="citations">Citing publications ({len(citations)})</h2><ol>{''.join(citation(c) for c in citations) or '<li>No OpenAlex citation records found.</li>'}</ol>
<p><a href="https://github.com/cornejotux/gfwr-citations/tree/main/data/author">Download the generated data</a> · <a href="https://github.com/cornejotux/gfwr-citations/actions">Update history</a></p></main></html>'''


def main():
    try:
        works, citations = collect()
    except Exception as error:
        print(f"Author citation update failed; existing data retained: {error}", file=sys.stderr)
        return 1
    status = {"orcid": {"url": ORCID_URL, "status": "complete"}, "openalex": {"url": OPENALEX, "status": "complete"},
              "google_scholar": {"url": SCHOLAR_URL, "status": "manual_profile_snapshot", "snapshot": SCHOLAR_SNAPSHOT, "note": "Not automatically scraped."}, "updated_at": TODAY}
    write("data/author/works.json", works)
    write("data/author/citing-publications.json", citations)
    write("data/author/citing-publications.csv", csv_text(citations, ["id", "title", "year", "authors", "doi", "url", "cites_dois", "source", "source_url"]))
    write("data/author/status.json", status)
    write("docs/my-publications.html", render(works, citations))
    print(f"{len(works)} ORCID works; {len(citations)} distinct OpenAlex citing publications")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
