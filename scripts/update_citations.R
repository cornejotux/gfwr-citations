# OpenAlex/Zenodo tracker inspired by NCEAS/codyn (see NOTICE).
library(httr2)
library(jsonlite)
library(yaml)
source('scripts/bibtex.R')

get_json <- function(url, query = list(), allow_404 = FALSE) {
  req <- request(url) |> req_user_agent('gfwr-citations/1.0') |> req_timeout(60) |>
    req_retry(max_tries = 4) |> req_error(is_error = function(resp) FALSE)
  if (length(query)) req <- do.call(req_url_query, c(list(req), query))
  key <- Sys.getenv('OPENALEX_API_KEY')
  if (startsWith(url, 'https://api.openalex.org/') && nzchar(key))
    req <- req |> req_headers(Authorization = paste('Bearer', key))
  resp <- req_perform(req)
  status <- resp_status(resp)
  if (status == 404 && allow_404) return(NULL)
  if (status >= 400) stop('API request failed (HTTP ', status, ') at ', sub('\\?.*', '', url))
  resp_body_json(resp, simplifyVector = FALSE)
}

fetch_pages <- function(query) {
  cursor <- '*'; seen <- character(); out <- list()
  repeat {
    page <- get_json('https://api.openalex.org/works', c(query, list(per_page = 200, cursor = cursor)))
    if (is.null(page$results) || is.null(page$meta$count)) stop('Invalid OpenAlex page')
    out <- c(out, page$results)
    next_cursor <- page$meta$next_cursor
    if (is.null(next_cursor) || !length(page$results)) break
    if (next_cursor %in% c(seen, cursor)) stop('Repeated OpenAlex cursor')
    seen <- c(seen, cursor); cursor <- next_cursor
  }
  out
}

write_changed <- function(path, value) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  value <- enc2utf8(paste(value, collapse = '\n'))
  old <- if (file.exists(path)) paste(readLines(path, warn = FALSE, encoding = 'UTF-8'), collapse = '\n') else NULL
  if (!identical(old, value)) writeLines(value, path, useBytes = TRUE)
}

html <- function(x) {
  x <- gsub('&', '&amp;', x, fixed = TRUE)
  x <- gsub('<', '&lt;', x, fixed = TRUE)
  x <- gsub('>', '&gt;', x, fixed = TRUE)
  gsub('"', '&quot;', x, fixed = TRUE)
}

