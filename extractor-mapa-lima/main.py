#!/usr/bin/env python3
import os
from src.actions import (
    extraer_red_vial,
    exportar_grafo_graphviz,
    generar_png_desde_dot, 
    crear_mapa_desde_json
)

def mostrar_menu():
    print("\n" + "=" * 60)
    print("DELIVERY PLANTAS")
    print("=" * 60)
    print("1. Extraer Red Vial de Lima")
    print("2. Exportar grafo para Graphviz (DOT + JSON)")
    print("3. Generar PNG desde DOT")
    print("4. Crear mapa HTML desde JSON")
    print("0. Salir")
    print("=" * 60)

def main():
    # Crear directorio de datos si no existe
    os.makedirs("data", exist_ok=True)
    
    while True:
        try:
            mostrar_menu()
            opcion = input("Selecciona una opción (0 - 4): ").strip()
            
            if opcion == "0":
                print("\n¡Gracias por usar Delivery Plantas!")
                break
            elif opcion == "1":
                extraer_red_vial()
            elif opcion == "2":
                exportar_grafo_graphviz()
            elif opcion == "3":
                generar_png_desde_dot()
            elif opcion == "4":
                crear_mapa_desde_json()
            else:
                print("Opción no válida.")
            
            input("\nPresiona Enter para continuar...")
            
        except KeyboardInterrupt:
            print("\n\nProceso interrumpido")
            break
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            input("Presiona Enter para continuar...")

if __name__ == "__main__":
    main()