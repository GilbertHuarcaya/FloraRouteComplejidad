"""
Validaciones para RF-02 y datos de entrada
"""

from typing import Tuple, Optional


class ValidadorRutas:
    """Validador de datos para la aplicacion de rutas"""
    
    # Limites geograficos de Lima
    LAT_MIN = -12.3
    LAT_MAX = -11.7
    LON_MIN = -77.2
    LON_MAX = -76.8
    
    # Limites de destinos
    MIN_DESTINOS = 1
    MAX_DESTINOS = 20
    
    @staticmethod
    def validar_formato_coordenadas(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
        """
        Valida formato de coordenadas
        
        Args:
            lat: Latitud
            lon: Longitud
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        # Validar tipos
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return False, "Las coordenadas deben ser numeros"
        
        # Validar rango general
        if not (-90 <= lat <= 90):
            return False, f"Latitud fuera de rango: {lat}. Debe estar entre -90 y 90"
        
        if not (-180 <= lon <= 180):
            return False, f"Longitud fuera de rango: {lon}. Debe estar entre -180 y 180"
        
        return True, None
    
    @staticmethod
    def validar_rango_geografico_lima(lat: float, lon: float) -> Tuple[bool, Optional[str]]:
        """
        Valida que las coordenadas esten en el area de Lima
        
        Args:
            lat: Latitud
            lon: Longitud
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        # Primero validar formato
        formato_valido, error = ValidadorRutas.validar_formato_coordenadas(lat, lon)
        if not formato_valido:
            return False, error
        
        # Validar que este en Lima
        if not (ValidadorRutas.LAT_MIN <= lat <= ValidadorRutas.LAT_MAX):
            return False, f"Latitud fuera del area de Lima: {lat}. Debe estar entre {ValidadorRutas.LAT_MIN} y {ValidadorRutas.LAT_MAX}"
        
        if not (ValidadorRutas.LON_MIN <= lon <= ValidadorRutas.LON_MAX):
            return False, f"Longitud fuera del area de Lima: {lon}. Debe estar entre {ValidadorRutas.LON_MIN} y {ValidadorRutas.LON_MAX}"
        
        return True, None
    
    @staticmethod
    def validar_cantidad_destinos(cantidad: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que la cantidad de destinos este en rango
        
        Args:
            cantidad: Numero de destinos
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not isinstance(cantidad, int):
            return False, "La cantidad de destinos debe ser un numero entero"
        
        if cantidad < ValidadorRutas.MIN_DESTINOS:
            return False, f"Debe haber al menos {ValidadorRutas.MIN_DESTINOS} destino"
        
        if cantidad > ValidadorRutas.MAX_DESTINOS:
            return False, f"No se pueden agregar mas de {ValidadorRutas.MAX_DESTINOS} destinos"
        
        return True, None
    
    @staticmethod
    def validar_nodo_existe(nodo_id: int, grafo: dict) -> Tuple[bool, Optional[str]]:
        """
        Valida que un nodo exista en el grafo
        
        Args:
            nodo_id: ID del nodo
            grafo: Diccionario de adyacencia del grafo
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not isinstance(nodo_id, int):
            return False, "El ID del nodo debe ser un numero entero"
        
        if nodo_id not in grafo:
            return False, f"El nodo {nodo_id} no existe en el grafo"
        
        return True, None
    
    @staticmethod
    def validar_stock_flores(stock_disponible: dict, flores_requeridas: dict) -> Tuple[bool, Optional[str]]:
        """
        Valida que haya stock suficiente de flores
        
        Args:
            stock_disponible: Diccionario {tipo_flor: cantidad_disponible}
            flores_requeridas: Diccionario {tipo_flor: cantidad_requerida}
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        for flor, cantidad_req in flores_requeridas.items():
            cantidad_disp = stock_disponible.get(flor, 0)
            
            if cantidad_disp < cantidad_req:
                return False, f"Stock insuficiente de {flor}: disponible={cantidad_disp}, requerido={cantidad_req}"
        
        return True, None
    
    @staticmethod
    def validar_capacidad_entrega(cantidad_destinos: int, capacidad_maxima: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que la cantidad de destinos no exceda la capacidad de entrega
        
        Args:
            cantidad_destinos: Numero de destinos en el pedido
            capacidad_maxima: Capacidad maxima de entregas del vivero
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if cantidad_destinos > capacidad_maxima:
            return False, f"La cantidad de destinos ({cantidad_destinos}) excede la capacidad de entrega del vivero ({capacidad_maxima})"
        
        return True, None
