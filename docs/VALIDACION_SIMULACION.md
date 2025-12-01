Validación por simulación (reabastecimiento)

Resumen

Esta validación simula si, siguiendo una secuencia de paradas (origen -> suplentes -> destinos), el sistema puede reabastecerse y cumplir con todas las entregas sin quedarse sin stock.

Cómo funciona (algoritmo implementado)

1. Preparación
- Se toma la lista de viveros proveedores ordenada: el vivero origen (activo) primero, luego los viveros seleccionados/suplentes en el orden que fueron añadidos.
- Se toma la lista de destinos en orden (destinos ya agregados + el nuevo destino a validar).

2. Simulación por selección de suplentes con evaluación de coste (DP / búsqueda por subconjuntos)
- La implementación ahora prioriza tanto la factibilidad de stock como el coste en distancia/tiempo al elegir los suplentes.
- Enfoque:
	- Enumeramos subconjuntos de proveedores (incluyendo siempre el origen). Para cada subconjunto comprobamos si la suma de stock cubre la demanda total (esto es una enumeración por subconjuntos — técnica combinatoria que puede verse como DP/exhaustiva y está permitida dentro de las técnicas del curso).
	- Para los subconjuntos que cubren la demanda, calculamos el coste de la ruta que visita los proveedores seleccionados y todos los destinos usando `CalculadorRutas` (precalculo de matriz + TSP/DP). Esta evaluación usa algoritmos de grafos (Dijkstra) y el solucionador TSP ya implementado (Held-Karp / DP) para medir el coste real de incluir esos proveedores en la ruta.
	- Elegimos el subconjunto con menor coste (distancia) entre los factibles.
- Una vez elegido el subconjunto óptimo se realiza la asignación de cantidades a cada destino: para cada destino y cada tipo de flor, distribuimos la demanda entre los proveedores del subconjunto priorizando proveedores más cercanos al destino (usando distancias calculadas por `CalculadorRutas.dijkstra`). Esta regla de asignación es determinista y está basada en distancias de grafo.
- Ventaja: combina técnicas de grafos (Dijkstra, precálculo de distancias) y una búsqueda/exploración por subconjuntos (DP/exhaustiva) para escoger suplentes por coste, cumpliendo la restricción de usar técnicas enseñadas en clase.

3. Resultado
- Si todos los destinos se sirven en la simulación, la validación pasa y el destino puede agregarse en la aplicación real.
- En caso contrario, la validación falla y la UI muestra el mensaje devuelto por la simulación.

Notas de diseño

Notas de diseño

Notas de diseño

- Técnica utilizada: Búsqueda por subconjuntos (enumeración combinatoria) combinada con algoritmos de grafos para evaluación de distancia/tiempo (Dijkstra) y TSP por programación dinámica (Held-Karp) ya presentes en `CalculadorRutas`.
- Complejidad: enumerar subconjuntos de proveedores es O(2^S) donde S es el número de proveedores considerados; para cada subconjunto factible se ejecuta el TSP (DP) cuyo coste es exponencial en el número de nodos, por lo que el algoritmo es adecuado cuando S es pequeño (p.ej. S ≤ 8). Se recomienda limitar S (p.ej. top-K proveedores) para casos con muchos proveedores.
- Limitaciones: la asignación final de cantidades prioriza proveedores más cercanos al destino (regla determinista basada en grafos). Esto garantiza decisiones reproducibles y reduce la necesidad de backtracking adicional.

Recomendaciones

- Si necesitas que la simulación considere el tiempo/distancia y solo permita visitas a suplentes si el aumento en coste está dentro de tolerancia, se debe extender `CalculadorRutas` y la simulación para estimar el impacto en distancia/tiempo.
- Para cargas grandes o reglas más complejas (p. ej. split de pedido entre viveros en una misma entrega), se recomienda una asignación óptima (MIP o heurística avanzada) y pruebas con datos reales.

Archivo(s) modificados

- `src/controllers/gestor_rutas.py`: nueva función `_simular_entregas_con_reabastecimiento` y flag `validacion_por_simulacion`.
- `src/views/app.py`: checkbox en la barra lateral para activar/desactivar la validación por simulación.

Autor: Implementación automática (copiloto)
Fecha: (ver historial de commits)
