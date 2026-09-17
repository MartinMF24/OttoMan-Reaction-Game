# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  DUELO DE REFLEJOS EN VIVO — HUMANO vs ROBOT UNITREE G1
#
#  El jugador humano compite contra el robot humanoide Unitree G1.
#  - El robot reacciona con cinemática inversa (IK DLS) y rotación motriz.
#  - El humano pulsa las teclas 1, 2, 3, 4, 5, 6 para cada luz.
#  - Las teclas van estrictamente de izquierda a derecha según la cámara.
#  - Cuenta atrás inicial de 5 a 0 segundos antes de comenzar la partida.
#  - Marcador Premier League en vivo y reporte gráfico final de rendimiento.
# =====================================================================

import argparse
import ctypes
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

# Asegurar path al entorno para importar los modelos del robot
_ENTORNO = Path(__file__).resolve().parent.parent / "entorno"
if str(_ENTORNO) not in sys.path:
    sys.path.insert(0, str(_ENTORNO))

import mujoco
try:
    import mujoco.viewer
except ImportError:
    pass
from sim.robots import G1

try:
    from mi_desarrollo.marcador_premier import MarcadorPremierLeague
except ImportError:
    from marcador_premier import MarcadorPremierLeague


# =====================================================================
#  1. MODELO DE LUCES CON MAPEO DE IZQUIERDA A DERECHA (TECLAS 1 A 6)
# =====================================================================
# Con la cámara situada de frente al robot mirando su torso y rostro (azimuth=180),
# el eje Y mundial negativo queda a la IZQUIERDA de la pantalla,
# y el eje Y positivo queda a la DERECHA de la pantalla.
#
# Por tanto, ordenadas de izquierda a derecha para el jugador:
#   Tecla 1: y = -0.37 (Extrema Izquierda en pantalla)
#   Tecla 2: y = -0.25 (Arriba Izquierda en pantalla)
#   Tecla 3: y = -0.18 (Abajo Centro-Izq en pantalla)
#   Tecla 4: y = +0.18 (Abajo Centro-Der en pantalla)
#   Tecla 5: y = +0.25 (Arriba Derecha en pantalla)
#   Tecla 6: y = +0.37 (Extrema Derecha en pantalla)
# =====================================================================

@dataclass
class LuzHumanoVsRobot:
    id: int                       # 0 a 5
    tecla: str                    # '1', '2', '3', '4', '5', '6'
    nombre: str
    posicion: np.ndarray          # [x, y, z] en metros
    color_on: np.ndarray          # RGBA encendido (brillante)
    color_off: np.ndarray         # RGBA apagado (tenue)
    brazo_robot: str              # 'izquierdo' o 'derecho' para el robot
    giro_grados: float            # Giro corporal del robot hacia la luz
    encendida: bool = False
    radio: float = 0.045


