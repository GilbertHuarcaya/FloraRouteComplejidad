#!/usr/bin/env python3
"""
Extractor de Red Vial
Extrae la red de calles de Lima usando OSMnx
"""
import pandas as pd
import osmnx as ox
import math
import random
import warnings

warnings.filterwarnings('ignore')

class NetworkExtractor:
    """Extractor de red vial de Lima"""
    
    def __init__(self):
        self._configure_osmnx()
    
    def _configure_osmnx(self):
        # Configurar OSMnx
        try:
            ox.settings.log_console = False
            ox.settings.use_cache = True
        except AttributeError:
            pass
    
    def extract_lima_network(self):
        """Extraer red vial de Lima"""
        print("Descargando red vial de Lima...")
        
        try:
            # Método 1: Lima Metropolitana completa
            try:
                G = ox.graph_from_place(
                    "Lima Metropolitan Area, Peru",
                    network_type='drive',
                    simplify=True
                )
                print(f"Red extraída: {len(G.nodes)} nodos, {len(G.edges)} aristas")
            except:
                # Método 2: Por coordenadas de Lima
                print("Usando coordenadas de Lima...")
                north, south, east, west = -11.8, -12.3, -76.8, -77.3
                G = ox.graph_from_bbox(
                    north=north, south=south, east=east, west=west,
                    network_type='drive', simplify=True
                )
                print(f"Red extraída: {len(G.nodes)} nodos, {len(G.edges)} aristas")
            
            # Mejorar conectividad si hay muchas componentes
            components = self._find_components(G)
            if len(components) > 5:
                self._improve_connectivity(G)
            
            # Convertir a DataFrames
            nodes_df, edges_df = self._to_dataframes(G)
            
            # Guardar archivos
            nodes_df.to_csv("dataset/lima_nodes.csv", index=False)
            edges_df.to_csv("dataset/lima_edges.csv", index=False)
            
            print(f"Archivos guardados:")
            print(f"  dataset/lima_nodes.csv ({len(nodes_df)} nodos)")
            print(f"  dataset/lima_edges.csv ({len(edges_df)} aristas)")
            
            return True
            
        except Exception as e:
            print(f"Error en extracción: {str(e)}")
            return False
    
    def _find_components(self, G):
        # Encontrar componentes conectados usando DFS
        all_nodes = list(G.nodes())
        visited = set()
        components = []
        
        for start_node in all_nodes:
            if start_node in visited:
                continue
            
            component = set()
            stack = [start_node]
            
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                
                component.add(node)
                visited.add(node)
                
                # Agregar vecinos
                try:
                    neighbors = list(G.neighbors(node))
                    for neighbor in neighbors:
                        if neighbor not in component:
                            stack.append(neighbor)
                except:
                    pass
            
            if component:
                components.append(component)
        
        return components
    
    def _improve_connectivity(self, G):
        # Conectar componentes desconectados
        print("Mejorando conectividad...")
        
        components = self._find_components(G)
        print(f"Componentes encontrados: {len(components)}")
        
        if len(components) <= 1:
            return
        
        # Conectar componentes más grandes
        components = sorted(components, key=len, reverse=True)
        main_component = components[0]
        
        connections_added = 0
        for component in components[1:]:
            if connections_added >= 50:  # Límite de conexiones
                break
            
            # Encontrar conexión más cercana
            best_connection = self._find_best_connection(G, main_component, component)
            
            if best_connection:
                node1, node2, distance = best_connection
                if distance <= 5000:  # Máximo 5km
                    G.add_edge(node1, node2, length=distance)
                    G.add_edge(node2, node1, length=distance)
                    main_component.update(component)
                    connections_added += 1
        
        print(f"Conexiones agregadas: {connections_added}")
    
    def _find_best_connection(self, G, comp1, comp2):
        # Encuentra la mejor conexión entre dos componentes
        best_distance = float('inf')
        best_connection = None
        
        # Muestrear para eficiencia
        sample1 = random.sample(list(comp1), min(20, len(comp1)))
        sample2 = random.sample(list(comp2), min(20, len(comp2)))
        
        for node1 in sample1:
            for node2 in sample2:
                distance = self._calculate_distance(G, node1, node2)
                if distance < best_distance:
                    best_distance = distance
                    best_connection = (node1, node2, distance)
        
        return best_connection
    
    def _calculate_distance(self, G, node1, node2):
        # Calcular distancia haversine entre nodos
        try:
            data1 = G.nodes[node1]
            data2 = G.nodes[node2]
            
            lat1 = data1.get('y', data1.get('lat'))
            lon1 = data1.get('x', data1.get('lon'))
            lat2 = data2.get('y', data2.get('lat'))
            lon2 = data2.get('x', data2.get('lon'))
            
            if None in [lat1, lon1, lat2, lon2]:
                return float('inf')
            
            # Fórmula de haversine
            R = 6371000  # Radio de la Tierra en metros
            lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
            lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = (math.sin(dlat/2)**2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
            
            distance = 2 * R * math.asin(math.sqrt(a))
            return distance
            
        except Exception:
            return float('inf')
    
    def _to_dataframes(self, G):
        # Convertir grafo a DataFrames
        print("Convirtiendo a DataFrames...")
        
        # Nodos
        nodes_data = []
        node_mapping = {}
        
        for idx, (node_id, data) in enumerate(G.nodes(data=True)):
            lat = data.get('y', data.get('lat'))
            lon = data.get('x', data.get('lon'))
            
            if lat is not None and lon is not None:
                nodes_data.append({
                    'node_id': idx,
                    'osm_id': node_id,
                    'lat': lat,
                    'lon': lon
                })
                node_mapping[node_id] = idx
        
        nodes_df = pd.DataFrame(nodes_data)
        
        # Aristas
        edges_data = []
        for u, v, data in G.edges(data=True):
            if u in node_mapping and v in node_mapping:
                length = data.get('length', 100.0)
                if length <= 0:
                    length = self._calculate_distance(G, u, v)
                    if length == float('inf'):
                        length = 100.0
                
                edges_data.append({
                    'node1': node_mapping[u],
                    'node2': node_mapping[v],
                    'distance': length
                })
        
        edges_df = pd.DataFrame(edges_data)
        
        return nodes_df, edges_df