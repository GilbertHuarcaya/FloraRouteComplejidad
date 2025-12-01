"""
Test unitario para GeneradorGuiaRuta

Verifica funcionalidad de generacion de instrucciones de navegacion
"""

import unittest
import math
from src.controllers.generador_guia_ruta import GeneradorGuiaRuta, InstruccionRuta


class TestGeneradorGuiaRuta(unittest.TestCase):
    """Test suite para GeneradorGuiaRuta"""
    
    def setUp(self):
        """Configuracion inicial para cada test"""
        # Crear grafo de prueba simple
        self.grafo_test = {
            1: {2: 1200.5, 5: 3000.0},
            2: {1: 1200.5, 3: 800.3},
            3: {2: 800.3, 4: 2300.7},
            4: {3: 2300.7, 5: 1500.0},
            5: {4: 1500.0, 1: 3000.0}
        }
        
        # Coordenadas de prueba (Lima)
        self.nodos_coords_test = {
            1: (-12.046374, -77.042793),  # Plaza de Armas
            2: (-12.055000, -77.038000),  # ~1km al sur
            3: (-12.061000, -77.045000),  # Giro oeste
            4: (-12.082000, -77.048000),  # Sur
            5: (-12.050000, -77.070000)   # Oeste
        }
        
        self.generador = GeneradorGuiaRuta(self.grafo_test, self.nodos_coords_test)
    
    def test_inicializacion(self):
        """Verifica que el generador se inicializa correctamente"""
        self.assertIsNotNone(self.generador.grafo)
        self.assertIsNotNone(self.generador.nodos_coords)
        self.assertEqual(len(self.generador.nodos_coords), 5)
    
    def test_calcular_bearing_norte(self):
        """Verifica calculo de bearing hacia el norte"""
        # Desde Plaza de Armas (-12.046) hacia mas norte (-12.036)
        lat1, lon1 = -12.046374, -77.042793
        lat2, lon2 = -12.036374, -77.042793  # Mismo lon, lat mas al norte
        
        bearing = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2, lon2)
        
        # Bearing hacia norte deberia ser cercano a 0° o 360°
        self.assertTrue(bearing < 10 or bearing > 350, 
                       f"Bearing hacia norte: {bearing}°")
    
    def test_calcular_bearing_sur(self):
        """Verifica calculo de bearing hacia el sur"""
        lat1, lon1 = -12.046374, -77.042793
        lat2, lon2 = -12.056374, -77.042793  # Mismo lon, lat mas al sur
        
        bearing = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2, lon2)
        
        # Bearing hacia sur deberia ser cercano a 180°
        self.assertTrue(170 < bearing < 190, 
                       f"Bearing hacia sur: {bearing}°")
    
    def test_calcular_bearing_este(self):
        """Verifica calculo de bearing hacia el este"""
        lat1, lon1 = -12.046374, -77.042793
        lat2, lon2 = -12.046374, -77.032793  # Mismo lat, lon mas al este
        
        bearing = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2, lon2)
        
        # Bearing hacia este deberia ser cercano a 90°
        self.assertTrue(80 < bearing < 100, 
                       f"Bearing hacia este: {bearing}°")
    
    def test_calcular_bearing_oeste(self):
        """Verifica calculo de bearing hacia el oeste"""
        lat1, lon1 = -12.046374, -77.042793
        lat2, lon2 = -12.046374, -77.052793  # Mismo lat, lon mas al oeste
        
        bearing = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2, lon2)
        
        # Bearing hacia oeste deberia ser cercano a 270°
        self.assertTrue(260 < bearing < 280, 
                       f"Bearing hacia oeste: {bearing}°")
    
    def test_clasificar_angulo_recto(self):
        """Verifica clasificacion de angulo recto"""
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(0), "↑ Recto")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(10), "↑ Recto")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-10), "↑ Recto")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(20), "↑ Recto")
    
    def test_clasificar_angulo_derecha(self):
        """Verifica clasificacion de giros a la derecha"""
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(45), "↗ Ligera derecha")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(90), "→ Derecha")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(135), "↘ Derecha cerrada")
    
    def test_clasificar_angulo_izquierda(self):
        """Verifica clasificacion de giros a la izquierda"""
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-45), "↖ Ligera izquierda")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-90), "← Izquierda")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-135), "↙ Izquierda cerrada")
    
    def test_clasificar_angulo_retorno(self):
        """Verifica clasificacion de retorno (U-turn)"""
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(175), "↩ Retorno")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-175), "↩ Retorno")
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(180), "↩ Retorno")
    
    def test_generar_guia_secuencia_simple(self):
        """Verifica generacion de guia para secuencia simple"""
        secuencia = [1, 2, 3]
        instrucciones = self.generador.generar_guia(secuencia)
        
        self.assertEqual(len(instrucciones), 2)  # n-1 instrucciones
        
        # Verificar primera instruccion
        inst1 = instrucciones[0]
        self.assertEqual(inst1.paso, 1)
        self.assertEqual(inst1.nodo_origen, 1)
        self.assertEqual(inst1.nodo_destino, 2)
        self.assertEqual(inst1.direccion, "🚀 Salida")
        self.assertGreater(inst1.distancia_km, 0)
        
        # Verificar segunda instruccion
        inst2 = instrucciones[1]
        self.assertEqual(inst2.paso, 2)
        self.assertEqual(inst2.nodo_origen, 2)
        self.assertEqual(inst2.nodo_destino, 3)
    
    def test_generar_guia_secuencia_vacia(self):
        """Verifica comportamiento con secuencia vacia"""
        instrucciones = self.generador.generar_guia([])
        self.assertEqual(len(instrucciones), 0)
    
    def test_generar_guia_un_nodo(self):
        """Verifica comportamiento con un solo nodo"""
        instrucciones = self.generador.generar_guia([1])
        self.assertEqual(len(instrucciones), 0)
    
    def test_obtener_datos_arista(self):
        """Verifica extraccion de datos de arista"""
        datos = self.generador._obtener_datos_arista(1, 2)
        
        self.assertIn('calle', datos)
        self.assertIn('distancia_km', datos)
        self.assertIn('lat_origen', datos)
        self.assertIn('lon_origen', datos)
        self.assertIn('lat_destino', datos)
        self.assertIn('lon_destino', datos)
        
        # Verificar distancia correcta
        self.assertAlmostEqual(datos['distancia_km'], 1200.5 / 1000, places=3)
        
        # Verificar coordenadas
        self.assertEqual(datos['lat_origen'], -12.046374)
        self.assertEqual(datos['lon_origen'], -77.042793)
    
    def test_obtener_datos_arista_inexistente(self):
        """Verifica manejo de arista inexistente"""
        # Nodos sin conexion directa
        datos = self.generador._obtener_datos_arista(1, 4)
        
        # Debe retornar estructura valida pero con distancia 0
        self.assertEqual(datos['distancia_km'], 0)
        self.assertIn('calle', datos)
    
    def test_calcular_direccion(self):
        """Verifica calculo de direccion entre tres nodos"""
        # Secuencia: 1 -> 2 -> 3
        direccion = self.generador._calcular_direccion(1, 2, 3)
        
        # Debe retornar alguna direccion valida
        direcciones_validas = [
            "↑ Recto", "↗ Ligera derecha", "→ Derecha", "↘ Derecha cerrada",
            "↖ Ligera izquierda", "← Izquierda", "↙ Izquierda cerrada", "↩ Retorno"
        ]
        self.assertIn(direccion, direcciones_validas)
    
    def test_generar_instruccion_salida(self):
        """Verifica generacion de instruccion de salida"""
        inst = self.generador._generar_instruccion(
            "🚀 Salida", "Av. Arequipa", 1.5, es_salida=True
        )
        
        self.assertIn("Salga", inst)
        self.assertIn("1.50", inst)
    
    def test_generar_instruccion_recto(self):
        """Verifica generacion de instruccion recto"""
        inst = self.generador._generar_instruccion(
            "↑ Recto", "Jr. Lima", 0.8, es_salida=False
        )
        
        self.assertIn("Continúe recto", inst)
        self.assertIn("0.80", inst)
    
    def test_generar_instruccion_derecha(self):
        """Verifica generacion de instruccion giro derecha"""
        inst = self.generador._generar_instruccion(
            "→ Derecha", "Av. Javier Prado", 2.3, es_salida=False
        )
        
        self.assertIn("Gire a la derecha", inst)
        self.assertIn("2.30", inst)
    
    def test_generar_instruccion_izquierda(self):
        """Verifica generacion de instruccion giro izquierda"""
        inst = self.generador._generar_instruccion(
            "← Izquierda", "Av. Salaverry", 1.2, es_salida=False
        )
        
        self.assertIn("Gire a la izquierda", inst)
        self.assertIn("1.20", inst)
    
    def test_calcular_distancia_haversine(self):
        """Verifica calculo de distancia con formula de Haversine"""
        # Plaza de Armas a Miraflores (aprox 8-9 km)
        lat1, lon1 = -12.046374, -77.042793
        lat2, lon2 = -12.119294, -77.034511
        
        distancia = self.generador.calcular_distancia_haversine(lat1, lon1, lat2, lon2)
        
        # Distancia aproximada 8-9 km
        self.assertTrue(7 < distancia < 10, 
                       f"Distancia calculada: {distancia} km")
    
    def test_calcular_distancia_haversine_mismo_punto(self):
        """Verifica distancia cero entre mismo punto"""
        lat, lon = -12.046374, -77.042793
        distancia = self.generador.calcular_distancia_haversine(lat, lon, lat, lon)
        
        self.assertAlmostEqual(distancia, 0, places=5)
    
    def test_validar_instrucciones_validas(self):
        """Verifica validacion de instrucciones correctas"""
        secuencia = [1, 2, 3, 4]
        instrucciones = self.generador.generar_guia(secuencia)
        
        es_valido, error = self.generador.validar_instrucciones(instrucciones)
        
        self.assertTrue(es_valido)
        self.assertIsNone(error)
    
    def test_validar_instrucciones_vacias(self):
        """Verifica validacion de lista vacia"""
        es_valido, error = self.generador.validar_instrucciones([])
        
        self.assertFalse(es_valido)
        self.assertIsNotNone(error)
    
    def test_validar_instrucciones_secuencia_incorrecta(self):
        """Verifica deteccion de secuencia de pasos incorrecta"""
        # Crear instruccion con paso incorrecto
        inst_incorrecta = InstruccionRuta(
            paso=5,  # Deberia ser 1
            nodo_origen=1,
            nodo_destino=2,
            calle="Test",
            distancia_km=1.0,
            direccion="↑ Recto",
            instruccion="Test",
            lat_origen=-12.0,
            lon_origen=-77.0,
            lat_destino=-12.0,
            lon_destino=-77.0
        )
        
        es_valido, error = self.generador.validar_instrucciones([inst_incorrecta])
        
        self.assertFalse(es_valido)
        self.assertIn("Secuencia de pasos incorrecta", error)
    
    def test_generar_guia_con_waypoints(self):
        """Verifica generacion de guia con marcadores de waypoints"""
        secuencia = [1, 2, 3, 4]
        tipos_waypoint = {
            2: "destino",
            3: "vivero",
            4: "destino"
        }
        
        instrucciones = self.generador.generar_guia_con_waypoints(secuencia, tipos_waypoint)
        
        self.assertEqual(len(instrucciones), 3)
        
        # Verificar marcadores
        self.assertIn("📦 [ENTREGA]", instrucciones[0].instruccion)  # Nodo 2 es destino
        self.assertIn("🏪 [REABASTECIMIENTO]", instrucciones[1].instruccion)  # Nodo 3 es vivero
        self.assertIn("📦 [ENTREGA]", instrucciones[2].instruccion)  # Nodo 4 es destino
    
    def test_coherencia_distancias(self):
        """Verifica que distancias sean coherentes entre grafo y Haversine"""
        # Obtener distancia del grafo
        dist_grafo = self.grafo_test[1][2] / 1000  # km
        
        # Calcular distancia Haversine
        lat1, lon1 = self.nodos_coords_test[1]
        lat2, lon2 = self.nodos_coords_test[2]
        dist_haversine = self.generador.calcular_distancia_haversine(lat1, lon1, lat2, lon2)
        
        # Distancias deben ser similares (tolerancia 20% por diferencia metodos)
        ratio = dist_grafo / dist_haversine
        self.assertTrue(0.8 < ratio < 1.2, 
                       f"Ratio distancias: {ratio} (grafo={dist_grafo}, haversine={dist_haversine})")