class EntornoLucesDuelo:
    """Gestiona las 6 luces LED mapeadas de izquierda a derecha con teclas 1 a 6."""

    def __init__(self):
        self.luces = [
            LuzHumanoVsRobot(
                id=0,
                tecla="1",
                nombre="Luz 1 (Ext. Izq)",
                posicion=np.array([0.20, -0.37, 0.95]),
                color_on=np.array([1.0, 0.15, 0.25, 0.98], dtype=np.float32),  # Coral / Rojo vivo
                color_off=np.array([0.30, 0.08, 0.10, 0.25], dtype=np.float32),
                brazo_robot="derecho",
                giro_grados=-35.0,
            ),
            LuzHumanoVsRobot(
                id=1,
                tecla="2",
                nombre="Luz 2 (Arr. Izq)",
                posicion=np.array([0.35, -0.25, 1.05]),
                color_on=np.array([1.0, 0.55, 0.05, 0.98], dtype=np.float32),  # Naranja
                color_off=np.array([0.30, 0.18, 0.05, 0.25], dtype=np.float32),
                brazo_robot="derecho",
                giro_grados=-15.0,
            ),
            LuzHumanoVsRobot(
                id=2,
                tecla="3",
                nombre="Luz 3 (Abj. Centro-Izq)",
                posicion=np.array([0.30, -0.18, 0.88]),
                color_on=np.array([1.0, 0.92, 0.05, 0.98], dtype=np.float32),  # Amarillo oro
                color_off=np.array([0.28, 0.25, 0.05, 0.25], dtype=np.float32),
                brazo_robot="derecho",
                giro_grados=-5.0,
            ),
            LuzHumanoVsRobot(
                id=3,
                tecla="4",
                nombre="Luz 4 (Abj. Centro-Der)",
                posicion=np.array([0.30, +0.18, 0.88]),
                color_on=np.array([0.05, 1.0, 0.40, 0.98], dtype=np.float32),  # Verde lima
                color_off=np.array([0.08, 0.28, 0.12, 0.25], dtype=np.float32),
                brazo_robot="izquierdo",
                giro_grados=+5.0,
            ),
            LuzHumanoVsRobot(
                id=4,
                tecla="5",
                nombre="Luz 5 (Arr. Der)",
                posicion=np.array([0.35, +0.25, 1.05]),
                color_on=np.array([0.05, 0.80, 1.0, 0.98], dtype=np.float32),   # Azul cian
                color_off=np.array([0.08, 0.22, 0.32, 0.25], dtype=np.float32),
                brazo_robot="izquierdo",
                giro_grados=+15.0,
            ),
            LuzHumanoVsRobot(
                id=5,
                tecla="6",
                nombre="Luz 6 (Ext. Der)",
                posicion=np.array([0.20, +0.37, 0.95]),
                color_on=np.array([0.95, 0.15, 0.90, 0.98], dtype=np.float32),  # Magenta neón
                color_off=np.array([0.28, 0.08, 0.25, 0.25], dtype=np.float32),
                brazo_robot="izquierdo",
                giro_grados=+35.0,
            ),
        ]
        self.indice_activa = 0
        self.activar_luz(0)

    def activar_luz(self, indice: int):
        self.indice_activa = indice % len(self.luces)
        for i, luz in enumerate(self.luces):
            luz.encendida = (i == self.indice_activa)

    def activar_aleatoria(self) -> LuzHumanoVsRobot:
        opciones = [i for i in range(len(self.luces)) if i != self.indice_activa]
        self.activar_luz(random.choice(opciones))
        return self.luz_activa

    @property
    def luz_activa(self) -> LuzHumanoVsRobot:
        return self.luces[self.indice_activa]

    def dibujar_en_escena(self, user_scn) -> int:
        """Renderiza pedestales, esferas LED y auras brillantes en el visor MuJoCo."""
        identidad = np.eye(3).flatten()
        n = 0
        color_pedestal = np.array([0.24, 0.26, 0.28, 0.90], dtype=np.float32)

        def _geom(tipo, size, pos, rgba):
            nonlocal n
            if n >= user_scn.maxgeom:
                return
            mujoco.mjv_initGeom(
                user_scn.geoms[n], tipo,
                np.array(size, dtype=np.float64),
                np.array(pos, dtype=np.float64),
                identidad, np.array(rgba, dtype=np.float32)
            )
            n += 1

        for luz in self.luces:
            x, y, z = luz.posicion
            # 1. Pedestal cilíndrico desde el suelo hasta la luz
            h_pedestal = z - luz.radio
            if h_pedestal > 0:
                _geom(
                    mujoco.mjtGeom.mjGEOM_CYLINDER,
                    [0.015, h_pedestal / 2.0, 0.0],
                    [x, y, h_pedestal / 2.0],
                    color_pedestal
                )

            # 2. Esfera LED
            color = luz.color_on if luz.encendida else luz.color_off
            radio_actual = luz.radio if luz.encendida else (luz.radio * 0.85)
            _geom(
                mujoco.mjtGeom.mjGEOM_SPHERE,
                [radio_actual, radio_actual, radio_actual],
                [x, y, z],
                color
            )

            # 3. Halo translúcido pulsante para la luz activa
            if luz.encendida:
                halo = color.copy()
                halo[3] = 0.38
                _geom(
                    mujoco.mjtGeom.mjGEOM_SPHERE,
                    [luz.radio * 1.40, luz.radio * 1.40, luz.radio * 1.40],
                    [x, y, z],
                    halo
                )

        user_scn.ngeom = n
        return n


