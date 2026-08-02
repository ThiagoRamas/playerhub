# ADR 0001: el dataset es una fuente de importación

- Estado: aceptada
- Fecha: 2026-08-01

## Contexto

PlayerHub necesita información histórica amplia sin depender en cada consulta de una API externa. Los CSV disponibles contienen perfiles, clubes, rendimientos, valores, transferencias y lesiones, pero presentan duplicados, cobertura parcial y convenciones propias de la fuente.

## Decisión

PlayerHub definirá un modelo de dominio propio en PostgreSQL. Un ETL versionado traducirá los CSV a ese modelo. La API y el frontend solo consultarán la base de PlayerHub y nunca leerán directamente los CSV.

Cada importación será reproducible, auditable e idempotente. Los identificadores externos se conservarán para trazabilidad, pero no serán claves primarias del dominio.

## Consecuencias

### Positivas

- La aplicación no queda acoplada a la disponibilidad ni al formato de una fuente externa.
- Las reglas de limpieza son explícitas y comprobables.
- El dominio puede evolucionar independientemente del dataset.
- Las cargas futuras pueden actualizar datos sin duplicarlos.

### Costos

- Se necesita mantener un ETL, migraciones y controles de calidad.
- La actualización de los datos no es automática por sí misma.
- Los registros incompletos requieren estrategias de enriquecimiento.
- Deben revisarse licencia, atribución y permisos antes de publicar el contenido.

