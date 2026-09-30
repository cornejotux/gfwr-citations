# gfwr-citations

Listado actualizable de publicaciones que citan o mencionan el paquete R [gfwr](https://github.com/GlobalFishingWatch/gfwr), inspirado en [NCEAS/codyn](https://github.com/NCEAS/codyn/blob/main/.github/workflows/update-citations.yaml).

**[Consultar el sitio](https://cornejotux.github.io/gfwr-citations/)** · **[Estado de las actualizaciones](https://github.com/cornejotux/gfwr-citations/actions/workflows/update-citations.yml)**

## Cómo funciona

1. Consulta Zenodo para descubrir el DOI conceptual y todas las versiones del paquete (incluidas versiones nuevas).
2. Resuelve esos DOI en OpenAlex y descarga las publicaciones que los citan, con paginación completa.
3. Busca `gfwr` en el texto indexado por OpenAlex para detectar menciones adicionales.
4. Separa citas enlazadas, citas verificadas manualmente y candidatos pendientes. Excluye las versiones del propio paquete; deduplica por ID y DOI, sin fusionar artículos solo por su título.
5. Actualiza los archivos y el sitio. GitHub conserva el historial; solo se genera un commit cuando cambian los resultados.

El workflow corre el **día 1 de cada mes a las 06:00 UTC**, permite ejecución manual desde Actions → Update gfwr citations → Run workflow y se ejecuta cuando cambia código o configuración. La publicación de Pages ocurre dentro del mismo workflow; no requiere el bot privado de NCEAS ni un token personal.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `data/citations.csv` | Citas enlazadas por OpenAlex o verificadas manualmente |
| `data/candidates.csv` | Resultados de búsqueda que necesitan revisión |
| `data/citations.bib` | Bibliografía de las citas enlazadas/verificadas |
| `data/records.json` | Todos los registros, estado y evidencia |
| `data/sources.json` | DOI consultados, IDs y DOI aún no indexados |
| `data/status.json` | Estado de las consultas de citas y menciones |
| `data/candidate-cache.json` | Última búsqueda completa de candidatos, cuando existe |
| `docs/index.html` | Página estática que publica GitHub Pages |
| `config/sources.yml` | Fuentes y decisiones de revisión |

`citation_linked_openalex` significa que OpenAlex registra una referencia a un DOI del paquete; no implica revisión humana. `verified_manually` identifica una comprobación documentada. `candidate` nunca se cuenta como cita confirmada.

## Revisar resultados

Abrir el texto del candidato y comprobar la referencia al paquete. Agregar su ID y el enlace de evidencia en `confirmed_works`, por ejemplo:

```yaml
confirmed_works:
  W1234567890: https://publisher.example/article
```

El ID y enlace anteriores son ilustrativos. Para descartar falsos positivos, agregar los IDs reales a `exclude_works`. Guardar cambios en `main` dispara la actualización. La confirmación manual se vuelve a consultar aunque el registro deje de aparecer en las búsquedas.

## Ejecutar localmente

Desde la raíz del repositorio, con R instalado:

```r
install.packages(c("httr2", "jsonlite", "yaml"))
```

```sh
Rscript tests/test.R
Rscript scripts/update_citations.R
```

Opcional: configurar el secreto `OPENALEX_API_KEY` en Settings → Secrets and variables → Actions para ampliar el presupuesto de consultas. La clave se envía por encabezado y no se guarda en los archivos. Consultar las [condiciones actuales de acceso de OpenAlex](https://help.openalex.org/api/authentication/). No hace falta un token de la API de Global Fishing Watch.

## Configuración en GitHub

- GitHub Pages: Settings → Pages → Source: **GitHub Actions**.
- El workflow necesita escritura de contenidos para guardar los archivos. Si se protege `main`, adaptar el guardado a un PR o autorizar un bot; no desactivar protecciones existentes indiscriminadamente.
- GitHub puede desactivar workflows programados de repositorios públicos tras 60 días sin actividad. Revisar Actions si no hay ejecuciones recientes; la programación depende del servicio y puede demorarse. [Documentación](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Alcance y mantenimiento

OpenAlex no indexa todas las referencias ni el texto completo de todas las publicaciones. Las referencias mediante URL o sin DOI pueden quedar fuera; las búsquedas de texto pueden producir falsos positivos. No es un recuento exhaustivo de todas las citas a gfwr. Los DOI no indexados quedan registrados y se reintentan en cada ejecución. Si falla Zenodo o la consulta de citas por DOI, la ejecución se detiene antes de sustituir los archivos. Si solo falla la búsqueda de menciones, las citas se actualizan, se conservan los candidatos anteriores y se publica una advertencia visible en el sitio, en Actions y en `data/status.json`. Sin caché previo, cero candidatos significa búsqueda pendiente, no ausencia de menciones. Un registro retirado por OpenAlex puede desaparecer del listado, pero permanece en el historial Git.

El sitio enlaza a Actions para consultar la fecha de la última ejecución, sin modificar archivos solo para cambiar una fecha. CSV, JSON y BibTeX son salidas generadas: editar las decisiones en la configuración.

## Créditos

El formateador BibTeX se adaptó del script de codyn, cuyo diseño de DOI → OpenAlex → GitHub Actions sirve de base. Ver `NOTICE` y `LICENSE` (Apache 2.0). El rastreo de versiones, separación de candidatos, exportaciones y sitio se implementaron para gfwr.