# =====================================================================
#  2. SISTEMA DE ENTRADA ASÍNCRONO PARA EL HUMANO (TECLAS 1 A 6)
# =====================================================================
class EntradaTecladoHumano:
    """Captura las teclas 1 a 6 con latencia cero a nivel de hardware y visor."""

    def __init__(self):
        # Códigos virtuales Windows para teclas 1-6 (fila superior) y teclado numérico
        self.mapa_vk = {
            "1": (0x31, 0x61),  # VK_1, VK_NUMPAD1
            "2": (0x32, 0x62),
            "3": (0x33, 0x63),
            "4": (0x34, 0x64),
            "5": (0x35, 0x65),
            "6": (0x36, 0x66),
        }
        self.estados_previos = {tecla: False for tecla in self.mapa_vk}
        self.ultima_tecla_pulsada: Optional[str] = None
        self.tiempo_ultima_pulsacion: float = 0.0
        self.cualquier_tecla_pulsada: bool = False

    def limpiar(self):
        """Reinicia el estado de teclas acumuladas."""
        self.ultima_tecla_pulsada = None
        self.tiempo_ultima_pulsacion = 0.0
        self.cualquier_tecla_pulsada = False
        # Resetear estados de hardware
        try:
            get_async_key = ctypes.windll.user32.GetAsyncKeyState
            for codes in self.mapa_vk.values():
                for vk in codes:
                    get_async_key(vk)
        except Exception:
            pass

    def callback_visor(self, keycode: int):
        """Callback GLFW nativo de MuJoCo viewer."""
        self.cualquier_tecla_pulsada = True
        # GLFW: 49 ('1') a 54 ('6'), y teclado numérico 321 a 326
        tecla = None
        if 49 <= keycode <= 54:
            tecla = str(keycode - 48)
        elif 321 <= keycode <= 326:
            tecla = str(keycode - 320)

        if tecla:
            self.ultima_tecla_pulsada = tecla
            self.tiempo_ultima_pulsacion = time.perf_counter()

    def consultar(self) -> Optional[str]:
        """Sondea el estado instantáneo de teclas en Windows."""
        # 1. Si el callback del visor ya registró una pulsación, consumirla
        if self.ultima_tecla_pulsada:
            res = self.ultima_tecla_pulsada
            self.ultima_tecla_pulsada = None
            return res

        # 2. Consultar Windows GetAsyncKeyState a nivel de sistema operativo
        try:
            get_async_key = ctypes.windll.user32.GetAsyncKeyState
            for tecla, codes in self.mapa_vk.items():
                presionada = any(bool(get_async_key(vk) & 0x8000) for vk in codes)
                # Detección de flanco ascendente (key down nuevo)
                if presionada and not self.estados_previos[tecla]:
                    self.estados_previos[tecla] = True
                    return tecla
                elif not presionada:
                    self.estados_previos[tecla] = False
        except Exception:
            pass

        # 3. Fallback para consola (msvcrt)
        try:
            import msvcrt
            if msvcrt.kbhit():
                char = msvcrt.getch().decode("utf-8", errors="ignore")
                if char in self.mapa_vk:
                    return char
        except Exception:
            pass

        return None

    def consultar_cualquier_tecla(self) -> bool:
        """Detecta si se presionó cualquier tecla o botón para continuar o salir."""
        if self.cualquier_tecla_pulsada:
            self.cualquier_tecla_pulsada = False
            return True

        try:
            get_async_key = ctypes.windll.user32.GetAsyncKeyState
            teclas_chequeo = [0x20, 0x0D, 0x1B, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36]
            for vk in teclas_chequeo:
                if bool(get_async_key(vk) & 0x8000):
                    return True
        except Exception:
            pass

        try:
            import msvcrt
            if msvcrt.kbhit():
                msvcrt.getch()
                return True
        except Exception:
            pass

        return False


