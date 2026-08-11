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

Para ampliar automáticamente la cobertura sin indicar cada club, se puede cargar un país en lotes. Cada lote agrupa jugadores de varios clubes y recorre los archivos históricos una sola vez:

```powershell
docker compose --profile tools run --rm etl load-country --country Argentina --batch-size 20
```

Antes de una carga completa se recomienda validar un lote pequeño:

```powershell
docker compose --profile tools run --rm etl load-country --country Argentina --batch-size 3 --max-clubs 3
```

Si la ejecución se interrumpe, el mismo comando puede repetirse: las cargas terminadas quedan confirmadas y los registros existentes se actualizan sin duplicarse.

Cuando el catálogo de clubes contiene un nombre truncado, el importador recupera el nombre más frecuente presente en los perfiles vinculados. Esta regla corrige casos conocidos como `CA Newell\` sin modificar los CSV originales.

### Actualizar planteles vigentes

El archivo histórico se conserva y API-Football se utiliza únicamente como fuente de importación para planteles actuales. La clave se guarda solo en `.env`, que está excluido de Git:

```env
API_FOOTBALL_KEY=tu_clave_privada
```

En una base ya creada, aplicar la migración incremental una sola vez y reconstruir el importador:

```powershell
Get-Content database/migrations/002_live_data_sources.sql | docker compose exec -T database psql -U playerhub -d playerhub
docker compose --profile tools build etl
```

La primera ejecución de Independiente funciona como vista previa y no modifica datos:

```powershell
docker compose --profile tools run --rm etl sync-live-squad --club-id 1234
```

Antes de comparar, el ETL consulta perfiles individuales sin depender de una
temporada para completar nombre, fecha de nacimiento, nacionalidad, altura y
foto cuando el proveedor los tiene. Para cuidar el cupo gratuito solo consulta
jugadores nuevos o con coincidencias dudosas. Si esos perfiles no están
disponibles, la vista previa sigue funcionando pero la aplicación se bloquea
automáticamente antes de crear entidades con nombres abreviados.

El intervalo predeterminado de 6,5 segundos entre consultas respeta el límite
de 10 solicitudes por minuto del plan gratuito. Puede configurarse con
`API_FOOTBALL_MIN_INTERVAL_SECONDS` si cambia el plan contratado.

Cuando API-Football no publica el perfil de un juvenil, el ETL puede completar
el nombre y la fecha de nacimiento desde el plantel oficial de Reserva de
Independiente. Estas excepciones están identificadas por jugador y conservan la
URL oficial en la trazabilidad de la ejecución.
Cuando la fuente en vivo identifica sin ambigüedad a un jugador que figura
actualmente en otro club, el ETL cierra ese vínculo anterior antes de crear el
nuevo. El registro anterior no se elimina: queda disponible como historial con
`is_current = false`. El contador `relocated_from_other_clubs` permite revisar
estos casos en la vista previa.
El resultado separa altas, regresos, bajas, jugadores sin cambios y cedidos que deben conservarse. Después de revisar esa comparación, la misma instantánea puede aplicarse explícitamente:

```powershell
docker compose --profile tools run --rm etl sync-live-squad --club-id 1234 --apply
```

Si el club no puede identificarse automáticamente, se pueden consultar candidatos y proporcionar el identificador elegido:

```powershell
docker compose --profile tools run --rm etl find-live-clubs --search Independiente --country Argentina
docker compose --profile tools run --rm etl sync-live-squad --club-id 1234 --provider-team-id ID_ENCONTRADO
```

API-Football se consulta solo durante el ETL. La API web y el frontend continúan leyendo exclusivamente PostgreSQL.

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
