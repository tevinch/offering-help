# BigQuery: particionado y campos obligatorios en raw

Para tablas pequeñas, empezar con una tabla simple puede ser una decisión razonable. Conviene justificarla por el volumen, las consultas previstas y la operación de la carga. La documentación de BigQuery ofrece criterios de diseño; la expectativa de un trabajo práctico la confirma su equipo docente.

Los dos tamaños citados responden a preguntas distintas:

| Referencia | Cómo interpretarla |
| --- | --- |
| Aproximadamente **10 GB por partición** | Muchas particiones pequeñas agregan metadatos. Es una razón para reconsiderar la división, no un tamaño mínimo obligatorio. |
| **64 MB por tabla sin particionar o por partición** | Por debajo de ese tamaño, el beneficio de clustering suele ser despreciable. BigQuery permite aplicarlo igualmente. |

Son referencias al tamaño de las tablas o particiones, no al peso del CSV de origen. Superarlas tampoco garantiza una mejora para cualquier consulta. Fuentes: [cuándo particionar](https://docs.cloud.google.com/bigquery/docs/partitioned-tables#when_to_use_partitioning) y [cuándo usar clustering](https://docs.cloud.google.com/bigquery/docs/clustered-tables#when_to_use_clustering).

En un proyecto real, el particionado por fecha puede servir para consultar períodos concretos: un filtro adecuado permite omitir las otras particiones. También permite gestionar vencimientos, cargas y eliminaciones por partición. El clustering puede reducir los bloques leídos cuando las consultas filtran por sus columnas. Son beneficios diferentes y se pueden combinar. [Particionado](https://docs.cloud.google.com/bigquery/docs/partitioned-tables), [clustering](https://docs.cloud.google.com/bigquery/docs/clustered-tables).

Como criterio de arquitectura, raw no obliga a incorporar estas optimizaciones ni a reservarlas para otra capa. Cada tabla puede tener un diseño físico acorde a su uso. Por ejemplo:

| Situación | Decisión que conviene evaluar |
| --- | --- |
| Muestra pequeña, carga puntual y lectura completa | Mantener una tabla simple y documentar el motivo. |
| Historial creciente, consultas por fecha o gestión por períodos | Evaluar particionado y una granularidad útil. |
| Tabla con volumen suficiente y filtros frecuentes por determinadas columnas | Evaluar clustering y el orden de esas columnas. |

Antes de elegir, registrar el crecimiento esperado, los filtros reales, la política de retención y cómo se recargarán los datos. Comparar lecturas y tiempos con consultas representativas cuando el rendimiento sea el motivo de la decisión. Aquí no se presentan mediciones sobre las tablas del curso.

`REQUIRED` significa que la columna no admite `NULL`; `NULLABLE` lo permite y es el modo predeterminado. El modo define un contrato de admisión de datos y puede aplicarse a cualquier columna, no solo a IDs. [Modos del schema](https://docs.cloud.google.com/bigquery/docs/schemas#modes).

Un criterio útil para raw es decidir qué hacer si falta cada valor. Una fecha de evento podría ser obligatoria si el contrato exige rechazar registros sin ella; también podría admitirse su ausencia si el objetivo es conservar ese registro para revisión posterior. La elección necesita una política explícita, no se deduce del nombre de la columna. Marcar un ID como `REQUIRED` tampoco comprueba su unicidad; incluso las restricciones de clave declaradas en BigQuery no se hacen cumplir automáticamente. [Claves primarias y externas](https://docs.cloud.google.com/bigquery/docs/primary-foreign-keys).

Para `passenger_count`, permitir `NULL` conserva la distinción entre cantidad desconocida y cero pasajeros. Después se puede medir cuántos faltan y definir su tratamiento en una capa de calidad o transformación. `NULLABLE` no convierte texto inválido en un número ni resuelve otros errores de carga. Si se decide rechazar registros, conservar el archivo original, registrar el motivo y conciliar filas recibidas, cargadas y rechazadas. Aumentar la tolerancia a registros incorrectos puede omitirlos: no equivale a conservarlos. [Opciones de carga CSV](https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv#csv-options).

Para la [parte 1 del TP](https://github.com/juanmantegazza/ingenieria-datos-gcp/blob/main/tp/README.md), la consigna publicada pide schemas explícitos, el dataset `tp_raw` en US, verificar 399.634 viajes y 676 mediciones de clima, y explorar los datos. No establece allí una obligación de particionado o clustering. Queda por confirmar con el equipo docente si quieren demostrar esas técnicas aun con tablas pequeñas y qué contrato de nulabilidad esperan. Estos criterios ayudan a explicar una decisión; esa confirmación pedagógica sigue pendiente.

## Optional coffee

The example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
