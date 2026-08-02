# PlayerHub — auditoría inicial del dataset

Fecha de auditoría: 2026-08-01

## Propósito

Esta auditoría valida si los CSV pueden alimentar el modelo propio de PlayerHub. Los archivos originales son fuentes de importación: no definen las tablas de la aplicación y no deben modificarse.

## Inventario

| Archivo | Filas | Observaciones |
|---|---:|---|
| `player_profiles.csv` | 92.671 | Un registro único por `player_id` |
| `player_performances.csv` | 1.878.719 | Clave natural candidata única: jugador, temporada, competición y equipo |
| `player_market_value.csv` | 901.429 | Jugador y fecha son únicos |
| `player_latest_market_value.csv` | 69.441 | Derivable del historial; no es fuente canónica |
| `transfer_history.csv` | 1.101.440 | Contiene 117.944 jugadores, más que perfiles |
| `player_injuries.csv` | 143.195 | No identifica el club de la lesión |
| `player_national_performances.csv` | 92.701 | Requiere deduplicación y análisis adicional |
| `player_teammates_played_with.csv` | 1.257.342 | Métricas muy incompletas; no es esencial para el primer importador |
| `team_details.csv` | 2.175 | Cobertura insuficiente como catálogo global de clubes |
| `team_competitions_seasons.csv` | 196.378 | Solo 53.019 combinaciones distintas; hay 143.359 repeticiones |
| `team_children.csv` | 7.695 | Permite relacionar equipos principales, reservas y juveniles |

## Hallazgos que afectan el diseño

### Cobertura incompleta

- Rendimientos referencia 13.511 clubes, pero 11.348 no aparecen en `team_details`.
- Perfiles referencia 11.859 clubes, pero 10.008 no aparecen en `team_details`.
- Transferencias referencia 44.938 clubes, pero 42.764 no aparecen en `team_details`.
- Transferencias contiene 26.733 jugadores que no aparecen en `player_profiles`.
- Rendimientos, valores de mercado, lesiones y compañeros sí tienen cobertura completa en perfiles.

El importador deberá crear entidades mínimas para referencias válidas ausentes y marcarlas como incompletas. No debe descartar silenciosamente esos registros ni fabricar atributos desconocidos.

### Valores que no son clubes

En `current_club_name` y transferencias aparecen estados como `Retired`, `Without Club`, `Unknown`, `---` y `Career break`. Estos valores se transformarán en estados del jugador o eventos de carrera; nunca se insertarán como clubes.

### Calidad y codificación

- Los 11 CSV pasan una decodificación UTF-8 estricta sin bytes inválidos ni caracteres de reemplazo. Las apariciones iniciales de `SÃ¼d` y `T�rkiye` fueron causadas por la codificación de salida de PowerShell, no por los archivos. El ETL debe abrirlos explícitamente como UTF-8 y las pruebas deben conservar caracteres como `ü`, `ó`, `ã` y `ñ`.
- `height = 0` aparece 18.867 veces y significa dato desconocido.
- `foot = N/A` aparece 1.698 veces y debe normalizarse como desconocido.
- `minutes_played` falta en 62,31 % de los rendimientos. Ausencia no equivale a cero.
- `goals` falta en 7,36 % de los rendimientos. Debe conservarse como desconocido salvo que una regla documentada pruebe lo contrario.
- `end_date` falta en 1.523 lesiones; puede representar una lesión abierta o un dato incompleto.

### Duplicados

- Lesiones tiene 111 filas repetidas según su clave natural candidata.
- Transferencias tiene 123 repeticiones según jugador, fecha, origen y destino.
- Rendimientos y valores de mercado no presentan duplicados con sus claves candidatas.
- `team_competitions_seasons` requiere deduplicación explícita antes de cargarlo.

## Reglas iniciales de importación

1. Conservar los CSV originales como datos de entrada inmutables.
2. Importar primero catálogos y entidades; después hechos históricos.
3. Guardar el identificador externo para trazabilidad, sin usarlo como clave primaria.
4. Registrar cada ejecución y sus conteos de leídos, aceptados, rechazados y corregidos.
5. Aplicar transformaciones deterministas y probadas.
6. Mantener `NULL` cuando el origen no permite conocer un valor.
7. Guardar errores no recuperables en una tabla o archivo de rechazos con su motivo.
8. Permitir entidades incompletas creadas desde referencias y enriquecerlas en cargas posteriores.

## Pendientes de auditoría

- Determinar el patrón real de nacionalidades múltiples en `citizenship`.
- Catalogar todos los valores de temporada y definir su normalización.
- Clasificar los tipos de equipos de `team_children`.
- Revisar casos de préstamos para validar períodos de pertenencia al club.
- Confirmar la moneda declarada o asumida por la fuente.

## Caso de aceptación: Club Atlético Independiente

El club está identificado consistentemente con el ID externo `1234`.

- 14 perfiles lo indican como club actual.
- 9 perfiles pertenecen a Independiente y aparecen cedidos en otro club.
- 243 jugadores tienen rendimientos históricos en el club, distribuidos en 1.705 registros y 31 temporadas.
- 300 jugadores participan en 901 movimientos de transferencia con Independiente como origen o destino.

La cobertura es suficiente para construir y demostrar la navegación club → plantel → jugador → trayectoria. La etiqueta “plantel actual” deberá mostrar la fecha de corte del dataset, porque los perfiles reflejan una instantánea y no información en vivo.
