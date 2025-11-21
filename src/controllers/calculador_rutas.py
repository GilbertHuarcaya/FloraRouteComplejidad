"""
Modulo: calculador_rutas.py
Descripcion: Algoritmos de optimizacion de rutas para TSP (Traveling Salesman Problem)
Implementa: Held-Karp (TSP exacto), Floyd-Warshall, Bellman-Ford
"""

import heapq
from typing import List, Tuple, Dict, Set
from itertools import combinations


class CalculadorRutas:
    """
    Clase para calcular rutas optimas usando programacion dinamica y algoritmos de grafos
    """
    
    def __init__(self, grafo: Dict[int, Dict[int, float]], factor_trafico: float = 1.0):
        """
        Args:
            grafo: Diccionario de adyacencia {nodo: {vecino: peso}}
            factor_trafico: Factor multiplicador por trafico (1.0 a 2.5)
        """
        self.grafo = grafo
        self.nodos = list(grafo.keys())
        self.matriz_distancias = {}
        self.precalculado = False
        self.factor_trafico = factor_trafico
    
    def dijkstra(self, origen: int, destino: int) -> Tuple[float, List[int]]:
        """
        Calcula camino mas corto entre dos nodos usando Dijkstra
        
        Args:
            origen: Nodo inicial
            destino: Nodo final
            
        Returns:
            Tupla (distancia, camino)
        """
        if origen not in self.grafo or destino not in self.grafo:
            return float('inf'), []
        
        distancias = {nodo: float('inf') for nodo in self.grafo}
        distancias[origen] = 0
        padres = {}
        visitados = set()
        heap: List[Tuple[float, int]] = [(0.0, origen)]
        
        while heap:
            dist_actual, actual = heapq.heappop(heap)
            
            if actual in visitados:
                continue
            
            visitados.add(actual)
            
            if actual == destino:
                break
            
            if dist_actual > distancias[actual]:
                continue
            
            for vecino, peso in self.grafo.get(actual, {}).items():
                # Aplicar factor de trafico al peso
                peso_con_trafico = peso * self.factor_trafico
                nueva_dist = distancias[actual] + peso_con_trafico
                
                if nueva_dist < distancias[vecino]:
                    distancias[vecino] = nueva_dist
                    padres[vecino] = actual
                    heapq.heappush(heap, (nueva_dist, vecino))
        
        # Reconstruir camino
        if distancias[destino] == float('inf'):
            return float('inf'), []
        
        camino = []
        actual = destino
        while actual is not None:
            camino.append(actual)
            actual = padres.get(actual)
        camino.reverse()
        
        return distancias[destino], camino
    
    def precalcular_matriz_distancias(self, nodos_interes: List[int]):
        """
        Precalcula matriz de distancias entre nodos de interes para optimizar Held-Karp
        
        Args:
            nodos_interes: Lista de nodos (origen + destinos)
        """
        self.matriz_distancias = {}
        
        # Usar Dijkstra para cada par de nodos
        for i in nodos_interes:
            for j in nodos_interes:
                if i != j:
                    dist, _ = self.dijkstra(i, j)
                    self.matriz_distancias[(i, j)] = dist
                else:
                    self.matriz_distancias[(i, j)] = 0
        
        self.precalculado = True
    
    def held_karp(self, origen: int, destinos: List[int], retornar_origen: bool = True) -> Tuple[float, List[int]]:
        """
        Algoritmo Held-Karp para TSP exacto usando programacion dinamica
        Complejidad: O(n^2 * 2^n)
        Factible para n <= 20
        
        Args:
            origen: Nodo de inicio
            destinos: Lista de nodos a visitar
            retornar_origen: Si True, cierra el ciclo volviendo al origen
            
        Returns:
            Tupla (distancia_total, secuencia_ordenada)
        """
        if not destinos:
            return 0, [origen]
        
        # Precalcular distancias si no se ha hecho
        nodos_interes = [origen] + destinos
        if not self.precalculado:
            self.precalcular_matriz_distancias(nodos_interes)
        
        n = len(destinos)
        destinos_set = set(destinos)
        
        # dp[subconjunto][ultimo_nodo] = (distancia_minima, nodo_previo)
        dp = {}
        
        # Caso base: ir desde origen a cada destino
        for i, destino in enumerate(destinos):
            subconjunto = frozenset([destino])
            dist = self.matriz_distancias.get((origen, destino), float('inf'))
            dp[(subconjunto, destino)] = (dist, origen)
        
        # Iterar sobre tamanos de subconjuntos de 2 a n
        for tamano in range(2, n + 1):
            for subconjunto_tuple in combinations(destinos, tamano):
                subconjunto = frozenset(subconjunto_tuple)
                
                # Para cada nodo como ultimo en el subconjunto
                for ultimo in subconjunto:
                    subconjunto_prev = subconjunto - {ultimo}
                    
                    mejor_dist = float('inf')
                    mejor_prev = None
                    
                    # Probar cada nodo del subconjunto previo como penultimo
                    for penultimo in subconjunto_prev:
                        if (subconjunto_prev, penultimo) not in dp:
                            continue
                        
                        dist_prev, _ = dp[(subconjunto_prev, penultimo)]
                        dist_actual = self.matriz_distancias.get((penultimo, ultimo), float('inf'))
                        dist_total = dist_prev + dist_actual
                        
                        if dist_total < mejor_dist:
                            mejor_dist = dist_total
                            mejor_prev = penultimo
                    
                    dp[(subconjunto, ultimo)] = (mejor_dist, mejor_prev)
        
        # Encontrar solucion optima
        todos_destinos = frozenset(destinos)
        mejor_dist_total = float('inf')
        mejor_ultimo = None
        
        for ultimo in destinos:
            if (todos_destinos, ultimo) in dp:
                dist, _ = dp[(todos_destinos, ultimo)]
                if dist < mejor_dist_total:
                    mejor_dist_total = dist
                    mejor_ultimo = ultimo
        
        if mejor_ultimo is None:
            return float('inf'), [origen]
        
        # Reconstruir secuencia
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
        
        # Si se solicita retornar al origen, agregar al final
        if retornar_origen:
            dist_retorno = self.matriz_distancias.get((mejor_ultimo, origen), float('inf'))
            mejor_dist_total += dist_retorno
            secuencia.append(origen)
        
        return mejor_dist_total, secuencia
    
    def calcular_ruta_tsp(self, origen: int, destinos: List[int], usar_heuristica: bool = False, retornar_origen: bool = True) -> Tuple[float, List[int]]:
        """
        Calcula ruta TSP optima eligiendo algoritmo segun numero de destinos
        
        Args:
            origen: Nodo de inicio
            destinos: Lista de nodos a visitar
            usar_heuristica: Si True, usa heuristica para n > 15
            retornar_origen: Si True, retorna al origen (ciclo cerrado TSP)
            
        Returns:
            Tupla (distancia_total, secuencia_ordenada)
        """
        n = len(destinos)
        
        if n == 0:
            return 0, [origen]
        
        if n == 1:
            dist = self.matriz_distancias.get((origen, destinos[0]), float('inf'))
            secuencia = [origen, destinos[0]]
            if retornar_origen:
                dist_retorno = self.matriz_distancias.get((destinos[0], origen), float('inf'))
                dist += dist_retorno
                secuencia.append(origen)
            return dist, secuencia
        
        return self.held_karp(origen, destinos, retornar_origen)

    
    def calcular_camino_completo(self, secuencia: List[int]) -> Tuple[List[int], float]:
        """
        Calcula el camino completo nodo por nodo para una secuencia de puntos
        
        Args:
            secuencia: Lista ordenada de nodos a visitar
            
        Returns:
            Tupla (camino_completo, distancia_total)
        """
        camino_completo = []
        distancia_total = 0
        
        for i in range(len(secuencia) - 1):
            origen = secuencia[i]
            destino = secuencia[i + 1]
            
            dist, camino_segmento = self.dijkstra(origen, destino)
            
            if not camino_segmento:
                raise ValueError(f"No hay camino entre {origen} y {destino}")
            
            # Agregar segmento (sin duplicar nodos)
            if camino_completo:
                camino_completo.extend(camino_segmento[1:])
            else:
                camino_completo.extend(camino_segmento)
            
            distancia_total += dist
        
        return camino_completo, distancia_total
