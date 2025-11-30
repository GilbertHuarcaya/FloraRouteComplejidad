# Delivery Plantas

Sistema para extracción de red vial de Lima y exportación de grafos.

## Funcionalidades

1. **Extraer Red Vial de Lima**: Descarga y procesa la red de calles de Lima usando OSMnx
7. **Exportar grafo para Graphviz**: Genera archivos DOT y JSON para visualización
8. **Generar PNG desde DOT**: Convierte archivos DOT a imágenes PNG
9. **Crear mapa HTML desde JSON**: Genera mapas interactivos desde archivos JSON

## Requisitos

- Python 3.8+
- pandas
- numpy
- osmnx (para extracción de red vial)
- folium (para mapas HTML)
- Graphviz (para generar PNG)

## Instalación

```bash
pip install pandas numpy osmnx folium
```

Para Graphviz:
- Windows: Descargar desde https://graphviz.org/download/
- Ubuntu: `sudo apt install graphviz`
- macOS: `brew install graphviz`

## Uso

```bash
python main.py
```

## Flujo de uso

1. Ejecutar opción 1 para extraer la red vial
2. Ejecutar opción 2 para exportar el grafo
3. Ejecutar opción 3 para generar PNG
4. Ejecutar opción 4 para crear mapa HTML

Los archivos se generan en el directorio actual del proyecto.