"""
Modelo de datos para Vivero
"""

from typing import Dict, Optional, Any


class Inventario:
    """Inventario de flores en un vivero"""
    
    def __init__(self, stock_flores: Dict[str, int]):
        """
        Args:
            stock_flores: Diccionario {tipo_flor: cantidad}
        """
        self.stock = stock_flores.copy()
    
    def tiene_stock(self, flores_requeridas: Dict[str, int]) -> bool:
        """Verifica si hay stock suficiente"""
        for flor, cantidad in flores_requeridas.items():
            if self.stock.get(flor, 0) < cantidad:
                return False
        return True
    
    def reducir_stock(self, flores_requeridas: Dict[str, int]):
        """Reduce el stock segun lo requerido"""
        for flor, cantidad in flores_requeridas.items():
            if flor in self.stock:
                self.stock[flor] = max(0, self.stock[flor] - cantidad)
    
    def obtener_stock(self, tipo_flor: str) -> int:
        """Retorna stock de un tipo de flor"""
        return self.stock.get(tipo_flor, 0)

    def esta_agotado(self) -> bool:
        """Retorna True si algun tipo de flor esta agotado (stock == 0)"""
        for cantidad in self.stock.values():
            if cantidad <= 0:
                return True
        return False


class Vivero:
    """Modelo de vivero con ubicacion e inventario"""
    
    def __init__(self, vivero_id: int, nombre: str, nodo_id: int, 
                 lat: float, lon: float, inventario: Inventario,
                 capacidad_entrega: int = 100,
                 horario_inicio: str = "08:00",
                 horario_fin: str = "18:00"):
        """
        Args:
            vivero_id: Identificador unico
            nombre: Nombre del vivero
            nodo_id: ID del nodo en el grafo
            lat: Latitud
            lon: Longitud
            inventario: Objeto Inventario
            capacidad_entrega: Capacidad maxima de entregas por dia
            horario_inicio: Hora de apertura (HH:MM)
            horario_fin: Hora de cierre (HH:MM)
        """
        self.vivero_id = vivero_id
        self.nombre = nombre
        self.nodo_id = nodo_id
        self.lat = lat
        self.lon = lon
        self.inventario = inventario
        self.capacidad_entrega = capacidad_entrega
        self.horario_inicio = horario_inicio
        self.horario_fin = horario_fin
    
    def validar_en_grafo(self, grafo: Dict[int, Dict[int, float]]) -> bool:
        """Valida que el nodo_id exista en el grafo
        
        Args:
            grafo: Diccionario de adyacencia {nodo: {vecino: peso}}
            
        Returns:
            bool: True si el nodo existe en el grafo
        """
        return self.nodo_id in grafo
    
    def puede_entregar(self, flores_requeridas: Dict[str, int]) -> bool:
        """Verifica si puede entregar las flores requeridas"""
        return self.inventario.tiene_stock(flores_requeridas)
    
    def __repr__(self):
        return f"Vivero({self.vivero_id}, {self.nombre}, nodo={self.nodo_id})"
