# Idioma del producto

PlayerHub se presenta en español para sus usuarios.

## Alcance

- Navegación, títulos, botones, filtros y estados visibles: español.
- Fechas y números: formato de Argentina (`es-AR`).
- Moneda: se muestra con su código original y formato local.
- Posiciones, tipos de transferencia y demás valores provenientes del dataset: se traducen en la capa de presentación.
- Mensajes de error dirigidos a usuarios: español.

## Contrato técnico

Los nombres de campos y los códigos internos de la API permanecen en inglés. Por ejemplo, `SQUAD`, `ON_LOAN` y `LOANED_OUT` se mostrarán en la interfaz como `En el plantel`, `A préstamo` y `Cedido a otro club`. Esta separación evita romper el contrato de la API y permite cambiar textos sin modificar los datos.