# =====================================================================
#  3. CONTROLADOR CINEMÁTICO DEL ROBOT UNITREE G1
# =====================================================================
class RobotCompetidorG1:
    """Gestiona el robot Unitree G1: torso, brazos y cinemática inversa (IK)."""

    def __init__(self, dificultad: str = "medio"):
        ruta_escena = G1.ruta_escena()
        if not ruta_escena or not os.path.exists(ruta_escena):
            raise FileNotFoundError("No se encontró el modelo XML del G1.")

        self.model = mujoco.MjModel.from_xml_path(ruta_escena)
        self.data = mujoco.MjData(self.model)

        # Configuración de latencia y destreza motriz según dificultad
        if dificultad == "facil":
            self.latencia_min, self.latencia_max = 0.16, 0.26
            self.ganancia_ik = 0.32
            self.ganancia_giro = 0.14
            self.nombre_dificultad = "Fácil (Entrenamiento)"
        elif dificultad == "dificil":
            self.latencia_min, self.latencia_max = 0.06, 0.12
            self.ganancia_ik = 0.44
            self.ganancia_giro = 0.22
            self.nombre_dificultad = "Difícil (Premier League)"
        else:
            self.latencia_min, self.latencia_max = 0.10, 0.18
            self.ganancia_ik = 0.38
            self.ganancia_giro = 0.18
            self.nombre_dificultad = "Medio (Competitivo)"

        self.yaw_actual = 0.0

        # Cuerpos de las manos
        self.id_mano_izq = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "left_wrist_yaw_link")
        self.id_mano_der = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "right_wrist_yaw_link")

        # DOFs de los brazos en qvel
        self.dofs_izq = list(range(21, 28))
        self.dofs_der = list(range(28, 35))

        # Postura de guardia inicial
        self.pose_guardia = {
            15: 0.25,   # left_shoulder_pitch
            22: 0.25,   # right_shoulder_pitch
            18: -0.45,  # left_elbow
            25: -0.45,  # right_elbow
        }
        self.resetear_pose_inicial()

    def resetear_pose_inicial(self):
        """Ubica al robot de pie en postura frontal lista para el duelo."""
        self.yaw_actual = 0.0
        self.data.qpos[0:7] = [0.0, 0.0, 0.793, 1.0, 0.0, 0.0, 0.0]
        self.data.qpos[7:] = 0.0
        for idx, val in G1.pose_de_pie.items():
            self.data.qpos[7 + idx] = val
        for idx, val in self.pose_guardia.items():
            self.data.qpos[7 + idx] = val
        mujoco.mj_forward(self.model, self.data)

    def posicion_mano(self, brazo: str) -> np.ndarray:
        body_id = self.id_mano_izq if brazo == "izquierdo" else self.id_mano_der
        return self.data.xpos[body_id].copy()

    def paso_ik_y_giro(self, luz: LuzHumanoVsRobot, lambda_dls: float = 0.015) -> float:
        """Orienta el torso y proyecta el brazo con DLS IK hacia la luz."""
        brazo = luz.brazo_robot
        objetivo = luz.posicion
        giro_deg = luz.giro_grados

        # 1. Giro del cuerpo hacia el ángulo de la esfera
        yaw_rad = math.radians(giro_deg)
        self.yaw_actual += self.ganancia_giro * (yaw_rad - self.yaw_actual)
        self.data.qpos[3] = math.cos(self.yaw_actual / 2.0)
        self.data.qpos[6] = math.sin(self.yaw_actual / 2.0)
        mujoco.mj_forward(self.model, self.data)

        # 2. Cinemática inversa
        body_id = self.id_mano_izq if brazo == "izquierdo" else self.id_mano_der
        dofs = self.dofs_izq if brazo == "izquierdo" else self.dofs_der

        pos_mano = self.data.xpos[body_id]
        error = objetivo - pos_mano
        distancia = float(np.linalg.norm(error))

        if distancia < 1e-4:
            return distancia

        jacp = np.zeros((3, self.model.nv))
        mujoco.mj_jacBody(self.model, self.data, jacp, None, body_id)
        J_arm = jacp[:, dofs]

        # Damped Least Squares
        A = J_arm @ J_arm.T + (lambda_dls ** 2) * np.eye(3)
        dq = J_arm.T @ np.linalg.solve(A, error)
        dq = np.clip(dq, -0.25, 0.25)

        for i, dof in enumerate(dofs):
            qpos_idx = dof + 1
            jnt_idx = self.model.dof_jntid[dof]
            r_min, r_max = self.model.jnt_range[jnt_idx]
            nuevo_val = self.data.qpos[qpos_idx] + self.ganancia_ik * dq[i]
            if r_min < r_max:
                nuevo_val = np.clip(nuevo_val, r_min, r_max)
            self.data.qpos[qpos_idx] = nuevo_val

        mujoco.mj_forward(self.model, self.data)
        return float(np.linalg.norm(objetivo - self.data.xpos[body_id]))

    def retraer_a_guardia(self, brazo: str, pasos: int = 8):
        """Retrae suavemente el brazo a la postura de guardia."""
        dofs = self.dofs_izq if brazo == "izquierdo" else self.dofs_der
        for _ in range(pasos):
            for dof in dofs:
                qpos_idx = dof + 1
                target_val = 0.0
                if dof in (21, 28):
                    target_val = 0.25
                elif dof in (24, 31):
                    target_val = -0.45
                self.data.qpos[qpos_idx] += 0.22 * (target_val - self.data.qpos[qpos_idx])
            mujoco.mj_forward(self.model, self.data)


