# PlayerHub — diseño lógico PostgreSQL

Estado: propuesta previa a la primera migración.

## Convenciones

- Claves primarias: `BIGINT GENERATED ALWAYS AS IDENTITY`.
- Identificadores externos: `source_external_id`, con unicidad por entidad cuando exista.
- Fechas sin hora: `DATE`. Instantes de carga: `TIMESTAMPTZ` en UTC.
- Importes: `BIGINT` en unidades completas de moneda para evitar errores de punto flotante.
- Contadores: `INTEGER` con restricción no negativa.
- Campos de dominio pequeños: `TEXT` con `CHECK`; se evitan enums de PostgreSQL para facilitar migraciones.
- Todas las tablas importadas incluyen trazabilidad mediante una ejecución ETL.
- Los nombres conservan Unicode y se almacenan en UTF-8.

## Catálogos

### `countries`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `name` | text | requerido, único |
| `iso_code` | char(2) | opcional, único |

### `position_groups`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | smallint identity | PK |
| `code` | text | único; goalkeeper, defender, midfield, attack |
| `name` | text | requerido |

### `positions`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | smallint identity | PK |
| `group_id` | smallint | FK → `position_groups` |
| `code` | text | único |
| `name` | text | requerido |

### `seasons`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `label` | text | requerido, por ejemplo `24/25` o `2025` |
| `start_year` | smallint | requerido |
| `end_year` | smallint | requerido |
| `calendar_type` | text | `SPLIT_YEAR`, `CALENDAR_YEAR` o `UNKNOWN` |

Unicidad: `label`, `start_year`, `end_year`. La etiqueta no se interpreta sin una regla explícita.

### `competitions`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `source_external_id` | text | único, opcional para stubs |
| `name` | text | requerido |
| `slug` | text | opcional |
| `country_id` | bigint | FK opcional → `countries` |
| `is_complete` | boolean | requerido, default false |

## Entidades

### `players`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `source_external_id` | bigint | único, requerido para esta fuente |
| `slug` | text | opcional |
| `display_name` | text | requerido |
| `full_name` | text | opcional |
| `date_of_birth` | date | opcional |
| `date_of_death` | date | opcional |
| `place_of_birth` | text | opcional |
| `country_of_birth_id` | bigint | FK opcional → `countries` |
| `height_cm` | smallint | opcional, entre 100 y 250 |
| `preferred_foot` | text | `RIGHT`, `LEFT`, `BOTH` o `UNKNOWN` |
| `career_status` | text | `ACTIVE`, `RETIRED`, `WITHOUT_CLUB`, `CAREER_BREAK` o `UNKNOWN` |
| `image_url` | text | opcional |
| `is_complete` | boolean | indica si existe perfil fuente |
| `data_as_of` | date | fecha de corte conocida |

Índices: nombre normalizado para búsqueda; nacimiento; estado. La búsqueda tolerante a errores puede usar `pg_trgm` en una etapa posterior.

### `player_citizenships`

PK compuesta: `player_id`, `country_id`. Ambas columnas son claves foráneas.

### `player_positions`

| Columna | Tipo | Regla |
|---|---|---|
| `player_id` | bigint | FK → `players` |
| `position_id` | smallint | FK → `positions` |
| `is_primary` | boolean | requerido |

PK compuesta. Índice único parcial para permitir una sola posición principal por jugador.

### `clubs`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `source_external_id` | bigint | único, opcional |
| `name` | text | requerido |
| `slug` | text | opcional |
| `country_id` | bigint | FK opcional → `countries` |
| `team_type` | text | `FIRST_TEAM`, `RESERVE`, `YOUTH`, `NATIONAL_TEAM` u `OTHER` |
| `logo_url` | text | opcional |
| `is_complete` | boolean | requerido, default false |
| `data_as_of` | date | opcional |

No se exige nombre único: existen homónimos. La identidad externa evita mezclar Independiente con otros clubes del mismo nombre.

### `club_relationships`

PK compuesta: `parent_club_id`, `child_club_id`, `relationship_type`. Las dos primeras columnas apuntan a `clubs`; se prohíbe relacionar un club consigo mismo.

### `agents`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `source_external_id` | bigint | único, opcional |
| `name` | text | requerido |
| `is_complete` | boolean | requerido, default false |

### `player_agent_representations`

Relaciona jugador y agente con `start_date`, `end_date` e `is_current`. Las fechas pueden ser nulas porque el perfil solo informa la relación observada en la fecha de corte.

## Planteles y trayectoria

### `player_club_memberships`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `player_id` | bigint | FK → `players` |
| `club_id` | bigint | FK → `clubs` |
| `membership_type` | text | `PERMANENT`, `LOAN`, `YOUTH` o `UNKNOWN` |
| `start_date` | date | opcional |
| `end_date` | date | opcional |
| `is_current` | boolean | requerido |
| `evidence_type` | text | `PROFILE_SNAPSHOT`, `TRANSFER_INFERRED` o `PERFORMANCE_INFERRED` |
| `confidence` | text | `CONFIRMED`, `HIGH`, `MEDIUM` o `LOW` |
| `data_as_of` | date | requerido para membresías actuales |

