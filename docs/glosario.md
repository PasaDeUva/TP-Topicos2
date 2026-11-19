# Glosario

Este glosario fija el significado de las modalidades de entrada y los términos equivalentes usados en la documentación, los changes de OpenSpec y el código.

## Modalidades de entrada

| Valor de datos | Nombre en prosa | Significado |
|---|---|---|
| `general` | Modalidad general | Entradas sin asiento asignado. Se venden por zona o sector, sin numeración. |
| `numerado` | Modalidad numerada | Entradas con asiento específico dentro del mapa del evento. |

El valor de datos (`general` o `numerado`) es el que se guarda en la base, se envía en las APIs y se usa en los tests. En prosa se usan los nombres de la columna central.

## Términos equivalentes

| Término en prosa | Equivale a | Uso recomendado |
|---|---|---|
| Modalidad general | `tipo = general` | Forma preferida. Usar siempre en prosa. |
| Entrada general | Entrada de modalidad general | Forma preferida para hablar de las entradas. |
| Modalidad numerada | `tipo = numerado` | Forma preferida. Usar siempre en prosa. |
| Entrada numerada | Entrada de modalidad numerada | Forma preferida para hablar de las entradas. |
| Entrada no numerada | Entrada general | Evitar. Solo citar si aparece en el enunciado. |
| Entrada por zona | Entrada general | Evitar. Solo citar si aparece en el enunciado. |
| Numerada (con asiento) | Entrada numerada | Evitar. |
| Cupo | Capacidad de la modalidad general | Usar solo para la capacidad de la modalidad general. |

## Notas

- Los términos "modalidad general" y "entrada general" son equivalentes y refieren a la misma modalidad. "No numerada" y "por zona" describen la misma modalidad pero no se usan en la documentación del proyecto.
- La capacidad de una modalidad general se llama "cupo". La capacidad de una modalidad numerada surge del mapa de asientos y no se llama cupo.
- Precio, capacidad y mapa de asientos se definen en el change de asientos y stock ([ADR-0003](adr/0003-servicio-eventos-e-inventario.md)). Este glosario no los define.
