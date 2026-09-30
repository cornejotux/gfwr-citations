# Adapted from NCEAS/codyn, Apache-2.0. See NOTICE.
`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || identical(x, "")) y else x

# Convert an OpenAlex title (which may contain HTML markup and entities) to
# BibTeX-safe text, keeping italics.
clean_text <- function(x) {
  if (is.null(x)) return("")
  x <- gsub("<(i|em)>(.*?)</\\1>", "\u0001\\2\u0002", x, perl = TRUE, ignore.case = TRUE)
  x <- gsub("<[^>]+>", "", x)
  entities <- c("&amp;" = "&", "&lt;" = "<", "&gt;" = ">", "&quot;" = "\"",
                "&#39;" = "'", "&apos;" = "'", "&nbsp;" = " ")
  for (e in names(entities)) x <- gsub(e, entities[[e]], x, fixed = TRUE)
  x <- gsub("[{}\\\\]", "", x)
  x <- gsub("([&%$#_])", "\\\\\\1", x)
  x <- gsub("\u0001", "\\\\emph{", x)
  x <- gsub("\u0002", "}", x)
  x <- gsub("\\s+", " ", x)
  trimws(x)
}

title_key <- function(x) gsub("[^a-z0-9]", "", tolower(x %||% ""))

ascii_name <- function(x) {
  x <- iconv(x, "UTF-8", "ASCII//TRANSLIT", sub = "")
  gsub("[^A-Za-z]", "", x)
}

work_to_bibtex <- function(w, corrections = list()) {
  id <- sub("^https://openalex.org/", "", w$id)
  authors <- vapply(w$authorships, function(a) {
    clean_text(a$raw_author_name %||% a$author$display_name %||% "")
  }, "")
  authors <- authors[nzchar(authors)]
  first_last <- if (length(authors)) ascii_name(tail(strsplit(authors[1], " ")[[1]], 1)) else ""
  key <- paste0(first_last %||% "anon", w$publication_year, "_", id)

  source <- clean_text(w$primary_location$source$display_name)
  b <- w$biblio
  pages <- if (!is.null(b$first_page)) {
    if (!is.null(b$last_page) && b$last_page != b$first_page) {
      paste0(b$first_page, "--", b$last_page)
    } else {
      b$first_page
    }
  }
  entry_type <- switch(w$type,
    article = , review = if (nzchar(source)) "article" else "misc",
    preprint = if (nzchar(source)) "article" else "misc",
    "book-chapter" = "incollection",
    book = "book",
    "conference-paper" = "inproceedings",
    dissertation = "phdthesis",
    report = "techreport",
    "misc"
  )
  container <- switch(entry_type,
    article = "journal", incollection = , inproceedings = "booktitle",
    phdthesis = "school", techreport = "institution", "howpublished")

  fields <- list(
    author = paste(authors, collapse = " and "),
    title = paste0("{", clean_text(w$title), "}"),
    year = w$publication_year,
    volume = b$volume,
    number = b$issue,
    pages = pages,
    doi = sub("^https://doi.org/", "", w$doi %||% ""),
    url = if (is.null(w$doi)) w$primary_location$landing_page_url
  )
  fields[[container]] <- source
  fix <- corrections[[id]]
  if (!is.null(fix$title)) fix$title <- paste0("{", clean_text(fix$title), "}")
  fields[names(fix)] <- fix
  fields <- Filter(function(v) !is.null(v) && nzchar(v), lapply(fields, as.character))
  body <- paste0("  ", names(fields), " = {", unlist(fields), "}", collapse = ",\n")
  list(key = key, year = w$publication_year, title = clean_text(fix$title %||% w$title),
       text = paste0("@", entry_type, "{", key, ",\n", body, "\n}"))
}