class TestFormulasGeometricas(unittest.TestCase):
    """Test suite para formulas geometricas"""
    
    def test_bearing_invariancia_escala(self):
        """Verifica que bearing no depende de la escala de distancia"""
        # Mismo bearing para puntos a diferente distancia en misma direccion
        lat1, lon1 = -12.0, -77.0
        
        # Punto cercano
        lat2_cerca, lon2_cerca = -12.001, -77.0
        bearing_cerca = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2_cerca, lon2_cerca)
        
        # Punto lejano (misma direccion)
        lat2_lejos, lon2_lejos = -12.01, -77.0
        bearing_lejos = GeneradorGuiaRuta.calcular_bearing(lat1, lon1, lat2_lejos, lon2_lejos)
        
        # Bearings deben ser muy similares
        self.assertAlmostEqual(bearing_cerca, bearing_lejos, places=1)
    
    def test_clasificacion_angulo_limites(self):
        """Verifica comportamiento en limites de rangos"""
        # Limite inferior recto
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(-20), "↑ Recto")
        
        # Limite superior recto
        self.assertEqual(GeneradorGuiaRuta.clasificar_angulo(20), "↑ Recto")
        
        # Justo fuera de recto
        self.assertNotEqual(GeneradorGuiaRuta.clasificar_angulo(21), "↑ Recto")
        self.assertNotEqual(GeneradorGuiaRuta.clasificar_angulo(-21), "↑ Recto")


if __name__ == '__main__':
    unittest.main(verbosity=2)