main <- function() {
  cfg <- read_yaml('config/sources.yml')
  # Resolve the newest release on every run, then enumerate ALL versions.
  latest <- get_json(paste0('https://zenodo.org/api/records/', cfg$zenodo_record, '/versions/latest'))
  url <- latest$links$versions
  if (is.null(url)) stop('Missing Zenodo versions URL')
  dois <- c(cfg$concept_doi, unlist(cfg$extra_dois)); visited <- character()
  repeat {
    if (url %in% visited) stop('Repeated Zenodo page')
    visited <- c(visited, url)
    page <- get_json(url)
    if (is.null(page$hits$hits)) stop('Invalid Zenodo versions response')
    dois <- c(dois, vapply(page$hits$hits, function(w) w$doi, ''))
    url <- page$links[['next']]
    if (is.null(url)) break
  }
  dois <- sort(unique(tolower(dois)))
  sources <- lapply(dois, function(doi) get_json(paste0('https://api.openalex.org/works/https://doi.org/', doi), allow_404 = TRUE))
  ids <- unique(vapply(Filter(Negate(is.null), sources), function(w) w$id, ''))
  missing <- dois[vapply(sources, is.null, TRUE)]
  if (length(missing)) message('DOIs not indexed in OpenAlex: ', paste(missing, collapse = ', '))
  if (!length(ids)) stop('No source DOI indexed; keeping existing outputs')
  citing <- fetch_pages(list(filter = paste0('cites:', paste(sub('https://openalex.org/', '', ids, fixed = TRUE), collapse = '|'))))
  candidates <- unlist(lapply(cfg$search_terms, function(term)
    fetch_pages(list(filter = paste0('fulltext.search:', term)))), recursive = FALSE)
  manual_ids <- names(cfg$confirmed_works)
  manual <- lapply(manual_ids, function(id) get_json(paste0('https://api.openalex.org/works/', id)))
  all <- c(citing, manual, candidates)
  citing_ids <- vapply(citing, function(w) w$id, '')
  # Only exact OpenAlex IDs / DOIs are deduplicated. Titles alone are not identities.
  seen <- character(); records <- list(); works <- list()
  for (w in all) {
    id <- sub('https://openalex.org/', '', w$id, fixed = TRUE)
    doi <- tolower(sub('https://doi.org/', '', w$doi %||% '', fixed = TRUE))
    keys <- c(w$id, if (nzchar(doi)) doi)
    if (any(keys %in% seen) || w$id %in% ids || doi %in% dois ||
        id %in% unlist(cfg$exclude_works) || (w$type %||% '') %in% unlist(cfg$exclude_types) ||
        is.null(w$publication_year) || w$publication_year < cfg$min_year) next
    seen <- c(seen, keys)
    confirmed <- id %in% manual_ids
    linked <- w$id %in% citing_ids
    status <- if (confirmed) 'verified_manually' else if (linked) 'citation_linked_openalex' else 'candidate'
    records[[length(records) + 1L]] <- data.frame(
      id = id, year = w$publication_year, title = w$title %||% '',
      authors = paste(vapply(w$authorships, function(a) a$author$display_name %||% '', ''), collapse = '; '),
      doi = doi, url = if (nzchar(doi)) paste0('https://doi.org/', doi) else w$id,
      status = status, evidence = if (confirmed) cfg$confirmed_works[[id]] else if (linked) paste(intersect(w$referenced_works, ids), collapse = '; ') else 'OpenAlex fulltext.search: gfwr',
      stringsAsFactors = FALSE)
    works[[length(works) + 1L]] <- w
  }
  rows <- if (length(records)) do.call(rbind, records) else data.frame(id=character(), year=integer(), title=character(), authors=character(), doi=character(), url=character(), status=character(), evidence=character())
  ord <- order(-rows$year, rows$id); rows <- rows[ord, , drop = FALSE]; works <- works[ord]
  accepted <- rows$status != 'candidate'
  # All requests must finish before any output is replaced.
  for (name in c('citations', 'candidates')) {
    keep <- if (name == 'citations') accepted else !accepted
    tmp <- tempfile(); write.csv(rows[keep, , drop=FALSE], tmp, row.names=FALSE, na='', fileEncoding='UTF-8')
    write_changed(paste0('data/', name, '.csv'), readLines(tmp, encoding='UTF-8')); unlink(tmp)
  }
  write_changed('data/records.json', toJSON(rows, pretty=TRUE, auto_unbox=TRUE))
  bib <- vapply(lapply(works[accepted], work_to_bibtex), `[[`, '', 'text')
  write_changed('data/citations.bib', c('% gfwr citations linked by OpenAlex or verified manually. See data/records.json.', paste(bib, collapse='\n\n')))
  write_changed('data/sources.json', toJSON(list(dois=dois, openalex_ids=ids, not_indexed=missing), pretty=TRUE, auto_unbox=FALSE))
  render_list <- function(keep) {
    if (!any(keep)) return('<p>No hay registros en esta categoría.</p>')
    paste0('<ol>', paste(vapply(which(keep), function(i) paste0('<li><a href="', html(rows$url[i]), '">', html(rows$title[i]), '</a> (', rows$year[i], ')<br><small>', html(rows$authors[i]), ' · ', html(rows$status[i]), '</small></li>'), ''), collapse='\n'), '</ol>')
  }
  write_changed('docs/index.html', c('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Publicaciones · gfwr</title>',
    '<style>body{font:18px/1.6 system-ui;max-width:960px;margin:40px auto;padding:0 24px;color:#173343;background:#f5f9fa}a{color:#006b79}li{margin-bottom:18px}small{color:#485b65}</style><main><h1>Publicaciones y menciones de gfwr</h1>',
    '<p>Actualización mensual desde OpenAlex y Zenodo. Cobertura parcial: una mención no demuestra una cita al paquete. Las citas enlazadas reflejan el índice de OpenAlex y pueden requerir revisión.</p>',
    '<p><a href="https://github.com/cornejotux/gfwr-citations/tree/main/data">Descargar CSV, JSON y BibTeX</a> · <a href="https://github.com/cornejotux/gfwr-citations/actions">Ver última ejecución</a></p>',
    paste0('<h2>Citas enlazadas o verificadas (', sum(accepted), ')</h2>'), render_list(accepted),
    paste0('<h2>Menciones candidatas por revisar (', sum(!accepted), ')</h2>'), render_list(!accepted), '</main></html>'))
  message('Saved ', sum(accepted), ' citations and ', sum(!accepted), ' candidates')
}
if (sys.nframe() == 0) main()
