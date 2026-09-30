# gfwr-citations

**[View publications and repositories](https://cornejotux.github.io/gfwr-citations/)** · [Actions](https://github.com/cornejotux/gfwr-citations/actions)

Tracker for citations, mentions, and code references to the [gfwr](https://github.com/GlobalFishingWatch/gfwr) R package. It follows the DOI → OpenAlex → GitHub Actions design used by [codyn](https://github.com/NCEAS/codyn/blob/main/.github/workflows/update-citations.yaml), with provenance recorded for every result.

## Sources

| Source | What it contributes | Update mode |
| --- | --- | --- |
| OpenAlex | Citations to gfwr DOIs and possible full-text mentions | Automatic, monthly |
| Zenodo | Concept DOI and all gfwr release DOIs | Automatic, monthly |
| GitHub | Package imports, calls, and links in public repositories | Automatic, monthly |
| Google Scholar | Additional publication discovery | Reviewed manual imports |
| ResearchGate | Publications and evidence in available full texts | Reviewed manual imports |

Google Scholar does not provide bulk access, so this project does not scrape it automatically. ResearchGate records are also imported manually. Their records include the source URL, observation date, method, and evidence note. A search result is never presented as a verified citation without reviewing the article.

## Evidence and statuses

Each publication has `sources` and an `evidence` list. Evidence records the platform, URL, method, note, and (for manual reviews) `observed_at`. If the same article appears in multiple sources, it is kept once by DOI and all evidence is retained.

- `verified_manually`: the package reference was checked in the article or bibliography.
- `citation_linked_openalex`: OpenAlex links the work to a gfwr DOI; it may still need review.
- `candidate`: discovered result awaiting review; it is not counted as a confirmed citation.
- Repository records are separate from publications. `code_reference` indicates a code reference, not successful execution.

## Files

| File | Contents |
| --- | --- |
| `data/records.json` | Unified publications and all evidence |
| `data/citations.csv` | Verified or linked citations |
| `data/candidates.csv` | Publications needing review |
| `data/citations.bib` | BibTeX for the unified citation list |
| `data/repositories.csv`, `data/repositories.json` | Repositories and evidence files |
| `data/source-status.json` | Status and update mode for each source |
| `config/external-publications.csv` | Reviewed Google Scholar and ResearchGate records |
| `config/sources.yml` | OpenAlex DOIs, filters, and manual reviews |
| `docs/index.html` | GitHub Pages site |

## Adding external records

Search [Google Scholar](https://scholar.google.com/scholar?q=%22gfwr%22+%22fishing%22) or [ResearchGate](https://www.researchgate.net/search/publication?q=gfwr), verify that `gfwr` refers to Global Fishing Watch, and add a row to `config/external-publications.csv`. Keep the platform-specific `source_url`, article URL, DOI, authors, year, `observed_at` (`YYYY-MM-DD`), `method: manual_review`, status, and a note describing where the reference was checked. Use `candidate` for a search result and `verified_manually` only after checking the article text or bibliography.

## Automation and limitations

The workflow runs on the first day of each month at 06:00 UTC, can be started manually, and runs when scripts or configuration change. OpenAlex and GitHub failures preserve their previous caches and are shown in `data/source-status.json` and on the site. GitHub code search has API limits; a README search fallback is used when possible.

Set the optional `OPENALEX_API_KEY` secret to avoid anonymous-search restrictions. GitHub uses the workflow token; `GITHUB_SEARCH_TOKEN` can be configured if the repository needs a separate read-only search token. Do not add credentials to files or issues.

Run locally with:

```sh
Rscript -e 'install.packages(c("httr2", "jsonlite", "yaml"))'
Rscript tests/test.R
python3 -m unittest discover -s tests -p 'test_*.py'
Rscript scripts/update_citations.R
python3 scripts/update_sources.py
```

Coverage is partial. OpenAlex, Google Scholar, ResearchGate, and GitHub have different indexing and access rules; records can contain false positives and missing citations. Full articles are not redistributed. See `NOTICE` and `LICENSE` for attribution and licensing.
