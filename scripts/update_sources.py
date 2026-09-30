"""Combine independently collected sources; standard-library only."""
import csv
import base64
import html
import hashlib
import io
import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

TODAY = date.today().isoformat()
SEARCH_URL = 'https://scholar.google.com/scholar?q=%22gfwr%22+%22fishing%22'
EXCLUDED = {'globalfishingwatch/gfwr', 'cornejotux/gfwr-citations'}
QUERIES = ['gfwr language:R', 'gfwr extension:Rmd', 'gfwr extension:qmd']
RANK = {'candidate': 0, 'citation_linked_openalex': 1, 'verified_manually': 2}


def read(path, default):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def write(path, value):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    if not p.exists() or p.read_text() != value:
        p.write_text(value, encoding='utf-8')


def csv_text(rows, fields):
    f = io.StringIO(); w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
    w.writeheader()
    for row in rows:
        w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items() if k in fields})
    return f.getvalue()


def api(path, params):
    token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('GitHub token unavailable')
    req = Request('https://api.github.com/' + path + '?' + urlencode(params), headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github.text-match+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'gfwr-citations'})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=45) as response:
                return json.load(response)
        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(min(int(e.headers.get('Retry-After', 10)), 30))
            else:
                raise RuntimeError(f'GitHub HTTP {e.code} on {path}') from None
    raise RuntimeError('GitHub retries exhausted')


def search_pages(endpoint, query):
    items = []
    for page in range(1, 11):
        # Legacy REST code search does not support is:public. Filter the explicit
        # repository.private flag before retaining or publishing any result.
        response = api('search/' + endpoint, {'q': query, 'per_page': 100, 'page': page})
        if response.get('incomplete_results') or response['total_count'] > 1000:
            raise RuntimeError('GitHub returned incomplete search; previous complete results retained')
        items.extend(response['items'])
        if len(items) >= response['total_count'] or len(response['items']) < 100:
            return items
        time.sleep(7)  # Code search has its own rate limit.
    return items


def classify(fragment):
    # Code evidence indicates a declaration/call, not proof of successful execution.
    if re.search(r'\b(?:library|require|requireNamespace)\s*\(\s*[\'"]?gfwr\b|\bgfwr\s*::', fragment, re.I):
        return 'code_reference'
    if re.search(r'GlobalFishingWatch/gfwr\b', fragment, re.I):
        return 'package_url'
    return 'candidate'


def repositories(items):
    grouped = {}
    for item in items:
        repo = item['repository']; name = repo['full_name']
        if repo.get('private') or repo.get('fork') or name.lower() in EXCLUDED:
            continue
        evidence = []
        for match in item.get('text_matches', []):
            fragment = match.get('fragment', '')
            kind = classify(fragment)
            if kind != 'candidate':
                evidence.append({'source': 'GitHub', 'method': 'code_search_api',
                    'url': item['html_url'], 'path': item['path'], 'blob_sha': item['sha'],
                    'type': kind, 'note': 'Referencia de código al paquete; no demuestra ejecución.'})
        if not evidence:
            continue  # Avoid random strings and similarly named packages.
        r = grouped.setdefault(name, {'id': 'github:' + name.lower(), 'name': name,
            'url': repo['html_url'], 'source': 'GitHub', 'status': 'code_reference', 'evidence': []})
        for e in evidence:
            if e not in r['evidence']: r['evidence'].append(e)
    return sorted(grouped.values(), key=lambda r: r['name'].lower())


