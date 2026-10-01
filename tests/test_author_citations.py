import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('author_citations', Path(__file__).resolve().parents[1] / 'scripts/update_author_citations.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


class AuthorCitationTests(unittest.TestCase):
    def test_doi_normalization_and_orcid_correction(self):
        self.assertEqual(a.doi_key('https://doi.org/10.1000/ABC'), '10.1000/abc')
        self.assertEqual(a.doi_key('10.1111/j.December 20091439-0485.2010.00372.x'), '10.1111/j.1439-0485.2010.00372.x')

    def test_orcid_works_extracts_doi(self):
        payload = {'group': [{'work-summary': [{'put-code': 7, 'title': {'title': {'value': 'A work'}}, 'publication-date': {'year': {'value': '2020'}}, 'external-ids': {'external-id': [{'external-id-type': 'doi', 'external-id-value': '10.1/ABC'}]}}]}]}
        self.assertEqual(a.orcid_works(payload), [{'put_code': '7', 'title': 'A work', 'year': '2020', 'doi': '10.1/abc', 'orcid_url': 'https://orcid.org/0000-0002-4244-2865/7'}])


if __name__ == '__main__':
    unittest.main()
