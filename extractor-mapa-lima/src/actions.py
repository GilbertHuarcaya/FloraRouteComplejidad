#!/usr/bin/env python3
"""
Actions - Funciones principales del sistema
"""
import os
import subprocess
import json
import pandas as pd
from src.extractor import NetworkExtractor
from src.optimizer import GraphExporter

def extraer_red_vial():
    """Extraer red vial de Lima usando OSMnx"""
    print("\nExtrayendo red vial de Lima...")
    print("=" * 50)
    
    try:
        extractor = NetworkExtractor()
        success = extractor.extract_lima_network()
        
        if success:
            print("Red vial extraída exitosamente")
            return True
        else:
            print("Error en la extracción")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def exportar_grafo_graphviz():
    """Exportar grafo para Graphviz (DOT + JSON)"""
    print("\nExportando grafo para Graphviz...")
    print("=" * 50)
    
    nodes_file = "dataset/lima_nodes.csv"
    edges_file = "dataset/lima_edges.csv"
    
    if not os.path.exists(nodes_file) or not os.path.exists(edges_file):
        print("Archivos de red no encontrados")
        print("Ejecuta primero la opción 1 (Extraer Red Vial)")
        return False
    
    try:
        # Configuración
        mode = input("Modo ('full' o 'reduced', default='reduced'): ").strip().lower()
        if mode not in ("full", "reduced"):
            mode = "reduced"
        
        prefix = input("Prefijo de archivo (default='graph'): ").strip()
        if not prefix:
            prefix = "graph"
        
        try:
            nodes = int(input("Número de nodos objetivo (default=1500): ").strip() or "1500")
            if nodes < 1:
                nodes = 1500
        except ValueError:
            nodes = 1500
        
        print(f"Exportando en modo '{mode}' con {nodes} nodos objetivo...")
        
        # Exportar
        exporter = GraphExporter(nodes_file, edges_file)
        dot_path, json_path = exporter.export_for_graphviz(
            filename_prefix=prefix,
            mode=mode,
            target_nodes=nodes
        )
        
        if dot_path and json_path:
            print(f"\nArchivos generados exitosamente:")
            print(f"  {dot_path}")
            print(f"  {json_path}")
            return True
        else:
            print("Error generando archivos")
            return False
            
    except Exception as e:
        print(f"Error exportando grafo: {e}")
        return False

def generar_png_desde_dot():
    """Generar PNG desde archivo DOT usando Graphviz"""
    print("\nGenerando PNG desde DOT...")
    print("=" * 50)
    
    dot_path = input("Archivo DOT (default='graph.dot'): ").strip() or "graph.dot"
    
    if not os.path.exists(dot_path):
        print(f"Archivo DOT no encontrado: {dot_path}")
        print("Ejecuta primero la opción 2 (Exportar grafo)")
        return False
    
    png_path = os.path.splitext(dot_path)[0] + ".png"
    
    try:
        print(f"Generando {png_path}...")
        result = subprocess.run(
            ["dot", "-Tpng", dot_path, "-o", png_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"PNG generado exitosamente: {png_path}")
            return True
        else:
            print(f"Error generando PNG:")
            print(f"  Stdout: {result.stdout}")
            print(f"  Stderr: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("Graphviz 'dot' no está disponible en el PATH del sistema")
        print("Instala Graphviz desde: https://graphviz.org/download/")
        return False
    except Exception as e:
        print(f"Error ejecutando dot: {e}")
        return False

def crear_mapa_desde_json():
    """Crear mapa HTML desde archivo JSON de adyacencia"""
    print("\nCreando mapa HTML desde JSON...")
    print("=" * 50)
    
    json_path = input("Archivo JSON (default='graph.json'): ").strip() or "graph.json"
    
    if not os.path.exists(json_path):
        print(f"Archivo JSON no encontrado: {json_path}")
        print("Ejecuta primero la opción 2 (Exportar grafo)")
        return False
    
    nodes_file = "dataset/lima_nodes.csv"
    edges_file = "dataset/lima_edges.csv"
    
    if not os.path.exists(nodes_file):
        print("Archivo de nodos no encontrado")
        print("Ejecuta primero la opción 1 (Extraer Red Vial)")
        return False
    
    try:
        exporter = GraphExporter(nodes_file, edges_file)
        success = exporter.create_map_from_json(json_path)
        
        if success:
            print("Mapa HTML generado exitosamente")
            return True
        else:
            print("Error generando mapa")
            return False
            
    except Exception as e:
        print(f"Error creando mapa: {e}")
        return False