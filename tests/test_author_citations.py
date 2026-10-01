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

    def test_merge_keeps_scholar_items_and_adds_orcid_only_work(self):
        scholar = [{'title': 'Scholar work', 'year': '2020', 'doi': '10.1/a'}]
        orcid = [{'title': 'ORCID version', 'year': '2020', 'doi': '10.1/a', 'orcid_url': 'https://orcid.org/1'}, {'title': 'ORCID only', 'year': '2021', 'doi': '10.1/b', 'orcid_url': 'https://orcid.org/2'}]
        rows = a.merge_works(orcid, scholar)
        self.assertEqual(len(rows), 2)
        self.assertEqual(next(r for r in rows if r['doi']=='10.1/a')['sources'], ['Google Scholar', 'ORCID'])


if __name__ == '__main__':
    unittest.main()
