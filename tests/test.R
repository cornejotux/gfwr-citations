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
