# crossref-validator

**Check that the titles, years, authors, journals, volumes and pages in your BibTeX match the
authoritative Crossref record for each DOI, and catch retraction notices on the way.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Citation metadata gets corrupted: a DOI pasted onto the wrong entry, an online-first year, a
misspelled first author, pages from the preprint. Such errors are invisible until a copy editor or
reviewer finds them. Crossref holds publisher-deposited metadata for over 150 million works; comparing
against it is a quick automated quality gate before submission.

## Features

- Fuzzy title comparison (accents, LaTeX, JATS tags and punctuation ignored)
- Year (off-by-one flagged as a warning, typical of online-first vs print), first-author surname,
  journal (full or abbreviated title), volume, issue and pages
- Flags DOIs unknown to Crossref and records that are retraction notices
- Polite-pool support with `--mailto`; JSON output; exit code 1 on mismatches

## Usage

```bash
pip install .
crossref-validator refs.bib --mailto you@university.edu
crossref-validator refs.bib --json > validation.json
```

## Testing

Offline tests use recorded Crossref messages:

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