# =====================================================================
#  4. MOTOR DE DUELO: HUMANO vs ROBOT
# =====================================================================
class JuegoHumanoVsRobot:
    """Gestiona la partida completa, cuenta regresiva, marcador y métricas."""

    def __init__(self, dificultad: str = "medio"):
        self.entorno = EntornoLucesDuelo()
        self.robot = RobotCompetidorG1(dificultad=dificultad)
        self.teclado = EntradaTecladoHumano()
        self.marcador = MarcadorPremierLeague()

        self.puntos_humano = 0
        self.puntos_robot = 0
        self.historial_rondas = []

    def disputar_ronda(
        self,
        callback_frame=None,
        tiempo_max_ronda: float = 2.5,
        umbral_toque_robot: float = 0.052,
        simular_humano: bool = False
    ) -> dict:
        """Disputa una luz: el primero entre el humano y el robot en reaccionar suma el punto."""
        luz = self.entorno.luz_activa
        self.teclado.limpiar()

        latencia_robot = random.uniform(self.robot.latencia_min, self.robot.latencia_max)
        t_inicio = time.perf_counter()

        ganador = None
        t_reaccion = None
        dist_robot_final = 99.0
        tecla_pulsada = None

        # Si corre en modo headless sin ventana, simular tiempo de reacción humano realista
        tiempo_simulado_humano = random.uniform(0.18, 0.32) if simular_humano else 999.0

        while (time.perf_counter() - t_inicio) < tiempo_max_ronda:
            t_transcurrido = time.perf_counter() - t_inicio

            # 1. Movimiento del robot (tras su latencia física)
            if t_transcurrido >= latencia_robot:
                dist_robot_final = self.robot.paso_ik_y_giro(luz)

            if callback_frame:
                callback_frame()

            # 2. Consultar entrada del humano
            tecla = self.teclado.consultar()
            if simular_humano and t_transcurrido >= tiempo_simulado_humano:
                tecla = luz.tecla  # Acierto simulado

            if tecla:
                tecla_pulsada = tecla
                t_reaccion = t_transcurrido
                if tecla == luz.tecla:
                    ganador = "HUMANO"
                    self.puntos_humano += 1
                else:
                    ganador = "ROBOT G1 (FALLO HUMANO)"
                    self.puntos_robot += 1
                break

            # 3. Consultar si el robot tocó físicamente la luz
            if dist_robot_final <= umbral_toque_robot:
                ganador = "ROBOT G1"
                self.puntos_robot += 1
                t_reaccion = t_transcurrido
                break

            time.sleep(0.005)

        if ganador is None:
            ganador = "NINGUNO (TIMEOUT)"
            t_reaccion = tiempo_max_ronda

        info_ronda = {
            "ronda": len(self.historial_rondas) + 1,
            "luz_id": luz.id,
            "tecla_correcta": luz.tecla,
            "tecla_pulsada": tecla_pulsada or "---",
            "luz_nombre": luz.nombre,
            "ganador": ganador,
            "tiempo_s": round(t_reaccion, 3),
            "puntos_humano": self.puntos_humano,
            "puntos_robot": self.puntos_robot,
            "dist_robot_cm": round(dist_robot_final * 100.0, 1),
        }
        self.historial_rondas.append(info_ronda)

        # Retraer robot a posición de guardia
        self.robot.retraer_a_guardia(luz.brazo_robot, pasos=6)
        if callback_frame:
            callback_frame()

        # Activar siguiente luz aleatoria
        self.entorno.activar_aleatoria()
        return info_ronda

    def correr(self, duracion_segundos: float = 30.0, sin_ventana: bool = False):
        """Inicia el duelo de reflejos con visor 3D frontal y cuenta atrás de 5 a 0."""
        if sin_ventana:
            return self._correr_sin_ventana(duracion_segundos)

        print("\n  ==============================================================")
        print("    DUELO DE REFLEJOS EN VIVO — HUMANO vs UNITREE G1")
        print(f"    Duración: {duracion_segundos:.0f} s | Dificultad: {self.robot.nombre_dificultad}")
        print("  ==============================================================")
        print("    Mapeo de teclas de IZQUIERDA a DERECHA:")
        print("      [1] Ext.Izq    [2] Arr.Izq    [3] Abj.Centro-Izq")
        print("      [4] Abj.Centro-Der  [5] Arr.Der    [6] Ext.Der")
        print("  ==============================================================\n")

        try:
            import mujoco.viewer
        except Exception as exc:
            print(f"\n[AVISO] No se pudo abrir el visor 3D ({exc}). Corriendo en modo consola...")
            return self._correr_sin_ventana(duracion_segundos)

        with mujoco.viewer.launch_passive(
            self.robot.model, self.robot.data,
            show_left_ui=False, show_right_ui=False,
            key_callback=self.teclado.callback_visor
        ) as viewer:
            # Cámara frontal centrada mirando a las luces y al robot detrás
            viewer.cam.lookat[:] = [0.20, 0.0, 0.88]
            viewer.cam.distance = 2.1
            viewer.cam.azimuth = 180.0      # De frente al robot (lado opuesto)
            viewer.cam.elevation = -12.0     # Ángulo cenital óptimo

            ultimo_ganador = None
            ultimo_tiempo = None
            ultimo_nombre_luz = ""

            # -------------------------------------------------------------
            # CUENTA ATRÁS INICIAL DE 5 A 0 SEGUNDOS
            # -------------------------------------------------------------
            print("  [PREPARACIÓN] Coloca tus dedos sobre las teclas [1] [2] [3] [4] [5] [6]...")
            t_cuenta = 5.0
            t_inicio_cuenta = time.perf_counter()
            ultimo_seg_impreso = 6

            while viewer.is_running() and (time.perf_counter() - t_inicio_cuenta) < t_cuenta:
                transcurrido = time.perf_counter() - t_inicio_cuenta
                restante = max(0.0, t_cuenta - transcurrido)
                seg_actual = int(math.ceil(restante))

                if seg_actual < ultimo_seg_impreso and seg_actual > 0:
                    print(f"    -> ¡Comienza en {seg_actual}...!")
                    ultimo_seg_impreso = seg_actual

                self.marcador.aplicar_al_visor_humano_vs_robot(
                    viewer=viewer,
                    puntos_humano=0,
                    puntos_robot=0,
                    tiempo_restante=duracion_segundos,
                    ronda=1,
                    cuenta_atras=restante,
                    ultimo_ganador=None,
                    tiempo_toque=None,
                    nombre_luz=""
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()
                time.sleep(0.02)

            print("    -> ¡¡¡YA!!! ¡COMIENZA EL DUELO!\n")
            self.teclado.limpiar()

            # -------------------------------------------------------------
            # LOOP PRINCIPAL DE LA PARTIDA
            # -------------------------------------------------------------
            t_inicio = time.perf_counter()
            ronda = 1

            def frame_update():
                t_transcurrido = time.perf_counter() - t_inicio
                t_restante = max(0.0, duracion_segundos - t_transcurrido)
                self.marcador.aplicar_al_visor_humano_vs_robot(
                    viewer=viewer,
                    puntos_humano=self.puntos_humano,
                    puntos_robot=self.puntos_robot,
                    tiempo_restante=t_restante,
                    ronda=ronda,
                    cuenta_atras=0.0,
                    ultimo_ganador=ultimo_ganador,
                    tiempo_toque=ultimo_tiempo,
                    nombre_luz=ultimo_nombre_luz
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()

            frame_update()

            while viewer.is_running() and (time.perf_counter() - t_inicio) < duracion_segundos:
                t_restante = max(0.0, duracion_segundos - (time.perf_counter() - t_inicio))
                luz_act = self.entorno.luz_activa
                print(f"  [Quedan {t_restante:4.1f}s | #{ronda}] Luz: {luz_act.nombre} (Tecla [{luz_act.tecla}]) -> ¡Reaccioná!")

                res = self.disputar_ronda(callback_frame=frame_update)
                ultimo_ganador = res["ganador"]
                ultimo_tiempo = res["tiempo_s"]
                ultimo_nombre_luz = res["luz_nombre"]

                if "HUMANO" in ultimo_ganador and "FALLO" not in ultimo_ganador:
                    print(f"         ¡PUNTO HUMANO! Pulsaste [{res['tecla_correcta']}] en {res['tiempo_s']:.3f} s")
                elif "FALLO" in ultimo_ganador:
                    print(f"         ¡FALLASTE! Pulsaste [{res['tecla_pulsada']}] en vez de [{res['tecla_correcta']}] -> Punto Robot")
                else:
                    print(f"         ¡PUNTO ROBOT! Tocó la luz en {res['tiempo_s']:.3f} s")

                ronda += 1
                time.sleep(0.35)  # Pausa visual entre toques

            # -------------------------------------------------------------
            # PANTALLA FINAL: GANADOR Y RESULTADOS (NO CIERRA HASTA TOCAR BOTÓN)
            # -------------------------------------------------------------
            print("\n  ==============================================================")
            print("    ¡TIEMPO CUMPLIDO! Mostrando ganador y resultados en pantalla.")
            print("    -> Presiona cualquier tecla o botón para finalizar...")
            print("  ==============================================================\n")

            # Breve pausa y limpiar acumulados para no capturar teclas previas
            time.sleep(0.3)
            self.teclado.limpiar()

            while viewer.is_running():
                self.marcador.aplicar_visor_fin_de_juego(
                    viewer=viewer,
                    puntos_humano=self.puntos_humano,
                    puntos_robot=self.puntos_robot,
                    historial=self.historial_rondas
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()

                if self.teclado.consultar_cualquier_tecla():
                    print("  -> ¡Botón detectado! Finalizando y guardando reporte...\n")
                    break

                time.sleep(0.03)

        return self.imprimir_y_guardar_resultados()

    def _correr_sin_ventana(self, duracion_segundos: float = 2.0):
        """Modo simulación sin GUI para verificación automatizada."""
        print(f"\n  Iniciando duelo Humano vs Robot sin ventana ({duracion_segundos}s)...")
        t_inicio = time.perf_counter()
        while (time.perf_counter() - t_inicio) < duracion_segundos:
            self.disputar_ronda(simular_humano=True)
        return self.imprimir_y_guardar_resultados()

    def imprimir_y_guardar_resultados(self) -> dict:
        """Imprime resumen estadístico en consola y guarda reporte gráfico."""
        total_rondas = len(self.historial_rondas)
        tiempos_humano = [r["tiempo_s"] for r in self.historial_rondas if "HUMANO" in r["ganador"] and "FALLO" not in r["ganador"]]
        tiempos_robot = [r["tiempo_s"] for r in self.historial_rondas if "ROBOT" in r["ganador"]]

        t_medio_h = float(np.mean(tiempos_humano)) if tiempos_humano else 0.0
        t_medio_r = float(np.mean(tiempos_robot)) if tiempos_robot else 0.0

        print("\n  " + "=" * 62)
        print("        RESULTADOS FINALES — DUELO HUMANO vs ROBOT G1")
        print("  " + "=" * 62)
        if self.puntos_humano > self.puntos_robot:
            print("    [CAMPEON] *** ¡FELICITACIONES! GANASTE EL MATCH CONTRA EL ROBOT ***")
        elif self.puntos_robot > self.puntos_humano:
            print("    [VICTORIA ROBOT] EL ROBOT UNITREE G1 SE LLEVA EL MATCH ESTA VEZ")
        else:
            print("    [EMPATE] ¡EMPATE EMOCIONANTE! NINGUNO DIO EL BRAZO A TORCER")
        print("  " + "-" * 62)
        print(f"    HUMANO:    {self.puntos_humano:2d} puntos  ({(self.puntos_humano / max(1, total_rondas)) * 100:.1f} %)")
        print(f"    ROBOT G1:  {self.puntos_robot:2d} puntos  ({(self.puntos_robot / max(1, total_rondas)) * 100:.1f} %)")
        print(f"    Disputadas: {total_rondas} luces en total")
        print("  " + "-" * 62)
        if tiempos_humano:
            print(f"    Reflejo Humano Medio: {t_medio_h:.3f} s  (Récord: {min(tiempos_humano):.3f} s)")
        if tiempos_robot:
            print(f"    Reflejo Robot Medio:  {t_medio_r:.3f} s  (Récord: {min(tiempos_robot):.3f} s)")
        print("  " + "=" * 62 + "\n")

        self._guardar_reporte_grafico()

        return {
            "puntos_humano": self.puntos_humano,
            "puntos_robot": self.puntos_robot,
            "total_rondas": total_rondas,
            "tiempo_medio_humano": round(t_medio_h, 3),
            "tiempo_medio_robot": round(t_medio_r, 3),
        }

    def _guardar_reporte_grafico(self):
        """Genera el gráfico oficial de telemetría y rendimiento."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            rondas = [r["ronda"] for r in self.historial_rondas]
            if not rondas:
                return

            pts_h_acum = []
            pts_r_acum = []
            ac_h, ac_r = 0, 0
            for r in self.historial_rondas:
                if "HUMANO" in r["ganador"] and "FALLO" not in r["ganador"]:
                    ac_h += 1
                elif "ROBOT" in r["ganador"]:
                    ac_r += 1
                pts_h_acum.append(ac_h)
                pts_r_acum.append(ac_r)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            fig.patch.set_facecolor("#18181E")

            # Panel 1: Evolución del marcador
            ax1.set_facecolor("#22222A")
            ax1.plot(rondas, pts_h_acum, marker="o", color="#00E5FF", linewidth=2.5, label="Humano (Teclas 1-6)")
            ax1.plot(rondas, pts_r_acum, marker="s", color="#FF3366", linewidth=2.5, label="Robot Unitree G1")
            ax1.set_title("Evolución del Marcador — Humano vs Robot G1", color="white", fontsize=12, pad=10)
            ax1.set_xlabel("Ronda / Luz Disputada", color="#DDD")
            ax1.set_ylabel("Puntos Acumulados", color="#DDD")
            ax1.grid(True, linestyle="--", alpha=0.3)
            ax1.tick_params(colors="white")
            ax1.legend(facecolor="#2A2A35", edgecolor="#444", labelcolor="white")

            # Panel 2: Tiempos de reacción
            ax2.set_facecolor("#22222A")
            tiempos = [r["tiempo_s"] for r in self.historial_rondas]
            colores = ["#00E5FF" if ("HUMANO" in r["ganador"] and "FALLO" not in r["ganador"]) else "#FF3366"
                       for r in self.historial_rondas]
            ax2.bar(rondas, tiempos, color=colores, alpha=0.85, width=0.6)
            ax2.set_title("Tiempos de Reacción por Ronda (s)", color="white", fontsize=12, pad=10)
            ax2.set_xlabel("Ronda", color="#DDD")
            ax2.set_ylabel("Segundos", color="#DDD")
            ax2.grid(True, linestyle="--", alpha=0.3)
            ax2.tick_params(colors="white")

            ruta_png = Path(__file__).resolve().parent / "reporte_humano_vs_robot.png"
            plt.tight_layout()
            plt.savefig(ruta_png, dpi=120, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            print(f"  [REPORTE] Gráfico del duelo guardado en: {ruta_png}")
        except Exception as e:
            print(f"  [AVISO] No se pudo generar el reporte gráfico ({e})")


# =====================================================================
#  5. PUNTO DE ENTRADA CLI
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Duelo de Reflejos en Vivo: Humano vs Robot G1")
    parser.add_argument("--duracion", type=float, default=30.0, help="Duración de la partida en segundos (default: 30)")
    parser.add_argument("--dificultad", type=str, choices=["facil", "medio", "dificil"], default="medio",
                        help="Dificultad del robot (facil, medio, dificil)")
    parser.add_argument("--sin-ventana", action="store_true", help="Corre sin visor 3D para pruebas de integración")
    args = parser.parse_args()

    juego = JuegoHumanoVsRobot(dificultad=args.dificultad)
    juego.correr(duracion_segundos=args.duracion, sin_ventana=args.sin_ventana)
