"""
Modulo: generador_guia_ruta.py
Descripcion: Genera instrucciones turn-by-turn para navegacion de rutas

TÉCNICA IMPLEMENTADA: GEOMETRÍA COMPUTACIONAL + ALGORITMOS DE BÚSQUEDA
- Cálculo de bearings (rumbos) entre coordenadas
- Clasificación de ángulos de giro para instrucciones
- Generación de guías paso a paso desde secuencia de nodos
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import math
import logging


logger = logging.getLogger(__name__)


@dataclass
class InstruccionRuta:
    """Representa una instruccion de navegacion paso a paso"""
    paso: int
    nodo_origen: int
    nodo_destino: int
    calle: str
    distancia_km: float
    direccion: str
    instruccion: str
    lat_origen: float
    lon_origen: float
    lat_destino: float
    lon_destino: float


class GeneradorGuiaRuta:
    """
    Genera instrucciones detalladas de navegacion desde una secuencia de nodos.
    
    Esta clase toma una ruta representada como secuencia de nodos y produce
    instrucciones turn-by-turn (giro a giro) para guiar al conductor.
    
    TECNICA: GEOMETRIA COMPUTACIONAL
    - Calculo de bearings (azimuth) entre coordenadas geograficas
    - Clasificacion de angulos de giro en direcciones legibles
    - Generacion de texto descriptivo para delivery
    """
    
    def __init__(self, grafo: Dict[int, Dict[int, float]], nodos_coords: Dict[int, Tuple[float, float]]):
        """
        Args:
            grafo: Diccionario de adyacencia {nodo: {vecino: distancia}}
            nodos_coords: Diccionario {nodo_id: (lat, lon)} con coordenadas
        """
        self.grafo = grafo
        self.nodos_coords = nodos_coords
        logger.info(f"GeneradorGuiaRuta inicializado con {len(nodos_coords)} nodos")
    
    def generar_guia(self, secuencia_nodos: List[int]) -> List[InstruccionRuta]:
        """
        Genera lista de instrucciones desde secuencia de nodos.
        
        Args:
            secuencia_nodos: Lista ordenada de nodos que conforman la ruta
            
        Returns:
            Lista de InstruccionRuta con paso a paso
            
        Example:
            >>> generador = GeneradorGuiaRuta(grafo, nodos_coords)
            >>> instrucciones = generador.generar_guia([1, 5, 8, 12])
            >>> for inst in instrucciones:
            ...     print(f"{inst.paso}. {inst.instruccion}")
            1. Salga hacia el destino durante 1.2 km
            2. Gire a la derecha y continúe 0.8 km
            3. Gire a la izquierda y continúe 2.3 km
        """
        if len(secuencia_nodos) < 2:
            logger.warning("Secuencia con menos de 2 nodos, no hay instrucciones")
            return []
        
        logger.info(f"Generando guía para ruta de {len(secuencia_nodos)} nodos")
        
        instrucciones = []
        
        for i in range(len(secuencia_nodos) - 1):
            nodo_actual = secuencia_nodos[i]
            nodo_siguiente = secuencia_nodos[i + 1]
            
            # 1. Extraer datos de la arista
            arista_data = self._obtener_datos_arista(nodo_actual, nodo_siguiente)
            
            # 2. Calcular direccion (solo si hay nodo previo para comparar)
            if i == 0:
                direccion = "🚀 Salida"
                logger.debug(f"Paso {i+1}: Salida desde nodo {nodo_actual}")
            else:
                nodo_anterior = secuencia_nodos[i - 1]
                direccion = self._calcular_direccion(
                    nodo_anterior, nodo_actual, nodo_siguiente
                )
                logger.debug(f"Paso {i+1}: Dirección {direccion} desde nodo {nodo_actual} a {nodo_siguiente}")
            
            # 3. Generar instruccion textual
            instruccion_texto = self._generar_instruccion(
                direccion,
                arista_data['calle'],
                arista_data['distancia_km'],
                i == 0  # es_salida
            )
            
            # 4. Crear objeto InstruccionRuta
            instrucciones.append(InstruccionRuta(
                paso=i + 1,
                nodo_origen=nodo_actual,
                nodo_destino=nodo_siguiente,
                calle=arista_data['calle'],
                distancia_km=arista_data['distancia_km'],
                direccion=direccion,
                instruccion=instruccion_texto,
                lat_origen=arista_data['lat_origen'],
                lon_origen=arista_data['lon_origen'],
                lat_destino=arista_data['lat_destino'],
                lon_destino=arista_data['lon_destino']
            ))
        
        logger.info(f"Generadas {len(instrucciones)} instrucciones de navegación")
        return instrucciones
    
    def _obtener_datos_arista(self, nodo1: int, nodo2: int) -> dict:
        """
        Extrae informacion de la arista entre dos nodos
        
        Args:
            nodo1: Nodo origen
            nodo2: Nodo destino
            
        Returns:
            Diccionario con datos de la arista:
                - calle: nombre de calle (o "Calle desconocida")
                - distancia_km: distancia en kilometros
                - lat_origen, lon_origen: coordenadas origen
                - lat_destino, lon_destino: coordenadas destino
        """
        # Obtener distancia del grafo
        distancia_metros = 0
        if nodo1 in self.grafo and nodo2 in self.grafo[nodo1]:
            distancia_metros = self.grafo[nodo1][nodo2]
        else:
            logger.warning(f"Arista {nodo1}->{nodo2} no encontrada en grafo")
        
        # Obtener coordenadas
        lat_origen, lon_origen = self.nodos_coords.get(nodo1, (0.0, 0.0))
        lat_destino, lon_destino = self.nodos_coords.get(nodo2, (0.0, 0.0))
        
        # Nombre de calle (por ahora generico, puede mejorarse con OSM data)
        calle = f"vía {nodo1}-{nodo2}"
        
        return {
            'calle': calle,
            'distancia_km': distancia_metros / 1000.0,
            'lat_origen': lat_origen,
            'lon_origen': lon_origen,
            'lat_destino': lat_destino,
            'lon_destino': lon_destino
        }
    
    def _calcular_direccion(self, nodo_anterior: int, nodo_actual: int, 
                           nodo_siguiente: int) -> str:
        """
        Calcula direccion del giro usando bearings
        
        TECNICA: GEOMETRIA COMPUTACIONAL
        - Calcula bearing (rumbo) entre dos pares de coordenadas
        - Diferencia de bearings determina angulo de giro
        - Clasifica angulo en direccion legible
        
        Args:
            nodo_anterior: Nodo previo en la ruta
            nodo_actual: Nodo actual (punto de giro)
            nodo_siguiente: Siguiente nodo
            
        Returns:
            String con direccion clasificada (ej: "→ Derecha", "↑ Recto")
        """
        # Obtener coordenadas
        lat1, lon1 = self.nodos_coords.get(nodo_anterior, (0.0, 0.0))
        lat2, lon2 = self.nodos_coords.get(nodo_actual, (0.0, 0.0))
        lat3, lon3 = self.nodos_coords.get(nodo_siguiente, (0.0, 0.0))
        
        # Calcular bearings de ambos segmentos
        bearing1 = self.calcular_bearing(lat1, lon1, lat2, lon2)
        bearing2 = self.calcular_bearing(lat2, lon2, lat3, lon3)
        
        # Calcular angulo de giro (normalizado a [-180, 180])
        angulo = (bearing2 - bearing1 + 180) % 360 - 180
        
        logger.debug(f"Ángulo de giro: {angulo:.1f}° (bearing1={bearing1:.1f}, bearing2={bearing2:.1f})")
        
        # Clasificar angulo en direccion
        direccion = self.clasificar_angulo(angulo)
        
        return direccion
    
    def _generar_instruccion(self, direccion: str, calle: str, 
                            distancia: float, es_salida: bool) -> str:
        """
        Genera texto legible para la instruccion
        
        Args:
            direccion: Direccion clasificada (ej: "→ Derecha")
            calle: Nombre de la calle
            distancia: Distancia en km
            es_salida: True si es la primera instruccion
            
        Returns:
            Texto descriptivo para el conductor
        """
        if es_salida:
            return f"Salga hacia el destino por {calle} durante {distancia:.2f} km"
        
        if direccion.startswith("↑"):
            return f"Continúe recto por {calle} durante {distancia:.2f} km"
        elif direccion.startswith("→") or direccion == "→ Derecha":
            return f"Gire a la derecha en {calle} y continúe {distancia:.2f} km"
        elif direccion.startswith("←") or direccion == "← Izquierda":
            return f"Gire a la izquierda en {calle} y continúe {distancia:.2f} km"
        elif direccion.startswith("↩"):
            return f"Dé vuelta en U en {calle} y continúe {distancia:.2f} km"
        elif "derecha" in direccion.lower():
            return f"Gire ligeramente a la derecha en {calle} y continúe {distancia:.2f} km"
        elif "izquierda" in direccion.lower():
            return f"Gire ligeramente a la izquierda en {calle} y continúe {distancia:.2f} km"
        else:
            return f"Siga por {calle} durante {distancia:.2f} km ({direccion})"
    
    @staticmethod
    def calcular_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula rumbo (azimuth) entre dos coordenadas geograficas
        
        TECNICA: GEOMETRIA ESFERICA
        Usa formula de bearing para calcular direccion entre dos puntos en la Tierra
        
        Args:
            lat1: Latitud punto inicial
            lon1: Longitud punto inicial
            lat2: Latitud punto final
            lon2: Longitud punto final
            
        Returns:
            Bearing en grados [0, 360), donde 0° = Norte, 90° = Este
            
        Formula:
            θ = atan2(sin(Δλ)⋅cos(φ₂), cos(φ₁)⋅sin(φ₂) − sin(φ₁)⋅cos(φ₂)⋅cos(Δλ))
            donde φ = latitud, λ = longitud
        """
        # Convertir a radianes
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        # Formula de bearing
        x = math.sin(dlon_rad) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalizar a [0, 360)
        bearing_normalizado = (bearing_deg + 360) % 360
        
        return bearing_normalizado
    
    @staticmethod
    def clasificar_angulo(angulo: float) -> str:
        """
        Clasifica angulo en direccion legible con emoji
        
        Args:
            angulo: Angulo en grados [-180, 180]
                - Positivo: giro a la derecha
                - Negativo: giro a la izquierda
                - Cercano a 0: recto
        
        Returns:
            Direccion legible:
                - "↑ Recto": -20° a 20°
                - "↗ Ligera derecha": 20° a 70°
                - "→ Derecha": 70° a 110°
                - "↘ Derecha cerrada": 110° a 160°
                - "↖ Ligera izquierda": -70° a -20°
                - "← Izquierda": -110° a -70°
                - "↙ Izquierda cerrada": -160° a -110°
                - "↩ Retorno": |angulo| > 160°
        """
        # Clasificacion por rangos de angulo
        if -20 <= angulo <= 20:
            return "↑ Recto"
        elif 20 < angulo < 70:
            return "↗ Ligera derecha"
        elif 70 <= angulo <= 110:
            return "→ Derecha"
        elif 110 < angulo < 160:
            return "↘ Derecha cerrada"
        elif -70 < angulo < -20:
            return "↖ Ligera izquierda"
        elif -110 <= angulo <= -70:
            return "← Izquierda"
        elif -160 < angulo < -110:
            return "↙ Izquierda cerrada"
        else:  # |angulo| >= 160
            return "↩ Retorno"
    
    def generar_guia_con_waypoints(self, secuencia_nodos: List[int], 
                                    tipos_waypoint: Optional[Dict[int, str]] = None) -> List[InstruccionRuta]:
        """
        Genera guia de ruta identificando tipos de waypoints (destinos, viveros)
        
        Args:
            secuencia_nodos: Lista ordenada de nodos
            tipos_waypoint: Diccionario {nodo_id: tipo} donde tipo puede ser:
                - "destino": Punto de entrega
                - "vivero": Punto de reabastecimiento
                - "paso": Nodo intermedio (por defecto)
        
        Returns:
            Lista de InstruccionRuta con informacion adicional sobre waypoints
        """
        tipos_waypoint = tipos_waypoint or {}
        
        instrucciones = self.generar_guia(secuencia_nodos)
        
        # Agregar informacion de tipo de waypoint a las instrucciones
        for inst in instrucciones:
            tipo_destino = tipos_waypoint.get(inst.nodo_destino, "paso")
            
            if tipo_destino == "destino":
                inst.instruccion += " 📦 [ENTREGA]"
            elif tipo_destino == "vivero":
                inst.instruccion += " 🏪 [REABASTECIMIENTO]"
        
        return instrucciones
    
    def calcular_distancia_haversine(self, lat1: float, lon1: float, 
                                    lat2: float, lon2: float) -> float:
        """
        Calcula distancia real entre dos coordenadas usando formula de Haversine
        
        TECNICA: GEOMETRIA ESFERICA
        Formula de Haversine para distancia sobre superficie terrestre
        
        Args:
            lat1, lon1: Coordenadas punto 1
            lat2, lon2: Coordenadas punto 2
            
        Returns:
            Distancia en kilometros
            
        Formula:
            a = sin²(Δφ/2) + cos(φ₁)⋅cos(φ₂)⋅sin²(Δλ/2)
            c = 2⋅atan2(√a, √(1−a))
            d = R⋅c
            donde R = radio de la Tierra (6371 km)
        """
        R = 6371.0  # Radio de la Tierra en km
        
        # Convertir a radianes
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        # Formula de Haversine
        a = math.sin(dlat / 2)**2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distancia = R * c
        
        return distancia
    
    def validar_instrucciones(self, instrucciones: List[InstruccionRuta], 
                              distancia_total_esperada: Optional[float] = None) -> Dict[str, Any]:
        """
        Valida que las instrucciones generadas sean consistentes
        
        Args:
            instrucciones: Lista de instrucciones a validar
            distancia_total_esperada: Distancia total de la ruta (opcional, para validar consistencia)
            
        Returns:
            Diccionario con resultado de validacion:
                - 'valido': bool
                - 'mensaje': str (descripcion del resultado)
                - 'distancia_instrucciones': float
                - 'diferencia': float (si se proporciono distancia esperada)
        """
        if not instrucciones:
            return {'valido': False, 'mensaje': 'No hay instrucciones para validar'}
        
        # Verificar secuencia continua de pasos
        for i, inst in enumerate(instrucciones):
            if inst.paso != i + 1:
                return {
                    'valido': False, 
                    'mensaje': f"Secuencia de pasos incorrecta en paso {inst.paso}"
                }
        
        # Verificar que coordenadas estan en rango valido (Lima)
        LIMA_LAT_MIN, LIMA_LAT_MAX = -12.5, -11.5
        LIMA_LON_MIN, LIMA_LON_MAX = -77.5, -76.5
        
        for inst in instrucciones:
            if not (LIMA_LAT_MIN <= inst.lat_origen <= LIMA_LAT_MAX):
                logger.warning(f"Latitud origen fuera de rango Lima en paso {inst.paso}")
            if not (LIMA_LON_MIN <= inst.lon_origen <= LIMA_LON_MAX):
                logger.warning(f"Longitud origen fuera de rango Lima en paso {inst.paso}")
        
        # Verificar que distancias son positivas
        for inst in instrucciones:
            if inst.distancia_km < 0:
                return {
                    'valido': False,
                    'mensaje': f"Distancia negativa en paso {inst.paso}"
                }
        
        # Calcular distancia total de instrucciones
        distancia_total = sum(inst.distancia_km for inst in instrucciones)
        
        resultado = {
            'valido': True,
            'mensaje': f"Validación exitosa de {len(instrucciones)} instrucciones",
            'distancia_instrucciones': distancia_total
        }
        
        # Validar consistencia con distancia esperada
        if distancia_total_esperada is not None:
            diferencia = abs(distancia_total - distancia_total_esperada)
            diferencia_porcentaje = (diferencia / distancia_total_esperada * 100) if distancia_total_esperada > 0 else 0
            
            resultado['diferencia'] = diferencia
            resultado['diferencia_porcentaje'] = diferencia_porcentaje
            
            if diferencia_porcentaje > 5:  # Margen de error: 5%
                resultado['mensaje'] = f"Diferencia en distancia: {diferencia:.2f} km ({diferencia_porcentaje:.1f}%)"
        
        logger.info(resultado['mensaje'])
        return resultado
    
    def exportar_instrucciones_texto(self, instrucciones: List[InstruccionRuta]) -> str:
        """
        Exporta instrucciones a formato de texto plano para descargar
        
        Args:
            instrucciones: Lista de instrucciones generadas
            
        Returns:
            String con instrucciones formateadas para archivo .txt
        """
        lineas = []
        lineas.append("=" * 70)
        lineas.append("GUÍA DE RUTA DETALLADA - FLORAROUTE")
        lineas.append("=" * 70)
        lineas.append("")
        
        total_distancia = sum(inst.distancia_km for inst in instrucciones)
        lineas.append(f"Distancia Total: {total_distancia:.2f} km")
        lineas.append(f"Total de Pasos: {len(instrucciones)}")
        lineas.append("")
        lineas.append("-" * 70)
        lineas.append("")
        
        for inst in instrucciones:
            lineas.append(f"PASO {inst.paso}")
            lineas.append(f"  Dirección: {inst.direccion}")
            lineas.append(f"  Instrucción: {inst.instruccion}")
            lineas.append(f"  Distancia: {inst.distancia_km:.2f} km")
            lineas.append(f"  Desde nodo {inst.nodo_origen} → Hacia nodo {inst.nodo_destino}")
            lineas.append("")
        
        lineas.append("-" * 70)
        lineas.append(f"FIN DE RUTA - Total: {total_distancia:.2f} km")
        lineas.append("=" * 70)
        
        return "\n".join(lineas)
    
    def visualizar_en_mapa(self, instrucciones: List[InstruccionRuta], 
                          center: Optional[Tuple[float, float]] = None):
        """
        Visualiza instrucciones de ruta en mapa interactivo con Folium
        
        Args:
            instrucciones: Lista de instrucciones generadas
            center: Tupla (lat, lon) para centrar el mapa (opcional)
            
        Returns:
            Objeto folium.Map con la ruta y marcadores
        """
        try:
            import folium
        except ImportError:
            logger.error("Folium no instalado. Ejecutar: pip install folium")
            return None
        
        if not instrucciones:
            logger.warning("No hay instrucciones para visualizar")
            return None
        
        # Determinar centro del mapa
        if center is None:
            # Usar primera instruccion como centro
            center = (instrucciones[0].lat_origen, instrucciones[0].lon_origen)
        
        # Crear mapa
        mapa = folium.Map(location=center, zoom_start=13, tiles="OpenStreetMap")
        
        # Coordenadas de la ruta completa
        coordenadas_ruta = []
        
        # Agregar marcadores y construir polyline
        for i, inst in enumerate(instrucciones):
            # Agregar coordenada origen al path
            if i == 0:
                coordenadas_ruta.append([inst.lat_origen, inst.lon_origen])
            
            # Agregar coordenada destino
            coordenadas_ruta.append([inst.lat_destino, inst.lon_destino])
            
            # Marcador en cada punto de instruccion
            color = 'green' if i == 0 else 'red' if i == len(instrucciones) - 1 else 'blue'
            
            folium.Marker(
                [inst.lat_destino, inst.lon_destino],
                popup=f"<b>Paso {inst.paso}</b><br>{inst.direccion}<br>{inst.instruccion}",
                tooltip=f"Paso {inst.paso}: {inst.direccion}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(mapa)
        
        # Dibujar polyline de la ruta
        if len(coordenadas_ruta) > 1:
            folium.PolyLine(
                coordenadas_ruta,
                color='blue',
                weight=4,
                opacity=0.7,
                tooltip=f"Ruta completa ({len(instrucciones)} pasos)"
            ).add_to(mapa)
        
        logger.info(f"Mapa generado con {len(instrucciones)} instrucciones")
        return mapa