def github_update():
    cache = read('data/github-cache.json', {'records': [], 'checked_at': None})
    try:
        items = []
        for query in QUERIES:
            items.extend(search_pages('code', query + ' -repo:GlobalFishingWatch/gfwr -repo:cornejotux/gfwr-citations'))
            time.sleep(7)
        records = repositories(items)
        cache = {'records': records, 'checked_at': TODAY, 'queries': QUERIES}
        write('data/github-cache.json', cache)
        status = 'complete'
        error = None
    except (RuntimeError, OSError, ValueError, KeyError) as e:
        records = cache['records']; status = 'unavailable_cached_results' if cache['checked_at'] else 'unavailable_no_results'
        error = str(e)
        print('GitHub unavailable; preserving cached results:', error)
        if os.getenv('GITHUB_ACTIONS'): print('::warning::GitHub search unavailable; cached repository results retained.')
    readme_status = None
    if status != 'complete':
        readme_cache = read('data/github-readme-cache.json', {'records': [], 'checked_at': None})
        try:
            discovered = []
            for repo in search_pages('repositories', '"GlobalFishingWatch/gfwr" in:readme fork:false is:public'):
                if repo.get('private') or repo.get('fork') or repo['full_name'].lower() in EXCLUDED:
                    continue
                payload = api('repos/' + repo['full_name'] + '/readme', {})
                content = base64.b64decode(payload['content']).decode('utf-8')
                if classify(content) == 'candidate': continue
                discovered.append({'id': 'github:' + repo['full_name'].lower(), 'name': repo['full_name'],
                    'url': repo['html_url'], 'source': 'GitHub', 'status': 'readme_reference',
                    'evidence': [{'source':'GitHub','method':'readme_search_api','url':payload['html_url'],
                        'path':payload['path'],'blob_sha':payload['sha'],'type':'readme_reference',
                        'observed_at':TODAY,'note':'README público con una referencia al paquete; no demuestra uso o ejecución.'}]})
            readme_cache = {'records': discovered, 'checked_at': TODAY}
            write('data/github-readme-cache.json', readme_cache)
            readme_status = 'complete'
            status = 'partial_code_cached_readme_complete'
        except (RuntimeError, OSError, ValueError, KeyError) as e:
            readme_status = 'unavailable_cached_results'
            print('GitHub README search unavailable:', str(e))
        combined = {r['id']: dict(r, evidence=list(r['evidence'])) for r in records}
        for r in readme_cache['records']:
            if r['id'] in combined:
                for evidence in r['evidence']:
                    if evidence not in combined[r['id']]['evidence']: combined[r['id']]['evidence'].append(evidence)
            else: combined[r['id']] = r
        records = sorted(combined.values(), key=lambda r: r['name'].lower())
    return records, {'mode': 'automatic', 'status': status, 'last_successful_check': cache['checked_at'], 'error': error, 'readme_search': readme_status}


def doi_key(value):
    return re.sub(r'^https?://(?:dx\.)?doi.org/', '', value.strip(), flags=re.I).lower()


def merge_publications(openalex, external):
    grouped = {}
    for row in openalex:
        row = dict(row)
        row['doi'] = doi_key(row.get('doi', ''))
        row['evidence'] = [{'source': 'OpenAlex', 'method': 'api', 'url': 'https://openalex.org/' + row['id'],
            'type': 'citation_link' if row['status'] == 'citation_linked_openalex' else 'discovery',
            'note': 'Registro bibliográfico obtenido de OpenAlex.'}]
        if row['status'] == 'verified_manually':
            row['evidence'].append({'source': 'Publisher', 'method': 'manual_review',
                'url': next(r['evidence'] for r in openalex if r['id'] == row['id']),
                'type': 'verified_citation', 'note': 'Referencia al paquete comprobada en el artículo.'})
        grouped['doi:' + row['doi'] if row['doi'] else 'id:' + row['id']] = row
    for raw in external:
        row = dict(raw)
        source = row['source']
        if source not in ('Google Scholar', 'ResearchGate') or row['status'] not in ('candidate', 'verified_manually'):
            raise ValueError('Invalid source or status in external-publications.csv')
        if not row['source_url'].startswith('https://') or not row['observed_at']:
            raise ValueError('External records require a source URL and observation date')
        date.fromisoformat(row['observed_at'])
        if row['status'] == 'verified_manually' and not row['note'].strip():
            raise ValueError('A verified citation requires an evidence note')
        host = urlsplit(row['source_url']).hostname
        if (source == 'Google Scholar' and host != 'scholar.google.com') or (source == 'ResearchGate' and host not in ('researchgate.net', 'www.researchgate.net')):
            raise ValueError('Source URL does not match source label')
        row['doi'] = doi_key(row['doi'])
        key = 'doi:' + row['doi'] if row['doi'] else 'id:' + row['id']
        e = {'source': source, 'method': row['method'], 'url': row['source_url'],
             'type': 'verified_citation' if row['status'] == 'verified_manually' else 'discovery',
             'observed_at': row['observed_at'], 'note': row['note'], 'result_url': row['url']}
        if key not in grouped:
            grouped[key] = {k: row[k] for k in ('id', 'year', 'title', 'authors', 'doi', 'url', 'status')}
            grouped[key]['evidence'] = []
        target = grouped[key]
        if RANK[row['status']] > RANK[target['status']]: target['status'] = row['status']
        if e not in target['evidence']: target['evidence'].append(e)
    for row in grouped.values():
        row['sources'] = sorted({e['source'] for e in row['evidence']})
    return sorted(grouped.values(), key=lambda r: (-int(r['year'] or 0), r['title']))


