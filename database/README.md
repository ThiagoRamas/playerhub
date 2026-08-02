# Base de datos

## Estructura

- `migrations/001_initial_schema.sql`: esquema inicial completo y catálogos de posiciones.
- `schema-design.md`: justificación del modelo lógico.
- `verify_schema.sql`: comprobaciones posteriores a la migración.

## Desarrollo local

La imagen oficial de PostgreSQL ejecuta automáticamente las migraciones de `migrations/` al crear un volumen vacío.

```powershell
Copy-Item .env.example .env
docker compose up -d database
docker compose ps
Get-Content database/verify_schema.sql | docker compose exec -T database psql -U playerhub -d playerhub
```

Las nuevas migraciones deberán ser incrementales y no depender de reinicializar el volumen. El volumen no debe eliminarse como parte de una operación cotidiana porque contiene toda la base local.
