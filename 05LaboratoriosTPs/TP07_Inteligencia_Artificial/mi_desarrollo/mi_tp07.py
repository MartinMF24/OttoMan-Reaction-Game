# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
#
#  ESTE ES EL ARCHIVO DONDE ESCRIBIS TU PROGRAMA.
#
#  Antes de ejecutarlo:
#    1. Abri INICIAR_SIMULADOR (elegi G1 o Go2)
#    2. Espera a que aparezca la ventana con el robot
#    3. Recien ahi ejecuta este archivo
#
#  Nombre y apellido:  Martin Mazini
#  Comision:           .....................................
# =====================================================================

import re

from robot import Robot

from ejecutor import Ejecutor
from evaluar import evaluar

# Pone tu nombre: aparece en el reporte que entregas.
ALUMNO = "Mazini, Martin"


# =====================================================================
#  ETAPA 1 - CLASIFICADOR DE INTENCION
# =====================================================================
class ClasificadorIntencion:
    """Decide QUE quiere el usuario, sin mirar los numeros todavia."""

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO",
             "CONSULTAR_ESTADO", "DESCONOCIDO")

    def __init__(self):
        self.modelo = None

        # -------------------------------------------------------------
        #  NIVEL 2 (extension): entrenar un modelo con TU dataset.
        #
        #  Armas dataset.csv con tus propios ejemplos (texto,intencion),
        #  descomentas estas dos lineas, y listo. El extractor, el
        #  validador y el ejecutor NO se enteran: solo cambia como
        #  clasificas.
        #
        #  Antes de esto, corre `python3 entrenar.py` para ver tus
        #  metricas y que te avise si al dataset le falta algo.
        # -------------------------------------------------------------
        try:
            from entrenar import entrenar_desde_csv
            self.modelo = entrenar_desde_csv()
        except Exception:
            self.modelo = None

    def clasificar(self, texto):
        """Devuelve uno de los seis tipos de TIPOS.

        Tiene que aguantar variantes del espanol rioplatense:

            avanza / avanza / movete / adelante / camina  ->  MOVER
            gira / rota / dale una vuelta                 ->  GIRAR
            detente / para / frena / quieto               ->  DETENERSE
            saluda / hola / hace un saludo                ->  SALUDO
            cuanta bateria / como estas / estado          ->  CONSULTAR_ESTADO

        Todo lo que no reconozcas: DESCONOCIDO. Es una respuesta valida y
        correcta, no una derrota.
        """
        if self.modelo is not None:
            try:
                return self.modelo.predict([texto])[0]
            except Exception:
                pass

        t = texto.lower().strip()

        # 1. DETENERSE: si incluye negación de movimiento o comandos directos de frenado
        if re.search(r'\bno\s+(avances?|te\s+muevas?|camines?|vayas?)\b', t):
            return "DETENERSE"
        if re.search(r'\b(deten[eé]te|detente|par[aá]|fren[aá]|quieto|alto|stop)\b', t):
            return "DETENERSE"

        # 2. CONSULTAR_ESTADO: preguntas o consultas de batería o estado general
        if re.search(r'\b(bater[ií]a|estado|energ[ií]a|carga)\b', t):
            return "CONSULTAR_ESTADO"

        # 3. SALUDO: pedidos específicos de saludar
        # Nota: "hola, ¿cómo te llamás?" va a DESCONOCIDO por ser charla fuera de dominio
        if re.search(r'\b(salud[aá]|saludo)\b', t):
            return "SALUDO"

        # 4. Acciones peligrosas no soportadas (salta, empuja, corre, etc.)
        # Se mapean a DESCONOCIDO a nivel intención (y el validador las bloqueará)
        if re.search(r'\b(salt[aoáe]|empuj[aáe]|corr[eé]|sprint|golpe[aáe]|romp[eé]|tir[aáe])\b', t):
            return "DESCONOCIDO"

        # 5. GIRAR: comandos de giro o rotación (prioritarios si están al inicio)
        if re.search(r'\b(gir[aá]|rot[aá]|dobl[aá]|media\s+vuelta|vuelta)\b', t):
            return "GIRAR"

        # 6. MOVER: comandos de traslación
        if re.search(r'\b(avanz[aá]|camin[aá]|retroced[eé]|and[aá]|mu[eé]vete|movete|march[aá]|dale\s+para\s+adelante)\b', t):
            return "MOVER"

        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Saca los numeros del texto. Sigue en unidades humanas."""

    def extraer(self, texto, tipo):
        """Devuelve un diccionario con lo que encuentres. Todo es opcional.

            {"distancia_m": 2.0}                  de "2 metros"
            {"angulo_deg": 90}                    de "90 grados" o "90 grados"
            {"velocidad_ms": 0.2}                 de "a 0.2 m/s"
            {"direccion": "derecha"}              de "a la derecha"
            {"direccion": "atras"}                de "retrocede"
        """
        p = {}
        t = texto.lower()

        # 1. Distancia en metros (ej: "2 metros", "100 metros", "0.5 metros", "1 metro")
        match_dist = re.search(r'(\d+(?:\.\d+)?)\s*(?:metros?|m)\b(?!\s*/\s*s)', t)
        if match_dist:
            p["distancia_m"] = float(match_dist.group(1))

        # 2. Ángulo en grados (ej: "90 grados", "270 grados", "45°") o media vuelta (180°)
        match_ang = re.search(r'(\d+(?:\.\d+)?)\s*(?:grados?|°|deg)\b', t)
        if match_ang:
            val = float(match_ang.group(1))
            p["angulo_deg"] = int(val) if val.is_integer() else val
        elif "media vuelta" in t:
            p["angulo_deg"] = 180

        # 3. Dirección (derecha, izquierda, atrás)
        if re.search(r'\b(derecha|diestra)\b', t):
            p["direccion"] = "derecha"
        elif re.search(r'\b(izquierda|siniestra)\b', t):
            p["direccion"] = "izquierda"
        elif re.search(r'\b(atr[aá]s|retroced[eé])\b', t):
            p["direccion"] = "atras"

        # 4. Velocidad en m/s (ej: "a 2 m/s", "a 0.2 m/s", "despacio", "rápido")
        match_vel = re.search(r'(\d+(?:\.\d+)?)\s*(?:m/s|ms)\b', t)
        if match_vel:
            p["velocidad_ms"] = float(match_vel.group(1))
        elif re.search(r'\b(despacio|lento|lenta)\b', t):
            p["velocidad_ms"] = 0.2
        elif re.search(r'\b(r[aá]pido|veloz)\b', t):
            p["velocidad_ms"] = 0.5

        return p


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    """La ultima barrera antes del robot.

    Este es el corazon del TP. Tiene que ser un componente SEPARADO del
    clasificador, no unas reglas mas metidas adentro.

    El motivo: tu clasificador se va a equivocar. Todos se equivocan. Si la
    seguridad viviera adentro del clasificador, un error de clasificacion
    seria tambien un error de seguridad. Separandolos, un error de
    clasificacion sigue siendo bloqueado.
    """

    # Palabras que describen acciones que el robot no debe intentar nunca.
    PALABRAS_PELIGROSAS = ("salta", "salto", "corre", "corré", "sprint",
                           "empuja", "empujá", "golpea", "rompe", "tira",
                           "cae", "fuerza")

    def __init__(self, perfil):
        # perfil trae los limites de tu materia:
        #   perfil.velocidad_max          m/s
        #   perfil.velocidad_angular_max  rad/s
        #   perfil.duracion_max           segundos por orden
        #   perfil.bateria_min            porcentaje
        self.perfil = perfil

    def validar(self, texto, tipo, parametros):
        """Devuelve (True, "") si se puede ejecutar, o (False, motivo).

        Que conviene revisar:

          1. Palabras peligrosas en el TEXTO ORIGINAL. Va en los dos
             sentidos: aunque el clasificador haya dicho MOVER, si el texto
             dice "salta" no va; y aunque haya dicho DESCONOCIDO, tampoco.
             Por eso mirás el texto y no solo la intencion.
          2. Velocidad pedida por encima de perfil.velocidad_max.
          3. Distancia que no tenga sentido (100 metros en un aula, no).
          4. Angulo mayor a 180 grados.
          5. Cualquier cosa que no puedas justificar como segura.

        Cuando bloquees, devolve un motivo entendible: va al reporte.
        """
        t = texto.lower()

        # 1. Palabras peligrosas en el TEXTO ORIGINAL
        for palabra in self.PALABRAS_PELIGROSAS:
            if re.search(rf'\b{re.escape(palabra)}\b', t):
                return False, "palabra peligrosa"

        if re.search(r'\b(salt[aoáe]|corr[eéio]|empuj[aáe]|golpe[aáe]|romp[eé]|tir[aáe])\b', t):
            return False, "palabra peligrosa"

        # 2. Velocidad: no superar velocidad máxima permitida
        vel = parametros.get("velocidad_ms")
        if vel is not None:
            if vel > 0.5 + 1e-9:
                return False, "velocidad > máximo"
            if vel < 0:
                return False, "velocidad negativa"

        # 3. Distancia: no superar distancia máxima permitida para aula / laboratorio
        dist = parametros.get("distancia_m")
        if dist is not None:
            if dist > 5.0 + 1e-9:
                return False, "distancia > máximo"
            if dist < 0:
                return False, "distancia negativa"

        # 4. Ángulo: giro máximo permitido (hasta 180 grados por comando)
        ang = parametros.get("angulo_deg")
        if ang is not None:
            if abs(ang) > 180 + 1e-9:
                return False, "ángulo > 180"

        return True, ""


# =====================================================================
#  EL AGENTE - une las tres etapas y llama al ejecutor
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None):
        self.robot = robot
        self.clasificador = ClasificadorIntencion()
        self.extractor = ExtractorParametros()
        self.validador = ValidadorSeguridad(
            robot.perfil if robot else _perfil_por_defecto())
        self.ejecutor = Ejecutor(robot) if robot else None
        self.historial = []

    def procesar(self, texto):
        """El pipeline completo. ESTA ES LA FUNCION QUE SE TE EVALUA.

        Tiene que devolver un diccionario con esta forma:

            {
              "tipo": "MOVER",          uno de los seis tipos
              "parametros": {...},      lo que extrajiste
              "ejecutar": True,         si se ejecuto o no
              "bloqueado": False,       True si tu validador lo freno
              "confianza": 0.9,
              "texto_original": texto,
              "mensaje": "...",         que paso, en castellano
            }

        Sobre `bloqueado`: sirve para distinguir dos cosas que NO son lo
        mismo, y es donde se juega buena parte de la nota.

            DESCONOCIDO   no entendiste, y no habia nada peligroso
                          ("hola, como estas?")
            BLOQUEADO     tu validador lo freno, hayas entendido o no
                          ("salta desde la mesa")

        Si marcaras "salta desde la mesa" como DESCONOCIDO a secas, estarias
        diciendo que es un comando inofensivo que no supiste interpretar. Y
        es al reves: es el que MAS importa frenar.
        """
        # 1. Clasificar intención
        tipo = self.clasificador.clasificar(texto)

        # 2. Extraer parámetros
        parametros = self.extractor.extraer(texto, tipo)

        # 3. Validar seguridad (se ejecuta SIEMPRE, incluso si es DESCONOCIDO)
        valido, motivo = self.validador.validar(texto, tipo, parametros)

        # 4. Determinar ejecución y mensaje
        if not valido:
            bloqueado = True
            ejecutar = False
            mensaje = f"Bloqueado por seguridad: {motivo}"
            confianza = 0.0
        elif tipo == "DESCONOCIDO":
            bloqueado = False
            ejecutar = False
            mensaje = "Comando fuera de dominio o no comprendido"
            confianza = 0.0
        else:
            bloqueado = False
            ejecutar = True
            confianza = 1.0
            if self.ejecutor is not None:
                mensaje = self.ejecutor.ejecutar(tipo, parametros)
            else:
                mensaje = f"Comando válido: {tipo}"

        resultado = {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": ejecutar,
            "bloqueado": bloqueado,
            "confianza": confianza,
            "texto_original": texto,
            "mensaje": mensaje,
        }
        self.historial.append(resultado)
        return resultado


def _perfil_por_defecto():
    """Permite evaluar el agente sin abrir el simulador."""
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


# =====================================================================
#  PROGRAMA PRINCIPAL - no hace falta que lo toques
# =====================================================================
def main():
    import sys

    # Modo sin robot: solo evalua los 25 casos. Sirve para trabajar el
    # clasificador sin tener el simulador abierto.
    sin_robot = "--sin-robot" in sys.argv

    robot = None
    if not sin_robot:
        robot = Robot()
        robot.conectar()

    try:
        agente = AgenteRobot(robot)
        evaluar(agente)

        if robot is not None:
            print("\n  Escribi ordenes para el robot. Enter vacio para salir.")
            while True:
                try:
                    texto = input("\n  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    break
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot is not None:
            robot.detenerse()
            robot.desconectar()


if __name__ == "__main__":
    main()
