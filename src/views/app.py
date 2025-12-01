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
        # Obtener el nodo mas cercano a las coordenadas del vivero
        try:
            nodo_asociado = encontrar_nodo_cercano(float(row['lat']), float(row['lon']), _nodos_coords)
        except Exception:
            # fallback al nodo provisto en CSV si la busqueda falla
            nodo_asociado = int(row.get('nodo_id', -1)) if row.get('nodo_id') not in (None, '') else -1

        vivero = Vivero(
            vivero_id=int(row['vivero_id']),
            nombre=row['nombre'],
            nodo_id=int(nodo_asociado),
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
    # soportar seleccion multiple de viveros (display strings en el multiselect)
    if 'multiselect_viveros' not in st.session_state:
        st.session_state.multiselect_viveros = []
    # ids de viveros seleccionados (para uso interno)
    if 'viveros_seleccionados_ids' not in st.session_state:
        st.session_state.viveros_seleccionados_ids = []
    # origen activo (id)
    if 'vivero_origen_activo' not in st.session_state:
        st.session_state.vivero_origen_activo = None
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

    # mantener viveros_df en session_state para permitir actualizaciones en runtime
    if 'viveros_df' not in st.session_state:
        st.session_state.viveros_df = viveros_df
    else:
        # usar la version en session_state (puede haber sido actualizada)
        viveros_df = st.session_state.viveros_df
    
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
    # Opcion: validacion por simulacion (origen -> suplente -> destino)
    usar_simulacion = st.sidebar.checkbox("Usar validación por simulación (reabastecimiento)", value=False, key="usar_simulacion")
    try:
        gestor.set_validacion_por_simulacion(usar_simulacion)
    except Exception:
        pass
    # Nota: no escribir keys de widgets en session_state aquí.
    # El formulario de crear vivero leerá `st.session_state.get('mapa_clicked')`
    # localmente para poblar valores por defecto (igual que en agregar destino).
    
    # Seccion 1.5: Gestion de viveros - crear nuevo vivero y persistir
    with st.sidebar.expander("Crear nuevo vivero"):
        # Seguir la misma logica que "Agregar Destino": usar st.session_state.mapa_clicked
        # para poblar los valores por defecto y NO modificar keys de widgets despues de
        # que hayan sido instanciadas.
        with st.form("form_crear_vivero"):
            st.write("Crear nuevo vivero:")

            # Usar coordenadas del click si existen, sino valores por defecto
            if st.session_state.get('mapa_clicked'):
                default_lat = max(-12.3, min(-11.7, st.session_state['mapa_clicked']['lat']))
                default_lon = max(-77.2, min(-76.8, st.session_state['mapa_clicked']['lon']))
                st.info("Usando coordenadas del mapa para el nuevo vivero")
            else:
                default_lat = -12.0464
                default_lon = -77.0428

            crear_nombre = st.text_input("Nombre del vivero", value="", key="crear_nombre")
            crear_lat = st.number_input("Latitud", min_value=-12.3, max_value=-11.7, value=float(default_lat), format="%.6f", key="crear_lat")
            crear_lon = st.number_input("Longitud", min_value=-77.2, max_value=-76.8, value=float(default_lon), format="%.6f", key="crear_lon")
            crear_capacidad = st.number_input("Capacidad de entrega", min_value=1, max_value=1000, value=20, key="crear_capacidad")
            crear_stock_rosas = st.number_input("Stock Rosas", min_value=0, max_value=100000, value=100, key="crear_stock_rosas")
            crear_stock_claveles = st.number_input("Stock Claveles", min_value=0, max_value=100000, value=50, key="crear_stock_claveles")
            crear_stock_lirios = st.number_input("Stock Lirios", min_value=0, max_value=100000, value=30, key="crear_stock_lirios")
            crear_horario_inicio = st.text_input("Horario inicio (HH:MM)", value="08:00", key="crear_horario_inicio")
            crear_horario_fin = st.text_input("Horario fin (HH:MM)", value="18:00", key="crear_horario_fin")

            submitted = st.form_submit_button("Guardar vivero")
            if submitted:
                try:
                    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'viveros.csv'))
                    df_exist = pd.read_csv(csv_path)
                    if 'vivero_id' in df_exist.columns and not df_exist.empty:
                        nuevo_id = int(df_exist['vivero_id'].max()) + 1
                    else:
                        nuevo_id = 1

                    nuevo_reg = {
                        'vivero_id': nuevo_id,
                        'nombre': crear_nombre,
                        'nodo_id': '',
                        'lat': float(crear_lat),
                        'lon': float(crear_lon),
                        'stock_rosas': int(crear_stock_rosas),
                        'stock_claveles': int(crear_stock_claveles),
                        'stock_lirios': int(crear_stock_lirios),
                        'stock_girasoles': 0,
                        'stock_tulipanes': 0,
                        'capacidad_entrega': int(crear_capacidad),
                        'horario_inicio': crear_horario_inicio,
                        'horario_fin': crear_horario_fin
                    }
                    df_exist = pd.concat([df_exist, pd.DataFrame([nuevo_reg])], ignore_index=True)
                    df_exist.to_csv(csv_path, index=False)

                    # registrar en gestor con nodo asociado
                    try:
                        nodo_asoc = encontrar_nodo_cercano(float(crear_lat), float(crear_lon), nodos_coords)
                    except Exception:
                        nodo_asoc = -1

                    inventario_new = Inventario({
                        'rosas': int(crear_stock_rosas),
                        'claveles': int(crear_stock_claveles),
                        'lirios': int(crear_stock_lirios),
                        'girasoles': 0,
                        'tulipanes': 0
                    })

                    vivero_obj = Vivero(
                        vivero_id=int(nuevo_id),
                        nombre=crear_nombre,
                        nodo_id=int(nodo_asoc) if nodo_asoc is not None else -1,
                        lat=float(crear_lat),
                        lon=float(crear_lon),
                        inventario=inventario_new,
                        capacidad_entrega=int(crear_capacidad),
                        horario_inicio=crear_horario_inicio,
                        horario_fin=crear_horario_fin
                    )

                    gestor.registrar_vivero(vivero_obj)

                    # Actualizar session_state (viveros_df y multiselect) antes de rerun
                    display_new = f"{crear_nombre} (ID: {nuevo_id})"
                    ms = list(st.session_state.get('multiselect_viveros', []))
                    if display_new not in ms:
                        ms.append(display_new)
                    st.session_state['multiselect_viveros'] = ms
                    st.session_state['viveros_seleccionados_ids'] = list(set(st.session_state.get('viveros_seleccionados_ids', []) + [int(nuevo_id)]))

                    # sincronizar seleccion con gestor
                    try:
                        gestor.set_viveros_seleccionados(st.session_state.get('viveros_seleccionados_ids', []))
                    except Exception:
                        pass

                    try:
                        existing_df = st.session_state.get('viveros_df')
                        if existing_df is not None:
                            st.session_state['viveros_df'] = pd.concat([existing_df, pd.DataFrame([nuevo_reg])], ignore_index=True)
                    except Exception:
                        pass

                    # eliminar mapa_clicked para que el form no se rellene con la misma coordenada
                    if 'mapa_clicked' in st.session_state:
                        st.session_state.pop('mapa_clicked')

                    st.success("Vivero guardado y registrado correctamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error guardando vivero: {e}")

    if not viveros_df.empty:
        # Mostrar multiselect para elegir varios viveros como posibles puntos de partida
        opciones_viveros = {f"{row['nombre']} (ID: {row['vivero_id']})": int(row['vivero_id']) for _, row in viveros_df.iterrows()}
        opciones_display = list(opciones_viveros.keys())

        # Sanitizar valores actuales en session_state.multiselect_viveros antes de instanciar widget
        current_ms = list(st.session_state.get('multiselect_viveros', []))
        sanitized = [v for v in current_ms if v in opciones_display]
        if sanitized != current_ms:
            st.session_state['multiselect_viveros'] = sanitized

        # Use session_state value (key) so programmatic updates persist
        seleccion_display = st.sidebar.multiselect(
            "Viveros de origen (puede seleccionar varios):",
            options=opciones_display,
            key="multiselect_viveros"
        )

        # Actualizar ids seleccionados en session_state
        st.session_state.viveros_seleccionados_ids = [opciones_viveros[d] for d in seleccion_display]
        # Sincronizar con el gestor para que la validacion use los viveros actuales
        try:
            gestor.set_viveros_seleccionados(st.session_state.viveros_seleccionados_ids)
        except Exception:
            pass

        # Selectbox para elegir cuál de los seleccionados será el origen activo
        if seleccion_display:
            origen_display_default = None
            # buscar display por id si ya hay origen activo
            if st.session_state.vivero_origen_activo:
                for d, vid in opciones_viveros.items():
                    if vid == st.session_state.vivero_origen_activo:
                        origen_display_default = d
                        break

            origen_display = st.sidebar.selectbox(
                "Iniciar desde (origen activo):",
                options=seleccion_display,
                index=(seleccion_display.index(origen_display_default) if origen_display_default in seleccion_display else 0)
            )

            if st.sidebar.button("Confirmar origen activo", key="btn_confirmar_vivero"):
                vivero_id = opciones_viveros[origen_display]
                exito, error = gestor.seleccionar_vivero(vivero_id)
                if exito:
                    st.session_state.vivero_seleccionado = vivero_id
                    st.session_state.vivero_origen_activo = vivero_id
                    st.sidebar.success(f"Origen activo: {origen_display}")
                else:
                    st.sidebar.error(f"Error: {error}")
        else:
            st.sidebar.info("Selecciona al menos un vivero para definir un origen activo")

    # Si algun vivero seleccionado esta agotado, avisar y permitir agregar un suplementario
    try:
        agotados = gestor.obtener_viveros_agotados()
    except Exception:
        agotados = []

    # intersectar con seleccionados
    seleccionados_ids = list(st.session_state.get('viveros_seleccionados_ids', []))
    agotados_seleccionados = [vid for vid in seleccionados_ids if vid in agotados]
    if agotados_seleccionados:
        nombres_agotados = []
        opciones_suplentes = {}
        for _, row in viveros_df.iterrows():
            vid = int(row['vivero_id'])
            display = f"{row['nombre']} (ID: {vid})"
            if vid in agotados_seleccionados:
                nombres_agotados.append(display)
            # preparar opciones para suplentes (no agotados)
            if vid not in agotados:
                opciones_suplentes[display] = vid

        st.sidebar.warning(f"El/Los vivero(s) agotados: {', '.join(nombres_agotados)}. Seleccione un vivero suplementario para completar los pedidos.")

        if opciones_suplentes:
            seleccion_suplente_display = st.sidebar.selectbox("Elegir vivero suplementario:", options=list(opciones_suplentes.keys()), key="select_suplente")
            if st.sidebar.button("Agregar vivero suplementario", key="btn_agregar_suplente"):
                suplente_id = opciones_suplentes.get(seleccion_suplente_display)
                if suplente_id:
                    exito, err = gestor.agregar_vivero_suplementario(suplente_id)
                    if exito:
                        # asegurar aparece en multiselect
                        ms = list(st.session_state.get('multiselect_viveros', []))
                        if seleccion_suplente_display not in ms:
                            ms.append(seleccion_suplente_display)
                            st.session_state['multiselect_viveros'] = ms
                        st.session_state['viveros_seleccionados_ids'] = list(set(st.session_state.get('viveros_seleccionados_ids', []) + [int(suplente_id)]))

                        # sincronizar seleccion con gestor
                        try:
                            gestor.set_viveros_seleccionados(st.session_state.get('viveros_seleccionados_ids', []))
                        except Exception:
                            pass
                        st.sidebar.success("Vivero suplementario agregado. La ruta priorizara su visita al calcularla.")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Error: {err}")
        else:
            st.sidebar.error("No hay viveros disponibles como suplentes. Por favor cree o habilite otro vivero.")
    
    st.sidebar.divider()
    # Seccion 2: Agregar destinos (RF-02)
    st.sidebar.subheader("2. Agregar Destinos")
    
    if (st.session_state.vivero_seleccionado is None) and (not st.session_state.viveros_seleccionados_ids):
        st.sidebar.info("Primero selecciona al menos un vivero origen (o confirma un origen activo)")
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
        
        retornar_origen = st.sidebar.checkbox(
            "Retornar al origen (ciclo cerrado)",
            value=True,
            help="Si esta marcado, la ruta vuelve al vivero de origen"
        )
        
        if st.sidebar.button("Calcular Ruta", key="btn_calcular"):
            with st.spinner("Calculando ruta optima..."):
                exito, error = gestor.calcular_ruta_optima(retornar_origen)
                
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
    
    # Agregar TODOS los viveros al mapa
    for _, vivero in viveros_df.iterrows():
        vid = int(vivero['vivero_id'])
        display = f"{vivero['nombre']} (ID: {vid})"
        is_selected = vid in st.session_state.viveros_seleccionados_ids
        is_activo = (st.session_state.vivero_origen_activo == vid)

        # obtener objeto Vivero del gestor si esta disponible para leer inventario/capacidad
        vivero_obj = None
        try:
            if hasattr(gestor, 'viveros') and int(vid) in gestor.viveros:
                vivero_obj = gestor.viveros[int(vid)]
        except Exception:
            vivero_obj = None

        # Estilo segun estado: agotado -> rojo, activo -> darkgreen, seleccionado -> green, default -> blue
        if vivero_obj is not None and hasattr(vivero_obj, 'esta_agotado') and vivero_obj.esta_agotado():
            icon = folium.Icon(color='red', icon='home', prefix='fa')
        elif is_activo:
            icon = folium.Icon(color='darkgreen', icon='home', prefix='fa')
        elif is_selected:
            icon = folium.Icon(color='green', icon='home', prefix='fa')
        else:
            icon = folium.Icon(color='blue', icon='home', prefix='fa')

        # obtener nodo asociado (cercano) para mostrar y referencia de ruta
        try:
            nodo_asociado = encontrar_nodo_cercano(float(vivero['lat']), float(vivero['lon']), nodos_coords)
        except Exception:
            nodo_asociado = vivero.get('nodo_id') if 'vivero' in locals() else vid

        # Construir popup con informacion de capacidad e inventario si disponemos del objeto
        if vivero_obj is not None:
            inv = vivero_obj.inventario.stock
            inv_str = "<br>".join([f"{k}: {v}" for k, v in inv.items()])
            popup_html = f"<b>{vivero['nombre']}</b><br>ID: {vid}<br>Nodo asociado: {nodo_asociado}<br>Capacidad: {vivero_obj.capacidad_entrega}<br>{inv_str}"
        else:
            popup_html = f"<b>{vivero['nombre']}</b><br>ID: {vid}<br>Nodo asociado: {nodo_asociado}<br>Capacidad: {vivero.get('capacidad_entrega', 'N/A')}"

        folium.Marker(
            [float(vivero['lat']), float(vivero['lon'])],
            popup=popup_html,
            tooltip=display,
            icon=icon
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
    # Devolver tambien el ultimo objeto clickeado para detectar clicks sobre marcadores
    mapa_output = st_folium(mapa, width=1200, height=600, returned_objects=["last_clicked", "last_object_clicked"])
    
    # Guardar coordenadas del click en session_state
    if mapa_output:
        # click libre en el mapa (no sobre marcador)
        if mapa_output.get("last_clicked"):
            clicked = mapa_output["last_clicked"]
            if clicked:
                lat_clicked = clicked.get("lat")
                lon_clicked = clicked.get("lng")
                if lat_clicked and lon_clicked:
                    new_mapa = {'lat': lat_clicked, 'lon': lon_clicked}
                    # solo actualizar y rerun si cambió
                    if st.session_state.get('mapa_clicked') != new_mapa:
                        st.session_state.mapa_clicked = new_mapa
                        # Propagar click para rellenar formulario de nuevo vivero
                        # llamamos rerun para que la barra lateral sea reconstruida usando estos valores
                        st.rerun()

        # Si se hizo click sobre un objeto (p. ej. un marcador), intentar reconocer vivero
        if mapa_output.get("last_object_clicked"):
            obj = mapa_output.get("last_object_clicked")
            # objetos de folium suelen traer propiedades con coordenadas, intentar extraer
            lat_o = None
            lon_o = None
            if isinstance(obj, dict):
                # estructuras varian; intentar varios caminos
                geom = obj.get('geometry') or obj.get('latlng')
                if geom and isinstance(geom, dict):
                    lat_o = geom.get('lat') or geom.get('latitude')
                    lon_o = geom.get('lng') or geom.get('longitude')
                else:
                    # a veces vienen como lista
                    coords = obj.get('coordinates')
                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                        lon_o, lat_o = coords[0], coords[1]

            # fallback: usar last_clicked si last_object_clicked no trae coords
            if (lat_o is None or lon_o is None) and mapa_output.get('last_clicked'):
                clicked = mapa_output['last_clicked']
                lat_o = clicked.get('lat')
                lon_o = clicked.get('lng')

            if lat_o and lon_o:
                try:
                    lat_o = float(lat_o)
                    lon_o = float(lon_o)
                except Exception:
                    lat_o = None
                    lon_o = None

            # Buscar vivero cercano por coordenadas
            if lat_o and lon_o:
                # tolerancia en grados (~50-100 metros depende de latitud)
                tolerancia = 0.0006
                encontrado = None
                for _, v in viveros_df.iterrows():
                    if abs(float(v['lat']) - lat_o) <= tolerancia and abs(float(v['lon']) - lon_o) <= tolerancia:
                        encontrado = int(v['vivero_id'])
                        display = f"{v['nombre']} (ID: {encontrado})"
                        break

                if encontrado:
                    # actualizar multiselect y origen activo solo si hay cambios
                    current = list(st.session_state.get('multiselect_viveros', [])) or []
                    need_rerun = False
                    if display not in current:
                        current.append(display)
                        st.session_state.multiselect_viveros = current
                        need_rerun = True

                    # reconstruir mapping local para ids
                    opciones_viveros_local = {f"{row['nombre']} (ID: {int(row['vivero_id'])})": int(row['vivero_id']) for _, row in viveros_df.iterrows()}
                    nuevos_ids = [opciones_viveros_local[d] for d in current if d in opciones_viveros_local]
                    if st.session_state.get('viveros_seleccionados_ids') != nuevos_ids:
                        st.session_state.viveros_seleccionados_ids = nuevos_ids
                        # sincronizar con gestor
                        try:
                            gestor.set_viveros_seleccionados(nuevos_ids)
                        except Exception:
                            pass
                        need_rerun = True

                    if st.session_state.get('vivero_origen_activo') != encontrado:
                        st.session_state.vivero_origen_activo = encontrado
                        need_rerun = True

                    if st.session_state.get('vivero_seleccionado') != encontrado:
                        st.session_state.vivero_seleccionado = encontrado
                        need_rerun = True

                    # no escribir keys de widgets; en su lugar almacenar mapa_clicked
                    try:
                        st.session_state['mapa_clicked'] = {'lat': float(v['lat']), 'lon': float(v['lon'])}
                        need_rerun = True
                    except Exception:
                        pass

                    # aplicar al gestor (no afecta rerun guard)
                    try:
                        gestor.seleccionar_vivero(encontrado)
                        # tambien sincronizar seleccionados por si cambiaron
                        try:
                            gestor.set_viveros_seleccionados(st.session_state.get('viveros_seleccionados_ids', []))
                        except Exception:
                            pass
                    except Exception:
                        pass

                    if need_rerun:
                        st.rerun()


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