Restricción: `end_date >= start_date` cuando ambas existan. Los préstamos permiten que un jugador tenga simultáneamente una membresía contractual y otra deportiva.

### `transfers`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `player_id` | bigint | FK → `players` |
| `season_id` | bigint | FK opcional → `seasons` |
| `transfer_date` | date | opcional |
| `from_club_id` | bigint | FK opcional → `clubs` |
| `to_club_id` | bigint | FK opcional → `clubs` |
| `transfer_type` | text | `TRANSFER`, `LOAN`, `LOAN_RETURN` o `DRAFT` |
| `from_career_state` | text | opcional cuando el origen no es un club |
| `to_career_state` | text | opcional cuando el destino no es un club |
| `market_value_amount` | bigint | opcional, no negativo |
| `fee_amount` | bigint | opcional, no negativo |
| `currency_code` | char(3) | opcional hasta confirmar la fuente |

Índices: jugador y fecha; club de origen; club de destino. Una huella de fuente evitará duplicar eventos al reimportar.

## Hechos deportivos y económicos

### `performances`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `player_id` | bigint | FK → `players` |
| `club_id` | bigint | FK → `clubs` |
| `competition_id` | bigint | FK → `competitions` |
| `season_id` | bigint | FK → `seasons` |
| `squad_appearances` | integer | opcional, no negativo |
| `appearances` | integer | opcional, no negativo |
| `goals` | integer | opcional, no negativo |
| `assists` | integer | opcional, no negativo |
| `own_goals` | integer | opcional, no negativo |
| `substituted_in` | integer | opcional, no negativo |
| `substituted_out` | integer | opcional, no negativo |
| `yellow_cards` | integer | opcional, no negativo |
| `second_yellow_cards` | integer | opcional, no negativo |
| `red_cards` | integer | opcional, no negativo |
| `penalty_goals` | integer | opcional, no negativo |
| `minutes_played` | integer | opcional, no negativo |
| `goals_conceded` | integer | opcional, no negativo |
| `clean_sheets` | integer | opcional, no negativo |

Unicidad: jugador, club, competición y temporada. Índices adicionales por club-temporada y competición-temporada.

### `market_values`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `player_id` | bigint | FK → `players` |
| `valued_on` | date | requerido |
| `amount` | bigint | requerido, no negativo |
| `currency_code` | char(3) | opcional hasta confirmar la fuente |

Unicidad: jugador y fecha. Índice descendente por jugador y fecha para obtener el valor actual.

### `injuries`

| Columna | Tipo | Regla |
|---|---|---|
| `id` | bigint | PK |
| `player_id` | bigint | FK → `players` |
| `season_id` | bigint | FK opcional → `seasons` |
| `reason` | text | requerido |
| `started_on` | date | opcional |
| `ended_on` | date | opcional |
| `days_missed` | integer | opcional, no negativo |
| `games_missed` | integer | opcional, no negativo |

No incluye `club_id`. Una huella normalizada de la fila permitirá deduplicar casos idénticos.

### `club_competition_seasons`

PK compuesta: `club_id`, `competition_id`, `season_id`. Conserva opcionalmente la denominación de división observada en la fuente.

## Trazabilidad del ETL

### `etl_runs`

Registra `id`, versión del importador, instante de inicio y fin, estado, fecha de corte, huella del dataset y conteos totales.

### `etl_file_results`

Por cada ejecución y archivo registra filas leídas, insertadas, actualizadas, omitidas y rechazadas.

### `etl_rejections`

Conserva ejecución, archivo, número de fila, motivo y una representación segura de los valores rechazados.

## Orden de carga

1. `etl_runs` y metadatos de archivos.
2. Países, grupos de posiciones, posiciones y temporadas.
3. Jugadores, clubes, competiciones y agentes, incluyendo stubs.
4. Ciudadanías, posiciones, relaciones de clubes y representaciones.
5. Membresías actuales desde perfiles.
6. Participaciones club-competición-temporada.
7. Rendimientos.
8. Valores de mercado.
9. Transferencias y membresías inferidas.
10. Lesiones.
11. Validaciones y cierre de la ejecución.

## Decisiones adoptadas para la primera migración

- `BIGINT IDENTITY` ofrece claves compactas, eficientes y fáciles de depurar. La API no promete que sean opacas; si luego se necesitan IDs públicos, se añadirá `public_id UUID` sin reemplazar las PK.
- Los tipos de estado se implementarán con `CHECK`, no con enums PostgreSQL.
- `player_latest_market_value.csv` servirá para control de calidad, no como tabla independiente.
- Los datos agregados de compañeros y selección quedan fuera de la primera migración para mantener enfocado el recorrido principal del MVP.
- No se asignará moneda hasta documentar la convención de la fuente.

