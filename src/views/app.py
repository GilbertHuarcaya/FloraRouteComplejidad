"""
Aplicacion Streamlit para Optimizacion de Rutas de Entrega
FloraRoute - Sistema de Rutas
"""

import streamlit as st
import folium
from streamlit_folium import st_folium, folium_static
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.controllers.gestor_rutas import GestorRutas
from src.controllers.generador_guia_ruta import GeneradorGuiaRuta, InstruccionRuta
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
    
    # Botón para agregar vivero clickeado (mostrar antes del mapa)
    if 'ultimo_vivero_clickeado' in st.session_state and st.session_state.ultimo_vivero_clickeado:
        vivero_click_info = st.session_state.ultimo_vivero_clickeado
        vid = vivero_click_info['id']
        nombre = vivero_click_info['nombre']
        display = vivero_click_info['display']
        
        # Verificar si ya está en la lista
        current_multiselect = st.session_state.get('multiselect_viveros', [])
        if display not in current_multiselect:
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                st.info(f"Vivero seleccionado: **{nombre}**")
            with col_btn2:
                if st.button("Agregar a Lista", key="btn_agregar_vivero_click", type="primary"):
                    # Agregar a pendientes
                    if 'pending_multiselect_add' not in st.session_state:
                        st.session_state['pending_multiselect_add'] = []
                    if display not in st.session_state['pending_multiselect_add']:
                        st.session_state['pending_multiselect_add'].append(display)
                    
                    # Limpiar vivero clickeado
                    st.session_state.pop('ultimo_vivero_clickeado', None)
                    st.success(f"{nombre} agregado")
                    st.rerun()
        else:
            st.success(f"**{nombre}** ya está en la lista de viveros")
    
    mapa_clicked = mostrar_mapa(gestor, viveros_df, nodos_coords)
    
    # Resumen de métricas debajo del mapa
    if st.session_state.ruta_calculada:
        mostrar_resumen_metricas(gestor)


