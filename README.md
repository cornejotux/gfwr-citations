# gfwr-citations

**[Ver publicaciones y repositorios](https://cornejotux.github.io/gfwr-citations/)** · [Ejecuciones](https://github.com/cornejotux/gfwr-citations/actions)

Rastreador de citas, menciones y referencias de código al paquete [gfwr](https://github.com/GlobalFishingWatch/gfwr). Basado en el diseño de [codyn](https://github.com/NCEAS/codyn/blob/main/.github/workflows/update-citations.yaml), con varias fuentes y procedencia por registro.

## Fuentes y nivel de automatización

| Fuente | Qué aporta | Cómo se actualiza |
| --- | --- | --- |
| OpenAlex | Citas a los DOI del paquete y posibles menciones en texto | API, mensualmente |
| Zenodo | DOI conceptual y DOI de todas las versiones de gfwr | API, mensualmente; es fuente de identificadores, no de publicaciones citantes |
| GitHub | Importaciones, llamadas y enlaces al paquete en archivos R, Rmd y Quarto | API de búsqueda de código, mensualmente |
| Google Scholar | Descubrimiento de publicaciones adicionales | Consulta revisada e importación de registros; **manual** |
| ResearchGate | Publicaciones y evidencia en los textos disponibles | Consulta revisada e importación de registros; **manual** |

No se presenta un enlace a una búsqueda como si fuera una cita verificada. La primera consulta de Scholar y ResearchGate se realizó el 30 de septiembre de 2026; cubre una selección revisada, no toda la plataforma. Los registros conservan su fecha original hasta que se revisan de nuevo.

Google Scholar [no ofrece acceso masivo](https://scholar.google.com/intl/en/scholar/help.html). No se implementa scraping desatendido ni se promete una API pública de ResearchGate. El workflow combina los registros importados de estas fuentes, pero **no descubre automáticamente nuevos resultados en Scholar o ResearchGate**.

## Procedencia y tipos de evidencia

Cada publicación contiene `sources` y una lista `evidence`. Cada evidencia conserva la plataforma, el enlace consultado, el método, una nota y, para las revisiones manuales, `observed_at`. Si aparece en varias fuentes, se conserva un solo registro por DOI y se agregan todas sus evidencias. Sin DOI se usa el ID estable; no se fusionan títulos similares automáticamente. Una fuente de descubrimiento no se convierte en prueba de una cita.

- `verified_manually`: referencia al paquete comprobada en el texto o bibliografía.
- `citation_linked_openalex`: OpenAlex enlaza una referencia a un DOI del paquete; puede requerir revisión.
- `candidate`: resultado pendiente de revisión; no cuenta como cita.
- Repositorios: se cuentan **por separado**, una vez por repositorio. `code_reference` indica una referencia de código, no demuestra que se ejecutó correctamente.

La búsqueda de GitHub tiene cobertura parcial: archivos indexados de la rama predeterminada, extensiones configuradas y límites de la API. Se excluyen registros privados, forks identificados, el paquete original y este rastreador. No se publican fragmentos de código: se guardan enlaces, rutas y SHA de los blobs para revisar la evidencia. Los ejemplos y tutoriales pueden aparecer junto a proyectos de investigación.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `data/records.json` | Publicaciones unificadas y todas sus evidencias |
| `data/citations.csv` | Citas verificadas o enlazadas |
| `data/candidates.csv` | Publicaciones por revisar |
| `data/citations.bib` | BibTeX mínimo del listado unificado de citas |
| `data/repositories.csv`, `data/repositories.json` | Repositorios y archivos con evidencia |
| `data/source-status.json` | Estado y modalidad de actualización por fuente |
| `data/github-cache.json` | Última búsqueda completa de GitHub y fecha |
| `data/openalex/` | Resultados y caché originales de OpenAlex; incluye BibTeX con metadatos detallados |
| `config/external-publications.csv` | Registros revisados de Scholar y ResearchGate |
| `config/sources.yml` | DOI, filtros y revisiones de OpenAlex |
| `docs/index.html` | Sitio publicado en GitHub Pages |

## Agregar registros de Scholar o ResearchGate

1. Buscar `"gfwr" "fishing"` en [Google Scholar](https://scholar.google.com/scholar?q=%22gfwr%22+%22fishing%22) o `gfwr` en [ResearchGate](https://www.researchgate.net/search/publication?q=gfwr).
2. Revisar el artículo y descartar homónimos: GFWR también es una sigla en otras disciplinas.
3. Agregar una fila a `config/external-publications.csv` desde GitHub o localmente. Usar un editor CSV que respete comillas cuando un campo contiene comas.
4. Conservar `source` (`Google Scholar` o `ResearchGate`), `source_url` de esa plataforma, `url` del artículo, DOI, título, autores, año, `observed_at` (AAAA-MM-DD), `method: manual_review`, `status` y `note` con el lugar donde se observó la referencia.
5. Usar `candidate` si solo se observó un resultado; usar `verified_manually` solo después de comprobar la cita. Para la misma publicación en varias plataformas, agregar una fila por fuente con el mismo DOI.
6. Guardar en `main`: el workflow incorporará las filas y actualizará el sitio. Nunca atribuir a Scholar un registro que solo se consultó en OpenAlex.

Para registros sin DOI, usar un ID único estable (por ejemplo `scholar:identificador-del-registro`). No usar el número total de resultados de Scholar como recuento de citas de gfwr. Para retirar un registro externo, quitar su fila; si también aparece en OpenAlex, excluirlo en `config/sources.yml`.

## Ejecución automática

Día **1 de cada mes a las 06:00 UTC**, ejecución manual desde Actions y ejecución al modificar scripts, configuración, pruebas o workflow. GitHub conserva los cambios de datos; el despliegue de Pages ocurre en el mismo workflow.

Las fuentes automáticas fallan de manera independiente. Una búsqueda incompleta de GitHub conserva la última búsqueda completa. Si OpenAlex falla, se mantienen sus archivos previos y se actualizan las otras fuentes. El sitio y `data/source-status.json` muestran el estado, para no confundir datos anteriores con búsquedas completas actuales.

### Secretos y permisos

- `OPENALEX_API_KEY`: opcional, recomendable para evitar restricciones de búsquedas anónimas; [acceso de OpenAlex](https://help.openalex.org/api/authentication/).
- GitHub utiliza el `GITHUB_TOKEN` del workflow. Si el entorno no permite buscar código público con ese token, configurar `GITHUB_SEARCH_TOKEN` con un token compatible de acceso mínimo para lectura de código público. No introducir tokens en archivos ni en issues. Los fallos quedan visibles y conservan la caché.
- No se requieren credenciales de Google Scholar, ResearchGate ni Global Fishing Watch.
- GitHub Pages debe usar **GitHub Actions** como fuente. El workflow necesita escritura de contenidos para guardar resultados. Si se protege `main`, adaptar la escritura a un PR o bot autorizado.
- GitHub puede desactivar las ejecuciones programadas de repositorios públicos tras 60 días sin actividad. Revisar [sus condiciones de programación](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) y Actions si no hay ejecuciones recientes.

## Ejecutar localmente

R, Python 3.9+ y los paquetes R `httr2`, `jsonlite`, `yaml`:

```sh
Rscript -e 'install.packages(c("httr2", "jsonlite", "yaml"))'
Rscript tests/test.R
python3 -m unittest discover -s tests -p 'test_*.py'
Rscript scripts/update_citations.R
python3 scripts/update_sources.py
```

Configurar `GH_TOKEN` mediante el gestor de secretos del entorno para la búsqueda de código; sin token se conserva la caché. El script R genera exclusivamente la etapa OpenAlex. El script Python combina todas las fuentes, consulta GitHub y genera el sitio y las exportaciones finales.

## Créditos y alcance

El formateador BibTeX y el diseño inicial DOI → OpenAlex → Actions se adaptaron de NCEAS/codyn. Ver `NOTICE` y `LICENSE` (Apache 2.0). La cobertura no es exhaustiva; los resultados pueden contener errores de las fuentes. Preprints y artículos con DOI diferentes se mantienen separados hasta revisión. No se redistribuyen artículos completos.
