"""
Gestor principal de rutas - Logica de negocio
"""

import time
from typing import Dict, List, Tuple, Optional
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
    
    def registrar_vivero(self, vivero: Vivero) -> bool:
        """
        Registra un vivero en el sistema
        
        Args:
            vivero: Objeto Vivero
            
        Returns:
            True si se registro exitosamente
        """
        if not vivero.validar_en_grafo(self.grafo):
            return False
        
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
        if self.pedido_actual is None:
            return False, "Debe seleccionar un vivero primero"
        
        # Validar coordenadas
        valido, error = self.validador.validar_rango_geografico_lima(lat, lon)
        if not valido:
            return False, error
        
        # Validar cantidad de destinos
        cantidad_actual = self.pedido_actual.cantidad_destinos()
        valido, error = self.validador.validar_cantidad_destinos(cantidad_actual + 1)
        if not valido:
            return False, error
        
        # Validar stock disponible
        if self.vivero_actual:
            valido, error = self.validador.validar_stock_flores(
                self.vivero_actual.inventario.stock,
                flores_requeridas
            )
            if not valido:
                return False, error
        
        # Si no se proporciono nodo_id, buscar el mas cercano
        if nodo_id is None:
            nodo_id = self._buscar_nodo_cercano(lat, lon)
        
        # Validar que el nodo existe
        valido, error = self.validador.validar_nodo_existe(nodo_id, self.grafo)
        if not valido:
            return False, error
        
        # Crear destino
        self.contador_destinos += 1
        destino = Destino(
            destino_id=self.contador_destinos,
            nodo_id=nodo_id,
            lat=lat,
            lon=lon,
            flores_requeridas=flores_requeridas
        )
        
        # Agregar al pedido
        if not self.pedido_actual.agregar_destino(destino):
            return False, "No se pudo agregar el destino"
        
        # Recalcular ruta automaticamente
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
        
        # Validar que quede al menos 1 destino
        if self.pedido_actual.cantidad_destinos() <= 1:
            return False, "Debe haber al menos 1 destino"
        
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
        
        # Extraer nodos
        origen_nodo = self.vivero_actual.nodo_id
        destinos_nodos = [d.nodo_id for d in self.pedido_actual.destinos]
        
        # Precalcular matriz de distancias
        nodos_interes = [origen_nodo] + destinos_nodos
        self.calculador.precalcular_matriz_distancias(nodos_interes)
        
        # Calcular ruta con medicion de tiempo
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