def mostrar_panel_control(gestor, viveros_df, nodos_coords, grafo):
    """Panel lateral de control (RF-01, RF-02)"""
    
    st.sidebar.header("Control de Rutas")
    st.sidebar.subheader("1. Seleccionar Vivero Origen")
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

                    # Actualizar session_state (viveros_df) - NO modificar multiselect_viveros aquí
                    display_new = f"{crear_nombre} (ID: {nuevo_id})"
                    
                    # Guardar en una key pendiente para aplicar en el próximo ciclo
                    if 'pending_multiselect_add' not in st.session_state:
                        st.session_state['pending_multiselect_add'] = []
                    if display_new not in st.session_state.get('pending_multiselect_add', []):
                        st.session_state['pending_multiselect_add'].append(display_new)
                    
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

        # Aplicar cambios pendientes del ciclo anterior ANTES de crear el widget
        current_ms = list(st.session_state.get('multiselect_viveros', []))
        pending_adds = st.session_state.get('pending_multiselect_add', [])
        if pending_adds:
            for item in pending_adds:
                if item not in current_ms and item in opciones_display:
                    current_ms.append(item)
                    st.sidebar.success(f"{item} agregado")
            st.session_state['pending_multiselect_add'] = []  # Limpiar pendientes
        
        # Sanitizar valores actuales ANTES de instanciar widget
        sanitized = [v for v in current_ms if v in opciones_display]
        if sanitized != current_ms:
            current_ms = sanitized
        
        # Actualizar ANTES de crear widget (no después)
        if st.session_state.get('multiselect_viveros') != current_ms:
            st.session_state['multiselect_viveros'] = current_ms

        # Use session_state value (key) so programmatic updates persist
        seleccion_display = st.sidebar.multiselect(
            "Viveros de origen (puede seleccionar varios):",
            options=opciones_display,
            key="multiselect_viveros",
            help="Los viveros seleccionados actuarán automáticamente como suplementarios si el origen principal se agota"
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
                    # Solo marcar que se recalcule la ruta, NO limpiar destinos
                    st.session_state.ruta_calculada = False
                    st.sidebar.success(f"Origen activo: {origen_display}")
                else:
                    st.sidebar.error(f"Error: {error}")
        else:
            st.sidebar.info("Selecciona al menos un vivero para definir un origen activo")

    # Mostrar información sobre viveros agotados (solo informativo)
    try:
        agotados = gestor.obtener_viveros_agotados()
    except Exception:
        agotados = []

    seleccionados_ids = list(st.session_state.get('viveros_seleccionados_ids', []))
    agotados_seleccionados = [vid for vid in seleccionados_ids if vid in agotados]
    if agotados_seleccionados:
        nombres_agotados = []
        for _, row in viveros_df.iterrows():
            vid = int(row['vivero_id'])
            display = f"{row['nombre']} (ID: {vid})"
            if vid in agotados_seleccionados:
                nombres_agotados.append(display)
        
        st.sidebar.info(f"ℹ️ Vivero(s) con stock bajo: {', '.join(nombres_agotados)}. El sistema usará automáticamente otros viveros seleccionados como suplementarios.")
    
    st.sidebar.divider()
    # Seccion 2: Agregar destinos (RF-02)
    st.sidebar.subheader("2. Agregar Destinos")
    
    # Sincronizar destinos con el gestor al inicio (para mantener consistencia)
    if gestor.pedido_actual:
        destinos_gestor = gestor.obtener_destinos_actuales()
        st.session_state.destinos = [
            {
                'id': d['destino_id'],
                'lat': d['lat'],
                'lon': d['lon'],
                'flores': d['flores']
            }
            for d in destinos_gestor
        ]
    
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
                
                # Antes de agregar destino, sincronizar el estado de viveros seleccionados y origen activo
                try:
                    gestor.set_viveros_seleccionados(st.session_state.get('viveros_seleccionados_ids', []))
                    if st.session_state.get('vivero_origen_activo'):
                        try:
                            gestor.seleccionar_vivero(st.session_state.get('vivero_origen_activo'))
                        except Exception:
                            # no interrumpir si seleccionar_vivero falla
                            pass
                except Exception:
                    pass

                # Encontrar nodo mas cercano y agregar destino usando el gestor
                try:
                    nodo_cercano = encontrar_nodo_cercano(lat, lon, nodos_coords)
                    exito, error = gestor.agregar_destino(lat, lon, flores_req)
                except Exception as e:
                    exito = False
                    error = str(e)
                
                if exito:
                    # NO sincronizar desde el gestor aquí - el gestor ya tiene el destino agregado
                    # Solo incrementar el contador y agregar a la lista local
                    st.session_state.contador_destinos += 1
                    nuevo_destino = {
                        'id': st.session_state.contador_destinos,
                        'lat': lat,
                        'lon': lon,
                        'flores': flores_req
                    }
                    if nuevo_destino not in st.session_state.destinos:
                        st.session_state.destinos.append(nuevo_destino)
                    st.success("Destino agregado")
                    st.rerun()
                else:
                    st.error(f"Error: {error}")
        
        # Mostrar destinos agregados
        if st.session_state.destinos:
            st.sidebar.subheader("Destinos agregados:")
            
            # NO sincronizar automáticamente - mantener los destinos en session_state
            # La sincronización solo debe ocurrir al eliminar manualmente
            
            for dest in st.session_state.destinos:
                with st.sidebar.expander(f"Destino {dest['id']}"):
                    st.write(f"Lat: {dest['lat']:.6f}")
                    st.write(f"Lon: {dest['lon']:.6f}")
                    st.write(f"Flores: {dest['flores']}")
                    
                    if st.button(f"Eliminar", key=f"btn_eliminar_{dest['id']}"):
                        exito, error = gestor.eliminar_destino(dest['id'])
                        if exito:
                            # Eliminar de la lista local en session_state
                            st.session_state.destinos = [
                                d for d in st.session_state.destinos 
                                if d['id'] != dest['id']
                            ]
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
        
        # Checkbox de validación por simulación (reabastecimiento)
        usar_simulacion = st.sidebar.checkbox(
            "Calcular con reabastecimiento",
            value=False,
            key="usar_simulacion",
            help="Si está marcado, calcula una ruta que incluye paradas en viveros adicionales para reabastecer según sea necesario"
        )
        
        if st.sidebar.button("Calcular Ruta", key="btn_calcular"):
            # Activar/desactivar simulación en el gestor según el checkbox
            try:
                gestor.set_validacion_por_simulacion(usar_simulacion)
            except Exception:
                pass
            
            with st.spinner("Calculando ruta optima..."):
                # Sincronizar destinos de la UI con el pedido del gestor
                ui_destinos = list(st.session_state.get('destinos', []))
                pedido_count = gestor.pedido_actual.cantidad_destinos() if gestor.pedido_actual else 0
                proceed = True
                if (gestor.pedido_actual is None) or (pedido_count != len(ui_destinos)):
                    # (Re)crear pedido en el gestor usando el origen activo
                    origen_id = st.session_state.get('vivero_origen_activo') or st.session_state.get('vivero_seleccionado')
                    if not origen_id:
                        st.sidebar.error("No hay un origen activo para reconstruir el pedido")
                        proceed = False
                    else:
                        ok, err = gestor.seleccionar_vivero(origen_id)
                        if not ok:
                            st.sidebar.error(f"Error al crear pedido en gestor: {err}")
                            proceed = False
                        else:
                            # agregar destinos desde la UI al gestor
                            recon_ok = True
                            recon_err = None
                            for d in ui_destinos:
                                try:
                                    ok, err = gestor.agregar_destino(d['lat'], d['lon'], d['flores'])
                                except Exception as e:
                                    ok = False
                                    err = str(e)
                                if not ok:
                                    recon_ok = False
                                    recon_err = err
                                    break
                            if not recon_ok:
                                st.sidebar.error(f"Error al sincronizar destinos con el gestor: {recon_err}")
                                proceed = False

                if not proceed:
                    # no continuamos al calculo de ruta
                    pass
                else:
                    # Si NO se usa simulación, limpiar asignaciones previas
                    if not usar_simulacion:
                        if hasattr(gestor, 'asignaciones_reabastecimiento'):
                            gestor.asignaciones_reabastecimiento = None
                    
                    exito, error = gestor.calcular_ruta_optima(retornar_origen)

                    if exito:
                        st.session_state.ruta_calculada = True
                        if usar_simulacion:
                            st.sidebar.success(" Ruta con reabastecimiento calculada exitosamente")
                        else:
                            st.sidebar.success(" Ruta calculada exitosamente")
                    else:
                        st.sidebar.error(f"Error: {error}")
    else:
        st.sidebar.info("Agrega al menos 1 destino para calcular ruta")


def mostrar_mapa(gestor, viveros_df, nodos_coords):
    """Muestra el mapa interactivo con ruta real (RF-04)"""
    
    # Inicializar atributo si no existe (para gestores creados antes de esta feature)
    if not hasattr(gestor, 'asignaciones_reabastecimiento'):
        gestor.asignaciones_reabastecimiento = None
    
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
        # Agregar instrucción para agregar a lista de viveros suplementarios
        if is_selected:
            instruccion_click = "<div style='margin-top: 10px; padding: 8px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724;'><b>Ya está en la lista</b></div>"
        else:
            # Agregar atributo especial al marcador para identificarlo
            instruccion_click = f"<div style='margin-top: 10px; padding: 8px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; color: #856404;'><b>Vivero ID: {vid}</b><br><small>Agregalo con el botón de arriba del mapa</small></div>"
        
        if vivero_obj is not None:
            inv = vivero_obj.inventario.stock
            inv_str = "<br>".join([f"{k}: {v}" for k, v in inv.items()])
            popup_html = f"""
            <div style='width: 220px; font-family: Arial, sans-serif;'>
                <b style='font-size: 14px;'>{vivero['nombre']}</b><br>
                <b>ID:</b> {vid}<br>
                <b>Nodo:</b> {nodo_asociado}<br>
                <b>Capacidad:</b> {vivero_obj.capacidad_entrega}<br>
                <b>Inventario:</b><br>{inv_str}
                {instruccion_click}
            </div>
            """
        else:
            popup_html = f"""
            <div style='width: 220px; font-family: Arial, sans-serif;'>
                <b style='font-size: 14px;'>{vivero['nombre']}</b><br>
                <b>ID:</b> {vid}<br>
                <b>Nodo:</b> {nodo_asociado}<br>
                <b>Capacidad:</b> {vivero.get('capacidad_entrega', 'N/A')}
                {instruccion_click}
            </div>
            """

        folium.Marker(
            [float(vivero['lat']), float(vivero['lon'])],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=display,
            icon=icon
        ).add_to(mapa)
        
        # NUEVO: Agregar marcador invisible que capture el click
        if not is_selected:
            # Crear un círculo invisible que capture clicks
            folium.CircleMarker(
                [float(vivero['lat']), float(vivero['lon'])],
                radius=15,
                color='transparent',
                fill=True,
                fillColor='transparent',
                fillOpacity=0,
                popup=f"vivero_click_{vid}",  # ID especial para identificar
                tooltip=""
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
        
        # Mostrar información de reabastecimiento si hay simulación activa
        if hasattr(gestor, 'asignaciones_reabastecimiento') and gestor.asignaciones_reabastecimiento:
            st.write("### Reabastecimiento Activo")
            viveros_usados = set()
            for destino_id, suppliers in gestor.asignaciones_reabastecimiento.items():
                viveros_usados.update(suppliers.keys())
            
            viveros_nombres = []
            for vid in viveros_usados:
                viv = gestor.viveros.get(vid)
                if viv:
                    viveros_nombres.append(f"{viv.nombre} (ID: {vid})")
            
            st.write(f"**Viveros participantes:** {', '.join(viveros_nombres)}")
            
            # Detalle por destino
            st.write("**Asignación por destino:**")
            for destino_id, suppliers in gestor.asignaciones_reabastecimiento.items():
                st.write(f"  - Destino {destino_id}:")
                for vid, flores in suppliers.items():
                    viv = gestor.viveros.get(vid)
                    nombre_viv = viv.nombre if viv else f"Vivero {vid}"
                    flores_str = ", ".join([f"{f}: {q}" for f, q in flores.items()])
                    st.write(f"    • {nombre_viv}: {flores_str}")
        
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
                nodo_origen = secuencia[0] if secuencia else None
                
                # Identificar qué nodos son viveros (mirando todos los viveros registrados)
                nodos_viveros = set()
                viveros_dict = {}  # nodo_id -> nombre_vivero
                for _, viv_row in viveros_df.iterrows():
                    try:
                        nodo_vivero = encontrar_nodo_cercano(float(viv_row['lat']), float(viv_row['lon']), nodos_coords)
                        nodos_viveros.add(nodo_vivero)
                        viveros_dict[nodo_vivero] = viv_row['nombre']
                    except Exception:
                        pass
                
                # Identificar qué nodos son destinos
                nodos_destinos = set()
                for dest in st.session_state.destinos:
                    if 'nodo_id' in dest and dest['nodo_id']:
                        nodos_destinos.add(dest['nodo_id'])
                    else:
                        # Buscar nodo cercano
                        try:
                            nodo_dest = encontrar_nodo_cercano(dest['lat'], dest['lon'], nodos_coords)
                            nodos_destinos.add(nodo_dest)
                        except Exception:
                            pass
                
                for i, nodo_id in enumerate(secuencia):
                    if nodo_id in nodos_coords:
                        lat, lon = nodos_coords[nodo_id]
                        
                        # Determinar tipo de nodo
                        es_vivero = nodo_id in nodos_viveros
                        es_destino = nodo_id in nodos_destinos
                        es_retorno = (i == len(secuencia) - 1 and nodo_id == nodo_origen)
                        
                        if i == 0:
                            # Origen inicial
                            folium.CircleMarker(
                                [lat, lon],
                                radius=10,
                                color='darkgreen',
                                fill=True,
                                fillColor='lightgreen',
                                fillOpacity=0.9,
                                tooltip=f"Inicio: {viveros_dict.get(nodo_id, f'nodo {nodo_id}')}"
                            ).add_to(mapa)
                        elif es_retorno:
                            # Retorno al origen - NO es una parada de entrega
                            folium.CircleMarker(
                                [lat, lon],
                                radius=10,
                                color='darkgreen',
                                fill=True,
                                fillColor='orange',
                                fillOpacity=0.7,
                                tooltip=f"Retorno: {viveros_dict.get(nodo_id, f'nodo {nodo_id}')}"
                            ).add_to(mapa)
                        elif es_vivero and not es_destino:
                            # Vivero de reabastecimiento (no es destino)
                            folium.CircleMarker(
                                [lat, lon],
                                radius=9,
                                color='blue',
                                fill=True,
                                fillColor='lightblue',
                                fillOpacity=0.8,
                                tooltip=f"Reabastecimiento {i}: {viveros_dict.get(nodo_id, f'nodo {nodo_id}')}"
                            ).add_to(mapa)
                        else:
                            # Destino de entrega
                            folium.CircleMarker(
                                [lat, lon],
                                radius=8,
                                color='darkred',
                                fill=True,
                                fillColor='red',
                                fillOpacity=0.9,
                                tooltip=f"Entrega {i} (nodo {nodo_id})"
                            ).add_to(mapa)
                
                # Agregar leyenda al mapa cuando hay ruta con reabastecimiento
                if hasattr(gestor, 'asignaciones_reabastecimiento') and gestor.asignaciones_reabastecimiento:
                    leyenda_html = '''
                    <div style="position: fixed; 
                                bottom: 50px; left: 50px; width: 280px; height: auto; 
                                background-color: white; z-index:9999; font-size:14px;
                                border:2px solid grey; border-radius: 5px; padding: 10px">
                    <p style="margin: 0; font-weight: bold; text-align: center;">Leyenda de Ruta</p>
                    <p style="margin: 5px 0;"><span style="color: lightgreen; font-size: 20px;">●</span> Origen inicial</p>
                    <p style="margin: 5px 0;"><span style="color: lightblue; font-size: 20px;">●</span> Reabastecimiento</p>
                    <p style="margin: 5px 0;"><span style="color: red; font-size: 20px;">●</span> Entrega a destino</p>
                    <p style="margin: 5px 0;"><span style="color: orange; font-size: 20px;">●</span> Retorno al origen</p>
                    </div>
                    '''
                    mapa.get_root().html.add_child(folium.Element(leyenda_html))
    
    # Mostrar mapa y capturar clicks
    mapa_output = st_folium(
        mapa, 
        width=1200, 
        height=600, 
        returned_objects=["last_clicked", "last_object_clicked", "all_drawings"],
        key="mapa_principal"
    )
    
    # DETECTAR CLICKS Y PROCESAR
    need_rerun = False
    
    if mapa_output:
        # Intentar múltiples métodos de detección
        lat_clicked = None
        lon_clicked = None
        
        # Método 1: last_clicked
        if mapa_output.get("last_clicked"):
            clicked = mapa_output["last_clicked"]
            lat_clicked = clicked.get("lat")
            lon_clicked = clicked.get("lng")
        
        # Método 2: last_object_clicked
        elif mapa_output.get("last_object_clicked"):
            obj = mapa_output["last_object_clicked"]
            if isinstance(obj, dict):
                # Intentar extraer coordenadas
                if "lat" in obj and "lng" in obj:
                    lat_clicked = obj["lat"]
                    lon_clicked = obj["lng"]
                elif "geometry" in obj:
                    geom = obj["geometry"]
                    if isinstance(geom, dict):
                        lat_clicked = geom.get("lat") or geom.get("coordinates", [None, None])[1]
                        lon_clicked = geom.get("lng") or geom.get("coordinates", [None, None])[0]
        
        # Si detectamos un click, procesar
        if lat_clicked and lon_clicked:
            st.session_state.mapa_clicked = {'lat': lat_clicked, 'lon': lon_clicked}
            
            # Buscar vivero cercano (tolerancia generosa)
            tolerancia = 0.002  # ~200 metros - AUMENTADA
            vivero_encontrado = None
            distancia_minima = float('inf')
            
            for _, v in viveros_df.iterrows():
                v_lat = float(v['lat'])
                v_lon = float(v['lon'])
                dist = ((v_lat - lat_clicked)**2 + (v_lon - lon_clicked)**2)**0.5
                
                if dist <= tolerancia and dist < distancia_minima:
                    vivero_encontrado = v
                    distancia_minima = dist
            
            if vivero_encontrado is not None:
                vid = int(vivero_encontrado['vivero_id'])
                display = f"{vivero_encontrado['nombre']} (ID: {vid})"
                
                # Verificar si ya está en la lista
                current_multiselect = st.session_state.get('multiselect_viveros', [])
                
                if display not in current_multiselect:
                    # NO está en la lista - mostrar botón
                    vivero_click_info = {
                        'id': vid,
                        'nombre': vivero_encontrado['nombre'],
                        'display': display,
                        'lat': float(vivero_encontrado['lat']),
                        'lon': float(vivero_encontrado['lon'])
                    }
                    
                    prev = st.session_state.get('ultimo_vivero_clickeado')
                    if prev is None or prev.get('id') != vid:
                        st.session_state['ultimo_vivero_clickeado'] = vivero_click_info
                        need_rerun = True
                else:
                    # Ya está en la lista - limpiar selección
                    if 'ultimo_vivero_clickeado' in st.session_state:
                        st.session_state.pop('ultimo_vivero_clickeado')
                        need_rerun = True
    
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
        
        # ===== GUÍA DE RUTA DETALLADA =====
        st.markdown("---")
        st.subheader(" Guía de Ruta Detallada")
        st.markdown("**Instrucciones paso a paso para el conductor**")
        
        try:
            # 1. Obtener grafo y coordenadas (ya cargados en cache)
            grafo, nodos_coords = cargar_datos_iniciales()[:2]
            
            if not grafo or not nodos_coords:
                st.warning("⚠️ No se pudo cargar el grafo de Lima. Guía de ruta no disponible.")
            else:
                # 2. Crear generador
                generador = GeneradorGuiaRuta(grafo, nodos_coords)
                
                # 3. Obtener secuencia completa de nodos desde ruta
                if gestor.ruta_actual and gestor.ruta_actual.camino_completo:
                    secuencia_nodos = gestor.ruta_actual.camino_completo
                    
                    # 4. Identificar waypoints (destinos y viveros de reabastecimiento)
                    waypoints = {}
                    
                    # Marcar destinos
                    for destino in gestor.pedido_actual.destinos:
                        waypoints[destino.nodo_id] = f"📦 Destino {destino.destino_id}"
                    
                    # Marcar viveros de reabastecimiento (si existen)
                    if hasattr(gestor, 'asignaciones_reabastecimiento') and gestor.asignaciones_reabastecimiento:
                        viveros_reabast = set()
                        for dest_id, suppliers in gestor.asignaciones_reabastecimiento.items():
                            viveros_reabast.update(suppliers.keys())
                        
                        # Excluir vivero origen
                        viveros_reabast.discard(gestor.vivero_actual.vivero_id)
                        
                        for vivero_id in viveros_reabast:
                            vivero = gestor.viveros.get(vivero_id)
                            if vivero:
                                waypoints[vivero.nodo_id] = f"Reabastecimiento: {vivero.nombre}"
                    
                    # Marcar origen y retorno
                    if gestor.vivero_actual:
                        nodo_origen = gestor.vivero_actual.nodo_id
                        if secuencia_nodos[0] == nodo_origen:
                            waypoints[nodo_origen] = f"Origen: {gestor.vivero_actual.nombre}"
                        # Si la ruta retorna al origen, marcar último nodo
                        if len(secuencia_nodos) > 1 and secuencia_nodos[-1] == nodo_origen:
                            # No sobrescribir - ya está marcado como origen
                            pass
                    
                    # 5. Generar instrucciones
                    instrucciones = generador.generar_guia(secuencia_nodos)
                    
                    # 6. Enriquecer instrucciones con información de waypoints
                    for inst in instrucciones:
                        if inst.nodo_destino in waypoints:
                            nombre_waypoint = waypoints[inst.nodo_destino]
                            # Agregar información al final de la instrucción
                            inst.instruccion = f"{inst.instruccion} → {nombre_waypoint}"
                    
                    if not instrucciones:
                        st.info("ℹNo se pudieron generar instrucciones para esta ruta")
                    else:
                        # 7. Usar la distancia REAL calculada por el gestor (no recalcular)
                        # Esto garantiza que ambas métricas sean idénticas
                        distancia_total_real = gestor.ruta_actual.distancia_total
                        
                        validacion = generador.validar_instrucciones(
                            instrucciones, 
                            distancia_total_real
                        )
                        
                        if not validacion['valido']:
                            st.warning(f"Advertencia: {validacion['mensaje']}")
                        elif 'diferencia_porcentaje' in validacion and validacion['diferencia_porcentaje'] > 5:
                            st.warning(f"{validacion['mensaje']}")
                        
                        # 8. Mostrar tabla con pandas DataFrame
                        datos_guia = []
                        for inst in instrucciones:
                            datos_guia.append({
                                'Paso': inst.paso,
                                'Dirección': inst.direccion,
                                'Instrucción': inst.instruccion,
                                'Distancia': f"{inst.distancia_km:.2f} km",
                                'Desde Nodo': inst.nodo_origen,
                                'Hacia Nodo': inst.nodo_destino
                            })
                        
                        df_guia = pd.DataFrame(datos_guia)
                        
                        # Mostrar tabla con estilo
                        st.dataframe(
                            df_guia,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                'Paso': st.column_config.NumberColumn('Paso', width='small'),
                                'Dirección': st.column_config.TextColumn('Dirección', width='small'),
                                'Instrucción': st.column_config.TextColumn('Instrucción', width='large'),
                                'Distancia': st.column_config.TextColumn('Distancia', width='small'),
                                'Desde Nodo': st.column_config.NumberColumn('Desde', width='small'),
                                'Hacia Nodo': st.column_config.NumberColumn('Hacia', width='small')
                            }
                        )
                        
                        # 9. Mostrar métricas resumen (usando distancia real del gestor)
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Distancia Total", f"{distancia_total_real:.2f} km")
                        with col2:
                            st.metric("Total de Pasos", len(instrucciones))
                        with col3:
                            giros = len([i for i in instrucciones if '→' in i.direccion or '←' in i.direccion])
                            st.metric("Giros", giros)
                        
                        # 10. Opción de descargar instrucciones
                        instrucciones_texto = generador.exportar_instrucciones_texto(instrucciones)
                        pedido_id = gestor.pedido_actual.pedido_id if gestor.pedido_actual else "ruta"
                        st.download_button(
                            label="Descargar Instrucciones (TXT)",
                            data=instrucciones_texto,
                            file_name=f"guia_ruta_{pedido_id}.txt",
                            mime="text/plain",
                            key="download_instrucciones"
                        )
                        
                        # 11. Visualización en mapa (opcional)
                        with st.expander("Ver Mapa Interactivo con Instrucciones", expanded=False):
                            # Calcular centro del mapa (promedio de coordenadas)
                            lat_coords = [inst.lat_origen for inst in instrucciones] + [instrucciones[-1].lat_destino]
                            lon_coords = [inst.lon_origen for inst in instrucciones] + [instrucciones[-1].lon_destino]
                            lat_centro = sum(lat_coords) / len(lat_coords)
                            lon_centro = sum(lon_coords) / len(lon_coords)
                            
                            mapa_instrucciones = generador.visualizar_en_mapa(
                                instrucciones, 
                                center=(lat_centro, lon_centro)
                            )
                            
                            if mapa_instrucciones:
                                folium_static(mapa_instrucciones, width=1200, height=500)
                            else:
                                st.error("No se pudo generar el mapa de instrucciones")
                
                else:
                    st.info("ℹNo hay ruta calculada con camino completo")
        
        except Exception as e:
            st.error(f"❌ Error al generar guía de ruta: {str(e)}")
            import traceback
            with st.expander("Ver detalles del error"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
