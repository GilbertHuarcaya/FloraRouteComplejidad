"""
Script de demostracion para GeneradorGuiaRuta

Muestra como generar instrucciones turn-by-turn desde una ruta calculada
"""

import sys
import logging
from src.utils.cargador_datos import cargar_grafo_lima
from src.controllers.calculador_rutas import CalculadorRutas
from src.controllers.generador_guia_ruta import GeneradorGuiaRuta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_basica():
    """Demostracion basica del generador de guia de ruta"""
    
    print("=" * 80)
    print("DEMO: Generador de Guía de Ruta - FloraRoute")
    print("=" * 80)
    print()
    
    # 1. Cargar grafo de Lima
    print("📊 Cargando grafo de Lima...")
    grafo, nodos_coords = cargar_grafo_lima()
    print(f"✅ Grafo cargado: {len(grafo)} nodos, {len(nodos_coords)} coordenadas")
    print()
    
    # 2. Seleccionar nodos de ejemplo para la ruta
    # Usaremos nodos aleatorios del grafo para crear una ruta de prueba
    nodos_disponibles = list(grafo.keys())[:100]  # Primeros 100 nodos
    
    # Origen y destinos de ejemplo
    origen = nodos_disponibles[0]
    destinos = nodos_disponibles[10:15]  # 5 destinos
    
    print(f"🎯 Configuración de ruta:")
    print(f"   Origen: Nodo {origen}")
    print(f"   Destinos: {destinos}")
    print()
    
    # 3. Calcular ruta optima con TSP
    print("🧮 Calculando ruta óptima con Held-Karp (TSP)...")
    calculador = CalculadorRutas(grafo, factor_trafico=1.2)
    
    # Precalcular matriz de distancias
    nodos_interes = [origen] + destinos
    calculador.precalcular_matriz_distancias(nodos_interes)
    
    # Calcular TSP
    distancia_total, secuencia_optima = calculador.calcular_ruta_tsp(
        origen, 
        destinos, 
        retornar_origen=True
    )
    
    print(f"✅ Ruta calculada:")
    print(f"   Secuencia: {secuencia_optima}")
    print(f"   Distancia total: {distancia_total/1000:.2f} km")
    print()
    
    # 4. Calcular camino completo nodo por nodo
    print("🛣️  Calculando camino completo (nodo por nodo)...")
    camino_completo, distancia_real = calculador.calcular_camino_completo(secuencia_optima)
    print(f"✅ Camino completo: {len(camino_completo)} nodos")
    print(f"   Primeros 10 nodos: {camino_completo[:10]}")
    print(f"   Distancia real: {distancia_real/1000:.2f} km")
    print()
    
    # 5. Generar instrucciones de navegacion
    print("🧭 Generando instrucciones de navegación...")
    generador = GeneradorGuiaRuta(grafo, nodos_coords)
    
    # Generar guia con el camino completo (muchos nodos)
    # Para hacerlo mas legible, usamos solo algunos segmentos
    camino_simplificado = camino_completo[::max(1, len(camino_completo)//15)]  # ~15 pasos
    
    instrucciones = generador.generar_guia(camino_simplificado)
    print(f"✅ Generadas {len(instrucciones)} instrucciones")
    print()
    
    # 6. Validar instrucciones
    print("✔️  Validando instrucciones...")
    es_valido, error = generador.validar_instrucciones(instrucciones)
    if es_valido:
        print("✅ Instrucciones válidas")
    else:
        print(f"❌ Error de validación: {error}")
    print()
    
    # 7. Mostrar instrucciones
    print("=" * 80)
    print("📍 INSTRUCCIONES DE NAVEGACIÓN (TURN-BY-TURN)")
    print("=" * 80)
    print()
    
    distancia_acumulada = 0
    for inst in instrucciones:
        distancia_acumulada += inst.distancia_km
        
        print(f"🔹 Paso {inst.paso}:")
        print(f"   {inst.instruccion}")
        print(f"   └─ Distancia: {inst.distancia_km:.2f} km | Acumulado: {distancia_acumulada:.2f} km")
        print(f"   └─ Dirección: {inst.direccion}")
        print(f"   └─ Nodos: {inst.nodo_origen} → {inst.nodo_destino}")
        print(f"   └─ Coordenadas: ({inst.lat_origen:.6f}, {inst.lon_origen:.6f})")
        print()
    
    print("=" * 80)
    print(f"🏁 DESTINO ALCANZADO - Total recorrido: {distancia_acumulada:.2f} km")
    print("=" * 80)
    print()
    
    return instrucciones


def demo_con_waypoints():
    """Demostracion de guia con identificacion de waypoints (destinos y viveros)"""
    
    print("\n" + "=" * 80)
    print("DEMO: Guía con Waypoints (Destinos y Reabastecimientos)")
    print("=" * 80)
    print()
    
    # Cargar grafo
    grafo, nodos_coords = cargar_grafo_lima()
    
    # Crear ruta de ejemplo
    nodos_disponibles = list(grafo.keys())[:30]
    origen = nodos_disponibles[0]
    vivero_reabast = nodos_disponibles[5]  # Vivero de reabastecimiento
    destino1 = nodos_disponibles[10]
    destino2 = nodos_disponibles[15]
    destino3 = nodos_disponibles[20]
    
    # Secuencia: origen -> destino1 -> vivero -> destino2 -> destino3 -> origen
    secuencia = [origen, destino1, vivero_reabast, destino2, destino3, origen]
    
    # Mapear tipos de waypoints
    tipos_waypoint = {
        origen: "vivero",
        vivero_reabast: "vivero",
        destino1: "destino",
        destino2: "destino",
        destino3: "destino"
    }
    
    # Generar guia con waypoints
    generador = GeneradorGuiaRuta(grafo, nodos_coords)
    instrucciones = generador.generar_guia_con_waypoints(secuencia, tipos_waypoint)
    
    print("📍 RUTA CON REABASTECIMIENTO:")
    print()
    for inst in instrucciones:
        print(f"{inst.paso}. {inst.instruccion}")
    
    print()
    print("=" * 80)


def demo_geometria_computacional():
    """Demostracion de calculos geometricos (bearing, haversine)"""
    
    print("\n" + "=" * 80)
    print("DEMO: Cálculos de Geometría Computacional")
    print("=" * 80)
    print()
    
    # Coordenadas de ejemplo en Lima
    # Plaza de Armas Lima
    lat1, lon1 = -12.046374, -77.042793
    
    # Miraflores
    lat2, lon2 = -12.119294, -77.034511
    
    # San Isidro
    lat3, lon3 = -12.094722, -77.038333
    
    print("📍 Puntos de ejemplo:")
    print(f"   A (Plaza de Armas): {lat1}, {lon1}")
    print(f"   B (Miraflores):     {lat2}, {lon2}")
    print(f"   C (San Isidro):     {lat3}, {lon3}")
    print()
    
    # Calcular bearings
    bearing_AB = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2, lon2)
    bearing_BC = GeneradorGuiaRuta.calcular_bearing(lat2, lon2, lat3, lon3)
    
    print("🧭 Bearings (rumbos):")
    print(f"   A → B: {bearing_AB:.2f}° (desde Norte en sentido horario)")
    print(f"   B → C: {bearing_BC:.2f}° (desde Norte en sentido horario)")
    print()
    
    # Calcular angulo de giro
    angulo_giro = (bearing_BC - bearing_AB + 180) % 360 - 180
    direccion = GeneradorGuiaRuta.clasificar_angulo(angulo_giro)
    
    print("↪️  Ángulo de giro en B:")
    print(f"   Ángulo: {angulo_giro:.2f}°")
    print(f"   Dirección: {direccion}")
    print()
    
    # Calcular distancias con Haversine
    grafo_dummy = {}
    nodos_dummy = {}
    generador = GeneradorGuiaRuta(grafo_dummy, nodos_dummy)
    
    dist_AB = generador.calcular_distancia_haversine(lat1, lon1, lat2, lon2)
    dist_BC = generador.calcular_distancia_haversine(lat2, lon2, lat3, lon3)
    
    print("📏 Distancias (Haversine):")
    print(f"   A → B: {dist_AB:.2f} km")
    print(f"   B → C: {dist_BC:.2f} km")
    print()
    
    print("=" * 80)


if __name__ == "__main__":
    try:
        # Ejecutar demos
        demo_basica()
        demo_con_waypoints()
        demo_geometria_computacional()
        
        print("\n✅ Todas las demostraciones completadas exitosamente!")
        
    except Exception as e:
        logger.error(f"Error en la demostración: {e}", exc_info=True)
        sys.exit(1)
