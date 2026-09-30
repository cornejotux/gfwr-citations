import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

spec = importlib.util.spec_from_file_location('sources', Path(__file__).resolve().parents[1] / 'scripts/update_sources.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class SourcesTests(unittest.TestCase):
    def external(self, source='Google Scholar', status='candidate'):
        return dict(id='external:1',year='2025',title='Title',authors='A',doi='https://doi.org/10.1/TEST',url='https://doi.org/10.1/test',status=status,source=source,source_url='https://scholar.google.com/scholar?q=gfwr' if source=='Google Scholar' else 'https://www.researchgate.net/publication/1',method='manual_review',observed_at='2026-09-30',note='Evidence')

    def test_merge_preserves_sources_and_confirmation(self):
        rows=s.merge_publications([], [self.external('ResearchGate','verified_manually'),self.external()])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['sources'],['Google Scholar','ResearchGate'])
        self.assertEqual(rows[0]['status'],'verified_manually')
        self.assertEqual(len(rows[0]['evidence']),2)

    def test_discovery_does_not_confirm(self):
        self.assertEqual(s.merge_publications([], [self.external()])[0]['status'],'candidate')

    def test_source_url_validation(self):
        r=self.external(); r['source_url']='https://example.com'
        with self.assertRaises(ValueError): s.merge_publications([], [r])

    def test_repos_exclude_private_forks_and_noise(self):
        def item(name, fragment, **flags):
            return dict(repository=dict(full_name=name,html_url='https://github.com/'+name,**flags),sha='abc',path='test.R',html_url='https://github.com/'+name+'/blob/main/test.R',text_matches=[{'fragment':fragment}])
        good=item('org/public','library(gfwr)')
        rows=s.repositories([good,good,item('org/noise','gfWrite(x)'),item('org/private','gfwr::get_raster()',private=True),item('org/fork','library(gfwr)',fork=True),item('GlobalFishingWatch/gfwr','library(gfwr)')])
        self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['evidence']),1)

    def test_pagination_and_incomplete(self):
        with patch.object(s,'api',side_effect=[{'total_count':101,'items':[{}]*100},{'total_count':101,'items':[{}]}]),patch.object(s.time,'sleep'):
            self.assertEqual(len(s.search_pages('code','gfwr')),101)
        with patch.object(s,'api',return_value={'total_count':101,'items':[],'incomplete_results':True}):
            with self.assertRaises(RuntimeError): s.search_pages('code','gfwr')

    def test_api_failure_preserves_cache(self):
        root=os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            try:
                os.chdir(d)
                cache={'records':[{'name':'org/repo'}],'checked_at':'2026-09-01'}
                s.write('data/github-cache.json',cache)
                with patch.object(s,'search_pages',side_effect=RuntimeError('unavailable')):
                    rows,status=s.github_update()
                self.assertEqual(rows,cache['records'])
                self.assertEqual(status['status'],'unavailable_cached_results')
                self.assertEqual(s.read('data/github-cache.json',{}),cache)
            finally: os.chdir(root)

if __name__=='__main__': unittest.main()
