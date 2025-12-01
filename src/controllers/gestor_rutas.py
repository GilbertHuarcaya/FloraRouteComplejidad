"""
Gestor principal de rutas - Logica de negocio
"""

import time
from typing import Dict, List, Tuple, Optional
from itertools import combinations
from ..models.vivero import Vivero
from ..models.pedido import Pedido, Destino
from ..models.ruta import Ruta
from .calculador_rutas import CalculadorRutas
from .validador import ValidadorRutas


class GestorRutas:
    """Gestor principal de la logica de negocio para rutas"""
    
    def __init__(self, grafo: Dict[int, Dict[int, float]], factor_trafico: float = 1.0, nodos_coords: Optional[Dict[int, Tuple[float, float]]] = None):
        """
        Args:
            grafo: Diccionario de adyacencia del grafo de Lima
            factor_trafico: Factor de trafico actual (1.0 a 2.5)
            nodos_coords: Diccionario {nodo_id: (lat, lon)} para busqueda espacial
        """
        self.grafo = grafo
        self.calculador = CalculadorRutas(grafo, factor_trafico)
        self.nodos_coords = nodos_coords or {}  # Almacenar coordenadas en gestor
        self.validador = ValidadorRutas()
        
        self.viveros: Dict[int, Vivero] = {}
        self.pedidos: Dict[int, Pedido] = {}
        self.rutas: Dict[int, Ruta] = {}
        
        self.vivero_actual: Optional[Vivero] = None
        self.pedido_actual: Optional[Pedido] = None
        self.ruta_actual: Optional[Ruta] = None
        
        self.contador_destinos = 0
        self.contador_rutas = 0
        self.viveros_seleccionados_ids: List[int] = []  # viveros que el usuario seleccionó como orígenes (se usan como suplementarios automáticamente)
        self.validacion_por_simulacion: bool = False
        self.asignaciones_reabastecimiento: Optional[Dict] = None  # Guarda qué viveros reabasten cada destino
    
    def registrar_vivero(self, vivero: Vivero) -> bool:
        """
        Registra un vivero en el sistema
        
        Args:
            vivero: Objeto Vivero
            
        Returns:
            True si se registro exitosamente
        """
        # Allow registration even if nodo_id not yet in grafo (nodo_id may be -1 until associated)
        self.viveros[vivero.vivero_id] = vivero
        return True
    
    def seleccionar_vivero(self, vivero_id: int) -> Tuple[bool, Optional[str]]:
        """
        Selecciona un vivero como origen (RF-01)
        
        Args:
            vivero_id: ID del vivero
            
        Returns:
            Tupla (exito, mensaje_error)
        """
        if vivero_id not in self.viveros:
            return False, f"El vivero {vivero_id} no existe"
        
        self.vivero_actual = self.viveros[vivero_id]
        
        # Crear nuevo pedido
        pedido_id = len(self.pedidos) + 1
        self.pedido_actual = Pedido(pedido_id, vivero_id)
        self.pedidos[pedido_id] = self.pedido_actual
        
        return True, None
    
    def agregar_destino(self, lat: float, lon: float, 
                       flores_requeridas: Dict[str, int],
                       nodo_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Agrega un destino al pedido actual (RF-02)
        
        Args:
            lat: Latitud del destino
            lon: Longitud del destino
            flores_requeridas: Diccionario {tipo_flor: cantidad}
            nodo_id: ID del nodo (si se conoce)
            
        Returns:
            Tupla (exito, mensaje_error)
        """
        # Requerir que exista un vivero activo (origen) para definir el inicio del recorrido
        if self.vivero_actual is None:
            return False, "Debe seleccionar y confirmar un vivero activo como origen antes de agregar destinos"
        
        # Validar coordenadas
        valido, error = self.validador.validar_rango_geografico_lima(lat, lon)
        if not valido:
            return False, error
        
        # Validar cantidad de destinos
        if self.pedido_actual is None:
            return False, "No hay un pedido activo"
        cantidad_actual = self.pedido_actual.cantidad_destinos()
        valido, error = self.validador.validar_cantidad_destinos(cantidad_actual + 1)
        if not valido:
            return False, error
        
        # Construir lista de proveedores ordenada: origen activo primero,
        # luego los seleccionados (que actúan automáticamente como suplementarios)
        supplier_ids = [self.vivero_actual.vivero_id]
        for vid in self.viveros_seleccionados_ids:
            if vid != self.vivero_actual.vivero_id and vid in self.viveros and vid not in supplier_ids:
                supplier_ids.append(vid)

        # Verificar capacidad agregada (suma de capacidades de los viveros seleccionados)
        capacidad_total = 0
        for vid in supplier_ids:
            v = self.viveros.get(vid)
            if v and isinstance(v.capacidad_entrega, int):
                capacidad_total += v.capacidad_entrega

        valido, error = self.validador.validar_capacidad_entrega(
            self.pedido_actual.cantidad_destinos() + 1,
            capacidad_total
        )
        if not valido:
            return False, error

        # Validar stock acumulado para TODOS los destinos (existentes + nuevo)
        # Calcular demanda total por tipo de flor incluyendo el nuevo destino
        demanda_total = {}
        for d in self.pedido_actual.destinos:
            for flor, cant in d.flores_requeridas.items():
                demanda_total[flor] = demanda_total.get(flor, 0) + int(cant)
        for flor, cant in flores_requeridas.items():
            demanda_total[flor] = demanda_total.get(flor, 0) + int(cant)

        # Calcular stock acumulado en el orden de visita previsto (origen primero)
        stock_acumulado = {}
        for vid in supplier_ids:
            v = self.viveros.get(vid)
            if not v:
                continue
            for flor, cant in v.inventario.stock.items():
                stock_acumulado[flor] = stock_acumulado.get(flor, 0) + max(0, int(cant))

        # Validar que para cada tipo de flor la suma acumulada sea >= demanda total
        # Si la validacion por simulacion esta activada, OMITIMOS esta validacion temprana
        # y delegamos la comprobacion a la simulacion que puede combinar suplentes.
        if not self.validacion_por_simulacion:
            for flor, req_total in demanda_total.items():
                disponible = stock_acumulado.get(flor, 0)
                if disponible < req_total:
                    return False, f"Stock insuficiente de {flor}: disponible={disponible}, requerido={req_total}.\nAsegure selección de viveros suplementarios que sumen el stock necesario y confirme el origen activo."

        # Si no se proporciono nodo_id, buscar el mas cercano
        if nodo_id is None:
            nodo_id = self._buscar_nodo_cercano(lat, lon)

        # Validar que el nodo existe
        valido, error = self.validador.validar_nodo_existe(nodo_id, self.grafo)
        if not valido:
            return False, error

        # Crear destino (antes de la simulacion)
        self.contador_destinos += 1
        destino = Destino(
            destino_id=self.contador_destinos,
            nodo_id=nodo_id,
            lat=lat,
            lon=lon,
            flores_requeridas=flores_requeridas
        )

        # Si la validacion por simulacion esta activada, simular la secuencia de paradas
        if self.validacion_por_simulacion:
            sim_ok, sim_res = self._simular_entregas_con_reabastecimiento(self.pedido_actual.destinos + [destino], supplier_ids)
            if not sim_ok:
                return False, str(sim_res)  # sim_res contiene mensaje de fallo
            # sim_res es el mapa de asignacion por destino/suplidor
            if isinstance(sim_res, dict):
                asignaciones = sim_res
                # Guardar asignaciones para usar en calcular_ruta_optima
                self.asignaciones_reabastecimiento = asignaciones
            else:
                asignaciones = {}
        else:
            asignaciones = None

        # Agregar al pedido
        if not self.pedido_actual.agregar_destino(destino):
            return False, "No se pudo agregar el destino"

        # Determinar entregador y consumir stock usando las asignaciones de la simulacion (si existen)
        if asignaciones:
            # asignaciones: dict(destino_id -> {supplier_id: {flor: qty}})
            alloc_for_dest = asignaciones.get(destino.destino_id, {})
            # Reducir stock en cada vivero segun asignacion
            for vid, consumos in alloc_for_dest.items():
                v = self.viveros.get(vid)
                if not v:
                    continue
                v.inventario.reducir_stock(consumos)

            # Elegir entregador: preferir origen si aporto algo, sino el primer proveedor que aporto
            delivering_vid = None
            origen_id = self.vivero_actual.vivero_id if self.vivero_actual else None
            if origen_id and origen_id in alloc_for_dest and any(q > 0 for q in alloc_for_dest[origen_id].values()):
                delivering_vid = origen_id
            else:
                for vid in supplier_ids:
                    if vid in alloc_for_dest and any(q > 0 for q in alloc_for_dest[vid].values()):
                        delivering_vid = vid
                        break
        else:
            # Si no hubo simulacion, elegir entregador por capacidad (fallback)
            delivering_vid = None
            if self.vivero_actual and self.vivero_actual.vivero_id in supplier_ids and self.vivero_actual.capacidad_entrega > 0:
                delivering_vid = self.vivero_actual.vivero_id
            else:
                for vid in supplier_ids:
                    v = self.viveros.get(vid)
                    if v and v.capacidad_entrega > 0:
                        delivering_vid = vid
                        break

        # restar 1 a capacidad del vivero que realiza la entrega
        if delivering_vid:
            dv = self.viveros.get(delivering_vid)
            if dv and isinstance(dv.capacidad_entrega, int):
                dv.capacidad_entrega = max(0, dv.capacidad_entrega - 1)

        # Si el vivero se quedo sin stock de algun tipo, dejar marcado para UI
        # (la UI puede pedir al usuario seleccionar un vivero suplementario)
        # self._recalcular_ruta_automatico()  # Desactivado: usuario calculará manualmente
        
        return True, None
    
    def editar_destino(self, destino_id: int, nueva_lat: float, nueva_lon: float) -> Tuple[bool, Optional[str]]:
        """
        Edita las coordenadas de un destino (RF-02)
        
        Args:
            destino_id: ID del destino
            nueva_lat: Nueva latitud
            nueva_lon: Nueva longitud
            
        Returns:
            Tupla (exito, mensaje_error)
        """
        if self.pedido_actual is None:
            return False, "No hay un pedido activo"
        
        # Validar nuevas coordenadas
        valido, error = self.validador.validar_rango_geografico_lima(nueva_lat, nueva_lon)
        if not valido:
            return False, error
        
        # Buscar nuevo nodo cercano
        nuevo_nodo_id = self._buscar_nodo_cercano(nueva_lat, nueva_lon)
        
        # Editar en el pedido
        destino = self.pedido_actual.obtener_destino(destino_id)
        if destino is None:
            return False, f"Destino {destino_id} no encontrado"
        
        destino.lat = nueva_lat
        destino.lon = nueva_lon
        destino.nodo_id = nuevo_nodo_id
        
        # Recalcular ruta automaticamente
        # self._recalcular_ruta_automatico()  # Desactivado: usuario calculará manualmente
        
        return True, None
    
    def eliminar_destino(self, destino_id: int) -> Tuple[bool, Optional[str]]:
        """
        Elimina un destino del pedido (RF-02)
        
        Args:
            destino_id: ID del destino
            
        Returns:
            Tupla (exito, mensaje_error)
        """
        if self.pedido_actual is None:
            return False, "No hay un pedido activo"
        
        # Permitir eliminar destinos incluso si queda 0 (para pruebas/edición en UI)
        # La validación de rango para calcular ruta seguirá requiriendo entre 1 y 20 destinos.
        
        # Eliminar del pedido
        if not self.pedido_actual.eliminar_destino(destino_id):
            return False, f"Destino {destino_id} no encontrado"
        
        # Recalcular ruta automaticamente si quedan destinos
        # self._recalcular_ruta_automatico()  # Desactivado: usuario calculará manualmente
        
        return True, None
    
    def calcular_ruta_optima(self, retornar_origen: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Calcula la ruta optima para el pedido actual (RF-03)
        
        Args:
            retornar_origen: Si True, la ruta retorna al punto de origen (ciclo cerrado)
            
        Returns:
            Tupla (exito, mensaje_error)
        """
        if self.pedido_actual is None or self.vivero_actual is None:
            return False, "Debe seleccionar un vivero y agregar destinos"
        
        if not self.pedido_actual.validar_rango():
            return False, "Debe haber entre 1 y 20 destinos"
        
        # Extraer nodos de destinos
        destinos_nodos = [d.nodo_id for d in self.pedido_actual.destinos]
        origen_nodo = self.vivero_actual.nodo_id
        
        # Si la validación por simulación está activa, recalcular asignaciones con TODOS los destinos
        if self.validacion_por_simulacion:
            # Construir lista de supplier_ids (origen + seleccionados)
            supplier_ids = [self.vivero_actual.vivero_id]
            for vid in self.viveros_seleccionados_ids:
                if vid != self.vivero_actual.vivero_id and vid in self.viveros and vid not in supplier_ids:
                    supplier_ids.append(vid)
            
            # Recalcular simulación con TODOS los destinos actuales
            sim_ok, sim_res = self._simular_entregas_con_reabastecimiento(
                self.pedido_actual.destinos,
                supplier_ids
            )
            
            if sim_ok and isinstance(sim_res, dict):
                self.asignaciones_reabastecimiento = sim_res
            else:
                # Si falla la simulación, no hay asignaciones
                self.asignaciones_reabastecimiento = None
        
        # Si hay asignaciones de reabastecimiento (simulación activa), construir ruta con viveros
        if self.asignaciones_reabastecimiento:
            # Extraer todos los viveros que participan en el reabastecimiento
            viveros_reabastecimiento = set()
            for destino_id, suppliers in self.asignaciones_reabastecimiento.items():
                viveros_reabastecimiento.update(suppliers.keys())
            
            # Convertir IDs de viveros a nodos
            nodos_viveros_reabast = []
            for vid in viveros_reabastecimiento:
                v = self.viveros.get(vid)
                if v:
                    nodo = getattr(v, 'nodo_id', None)
                    if nodo is None or nodo == -1:
                        nodo = self._buscar_nodo_cercano(v.lat, v.lon)
                    if nodo not in nodos_viveros_reabast and nodo != origen_nodo:
                        nodos_viveros_reabast.append(nodo)
            
            # Construir lista de nodos a visitar: viveros de reabastecimiento + destinos
            nodos_a_visitar = nodos_viveros_reabast + destinos_nodos
            
            # Precalcular matriz de distancias
            nodos_interes = [origen_nodo] + nodos_a_visitar
            self.calculador.precalcular_matriz_distancias(nodos_interes)
            
            # Calcular ruta TSP incluyendo viveros y destinos
            tiempo_inicio = time.time()
            distancia_total, secuencia = self.calculador.calcular_ruta_tsp(
                origen_nodo,
                nodos_a_visitar,
                retornar_origen
            )
            tiempo_fin = time.time()
        else:
            # Ruta simple: solo origen y destinos
            nodos_interes = [origen_nodo] + destinos_nodos
            self.calculador.precalcular_matriz_distancias(nodos_interes)
            
            tiempo_inicio = time.time()
            distancia_total, secuencia = self.calculador.calcular_ruta_tsp(
                origen_nodo,
                destinos_nodos,
                retornar_origen
            )
            tiempo_fin = time.time()
        
        # Calcular camino completo nodo por nodo
        camino_completo, distancia_real = self.calculador.calcular_camino_completo(secuencia)
        
        # Crear objeto Ruta
        self.contador_rutas += 1
        ruta = Ruta(
            ruta_id=self.contador_rutas,
            origen_nodo=origen_nodo,
            secuencia_visitas=secuencia,
            distancia_total=distancia_real / 1000,  # Convertir a km
            tiempo_total=distancia_real / 1000 / 0.5  # Asumir 30 km/h promedio
        )
        
        ruta.tiempo_computo = tiempo_fin - tiempo_inicio
        ruta.camino_completo = camino_completo
        
        # Calcular metricas por segmento
        for i in range(len(secuencia) - 1):
            desde = secuencia[i]
            hasta = secuencia[i + 1]
            dist_segmento = self.calculador.matriz_distancias.get((desde, hasta), 0) / 1000
            tiempo_segmento = dist_segmento / 0.5
            ruta.agregar_segmento(desde, hasta, dist_segmento, tiempo_segmento)
        
        # Guardar ruta
        self.ruta_actual = ruta
        self.rutas[ruta.ruta_id] = ruta
        
        return True, None
    
    def _recalcular_ruta_automatico(self):
        """Recalcula la ruta automaticamente al modificar destinos"""
        if self.pedido_actual and self.pedido_actual.cantidad_destinos() > 0:
            self.calcular_ruta_optima()
    
    def _buscar_nodo_cercano(self, lat: float, lon: float) -> int:
        """
        Busca el nodo mas cercano a unas coordenadas usando distancia euclidiana
        
        Args:
            lat: Latitud
            lon: Longitud
            
        Returns:
            ID del nodo mas cercano que existe en el grafo
        """
        if not self.grafo:
            raise ValueError("Grafo no inicializado")
        
        # Usar coordenadas almacenadas en el gestor
        nodos_coords = self.nodos_coords
        
        mejor_nodo = None
        mejor_distancia = float('inf')
        
        # Buscar nodo más cercano
        for nodo_id in self.grafo.keys():
            if nodo_id not in nodos_coords:
                continue
            
            nodo_lat, nodo_lon = nodos_coords[nodo_id]
            
            # Distancia euclidiana (aproximación)
            distancia = ((lat - nodo_lat) ** 2 + (lon - nodo_lon) ** 2) ** 0.5
            
            if distancia < mejor_distancia:
                mejor_distancia = distancia
                mejor_nodo = nodo_id
        
        if mejor_nodo is None:
            # Fallback: retornar primer nodo del grafo
            return next(iter(self.grafo.keys()))
        
        return mejor_nodo
    
    def obtener_resumen(self) -> Optional[Dict]:
        """
        Obtiene resumen de la ruta actual (RF-05)
        
        Returns:
            Diccionario con metricas o None si no hay ruta
        """
        if self.ruta_actual is None:
            return None
        
        return self.ruta_actual.obtener_resumen()
    
    def exportar_resultados(self) -> Optional[List[Dict]]:
        """
        Exporta orden de visitas de la ruta actual (RF-05)
        
        Returns:
            Lista de diccionarios con orden de visitas o None si no hay ruta
        """
        if self.ruta_actual is None:
            return None
        
        return self.ruta_actual.exportar_orden_visitas()
    
    def obtener_viveros_disponibles(self) -> List[Dict]:
        """Retorna lista de viveros disponibles"""
        return [
            {
                'vivero_id': v.vivero_id,
                'nombre': v.nombre,
                'lat': v.lat,
                'lon': v.lon,
                'capacidad': v.capacidad_entrega
            }
            for v in self.viveros.values()
        ]

    def set_viveros_seleccionados(self, ids: List[int]) -> None:
        """Actualiza la lista de viveros seleccionados por el usuario"""
        self.viveros_seleccionados_ids = [vid for vid in ids if vid in self.viveros]

    def set_validacion_por_simulacion(self, value: bool) -> None:
        """Activa o desactiva la validacion por simulacion (reabastecimiento)"""
        self.validacion_por_simulacion = bool(value)

    def _simular_entregas_con_reabastecimiento(self, destinos: List[Destino], supplier_ids: List[int]) -> Tuple[bool, Optional[object]]:
        """Selecciona suplentes considerando coste de ruta y verifica factibilidad de stock.

        Enfoque:
        - Para cada subconjunto de proveedores (subconjunto que incluya el origen), comprobamos
          si la suma de stock de ese subconjunto cubre la demanda total. Esto es una
          enumeración por subconjuntos (DP/exhaustiva) que respeta la técnica de
          Programación Dinámica / Fuerza Bruta permitida en el curso.
        - Para los subconjuntos factibles calculamos el coste de la ruta que visita los
          proveedores seleccionados y todos los destinos (usando `CalculadorRutas` para
          computar distancias y TSP). Elegimos el subconjunto con menor coste.
        - Finalmente, asignamos las cantidades a cada destino priorizando proveedores
          cercanos al destino (usando distancias via `CalculadorRutas.dijkstra`).

        Retorna:
            (True, asignaciones) donde asignaciones es un dict: {destino_id: {supplier_id: {flor: qty}}}
            o (False, mensaje_error) si no existe asignación factible.
        """
        # Mapear cada proveedor a su stock y nodo
        supplier_stocks: Dict[int, Dict[str, int]] = {}
        supplier_nodes: Dict[int, int] = {}
        for vid in supplier_ids:
            v = self.viveros.get(vid)
            if v:
                supplier_stocks[vid] = {f: int(c) for f, c in v.inventario.stock.items()}
                nodo = getattr(v, 'nodo_id', None)
                if nodo is None or nodo == -1:
                    nodo = self._buscar_nodo_cercano(v.lat, v.lon)
                supplier_nodes[vid] = nodo
            else:
                supplier_stocks[vid] = {}
                supplier_nodes[vid] = -1

        # Demanda total
        demanda_total: Dict[str, int] = {}
        for d in destinos:
            for f, c in d.flores_requeridas.items():
                demanda_total[f] = demanda_total.get(f, 0) + int(c)

        # Enumerar subconjuntos de proveedores que incluyan el origen (primer elemento de supplier_ids)
        origen_id = supplier_ids[0]
        candidatos = supplier_ids
        n = len(candidatos)

        mejor_subconjunto = None
        mejor_coste = float('inf')

        # Precomputar nodos de destinos
        destinos_nodos = [d.nodo_id if d.nodo_id is not None else self._buscar_nodo_cercano(d.lat, d.lon) for d in destinos]

        # Iterar por tamaños de subconjunto (pruning por tamaño)
        for r in range(1, n + 1):
            for comb in combinations(candidatos, r):
                if origen_id not in comb:
                    continue
                # sumar stock del subconjunto
                disponible: Dict[str, int] = {}
                for sid in comb:
                    for f, c in supplier_stocks.get(sid, {}).items():
                        disponible[f] = disponible.get(f, 0) + int(c)
                
                ok = True
                for f, req in demanda_total.items():
                    if disponible.get(f, 0) < req:
                        ok = False
                        break
                if not ok:
                    continue

                # calcular coste de la ruta que visita proveedores (nodos) y destinos
                proveedor_nodos = [supplier_nodes[sid] for sid in comb]
                # armar lista de nodos de interes: origen + proveedores + destinos
                nodos_interes = [supplier_nodes[origen_id]] + [n for n in proveedor_nodos if n != supplier_nodes[origen_id]] + destinos_nodos

                def _approx_cost_by_coords(path_nodes: List[int], comb_sids: Tuple[int, ...]) -> float:
                    # convierte una secuencia de nodos a coordenadas y suma distancias euclidianas
                    coords = []  # list of (lat, lon)
                    # origin
                    # map node id to coords; for provider nodes that are -1, use vivero lat/lon
                    # build mapping from node ids of providers to their vivero coords
                    for n in path_nodes:
                        if n is None or n == -1:
                            # try to find matching provider by node -1 (use comb order)
                            # fallback: skip
                            continue
                        if n in self.nodos_coords:
                            coords.append(self.nodos_coords[n])
                        else:
                            # last resort: try to find a vivero with this nodo
                            found = None
                            for vid, v in self.viveros.items():
                                if getattr(v, 'nodo_id', None) == n:
                                    found = (v.lat, v.lon)
                                    break
                            if found:
                                coords.append(found)
                            else:
                                # cannot resolve coord, skip
                                continue
                    if len(coords) < 2:
                        return float('inf')
                    total = 0.0
                    for i in range(len(coords) - 1):
                        lat1, lon1 = coords[i]
                        lat2, lon2 = coords[i + 1]
                        total += ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
                    return total

                coste = float('inf')
                try:
                    # intentar cálculo exacto con CalculadorRutas
                    self.calculador.precalcular_matriz_distancias([n for n in nodos_interes if n is not None and n != -1])
                    _, sec = self.calculador.calcular_ruta_tsp(supplier_nodes[origen_id], [n for n in proveedor_nodos if n is not None and n != -1] + destinos_nodos, retornar_origen=False)
                    # calcular camino completo y distancia real
                    _, distancia_real = self.calculador.calcular_camino_completo(sec)
                    coste = distancia_real
                except Exception:
                    # fallback aproximado por coordenadas si faltan nodos en el grafo o falla el solver
                    # construir path_nodes: origin node, provider nodes, destino nodes
                    path_nodes = []
                    # origin
                    onode = supplier_nodes.get(origen_id, -1)
                    path_nodes.append(onode)
                    for sid in comb:
                        path_nodes.append(supplier_nodes.get(sid, -1))
                    path_nodes.extend(destinos_nodos)
                    approx = _approx_cost_by_coords(path_nodes, comb)
                    if approx == float('inf'):
                        # no podemos estimar coste; saltar este subconjunto
                        continue
                    coste = approx

                if coste < mejor_coste:
                    mejor_coste = coste
                    mejor_subconjunto = comb

            # si ya encontramos un subconjunto factible de tamaño r, podemos romper para preferir menor tamaño
            if mejor_subconjunto is not None:
                break

        if mejor_subconjunto is None:
            return False, "No se encontró subconjunto de proveedores que cubra la demanda"

        # Con el mejor subconjunto elegido, asignar stock a destinos priorizando proveedores más cercanos al destino
        asignaciones_resultado: Dict[int, Dict[int, Dict[str, int]]] = {}
        # construir stocks mutables
        stocks_mut = {sid: dict(supplier_stocks.get(sid, {})) for sid in mejor_subconjunto}

        # Precalcular distancias entre proveedores y destinos para priorizar
        prov_nodes = {sid: supplier_nodes[sid] for sid in mejor_subconjunto}
        for dest in destinos:
            asignaciones_resultado[dest.destino_id] = {}
            # ordenar proveedores por distancia al destino
            dist_list = []
            for sid, nodo in prov_nodes.items():
                if nodo is None or nodo == -1:
                    continue
                try:
                    dcost, _ = self.calculador.dijkstra(nodo, dest.nodo_id)
                except Exception:
                    dcost = float('inf')
                dist_list.append((dcost, sid))
            dist_list.sort()

            # asignar por flor
            for flor, need in dest.flores_requeridas.items():
                remaining = int(need)
                for _, sid in dist_list:
                    avail = stocks_mut.get(sid, {}).get(flor, 0)
                    if avail <= 0:
                        continue
                    take = min(avail, remaining)
                    if take <= 0:
                        continue
                    asignaciones_resultado[dest.destino_id].setdefault(sid, {})
                    asignaciones_resultado[dest.destino_id][sid][flor] = asignaciones_resultado[dest.destino_id][sid].get(flor, 0) + take
                    stocks_mut[sid][flor] = stocks_mut[sid].get(flor, 0) - take
                    remaining -= take
                    if remaining <= 0:
                        break
                if remaining > 0:
                    # esto no debería pasar porque el subconjunto cubre la demanda total, pero si ocurre devolvemos fallo
                    return False, f"Asignación fallida para destino {dest.destino_id}, flor {flor}"

        return True, asignaciones_resultado

    def obtener_viveros_agotados(self) -> List[int]:
        """Retorna lista de IDs de viveros que tienen algun stock agotado"""
        agotados = []
        for vid, v in self.viveros.items():
            try:
                if v.inventario and v.inventario.esta_agotado():
                    agotados.append(vid)
            except Exception:
                continue
        return agotados

    def obtener_destinos_actuales(self) -> List[Dict]:
        """Retorna lista de destinos del pedido actual"""
        if self.pedido_actual is None:
            return []
        
        return [
            {
                'destino_id': d.destino_id,
                'nodo_id': d.nodo_id,
                'lat': d.lat,
                'lon': d.lon,
                'flores': d.flores_requeridas
            }
            for d in self.pedido_actual.destinos
        ]
    
    def obtener_viveros_reabastecimiento(self) -> List[int]:
        """
        Retorna lista de IDs de viveros que participan en el reabastecimiento
        según las asignaciones de la simulación
        """
        if not self.asignaciones_reabastecimiento:
            return []
        
        viveros = set()
        for destino_id, suppliers in self.asignaciones_reabastecimiento.items():
            viveros.update(suppliers.keys())
        
        return list(viveros)
