# FloraRoute

## Descripción

FloraRoute es una aplicación de optimización de rutas para entregas de flores en Lima Metropolitana. Implementa algoritmos avanzados de teoría de grafos y programación dinámica para resolver el Problema del Vendedor Viajero (TSP).

## Técnicas Algorítmicas Implementadas

### 1. Programación Dinámica - Held-Karp (TSP)

**Ubicación:** `src/controllers/calculador_rutas.py` - Líneas 106-202

**Propósito:** Resolver el TSP de forma óptima encontrando el orden de visita que minimiza la distancia total.

**Código clave:**

```python
def held_karp(self, origen: int, destinos: List[int], retornar_origen: bool = True) -> Tuple[float, List[int]]:
    """
    Algoritmo Held-Karp para TSP exacto usando programacion dinamica
    Complejidad: O(n^2 * 2^n)
    """
    # Tabla de memorización
    dp = {}
    
    # Caso base: ir desde origen a cada destino
    for i, destino in enumerate(destinos):
        subconjunto = frozenset([destino])
        dist = self.matriz_distancias.get((origen, destino), float('inf'))
        dp[(subconjunto, destino)] = (dist, origen)
    
    # Construcción bottom-up con subestructura óptima
    for tamano in range(2, n + 1):
        for subconjunto_tuple in combinations(destinos, tamano):
            subconjunto = frozenset(subconjunto_tuple)
            
            for ultimo in subconjunto:
                subconjunto_prev = subconjunto - {ultimo}
                mejor_dist = float('inf')
                mejor_prev = None
                
                # Reutiliza soluciones de subproblemas
                for penultimo in subconjunto_prev:
                    dist_prev, _ = dp[(subconjunto_prev, penultimo)]
                    dist_actual = self.matriz_distancias.get((penultimo, ultimo), float('inf'))
                    dist_total = dist_prev + dist_actual
                    
                    if dist_total < mejor_dist:
                        mejor_dist = dist_total
                        mejor_prev = penultimo
                
                # Memorización del resultado
                dp[(subconjunto, ultimo)] = (mejor_dist, mejor_prev)
    
    # Backtracking para reconstruir la secuencia óptima
    secuencia = [mejor_ultimo]
    subconjunto_actual = todos_destinos
    nodo_actual = mejor_ultimo
    
    while len(subconjunto_actual) > 1:
        _, prev = dp[(subconjunto_actual, nodo_actual)]
        secuencia.append(prev)
        subconjunto_actual = subconjunto_actual - {nodo_actual}
        nodo_actual = prev
    
    secuencia.reverse()
    secuencia.insert(0, origen)
    
    return mejor_dist_total, secuencia
```

**Características:**
- Subestructura óptima
- Memorización en tabla DP
- Backtracking para reconstrucción de solución
- Complejidad: O(n² × 2^n)

### 2. Búsqueda en Grafos - Dijkstra

**Ubicación:** `src/controllers/calculador_rutas.py` - Líneas 29-87

**Propósito:** Calcular caminos más cortos entre nodos del grafo vial.

**Código clave:**

```python
def dijkstra(self, origen: int, destino: int) -> Tuple[float, List[int]]:
    """
    Calcula camino mas corto entre dos nodos usando Dijkstra
    Complejidad: O((V + E) log V)
    """
    distancias = {nodo: float('inf') for nodo in self.grafo}
    distancias[origen] = 0
    padres = {}
    visitados = set()
    heap = [(0.0, origen)]
    
    # Exploración con cola de prioridad
    while heap:
        dist_actual, actual = heapq.heappop(heap)
        
        if actual in visitados:
            continue
        
        visitados.add(actual)
        
        if actual == destino:
            break
        
        # Relajación de aristas
        for vecino, peso in self.grafo.get(actual, {}).items():
            peso_con_trafico = peso * self.factor_trafico
            nueva_dist = distancias[actual] + peso_con_trafico
            
            if nueva_dist < distancias[vecino]:
                distancias[vecino] = nueva_dist
                padres[vecino] = actual
                heapq.heappush(heap, (nueva_dist, vecino))
    
    # Backtracking para reconstruir camino
    camino = []
    actual = destino
    while actual is not None:
        camino.append(actual)
        actual = padres.get(actual)
    camino.reverse()
    
    return distancias[destino], camino
```

**Características:**
- Exploración con cola de prioridad (heap)
- Marcado de nodos visitados
- Relajación de aristas
- Backtracking para obtener el camino
- Complejidad: O((V + E) log V)

### 3. Integración de Algoritmos

**Flujo completo:**

1. **Precálculo de Matriz** (`líneas 89-104`): Ejecuta Dijkstra para cada par de nodos de interés
2. **Resolución TSP** (`líneas 106-202`): Held-Karp determina el orden óptimo de visitas
3. **Camino Completo** (`líneas 230-253`): Dijkstra expande cada segmento para visualización

## Instalación

### Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/GilbertHuarcaya/FloraRouteComplejidad
cd FloraRouteComplejidad
```

2. Crear entorno virtual (opcional):

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Instalar dependencias:

```bash
npm run install
```

## Ejecución

Iniciar la aplicación web:

```bash
npm run start
```

La aplicación se abrirá automáticamente en el navegador en `http://localhost:8501`

## Uso

### Paso 1: Seleccionar Vivero de Origen

En la barra lateral, seleccionar el vivero desde el cual partirán las entregas y confirmar la selección.

### Paso 2: Agregar Destinos

1. Hacer click en el mapa para seleccionar ubicaciones de entrega
2. Las coordenadas se cargarán automáticamente en el formulario
3. Especificar cantidades de flores requeridas (rosas, claveles, lirios)
4. Hacer clic en "Agregar Destino"
5. Repetir para agregar hasta 20 destinos

### Paso 3: Calcular Ruta Óptima

1. Seleccionar si la ruta debe retornar al origen (ciclo cerrado)
2. Hacer clic en "Calcular Ruta"
3. El sistema ejecutará los algoritmos Held-Karp y Dijkstra

### Paso 4: Visualizar Resultados

- **Mapa**: Muestra la ruta óptima como una línea azul siguiendo las calles reales
- **Métricas**: Distancia total, tiempo estimado, número de paradas
- **Tabla**: Orden de visitas con distancias y tiempos por segmento

## Complejidad Computacional

| Algoritmo | Complejidad | Uso |
|-----------|-------------|-----|
| Dijkstra | O((V + E) log V) | Caminos más cortos entre nodos |
| Held-Karp | O(n² × 2^n) | Orden óptimo de visitas (TSP) |
| Precálculo | O(n² × (V + E) log V) | Matriz de distancias |

**Límites:**
- Nodos del grafo: ~10,000 (V)
- Aristas del grafo: ~20,000 (E)
- Destinos por ruta: 1-20 (n)
- Tiempo de cómputo: 0.5-3 segundos (n=20)

## Dependencias Principales

- **streamlit**: Framework de interfaz web
- **folium**: Visualización de mapas interactivos
- **pandas**: Manipulación de datos
- **numpy**: Operaciones numéricas

## Restricciones

- Máximo 20 destinos por ruta (límite algorítmico de Held-Karp)
- Coordenadas deben estar dentro del área metropolitana de Lima
- Las distancias son positivas (requisito de Dijkstra)
- El grafo debe ser conexo

## Autores

u20231941
Choquehuanca Núñez Luciana Carolina 
u202322187
Huarcaya Matias Gilbert Alonso
u202317362
Santiago Peña Andreow Jomark
