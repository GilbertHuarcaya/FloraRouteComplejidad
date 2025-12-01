"""
Test de integracion: GeneradorGuiaRuta con datos reales
Verifica que el generador funciona correctamente con el grafo de Lima
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.controllers.generador_guia_ruta import GeneradorGuiaRuta, InstruccionRuta
from src.utils.cargador_datos import cargar_grafo_lima


def test_generador_guia_basico():
    """Test basico: generar instrucciones desde secuencia simple"""
    print("=" * 70)
    print("TEST 1: Generador de Guia Basico")
    print("=" * 70)
    
    # Cargar grafo real
    print("\n[1/5] Cargando grafo de Lima...")
    grafo, nodos_coords = cargar_grafo_lima()
    print(f"✓ Grafo cargado: {len(nodos_coords)} nodos, {len(grafo)} con aristas")
    
    # Crear generador
    print("\n[2/5] Inicializando GeneradorGuiaRuta...")
    generador = GeneradorGuiaRuta(grafo, nodos_coords)
    print("✓ Generador creado")
    
    # Seleccionar secuencia de prueba (nodos que sabemos que existen)
    print("\n[3/5] Seleccionando secuencia de prueba...")
    # Usar primeros 5 nodos del grafo como ejemplo
    nodos_disponibles = list(nodos_coords.keys())[:10]
    
    # Buscar una secuencia conectada (nodos que tengan aristas entre ellos)
    secuencia_prueba = []
    nodo_actual = nodos_disponibles[0]
    secuencia_prueba.append(nodo_actual)
    
    for _ in range(4):  # Agregar 4 nodos más
        if nodo_actual in grafo and grafo[nodo_actual]:
            # Tomar primer vecino disponible
            nodo_siguiente = list(grafo[nodo_actual].keys())[0]
            secuencia_prueba.append(nodo_siguiente)
            nodo_actual = nodo_siguiente
        else:
            break
    
    print(f"✓ Secuencia de prueba: {secuencia_prueba}")
    
    # Generar instrucciones
    print("\n[4/5] Generando instrucciones...")
    instrucciones = generador.generar_guia(secuencia_prueba)
    print(f"✓ Generadas {len(instrucciones)} instrucciones")
    
    # Validar
    print("\n[5/5] Validando instrucciones...")
    validacion = generador.validar_instrucciones(instrucciones)
    
    if validacion['valido']:
        print(f"✓ Validación exitosa")
        print(f"  - Distancia total: {validacion['distancia_instrucciones']:.2f} km")
    else:
        print(f"✗ Validación fallida: {validacion['mensaje']}")
        return False
    
    # Mostrar instrucciones
    print("\n" + "=" * 70)
    print("INSTRUCCIONES GENERADAS:")
    print("=" * 70)
    for inst in instrucciones:
        print(f"\nPaso {inst.paso}:")
        print(f"  Dirección: {inst.direccion}")
        print(f"  Instrucción: {inst.instruccion}")
        print(f"  Distancia: {inst.distancia_km:.2f} km")
        print(f"  Desde nodo {inst.nodo_origen} → Hacia nodo {inst.nodo_destino}")
    
    print("\n" + "=" * 70)
    print("✓ TEST COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    return True


def test_exportar_texto():
    """Test: exportar instrucciones a texto"""
    print("\n\n" + "=" * 70)
    print("TEST 2: Exportar Instrucciones a Texto")
    print("=" * 70)
    
    # Cargar grafo
    print("\n[1/3] Cargando grafo...")
    grafo, nodos_coords = cargar_grafo_lima()
    generador = GeneradorGuiaRuta(grafo, nodos_coords)
    
    # Generar secuencia
    print("\n[2/3] Generando instrucciones...")
    nodos_disponibles = list(nodos_coords.keys())[:10]
    secuencia = []
    nodo_actual = nodos_disponibles[0]
    secuencia.append(nodo_actual)
    
    for _ in range(3):
        if nodo_actual in grafo and grafo[nodo_actual]:
            nodo_siguiente = list(grafo[nodo_actual].keys())[0]
            secuencia.append(nodo_siguiente)
            nodo_actual = nodo_siguiente
    
    instrucciones = generador.generar_guia(secuencia)
    
    # Exportar a texto
    print("\n[3/3] Exportando a texto...")
    texto = generador.exportar_instrucciones_texto(instrucciones)
    
    print("\n" + "=" * 70)
    print("TEXTO EXPORTADO:")
    print("=" * 70)
    print(texto)
    
    print("\n" + "=" * 70)
    print("✓ TEST COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    return True


def test_validacion_distancias():
    """Test: validar consistencia de distancias"""
    print("\n\n" + "=" * 70)
    print("TEST 3: Validacion de Distancias")
    print("=" * 70)
    
    # Cargar grafo
    print("\n[1/4] Cargando grafo...")
    grafo, nodos_coords = cargar_grafo_lima()
    generador = GeneradorGuiaRuta(grafo, nodos_coords)
    
    # Generar secuencia
    print("\n[2/4] Generando ruta de prueba...")
    nodos_disponibles = list(nodos_coords.keys())[:10]
    secuencia = []
    nodo_actual = nodos_disponibles[0]
    secuencia.append(nodo_actual)
    distancia_esperada = 0.0
    
    for _ in range(5):
        if nodo_actual in grafo and grafo[nodo_actual]:
            nodo_siguiente = list(grafo[nodo_actual].keys())[0]
            secuencia.append(nodo_siguiente)
            distancia_esperada += grafo[nodo_actual][nodo_siguiente] / 1000.0
            nodo_actual = nodo_siguiente
    
    print(f"✓ Secuencia: {len(secuencia)} nodos")
    print(f"✓ Distancia esperada (del grafo): {distancia_esperada:.2f} km")
    
    # Generar instrucciones
    print("\n[3/4] Generando instrucciones...")
    instrucciones = generador.generar_guia(secuencia)
    distancia_instrucciones = sum(inst.distancia_km for inst in instrucciones)
    print(f"✓ Distancia en instrucciones: {distancia_instrucciones:.2f} km")
    
    # Validar con distancia esperada
    print("\n[4/4] Validando consistencia...")
    validacion = generador.validar_instrucciones(instrucciones, distancia_esperada)
    
    print(f"\nResultado de validación:")
    print(f"  - Válido: {validacion['valido']}")
    print(f"  - Mensaje: {validacion['mensaje']}")
    if 'diferencia' in validacion:
        print(f"  - Diferencia: {validacion['diferencia']:.4f} km")
        print(f"  - Diferencia %: {validacion['diferencia_porcentaje']:.2f}%")
    
    # La diferencia debe ser mínima (distancias vienen del mismo grafo)
    if validacion['valido'] and validacion.get('diferencia_porcentaje', 0) < 1.0:
        print("\n✓ Distancias consistentes (diferencia < 1%)")
        print("=" * 70)
        print("✓ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        return True
    else:
        print("\n✗ Distancias inconsistentes")
        return False


if __name__ == "__main__":
    print("\n🚀 INICIANDO TESTS DE INTEGRACIÓN: GeneradorGuiaRuta\n")
    
    resultados = []
    
    # Ejecutar tests
    try:
        resultados.append(("Test Básico", test_generador_guia_basico()))
    except Exception as e:
        print(f"\n✗ Error en Test Básico: {e}")
        import traceback
        traceback.print_exc()
        resultados.append(("Test Básico", False))
    
    try:
        resultados.append(("Test Exportar Texto", test_exportar_texto()))
    except Exception as e:
        print(f"\n✗ Error en Test Exportar Texto: {e}")
        import traceback
        traceback.print_exc()
        resultados.append(("Test Exportar Texto", False))
    
    try:
        resultados.append(("Test Validación Distancias", test_validacion_distancias()))
    except Exception as e:
        print(f"\n✗ Error en Test Validación Distancias: {e}")
        import traceback
        traceback.print_exc()
        resultados.append(("Test Validación Distancias", False))
    
    # Resumen final
    print("\n\n" + "=" * 70)
    print("RESUMEN DE TESTS")
    print("=" * 70)
    
    tests_exitosos = sum(1 for _, resultado in resultados if resultado)
    tests_totales = len(resultados)
    
    for nombre, resultado in resultados:
        simbolo = "✓" if resultado else "✗"
        print(f"{simbolo} {nombre}: {'ÉXITO' if resultado else 'FALLO'}")
    
    print("\n" + "=" * 70)
    print(f"RESULTADO FINAL: {tests_exitosos}/{tests_totales} tests exitosos")
    print("=" * 70)
    
    # Exit code
    sys.exit(0 if tests_exitosos == tests_totales else 1)
