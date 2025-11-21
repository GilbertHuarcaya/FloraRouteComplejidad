"""
Aplicacion Streamlit para Optimizacion de Rutas de Entrega
FloraRoute - Sistema de Rutas
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.controllers.gestor_rutas import GestorRutas
from src.models.vivero import Vivero, Inventario
from src.utils.cargador_datos import (
    cargar_grafo_lima,
    cargar_viveros,
    obtener_factor_trafico_actual,
    encontrar_nodo_cercano
)
from src.utils.exportador import ExportadorResultados


st.set_page_config(
    page_title="FloraRoute - Rutas de Entrega",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def cargar_datos_iniciales():
    """Carga grafo y viveros al iniciar"""
    grafo, nodos_coords = cargar_grafo_lima()
    viveros_df = cargar_viveros()
    factor_trafico = obtener_factor_trafico_actual()
    return grafo, nodos_coords, viveros_df, factor_trafico


@st.cache_resource
def inicializar_gestor(_grafo, _factor_trafico, _viveros_df, _nodos_coords):
    """Inicializa el gestor de rutas y registra viveros"""
    gestor = GestorRutas(_grafo, _factor_trafico, _nodos_coords)
    
    # Registrar viveros desde DataFrame
    for _, row in _viveros_df.iterrows():
        inventario = Inventario({
            'rosas': int(row['stock_rosas']),
            'claveles': int(row['stock_claveles']),
            'lirios': int(row['stock_lirios']),
            'girasoles': int(row['stock_girasoles']),
            'tulipanes': int(row['stock_tulipanes'])
        })
        
        vivero = Vivero(
            vivero_id=int(row['vivero_id']),
            nombre=row['nombre'],
            nodo_id=int(row['nodo_id']),
            lat=float(row['lat']),
            lon=float(row['lon']),
            inventario=inventario,
            capacidad_entrega=int(row['capacidad_entrega']),
            horario_inicio=row['horario_inicio'],
            horario_fin=row['horario_fin']
        )
        
        gestor.registrar_vivero(vivero)
    
    return gestor


def inicializar_estado():
    """Inicializa el estado de la sesion"""
    if 'vivero_seleccionado' not in st.session_state:
        st.session_state.vivero_seleccionado = None
    if 'destinos' not in st.session_state:
        st.session_state.destinos = []
    if 'contador_destinos' not in st.session_state:
        st.session_state.contador_destinos = 0
    if 'ruta_calculada' not in st.session_state:
        st.session_state.ruta_calculada = False
    if 'mapa_clicked' not in st.session_state:
        st.session_state.mapa_clicked = None


def main():
    """Funcion principal"""
    
    st.title("🌸 FloraRoute - Sistema de Optimizacion de Rutas")
    st.markdown("### Planificacion Inteligente de Entregas de Flores")
    
    inicializar_estado()
    
    with st.spinner("Cargando grafo de Lima..."):
        grafo, nodos_coords, viveros_df, factor_trafico = cargar_datos_iniciales()
        
        # Inicializar gestor solo una vez en session_state
        if 'gestor' not in st.session_state:
            st.session_state.gestor = inicializar_gestor(grafo, factor_trafico, viveros_df, nodos_coords)
        
        gestor = st.session_state.gestor
    
    if not grafo:
        st.error("No se pudo cargar el grafo de Lima")
        return
    
    if viveros_df.empty:
        st.warning("No se cargaron viveros")
    
    # Mostrar factor de trafico actual
    hora_actual = pd.Timestamp.now().hour
    st.sidebar.info(f"Factor de trafico: {factor_trafico:.1f}x (hora {hora_actual}:00)")
    
    # Panel de control en sidebar
    mostrar_panel_control(gestor, viveros_df, nodos_coords, grafo)
    
    # Layout principal: Mapa arriba
    st.subheader("Mapa Interactivo de Rutas")
    mapa_clicked = mostrar_mapa(gestor, viveros_df, nodos_coords)
    
    # Resumen de métricas debajo del mapa
    if st.session_state.ruta_calculada:
        mostrar_resumen_metricas(gestor)


def mostrar_panel_control(gestor, viveros_df, nodos_coords, grafo):
    """Panel lateral de control (RF-01, RF-02)"""
    
    st.sidebar.header("Control de Rutas")
    st.sidebar.subheader("1. Seleccionar Vivero Origen")
    
    if not viveros_df.empty:
        opciones_viveros = {f"{row['nombre']} (ID: {row['vivero_id']})": row['vivero_id'] for _, row in viveros_df.iterrows()}
        vivero_seleccionado_str = st.sidebar.selectbox(
            "Vivero de origen:",
            options=list(opciones_viveros.keys()),
            key="select_vivero"
        )
        
        if st.sidebar.button("Confirmar Vivero", key="btn_confirmar_vivero"):
            vivero_id = opciones_viveros[vivero_seleccionado_str]
            exito, error = gestor.seleccionar_vivero(vivero_id)
            
            if exito:
                st.session_state.vivero_seleccionado = vivero_id
                st.sidebar.success(f"Vivero seleccionado: {vivero_seleccionado_str}")
            else:
                st.sidebar.error(f"Error: {error}")
    
    st.sidebar.divider()
    
    # Seccion 2: Agregar destinos (RF-02)
    st.sidebar.subheader("2. Agregar Destinos")
    
    if st.session_state.vivero_seleccionado is None:
        st.sidebar.info("Primero selecciona un vivero")
    else:
        # Contador de destinos
        num_destinos = len(st.session_state.destinos)
        st.sidebar.metric("Destinos agregados", f"{num_destinos}/20")
        
        # Mostrar coordenadas clickeadas si existen
        if st.session_state.mapa_clicked:
            st.sidebar.success(f"Punto seleccionado en mapa: ({st.session_state.mapa_clicked['lat']:.6f}, {st.session_state.mapa_clicked['lon']:.6f})")
        
        # Formulario para agregar destino
        with st.sidebar.form("form_agregar_destino"):
            st.write("Agregar nuevo destino:")
            
            # Usar coordenadas del click si existen, sino valores por defecto
            if st.session_state.mapa_clicked:
                default_lat = max(-12.3, min(-11.7, st.session_state.mapa_clicked['lat']))  # Clamp dentro del rango
                default_lon = max(-77.2, min(-76.8, st.session_state.mapa_clicked['lon']))  # Clamp dentro del rango
                st.info("Usando coordenadas del mapa")
            else:
                default_lat = -12.0956
                default_lon = -77.0364
            
            lat = st.number_input(
                "Latitud", 
                min_value=-12.3, 
                max_value=-11.7, 
                value=float(default_lat),
                format="%.6f",
                key="input_lat"
            )
            
            lon = st.number_input(
                "Longitud", 
                min_value=-77.2, 
                max_value=-76.8, 
                value=float(default_lon),
                format="%.6f",
                key="input_lon"
            )
            
            st.write("Flores requeridas:")
            rosas = st.number_input("Rosas", min_value=0, max_value=100, value=10)
            claveles = st.number_input("Claveles", min_value=0, max_value=100, value=5)
            lirios = st.number_input("Lirios", min_value=0, max_value=100, value=3)
            
            submitted = st.form_submit_button("Agregar Destino")
            
            if submitted:
                flores_req = {
                    'rosas': int(rosas),
                    'claveles': int(claveles),
                    'lirios': int(lirios)
                }
                
                # Encontrar nodo mas cercano
                try:
                    nodo_cercano = encontrar_nodo_cercano(lat, lon, nodos_coords)
                    exito, error = gestor.agregar_destino(lat, lon, flores_req)
                except Exception as e:
                    exito = False
                    error = str(e)
                
                if exito:
                    st.session_state.contador_destinos += 1
                    st.session_state.destinos.append({
                        'id': st.session_state.contador_destinos,
                        'lat': lat,
                        'lon': lon,
                        'flores': flores_req
                    })
                    st.success("Destino agregado")
                    st.rerun()
                else:
                    st.error(f"Error: {error}")
        
        # Mostrar destinos agregados
        if st.session_state.destinos:
            st.sidebar.subheader("Destinos agregados:")
            
            for dest in st.session_state.destinos:
                with st.sidebar.expander(f"Destino {dest['id']}"):
                    st.write(f"Lat: {dest['lat']:.6f}")
                    st.write(f"Lon: {dest['lon']:.6f}")
                    st.write(f"Flores: {dest['flores']}")
                    
                    if st.button(f"Eliminar", key=f"btn_eliminar_{dest['id']}"):
                        exito, error = gestor.eliminar_destino(dest['id'])
                        if exito:
                            st.session_state.destinos = [d for d in st.session_state.destinos if d['id'] != dest['id']]
                            st.rerun()
                        else:
                            st.error(error)
    
    st.sidebar.divider()
    
    # Seccion 3: Calcular ruta (RF-03)
    st.sidebar.subheader("3. Calcular Ruta Optima")
    
    if st.session_state.vivero_seleccionado and st.session_state.destinos:
        usar_heuristica = st.sidebar.checkbox(
            "Usar heuristica para n > 15",
            value=False,
            help="Mas rapido pero puede no ser optimo"
        )
        
        retornar_origen = st.sidebar.checkbox(
            "Retornar al origen (ciclo cerrado)",
            value=True,
            help="Si esta marcado, la ruta vuelve al vivero de origen"
        )
        
        if st.sidebar.button("Calcular Ruta", key="btn_calcular"):
            with st.spinner("Calculando ruta optima..."):
                exito, error = gestor.calcular_ruta_optima(usar_heuristica, retornar_origen)
                
                if exito:
                    st.session_state.ruta_calculada = True
                    st.sidebar.success("Ruta calculada exitosamente")
                else:
                    st.sidebar.error(f"Error: {error}")
    else:
        st.sidebar.info("Agrega al menos 1 destino para calcular ruta")


def mostrar_mapa(gestor, viveros_df, nodos_coords):
    """Muestra el mapa interactivo con ruta real (RF-04)"""
    
    # Crear mapa centrado en Lima
    mapa = folium.Map(
        location=[-12.0464, -77.0428],
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    # Agregar plugin de click
    mapa.add_child(folium.LatLngPopup())
    
    # Agregar vivero seleccionado SIEMPRE
    if st.session_state.vivero_seleccionado:
        vivero_row = viveros_df[viveros_df['vivero_id'] == st.session_state.vivero_seleccionado]
        if not vivero_row.empty:
            vivero = vivero_row.iloc[0]
            folium.Marker(
                [vivero['lat'], vivero['lon']],
                popup=f"<b>{vivero['nombre']}</b><br>Origen",
                tooltip=vivero['nombre'],
                icon=folium.Icon(color='green', icon='home', prefix='fa')
            ).add_to(mapa)
    
    # Agregar destinos SIEMPRE
    for i, dest in enumerate(st.session_state.destinos, 1):
        folium.Marker(
            [dest['lat'], dest['lon']],
            popup=f"<b>Destino {i}</b><br>Lat: {dest['lat']:.6f}<br>Lon: {dest['lon']:.6f}",
            tooltip=f"Destino {i}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(mapa)
    
    # Logs colapsables
    with st.expander("Ver detalles de estado", expanded=False):
        if st.session_state.vivero_seleccionado:
            vivero_row = viveros_df[viveros_df['vivero_id'] == st.session_state.vivero_seleccionado]
            if not vivero_row.empty:
                vivero = vivero_row.iloc[0]
                st.write(f"**Vivero:** {vivero['nombre']} (Nodo {vivero['nodo_id']})")
                st.write(f"**Coordenadas:** {vivero['lat']:.6f}, {vivero['lon']:.6f}")
        
        st.write(f"**Destinos agregados:** {len(st.session_state.destinos)}")
        
        if st.session_state.ruta_calculada and gestor.ruta_actual:
            ruta = gestor.ruta_actual
            st.write(f"**Secuencia de visita:** {ruta.secuencia_visitas}")
            camino_len = len(ruta.camino_completo) if ruta.camino_completo else 0
            st.write(f"**Nodos en camino completo:** {camino_len}")
    
    # Dibujar ruta SOLO si fue calculada exitosamente
    if st.session_state.ruta_calculada and gestor.ruta_actual:
        ruta = gestor.ruta_actual
        
        # Verificar que camino_completo existe
        if ruta.camino_completo and len(ruta.camino_completo) > 0:
            coordenadas_ruta = []
            nodos_sin_coords = []
            
            # Obtener coordenadas de cada nodo del camino completo
            for nodo_id in ruta.camino_completo:
                if nodo_id in nodos_coords:
                    lat, lon = nodos_coords[nodo_id]
                    coordenadas_ruta.append([lat, lon])
                else:
                    nodos_sin_coords.append(nodo_id)
            
            if len(coordenadas_ruta) > 1:
                # Dibujar polyline que sigue las calles reales
                folium.PolyLine(
                    coordenadas_ruta,
                    color='blue',
                    weight=5,
                    opacity=0.8,
                    tooltip=f"Ruta optimizada ({len(coordenadas_ruta)} nodos)"
                ).add_to(mapa)
                
                # Agregar marcadores en los puntos de la secuencia (no intermedios)
                secuencia = ruta.secuencia_visitas
                for i, nodo_id in enumerate(secuencia):
                    if nodo_id in nodos_coords:
                        lat, lon = nodos_coords[nodo_id]
                        if i == 0:
                            # Origen
                            folium.CircleMarker(
                                [lat, lon],
                                radius=10,
                                color='darkgreen',
                                fill=True,
                                fillColor='lightgreen',
                                fillOpacity=0.9,
                                tooltip=f"Inicio (nodo {nodo_id})"
                            ).add_to(mapa)
                        else:
                            # Parada
                            folium.CircleMarker(
                                [lat, lon],
                                radius=8,
                                color='darkred',
                                fill=True,
                                fillColor='red',
                                fillOpacity=0.9,
                                tooltip=f"Parada {i} (nodo {nodo_id})"
                            ).add_to(mapa)
    
    # Mostrar mapa y capturar clicks
    mapa_output = st_folium(mapa, width=1200, height=600, returned_objects=["last_clicked"])
    
    # Guardar coordenadas del click en session_state
    if mapa_output and mapa_output.get("last_clicked"):
        clicked = mapa_output["last_clicked"]
        if clicked:
            lat_clicked = clicked.get("lat")
            lon_clicked = clicked.get("lng")
            if lat_clicked and lon_clicked:
                st.session_state.mapa_clicked = {
                    'lat': lat_clicked,
                    'lon': lon_clicked
                }


def mostrar_resumen_metricas(gestor):
    """Muestra resumen de metricas (RF-05)"""
    
    st.divider()
    st.subheader("Resumen de Ruta")
    
    resumen = gestor.obtener_resumen()
    
    if resumen:
        # Metricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Distancia Total",
                f"{resumen['distancia_total_km']:.2f} km",
                help="Distancia total de la ruta"
            )
        
        with col2:
            st.metric(
                "Tiempo Estimado",
                f"{resumen['tiempo_total_min']:.0f} min",
                help="Tiempo estimado de recorrido"
            )
        
        with col3:
            st.metric(
                "Numero de Paradas",
                resumen['numero_paradas'],
                help="Destinos a visitar"
            )

        # Orden de visitas
        st.subheader("Orden de Visitas")
        
        orden_visitas = gestor.exportar_resultados()
        
        if orden_visitas:
            df_orden = pd.DataFrame(orden_visitas)
            st.dataframe(df_orden, use_container_width=True)


if __name__ == "__main__":
    main()
