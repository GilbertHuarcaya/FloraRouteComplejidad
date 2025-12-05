"""
Modulo: cargador_datos.py
Descripcion: Carga datos desde CSVs (lima_nodes, lima_edges, viveros, trafico)
"""

import csv
import os
import pandas as pd
from typing import Dict, Tuple
from datetime import datetime


def cargar_grafo_lima() -> Tuple[Dict[int, Dict[int, float]], Dict[int, Tuple[float, float]]]:
    """
    Construye grafo desde lima_nodes.csv y lima_edges.csv
    
    Returns:
        Tupla (grafo_dict, nodos_coords)
        - grafo_dict: {nodo: {vecino: distancia}}
        - nodos_coords: {nodo_id: (lat, lon)}
    """
    ruta_nodos = 'dataset/lima_nodes.csv'
    ruta_aristas = 'dataset/lima_edges.csv'
    
    if not os.path.exists(ruta_nodos):
        raise FileNotFoundError(f"No encontrado: {ruta_nodos}")
    if not os.path.exists(ruta_aristas):
        raise FileNotFoundError(f"No encontrado: {ruta_aristas}")
    
    # Cargar nodos con coordenadas
    nodos_coords = {}
    with open(ruta_nodos, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for fila in reader:
            nodo_id = int(fila['node_id'])
            lat = float(fila['lat'])
            lon = float(fila['lon'])
            nodos_coords[nodo_id] = (lat, lon)
    
    # Construir grafo (diccionario de adyacencia) - estilo examples-guide
    grafo = {}
    with open(ruta_aristas, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for fila in reader:
            node1 = int(fila['node1'])
            node2 = int(fila['node2'])
            distancia = float(fila['distance'])
            
            if node1 not in nodos_coords or node2 not in nodos_coords:
                continue
            
            # Grafo no dirigido
            if node1 not in grafo:
                grafo[node1] = {}
            if node2 not in grafo:
                grafo[node2] = {}
            
            grafo[node1][node2] = distancia
            grafo[node2][node1] = distancia
    
    print(f"[OK] Grafo: {len(nodos_coords)} nodos, {len(grafo)} con aristas")
    return grafo, nodos_coords


def cargar_viveros() -> pd.DataFrame:
    """Carga inventario de viveros desde CSV"""
    ruta = 'dataset/viveros.csv'
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No encontrado: {ruta}")
    return pd.read_csv(ruta)


def parsear_inventario(vivero_row: pd.Series) -> Dict[str, int]:
    """Convierte columnas de stock en diccionario"""
    return {
        'rosas': int(vivero_row.get('stock_rosas', 0)),
        'claveles': int(vivero_row.get('stock_claveles', 0)),
        'lirios': int(vivero_row.get('stock_lirios', 0)),
        'girasoles': int(vivero_row.get('stock_girasoles', 0)),
        'tulipanes': int(vivero_row.get('stock_tulipanes', 0))
    }


def cargar_factor_trafico() -> Dict[int, float]:
    """
    Factores de trafico por hora (Lima)
    
    Returns:
        Dict {hora: factor} donde factor: 1.0 (sin trafico) a 2.5 (trafico pesado)
    """
    factores = {
        0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.2,
        6: 1.8, 7: 2.3, 8: 2.5, 9: 1.9,
        10: 1.4, 11: 1.5, 12: 1.6, 13: 1.7, 14: 1.5,
        15: 1.6, 16: 1.8, 17: 2.2, 18: 2.5, 19: 2.3,
        20: 1.7, 21: 1.4, 22: 1.2, 23: 1.0
    }
    return factores


def obtener_factor_trafico_actual() -> float:
    """Obtiene factor de trafico segun hora actual"""
    hora_actual = datetime.now().hour
    factores = cargar_factor_trafico()
    return factores.get(hora_actual, 1.0)


def validar_vivero_en_grafo(nodo_id: int, grafo: Dict) -> bool:
    """Valida que el nodo del vivero exista en el grafo"""
    return nodo_id in grafo


def encontrar_nodo_cercano(lat: float, lon: float, nodos_coords: Dict[int, Tuple[float, float]]) -> int:
    """
    Encuentra el nodo del grafo mas cercano a unas coordenadas
    
    Args:
        lat: Latitud
        lon: Longitud
        nodos_coords: {nodo_id: (lat, lon)}
        
    Returns:
        ID del nodo mas cercano
    """
    mejor_nodo = None
    mejor_distancia = float('inf')
    
    for nodo_id, (n_lat, n_lon) in nodos_coords.items():
        dist = ((lat - n_lat)**2 + (lon - n_lon)**2)**0.5
        if dist < mejor_distancia:
            mejor_distancia = dist
            mejor_nodo = nodo_id
    
    if mejor_nodo is None:
        raise ValueError("No se encontro nodo cercano")
    
    return mejor_nodo
