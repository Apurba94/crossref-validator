import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from crossref_validator.cli import main
from crossref_validator.core import compare, parse_bibtex, title_similarity, validate

MSG = {
    "title": ["Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid"],
    "container-title": ["Nature"], "short-container-title": ["Nature"],
    "issued": {"date-parts": [[1953, 4, 25]]},
    "author": [{"family": "Watson", "given": "J. D."}, {"family": "Crick", "given": "F. H. C."}],
    "volume": "171", "issue": "4356", "page": "737-738", "type": "journal-article",
}
GOOD = parse_bibtex("""@article{w, author={Watson, James and Crick, Francis},
title={Molecular structure of nucleic acids: a structure for deoxyribose nucleic acid},
journal={Nature}, year={1953}, volume={171}, number={4356}, pages={737--738}, doi={10.1038/171737a0}}""")[0]


def entry(**fields):
    e = {"type": "article", "key": "k", "fields": dict(GOOD["fields"])}
    e["fields"].update(fields)
    return e


class CompareTests(unittest.TestCase):
    def test_matching_entry_has_no_issues(self):
        self.assertEqual(compare(GOOD, MSG), [])

    def test_wrong_title_and_author(self):
        fields = {i[0] for i in compare(entry(title="A different paper", author="Smith, J"), MSG)}
        self.assertEqual(fields, {"title", "author"})

    def test_year_off_by_one_is_warning(self):
        self.assertEqual(compare(entry(year="1954"), MSG), [("year", "1954", "1953", "warning")])
        self.assertEqual(compare(entry(year="1960"), MSG)[0][3], "error")

    def test_volume_pages_and_journal(self):
        fields = {i[0] for i in compare(entry(volume="172", pages="1--5", journal="Science"), MSG)}
        self.assertEqual(fields, {"volume", "pages", "journal"})

    def test_retraction_flag(self):
        msg = dict(MSG, **{"update-to": [{"type": "retraction", "DOI": "10.x/y"}]})
        self.assertIn(("status", "", "retraction notice", "error"), compare(GOOD, msg))

    def test_similarity_ignores_markup(self):
        self.assertEqual(title_similarity("The <i>E. coli</i> genome", "The {E. coli} Genome"), 1.0)


class ValidateTests(unittest.TestCase):
    def test_statuses(self):
        entries = [GOOD, entry(doi=""), entry(doi="https://doi.org/10.9/none")]
        entries[1]["key"], entries[2]["key"] = "nodoi", "missing"
        seen = []

        def fetch(doi):
            seen.append(doi)
            return None if doi == "10.9/none" else MSG
        res = validate(entries, fetch)
        self.assertEqual([r["status"] for r in res], ["ok", "no-doi", "doi-not-found"])
        self.assertEqual(seen, ["10.1038/171737a0", "10.9/none"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.bib")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("@article{bad, title={Wrong}, year={1953}, doi={10.1038/171737a0}}")
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(main([path], fetch=lambda doi: MSG), 1)
            self.assertIn("mismatch", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
