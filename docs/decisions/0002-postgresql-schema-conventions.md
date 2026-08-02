# ADR 0002: convenciones del esquema PostgreSQL

- Estado: aceptada
- Fecha: 2026-08-01

## Contexto

PlayerHub importará millones de registros relacionados y necesita claves eficientes, reglas verificables e historial de cargas. También debe poder evolucionar mediante migraciones sin quedar atado a decisiones difíciles de cambiar.

## Decisión

- Usar PostgreSQL 16.
- Usar claves internas `BIGINT GENERATED ALWAYS AS IDENTITY`.
- Conservar IDs externos en columnas separadas y únicas.
- Usar `CHECK` para estados pequeños en lugar de enums propios de PostgreSQL.
- Guardar importes como enteros y exigir una moneda explícita cuando se conozca.
- Mantener valores desconocidos como `NULL`.
- Registrar procedencia mediante ejecuciones ETL y huellas de filas.
- Usar `pg_trgm` para búsquedas tolerantes en nombres.

## Consecuencias

Las consultas y relaciones principales usan claves compactas. Los estados pueden ampliarse con migraciones ordinarias y los procesos de importación son auditables. Como costo, el ETL debe resolver IDs externos a internos y mantener la trazabilidad de cada carga.

