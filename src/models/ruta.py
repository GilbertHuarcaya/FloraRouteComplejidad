"""
Modelo de datos para Ruta calculada
"""

from typing import List, Dict, Optional
from datetime import datetime


class Ruta:
    """Modelo de ruta calculada con metricas"""
    
    def __init__(self, ruta_id: int, origen_nodo: int, 
                 secuencia_visitas: List[int],
                 distancia_total: float = 0.0,
                 tiempo_total: float = 0.0):
        """
        Args:
            ruta_id: Identificador unico
            origen_nodo: Nodo de origen (vivero)
            secuencia_visitas: Lista ordenada de nodos a visitar
            distancia_total: Distancia en kilometros
            tiempo_total: Tiempo en minutos
        """
        self.ruta_id = ruta_id
        self.origen_nodo = origen_nodo
        self.secuencia_visitas = secuencia_visitas
        self.distancia_total = distancia_total
        self.tiempo_total = tiempo_total
        self.fecha_calculo = datetime.now()
        self.tiempo_computo = 0.0  # Tiempo de calculo en segundos
        self.camino_completo: List[int] = []  # Nodos intermedios
        self.metricas_segmentos: List[Dict] = []  # Metricas por segmento
    
    def calcular_metricas(self):
        """Calcula metricas derivadas"""
        if len(self.secuencia_visitas) > 1:
            # Verificar si retorna al origen (último nodo == primer nodo)
            retorna_origen = (self.secuencia_visitas[-1] == self.secuencia_visitas[0])
            
            if retorna_origen:
                # El último nodo es retorno, no es una parada de entrega
                # Número de paradas = longitud - 2 (sin origen inicial ni retorno final)
                self.numero_paradas = len(self.secuencia_visitas) - 2
            else:
                # Sin retorno: Número de paradas = longitud - 1 (sin contar origen)
                self.numero_paradas = len(self.secuencia_visitas) - 1
            
            self.distancia_promedio_parada = self.distancia_total / self.numero_paradas if self.numero_paradas > 0 else 0
            self.tiempo_promedio_parada = self.tiempo_total / self.numero_paradas if self.numero_paradas > 0 else 0
        else:
            self.numero_paradas = 0
            self.distancia_promedio_parada = 0
            self.tiempo_promedio_parada = 0
    
    def agregar_segmento(self, desde_nodo: int, hasta_nodo: int, 
                        distancia: float, tiempo: float):
        """Agrega metricas de un segmento de la ruta"""
        self.metricas_segmentos.append({
            'desde': desde_nodo,
            'hasta': hasta_nodo,
            'distancia_km': distancia,
            'tiempo_min': tiempo
        })
    
    def exportar_orden_visitas(self) -> List[Dict]:
        """
        Exporta orden de visitas con metricas
        
        Returns:
            Lista de diccionarios con informacion de cada parada
        """
        orden = []
        retorna_origen = len(self.secuencia_visitas) > 1 and (self.secuencia_visitas[-1] == self.secuencia_visitas[0])
        
        for i, nodo in enumerate(self.secuencia_visitas):
            es_retorno = retorna_origen and (i == len(self.secuencia_visitas) - 1)
            
            parada = {
                'orden': i + 1,
                'nodo_id': nodo,
                'es_origen': (i == 0),
                'es_retorno': es_retorno
            }
            
            # CORRECCION: Las metricas del segmento [i-1 -> i] deben mostrarse en la fila i
            # El segmento 0 va de nodo[0] a nodo[1], debe aparecer en fila de nodo[1]
            if i == 0:
                # Primer nodo (origen): sin distancia
                parada['distancia_desde_anterior_km'] = 0.0
                parada['tiempo_desde_anterior_min'] = 0.0
            elif i <= len(self.metricas_segmentos):
                # Para el nodo i, usar el segmento i-1 (que va desde nodo[i-1] hasta nodo[i])
                segmento = self.metricas_segmentos[i - 1]
                parada['distancia_desde_anterior_km'] = segmento['distancia_km']
                parada['tiempo_desde_anterior_min'] = segmento['tiempo_min']
            else:
                parada['distancia_desde_anterior_km'] = 0.0
                parada['tiempo_desde_anterior_min'] = 0.0
            
            orden.append(parada)
        
        return orden
    
    def obtener_resumen(self) -> Dict:
        """
        Obtiene resumen de la ruta
        
        Returns:
            Diccionario con metricas principales
        """
        self.calcular_metricas()
        
        return {
            'ruta_id': self.ruta_id,
            'origen_nodo': self.origen_nodo,
            'numero_paradas': self.numero_paradas,
            'distancia_total_km': round(self.distancia_total, 2),
            'tiempo_total_min': round(self.tiempo_total, 2),
            'distancia_promedio_parada_km': round(self.distancia_promedio_parada, 2),
            'tiempo_promedio_parada_min': round(self.tiempo_promedio_parada, 2),
            'tiempo_computo_s': round(self.tiempo_computo, 3),
            'fecha_calculo': self.fecha_calculo.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f"Ruta({self.ruta_id}, paradas={self.numero_paradas}, dist={self.distancia_total:.2f}km, tiempo={self.tiempo_total:.2f}min)"
