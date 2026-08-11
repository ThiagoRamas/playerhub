# ADR 0003: los planteles actuales se importan desde una API

- Estado: aceptada
- Fecha: 2026-08-03

## Contexto

El archivo histórico disponible representa una instantánea al 13 de septiembre de 2025. Es útil para conservar carreras, rendimientos, transferencias, lesiones y valores, pero no puede reflejar altas y bajas posteriores.

## Decisión

PlayerHub usará API-Football como fuente de importación para planteles registrados actuales. PostgreSQL continuará siendo la única fuente consultada por la API y la interfaz. La aplicación nunca dependerá de API-Football durante una visita del usuario.

Cada club y jugador tendrá identificadores separados por proveedor. La sincronización se ejecutará primero en modo de vista previa y solamente modificará la base cuando se indique `--apply` explícitamente.

Una instantánea completa puede:

- agregar jugadores que no existen;
- reconocer jugadores por el identificador estable del proveedor;
- cerrar vinculaciones de quienes ya no integran el plantel registrado;
- conservar la propiedad de jugadores que continúan cedidos a otro club;
- registrar fecha, huella y ejecución ETL para trazabilidad.

## Consecuencias

### Positivas

- Los planteles pueden actualizarse sin perder el historial importado.
- La aplicación sigue funcionando aunque la fuente externa no esté disponible.
- El proveedor puede reemplazarse sin cambiar las claves internas del dominio.
- El modo de vista previa reduce el riesgo de aplicar coincidencias incorrectas.
- Los perfiles individuales se consultan solamente para altas o coincidencias
  dudosas, sin exigir una temporada, para respetar los límites del plan gratuito.
- Si no puede completarse el nombre de un jugador nuevo, la sincronización puede
  mostrarse en vista previa pero no aplicarse.

### Límites

- Un plantel registrado no confirma por sí solo propiedad, contrato o condición de préstamo.
- Los jugadores nuevos se crean como perfiles incompletos hasta ejecutar un enriquecimiento posterior.
- Los valores de mercado del archivo histórico no se actualizan con este endpoint.
- Las coincidencias ambiguas deben revisarse antes de aplicar una sincronización.
