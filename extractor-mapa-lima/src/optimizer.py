#!/usr/bin/env python3
"""
Optimizer
Contiene funciones para exportar grafos y generar visualizaciones
"""
import pandas as pd
import json
import random
import folium

class GraphExporter:
    """Exportador de grafos para visualización"""
    
    def __init__(self, nodes_file, edges_file):
        self.nodes_file = nodes_file
        self.edges_file = edges_file
        self.nodes_df = None
        self.edges_df = None
        self.graph = None
        self._load_data()
    
    def _load_data(self):
        # Cargar datos de red
        try:
            self.nodes_df = pd.read_csv(self.nodes_file)
            self.edges_df = pd.read_csv(self.edges_file)
            self.nodes_df.columns = self.nodes_df.columns.str.strip()
            self.edges_df.columns = self.edges_df.columns.str.strip()
            print(f"Red cargada: {len(self.nodes_df)} nodos, {len(self.edges_df)} aristas")
            self._build_graph()
        except FileNotFoundError:
            raise FileNotFoundError("Archivos de red no encontrados")
        except Exception as e:
            raise Exception(f"Error cargando red: {str(e)}")
    
    def _build_graph(self):
        # Construir grafo de adyacencia
        self.graph = {int(row['node_id']): [] for _, row in self.nodes_df.iterrows()}
        
        for _, row in self.edges_df.iterrows():
            u = int(row['node1'])
            v = int(row['node2'])
            weight = float(row['distance'])
            
            if u in self.graph:
                self.graph[u].append((v, weight))
            if v in self.graph:
                self.graph[v].append((u, weight))
    
    def export_for_graphviz(self, filename_prefix="graph", mode="reduced", target_nodes=1500):
        """Exportar grafo a formato DOT y JSON"""
        
        # Determinar nodos conectados
        nodes_in_edges = set()
        for _, row in self.edges_df.iterrows():
            try:
                u = int(row['node1'])
                v = int(row['node2'])
            except:
                continue
            nodes_in_edges.add(u)
            nodes_in_edges.add(v)
        
        # Seleccionar subconjunto de nodos según el modo
        if mode == "reduced" and len(nodes_in_edges) > target_nodes:
            selected_nodes = self._select_connected_subgraph(nodes_in_edges, target_nodes)
        else:
            selected_nodes = nodes_in_edges
        
        print(f"Exportando {len(selected_nodes)} nodos...")
        
        # Generar archivos DOT y JSON
        dot_path = f"{filename_prefix}.dot"
        json_path = f"{filename_prefix}.json"
        
        # Archivo DOT
        with open(dot_path, 'w', encoding='utf-8') as f:
            f.write("graph G {\n")
            f.write("  node [shape=circle, style=filled, fillcolor=lightblue];\n")
            f.write("  edge [color=gray];\n")
            
            # Escribir aristas
            written_edges = set()
            for _, row in self.edges_df.iterrows():
                u, v = int(row['node1']), int(row['node2'])
                if u in selected_nodes and v in selected_nodes:
                    edge_key = tuple(sorted([u, v]))
                    if edge_key not in written_edges:
                        weight = int(row['distance'])
                        f.write(f"  {u} -- {v} [label=\"{weight}m\", weight={weight}];\n")
                        written_edges.add(edge_key)
            
            f.write("}\n")
        
        # Archivo JSON de adyacencia
        adjacency = {}
        for node in selected_nodes:
            adjacency[str(node)] = []
            if node in self.graph:
                for neighbor, weight in self.graph[node]:
                    if neighbor in selected_nodes:
                        adjacency[str(node)].append({str(neighbor): weight})
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(adjacency, f, indent=2, ensure_ascii=False)
        
        print(f"Archivos generados:")
        print(f"  {dot_path} - Archivo DOT para Graphviz")
        print(f"  {json_path} - Archivo JSON de adyacencia")
        
        return dot_path, json_path
    
    def _select_connected_subgraph(self, nodes_set, target_nodes):
        # Seleccionar subgrafo conectado comenzando desde un nodo aleatorio
        if not nodes_set:
            return set()
        
        # Comenzar desde un nodo aleatorio
        start_node = random.choice(list(nodes_set))
        selected = set()
        queue = [start_node]
        
        while queue and len(selected) < target_nodes:
            node = queue.pop(0)
            if node in selected:
                continue
            
            selected.add(node)
            
            # Agregar vecinos no visitados
            if node in self.graph:
                neighbors = [neighbor for neighbor, _ in self.graph[node]]
                random.shuffle(neighbors)  # Aleatorizar para diversidad
                for neighbor in neighbors:
                    if neighbor in nodes_set and neighbor not in selected and len(selected) < target_nodes:
                        queue.append(neighbor)
        
        return selected
    
    def create_map_from_json(self, json_file):
        """Crear mapa HTML desde archivo JSON de adyacencia"""
        
        if not json_file.endswith('.json'):
            json_file += '.json'
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                adjacency = json.load(f)
        except FileNotFoundError:
            print(f"Archivo JSON no encontrado: {json_file}")
            return False
        
        # Obtener coordenadas de nodos
        coords = {}
        for node_str in adjacency.keys():
            try:
                nid = int(node_str)
                row = self.nodes_df[self.nodes_df['node_id'] == nid]
                if not row.empty:
                    lat = float(row.iloc[0]['lat'])
                    lon = float(row.iloc[0]['lon'])
                    coords[node_str] = (lat, lon)
            except:
                continue
        
        if not coords:
            print("No se encontraron coordenadas para los nodos")
            return False
        
        # Crear mapa centrado
        lats = [c[0] for c in coords.values()]
        lons = [c[1] for c in coords.values()]
        center = [sum(lats) / len(lats), sum(lons) / len(lons)]
        
        # Generar mapa con folium
        route_map = folium.Map(location=center, zoom_start=12, tiles='OpenStreetMap')
        
        # Dibujar aristas
        drawn_edges = set()
        for u_str, neighbors in adjacency.items():
            if u_str not in coords:
                continue
            for neighbor_data in neighbors:
                for v_str, weight in neighbor_data.items():
                    if v_str not in coords:
                        continue
                    
                    edge_key = tuple(sorted([u_str, v_str]))
                    if edge_key in drawn_edges:
                        continue
                    drawn_edges.add(edge_key)
                    
                    lat1, lon1 = coords[u_str]
                    lat2, lon2 = coords[v_str]
                    folium.PolyLine(
                        locations=[(lat1, lon1), (lat2, lon2)],
                        color='blue',
                        weight=2,
                        opacity=0.8
                    ).add_to(route_map)
        
        # Agregar marcadores para nodos
        for nid, (lat, lon) in coords.items():
            folium.CircleMarker(
                location=(lat, lon),
                radius=3,
                color='blue',
                fill=True,
                fillOpacity=0.7,
                popup=f"Nodo: {nid}"
            ).add_to(route_map)
        
        # Guardar mapa
        map_path = json_file.replace('.json', '_map.html')
        route_map.save(map_path)
        print(f"Mapa generado: {map_path}")
        
        return True