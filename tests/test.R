source('scripts/update_citations.R')
stopifnot(identical(html('<a&"'), '&lt;a&amp;&quot;'))
stopifnot(identical(clean_text('A &amp; <em>B</em>'), 'A \\& \\emph{B}'))
w <- list(id='https://openalex.org/W1', title='A title', publication_year=2025,
          type='article', authorships=list(), primary_location=list(source=list(display_name='Journal')),
          doi='https://doi.org/10.1234/test', biblio=list(first_page='1', last_page='4'))
b <- work_to_bibtex(w)
stopifnot(grepl('pages = {1--4}', b$text, fixed=TRUE))
stopifnot(grepl('doi = {10.1234/test}', b$text, fixed=TRUE))
f <- tempfile(); write_changed(f, 'same'); before <- file.info(f)$mtime
write_changed(f, 'same'); stopifnot(identical(before, file.info(f)$mtime)); unlink(f)
# Pagination must retain every page and reject repeated cursors.
i <- 0L
get_json <- function(...) { i <<- i + 1L; if (i == 1) list(results=list(list(id='W1')), meta=list(count=2,next_cursor='next')) else list(results=list(list(id='W2')),meta=list(count=2,next_cursor=NULL)) }
stopifnot(length(fetch_pages(list())) == 2L)
get_json <- function(...) list(results=list(list(id='W1')),meta=list(count=2,next_cursor='*'))
stopifnot(inherits(try(fetch_pages(list()), silent=TRUE), 'try-error'))
cat('All tests passed\n')
# End-to-end fixtures: classification, deduplication, cache, failure preservation.
source('scripts/update_citations.R')
root <- getwd(); sandbox <- tempfile(); dir.create(sandbox); setwd(sandbox)
dir.create('config')
writeLines(c('zenodo_record: "1"', 'concept_doi: "10.1/source"', 'search_terms: [gfwr]', 'min_year: 2022', 'confirmed_works: {}'), 'config/sources.yml')
source_work <- list(id='https://openalex.org/W0', doi='https://doi.org/10.1/source')
a <- w; a$id <- 'https://openalex.org/W1'; a$referenced_works <- list(source_work$id)
b <- w; b$id <- 'https://openalex.org/W2'; b$doi <- 'https://doi.org/10.1/candidate'
get_json <- function(url, ...) {
 if (grepl('/versions/latest', url, fixed=TRUE)) return(list(links=list(versions='versions')))
 if (url == 'versions') return(list(hits=list(hits=list(list(doi='10.1/source')))))
 source_work
}
fetch_pages <- function(query) if (startsWith(query$filter, 'cites:')) list(a) else list(a,b)
main()
r <- fromJSON('data/openalex/records.json'); stopifnot(nrow(r)==2, sum(r$status=='candidate')==1)
original <- readLines('data/openalex/records.json')
fetch_pages <- function(query) if (startsWith(query$filter, 'cites:')) list(a) else stop('search unavailable')
suppressWarnings(main())
stopifnot(identical(original, readLines('data/openalex/records.json')))
stopifnot(fromJSON('data/openalex/status.json')$mention_search == 'unavailable_cached_results')
fetch_pages <- function(query) stop('citation query unavailable')
stopifnot(inherits(try(main(), silent=TRUE), 'try-error'))
stopifnot(identical(original, readLines('data/openalex/records.json')))
setwd(root); unlink(sandbox, recursive=TRUE)
cat('Pipeline and failure-preservation tests passed\n')