def bibtex(rows):
    def esc(s):
        return re.sub(r'([&%$#_])', r'\\\1', str(s).replace('\\', '').replace('{', '').replace('}', ''))
    entries = []
    for r in rows:
        fields = {'title': '{' + esc(r['title']) + '}', 'author': esc(r['authors'].replace('; ', ' and ')),
                  'year': r['year'], 'doi': esc(r['doi']), 'url': esc(r['url'])}
        body = ',\n'.join('  ' + k + ' = {' + str(v) + '}' for k, v in fields.items() if v)
        key = hashlib.sha256((r['doi'] or r['id']).encode()).hexdigest()[:12]
        entries.append('@misc{gfwr_' + key + ',\n' + body + '\n}')
    return '% gfwr verified/linked publications. Provenance: records.json\n' + '\n\n'.join(entries) + '\n'


def render(publications, repos, statuses):
    h = html.escape
    labels = {'candidate': 'Por revisar', 'verified_manually': 'Cita verificada', 'citation_linked_openalex': 'Cita enlazada por OpenAlex'}
    def evidence_list(r):
        return '<details><summary>Fuentes y evidencia</summary><ul>' + ''.join(
            f'<li><a href="{h(e["url"], quote=True)}">{h(e["source"])}</a> · {h(e["method"])}'
            + (f' · {h(e["observed_at"])}' if e.get('observed_at') else '')
            + f'<br>{h(e["note"])}</li>' for e in r['evidence']) + '</ul></details>'
    def pubs(rows):
        return '<ol>' + ''.join(f'<li><a href="{h(r["url"], quote=True)}">{h(r["title"])}</a> ({r["year"]})<br><small>{h(r["authors"])}</small><p class="tags">{h(labels[r["status"]])} · Fuentes: {h(", ".join(r["sources"]))}</p>{evidence_list(r)}</li>' for r in rows) + '</ol>' if rows else '<p>No hay registros.</p>'
    accepted = [r for r in publications if r['status'] != 'candidate']
    candidates = [r for r in publications if r['status'] == 'candidate']
    source_cards = ''.join(f'<li><strong>{h(k)}</strong>: {h(v["description"])}' + (f' Última consulta/revisión: {h(v["last_successful_check"])}.' if v.get('last_successful_check') else '') + '</li>' for k,v in statuses.items())
    repo_html = '<ol>' + ''.join(f'<li><a href="{h(r["url"])}">{h(r["name"])}</a><p class="tags">Fuente: GitHub · {"mención en README" if r["status"]=="readme_reference" else "referencia de código"}</p>{evidence_list(r)}</li>' for r in repos) + '</ol>'
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>gfwr · Publicaciones y usos</title>
<style>body{{font:17px/1.6 system-ui;max-width:1050px;margin:40px auto;padding:0 24px;color:#173343;background:#f5f9fa}}a{{color:#006b79;overflow-wrap:anywhere}}li{{margin:0 0 20px}}small{{color:#485b65}}.tags{{font-size:14px;margin:6px 0;color:#006b79}}details{{background:white;padding:10px 15px;border-radius:8px}}nav a{{margin-right:18px}}h2{{margin-top:42px}}.intro{{border-left:4px solid #006b79;padding-left:20px}}</style>
<main><h1>Publicaciones y usos de gfwr</h1><p class="intro">Cada registro identifica dónde se encontró y qué evidencia existe. Las publicaciones y los repositorios se cuentan por separado. La cobertura es parcial; aparecer en una búsqueda no demuestra una cita.</p>
<nav><a href="#citations">Citas ({len(accepted)})</a><a href="#candidates">Por revisar ({len(candidates)})</a><a href="#repositories">Repositorios ({len(repos)})</a><a href="#sources">Fuentes</a></nav>
<p><a href="https://github.com/cornejotux/gfwr-citations/tree/main/data">CSV, JSON y BibTeX</a> · <a href="https://github.com/cornejotux/gfwr-citations/actions">Historial de actualizaciones</a></p>
<h2 id="sources">Cobertura y actualización por fuente</h2><ul>{source_cards}</ul>
<p><a href="{SEARCH_URL}">Revisar Google Scholar</a> · <a href="https://www.researchgate.net/search/publication?q=gfwr">Revisar ResearchGate</a>. Los registros revisados se importan desde <a href="https://github.com/cornejotux/gfwr-citations/blob/main/config/external-publications.csv">el archivo de fuentes externas</a>. No se ejecuta una búsqueda automática en estas dos plataformas.</p>
<h2 id="citations">Citas enlazadas o verificadas ({len(accepted)})</h2>{pubs(accepted)}
<h2 id="candidates">Publicaciones por revisar ({len(candidates)})</h2>{pubs(candidates)}
<h2 id="repositories">Repositorios con referencias a gfwr ({len(repos)})</h2><p>Importaciones, llamadas o enlaces al paquete en archivos R, Rmd y Quarto de repositorios públicos indexados por GitHub. No demuestra ejecución del código ni constituye una cita académica. Se excluyen el paquete original, este rastreador y los forks identificados por la API.</p>{repo_html}</main></html>'''


def main():
    openalex = read('data/openalex/records.json', [])
    with open('config/external-publications.csv', encoding='utf-8', newline='') as f:
        external = list(csv.DictReader(f))
    publications = merge_publications(openalex, external)
    repos, gh_status = github_update()
    oa = read('data/openalex/status.json', {})
    oa_failed = os.getenv('OPENALEX_OUTCOME') == 'failure'
    statuses = {
        'OpenAlex': {'mode': 'automatic', 'status': 'unavailable_cached_results' if oa_failed else oa.get('mention_search', 'unknown'),
            'description': 'Actualización fallida; se conservan registros anteriores.' if oa_failed else ('Consulta automática mensual; búsqueda de menciones completa.' if oa.get('mention_search') == 'complete' else 'Citas por DOI actualizadas; búsqueda de menciones pendiente, se conserva la caché.')},
        'GitHub': dict(gh_status, description='Búsqueda automática mensual de referencias al paquete en código.' if gh_status['status']=='complete' else ('Búsqueda de README públicos completada. Búsqueda de código limitada; se conserva su última caché.' if gh_status['status']=='partial_code_cached_readme_complete' else 'Búsqueda no disponible; se conservan resultados anteriores. Revisar Actions y el token GITHUB_SEARCH_TOKEN.'))}
    for source in ('Google Scholar', 'ResearchGate'):
        dates = [r['observed_at'] for r in external if r['source']==source]
        statuses[source] = {'mode': 'manual', 'status': 'manual_review', 'last_successful_check': max(dates) if dates else None,
            'description': 'Consulta e importación revisada; no se actualiza automáticamente. La fecha corresponde a los registros revisados, no a una búsqueda exhaustiva.'}
    write('data/records.json', publications)
    fields = ['id','year','title','authors','doi','url','status','sources','evidence']
    accepted = [r for r in publications if r['status'] != 'candidate']
    write('data/citations.csv', csv_text(accepted, fields))
    write('data/candidates.csv', csv_text([r for r in publications if r['status']=='candidate'], fields))
    write('data/citations.bib', bibtex(accepted))
    write('data/repositories.json', repos)
    write('data/repositories.csv', csv_text(repos, ['id','name','url','source','status','evidence']))
    write('data/source-status.json', statuses)
    write('docs/index.html', render(publications, repos, statuses))
    print(f'{len(accepted)} citations, {len(publications)-len(accepted)} candidates, {len(repos)} repositories')

if __name__ == '__main__':
    main()
