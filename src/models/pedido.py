"""
Modelo de datos para Pedido y Destino
"""

from typing import Dict, List, Optional


class Destino:
    """Modelo de un punto de entrega"""
    
    def __init__(self, destino_id: int, nodo_id: int, 
                 lat: float, lon: float,
                 flores_requeridas: Dict[str, int],
                 prioridad: int = 1):
        """
        Args:
            destino_id: Identificador unico
            nodo_id: ID del nodo en el grafo
            lat: Latitud
            lon: Longitud
            flores_requeridas: Diccionario {tipo_flor: cantidad}
            prioridad: Nivel de prioridad (1=alta, 2=media, 3=baja)
        """
        self.destino_id = destino_id
        self.nodo_id = nodo_id
        self.lat = lat
        self.lon = lon
        self.flores_requeridas = flores_requeridas
        self.prioridad = prioridad
    
    def validar_coordenadas(self) -> bool:
        """Valida que las coordenadas esten en rango de Lima"""
        return (-12.3 <= self.lat <= -11.7 and -77.2 <= self.lon <= -76.8)
    
    def __repr__(self):
        return f"Destino({self.destino_id}, nodo={self.nodo_id}, lat={self.lat:.4f}, lon={self.lon:.4f})"


class Pedido:
    """Modelo de pedido con multiples destinos"""
    
    def __init__(self, pedido_id: int, vivero_origen_id: int):
        """
        Args:
            pedido_id: Identificador unico del pedido
            vivero_origen_id: ID del vivero de origen
        """
        self.pedido_id = pedido_id
        self.vivero_origen_id = vivero_origen_id
        self.destinos: List[Destino] = []
    
    def agregar_destino(self, destino: Destino) -> bool:
        """
        Agrega un destino al pedido
        
        Returns:
            True si se agrego exitosamente, False si excede limite
        """
        if len(self.destinos) >= 20:
            return False
        
        if not destino.validar_coordenadas():
            return False
        
        self.destinos.append(destino)
        return True
    
    def eliminar_destino(self, destino_id: int) -> bool:
        """
        Elimina un destino por ID
        
        Returns:
            True si se elimino, False si no se encontro
        """
        for i, destino in enumerate(self.destinos):
            if destino.destino_id == destino_id:
                self.destinos.pop(i)
                return True
        return False
    
    def editar_destino(self, destino_id: int, nueva_lat: float, nueva_lon: float) -> bool:
        """
        Edita las coordenadas de un destino
        
        Returns:
            True si se edito, False si no se encontro o coordenadas invalidas
        """
        for destino in self.destinos:
            if destino.destino_id == destino_id:
                # Validar nuevas coordenadas
                if not (-12.3 <= nueva_lat <= -11.7 and -77.2 <= nueva_lon <= -76.8):
                    return False
                destino.lat = nueva_lat
                destino.lon = nueva_lon
                return True
        return False
    
    def obtener_destino(self, destino_id: int) -> Optional[Destino]:
        """Obtiene un destino por ID"""
        for destino in self.destinos:
            if destino.destino_id == destino_id:
                return destino
        return None
    
    def cantidad_destinos(self) -> int:
        """Retorna el numero de destinos"""
        return len(self.destinos)
    
    def validar_rango(self) -> bool:
        """Valida que haya entre 1 y 20 destinos"""
        return 1 <= len(self.destinos) <= 20
    
    def __repr__(self):
        """ Representacion del pedido """
        return f"Pedido({self.pedido_id}, origen={self.vivero_origen_id}, destinos={len(self.destinos)})"
