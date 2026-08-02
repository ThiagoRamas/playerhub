# PlayerHub — modelo conceptual

Estado: propuesta para revisión antes del esquema PostgreSQL.

## Principios

- El dominio de PlayerHub es independiente del formato de los CSV.
- Cada entidad tiene un identificador interno propio y, cuando corresponda, un identificador externo trazable.
- Los datos desconocidos se representan como `NULL`, no como cero, texto vacío ni entidades ficticias.
- Los datos actuales y los históricos se modelan por separado.
- Ningún dato inferido se presenta como confirmado sin conservar su procedencia.

## Catálogos

### Country

Representa un país normalizado. Se reutiliza para nacimiento, ciudadanía y país del club.

### PositionGroup

Agrupa posiciones en `GOALKEEPER`, `DEFENDER`, `MIDFIELD` y `ATTACK`.

### Position

Representa una posición específica, por ejemplo `CENTRE_BACK`, `RIGHT_BACK`, `DEFENSIVE_MIDFIELD`, `RIGHT_WINGER` o `CENTRE_FORWARD`. Cada posición específica pertenece a un grupo; no se modelan posiciones hermanas como padres e hijos.

### Season

Representa una temporada normalizada. Conserva la etiqueta original y, cuando sea posible, año de inicio, año de fin y fechas. No se supone que todas las competiciones usan el mismo calendario.

### Competition

Representa una competición estable. Su participación por temporada se expresa mediante relaciones, no duplicando la competición.

## Entidades principales

### Player

Contiene identidad y atributos relativamente estables: nombre, slug, nacimiento, altura, pie hábil, estado de carrera y datos biográficos. No contiene estadísticas, lesiones, transferencias ni valor de mercado.

Relaciones:

- muchas ciudadanías mediante `PlayerCitizenship`;
- una o varias posiciones mediante `PlayerPosition`;
- cero o más representaciones mediante `PlayerAgentRepresentation`;
- pertenencias a clubes mediante `PlayerClubMembership`.

### Club

Representa un equipo identificable dentro del dataset. Puede ser principal, reserva, juvenil u otro tipo. Los registros incompletos son válidos si fueron referenciados por una fuente y quedan marcados para enriquecimiento.

`ClubRelationship` permite relacionar un equipo principal con reservas o divisiones juveniles sin asumir que son la misma entidad.

### Agent

Representa a un agente o agencia. La relación temporal con un jugador se mantiene separada para permitir cambios futuros.

## Trayectoria

### PlayerClubMembership

Representa la pertenencia de un jugador a un club durante un período.

Incluye:

- fecha de inicio y fin, si se conocen;
- condición: permanente, préstamo u otra;
- indicador de pertenencia vigente;
- origen y nivel de confianza del dato.

Puede haber períodos superpuestos cuando un jugador pertenece contractualmente a un club y juega cedido en otro. El plantel actual se consulta desde membresías vigentes, no desde una columna de `Player`.

### Transfer

Representa un evento de movimiento. Relaciona jugador, club de origen opcional, club de destino opcional, fecha, tipo, valor del jugador y monto de la operación.

Los estados `WITHOUT_CLUB`, `RETIRED`, `CAREER_BREAK` y `UNKNOWN` se guardan como resultado o contexto del evento, no como clubes.

### PlayerAgentRepresentation

Relaciona jugador y agente, con fechas opcionales. En la primera carga solo podrá conocerse la representación actual incluida en el perfil.

## Información deportiva y económica

### Performance

Agrega el rendimiento de un jugador para un club, competición y temporada. Sus métricas admiten `NULL` cuando el origen no informa el valor.

Clave natural candidata de la fuente:

```text
player + club + competition + season
```

### MarketValue

Guarda una observación fechada del valor estimado de un jugador, con moneda y fuente explícitas. El valor actual se calcula como la observación más reciente; no se duplica desde `player_latest_market_value`.

### Injury

Representa un período de lesión de un jugador: motivo, inicio, fin, días y partidos perdidos. No se relaciona con un club porque el dataset no aporta esa información.

### ClubCompetitionSeason

Registra la participación de un club en una competición durante una temporada. Es la normalización de los datos repetidos de equipos, competiciones y temporadas.

### NationalTeamPerformance

Representa el resumen de participación del jugador en una selección. Se mantiene separado de `Performance` porque el dataset y sus métricas tienen otra granularidad.

### TeammateAggregate

Almacena, de forma opcional, estadísticas agregadas entre dos jugadores. Se posterga para una etapa posterior del MVP porque sus métricas tienen alta ausencia de datos.

## Vista funcional del MVP

```text
Club
 ├─ información y competición actual
 ├─ plantel vigente
 │   └─ Player
 │       ├─ perfil y nacionalidades
 │       ├─ posiciones
 │       ├─ rendimiento por temporada
 │       ├─ evolución de valor
 │       ├─ transferencias
 │       └─ lesiones
 └─ temporadas y competiciones históricas
```

## Decisiones pendientes antes del esquema lógico

1. Tipo definitivo de identificador interno y estrategia para IDs públicos de la API.
2. Moneda de valores y transferencias cuando el archivo no la declara explícitamente.
3. Regla exacta para temporadas de calendario anual frente a temporadas partidas.
4. Tratamiento de ciudadanías múltiples codificadas en un solo campo.
5. Grado de inferencia permitido al reconstruir membresías desde transferencias.
6. Catálogo de estados de carrera y tipos de transferencia.

