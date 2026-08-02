# PlayerHub

PlayerHub es una plataforma de análisis de futbolistas y clubes construida sobre un modelo de datos propio. Los CSV de origen se procesan mediante un ETL y nunca son consultados directamente por la aplicación.

## Arquitectura objetivo

```text
Dataset → ETL Python → PostgreSQL → FastAPI → React
```

## Estado

- Auditoría inicial del dataset completada.
- Modelo de dominio documentado.
- Esquema lógico PostgreSQL diseñado.
- Primera migración disponible.
- Backend, frontend y ETL pendientes.

## Base de datos local

Requisito: Docker Desktop con Docker Compose.

1. Copiar `.env.example` como `.env`.
2. Ejecutar `docker compose up -d database`.
3. Esperar a que el servicio esté saludable.
4. Ejecutar la verificación:

```powershell
Get-Content database/verify_schema.sql | docker compose exec -T database psql -U playerhub -d playerhub
```

La migración ubicada en `database/migrations` se ejecuta automáticamente al crear el volumen por primera vez.

## ETL piloto

El primer importador carga una instantánea de un club: perfiles actuales, jugadores cedidos, países, posiciones, agentes y pertenencias. El club objetivo se configura con `PLAYERHUB_TARGET_CLUB_ID`; el valor inicial `1234` corresponde a Club Atlético Independiente.

```powershell
docker compose --profile tools build etl
docker compose --profile tools run --rm etl load-club-snapshot
```

Los CSV se montan como solo lectura desde `PLAYERHUB_DATASET_PATH`. El importador puede ejecutarse nuevamente sin duplicar entidades ni membresías.

Después de cargar la instantánea del club, el segundo comando importa para esos jugadores sus rendimientos, valores de mercado, transferencias y lesiones:

```powershell
docker compose --profile tools run --rm etl load-player-history
```

La carga histórica también es idempotente y registra inserciones y actualizaciones por cada CSV.

## API local

```powershell
docker compose up -d backend
```

La API queda disponible en `http://localhost:8000`, con documentación interactiva en `http://localhost:8000/docs`.

Pruebas de integración:

```powershell
docker compose run --rm backend python -m pytest -q
```

Endpoints iniciales:

- `GET /health`
- `GET /api/v1/clubs?search=Independiente`
- `GET /api/v1/clubs/{id}`
- `GET /api/v1/clubs/{id}/squad`
- `GET /api/v1/players/{id}`
- `GET /api/v1/players/{id}/performances`
- `GET /api/v1/players/{id}/market-values`
- `GET /api/v1/players/{id}/transfers`
- `GET /api/v1/players/{id}/injuries`

## Documentación

- `docs/domain-model.md`: entidades y reglas del dominio.
- `docs/data-audit.md`: calidad y cobertura del dataset.
- `database/schema-design.md`: decisiones del esquema lógico.
- `docs/decisions`: registros de decisiones de arquitectura.
