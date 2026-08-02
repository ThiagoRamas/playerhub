# PlayerHub

PlayerHub es una plataforma de análisis de futbolistas y clubes construida sobre un modelo de datos propio. Los CSV de origen se procesan mediante un ETL y nunca son consultados directamente por la aplicación.

El idioma de la aplicación es español. Los códigos internos y los nombres de campos de la API se mantienen estables en inglés, pero la interfaz, los mensajes para usuarios y la documentación funcional se presentan en español.

## Arquitectura objetivo

```text
Dataset → ETL Python → PostgreSQL → FastAPI → React
```

## Estado

- Auditoría inicial del dataset completada.
- Modelo de dominio documentado.
- Esquema lógico PostgreSQL diseñado.
- Primera migración disponible.
- El ETL piloto, la API y la primera interfaz web se encuentran implementados.

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

### Ampliar la base a otros clubes

El catálogo del propio dataset permite encontrar clubes que tienen información suficiente para cargar un plantel. Por ejemplo:

```powershell
docker compose --profile tools run --rm etl list-source-clubs --country Argentina --search River
```

El resultado incluye el `club_id` y la cantidad de perfiles disponibles. Para cargar la ficha y todo el historial de uno o varios clubes en una sola ejecución:

```powershell
docker compose --profile tools run --rm etl load-club-data --club-id 209
docker compose --profile tools run --rm etl load-club-data --club-id 209 --club-id 189
```

Los identificadores `209` y `189` corresponden a River Plate y Boca Juniors en esta versión del dataset. `--club-id` no modifica `.env`; si no se incluye, los comandos existentes siguen usando `PLAYERHUB_TARGET_CLUB_ID`. Las cargas pueden repetirse sin generar duplicados.

Pruebas del importador:

```powershell
docker compose --profile tools run --rm --entrypoint python etl -m unittest discover -s tests -v
```

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

## Aplicación web

La interfaz de PlayerHub está disponible en español e incluye búsqueda de clubes, resumen del plantel, valor de mercado y filtros para jugadores propios, incorporados a préstamo y cedidos. Cada tarjeta abre una ficha individual con rendimiento, evolución de valor, transferencias y lesiones.

```powershell
docker compose up -d --build frontend
```

Luego abrir `http://localhost:3000`.

## Documentación

- `docs/domain-model.md`: entidades y reglas del dominio.
- `docs/data-audit.md`: calidad y cobertura del dataset.
- `database/schema-design.md`: decisiones del esquema lógico.
- `docs/decisions`: registros de decisiones de arquitectura.
