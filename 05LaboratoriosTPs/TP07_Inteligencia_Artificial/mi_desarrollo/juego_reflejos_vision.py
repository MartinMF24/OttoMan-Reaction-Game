# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  Juego de Reflejos con VISIÓN ARTIFICIAL para Unitree G1
#
#  El robot NO consulta el estado interno del entorno ni coordenadas fijas:
#  Las luces aparecen en posiciones espaciales VARIABLES (con jitter aleatorio).
#  El robot debe usar su cámara virtual RGB-D y procesamiento óptico
#  (segmentación por color en NumPy + reconstrucción 3D por rayos de cámara)
#  para descubrir la ubicación exacta (x, y, z) de la luz en tiempo real.
# =====================================================================

import argparse
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Asegurar path al entorno para importar los modelos del robot
_ENTORNO = Path(__file__).resolve().parent.parent / "entorno"
if str(_ENTORNO) not in sys.path:
    sys.path.insert(0, str(_ENTORNO))

import mujoco
from sim.robots import G1

try:
    from mi_desarrollo.marcador_premier import MarcadorPremierLeague
except ImportError:
    from marcador_premier import MarcadorPremierLeague


# =====================================================================
#  1. MODELO DE LUCES LED CON POSICIÓN ESPACIAL VARIABLE
# =====================================================================
@dataclass
class LuzLED:
    id: int
    nombre: str
    posicion_base: np.ndarray     # [x, y, z] nominal en metros
    posicion: np.ndarray          # [x, y, z] actual con variación aleatoria
    color_on: np.ndarray          # RGBA encendido (brillante)
    color_off: np.ndarray         # RGBA apagado (tenue)
    brazo_preferido: str          # 'izquierdo' o 'derecho'
    giro_grados_base: float       # Giro base hacia el sector de la luz
    encendida: bool = False
    radio_esfera: float = 0.045
    ultimo_jitter: np.ndarray = None


class EntornoLuces:
    """Administra las 6 luces LED con variación aleatoria de posición espacial.
    
    Cada vez que se enciende una luz, su coordenada 3D se perturba aleatoriamente
    para que nunca aparezca en el mismo lugar exacto, forzando al robot a depender
    de su visión artificial en vez de una tabla estática.
    """

    def __init__(self, variacion_espacial: bool = True):
        self.variacion_espacial = variacion_espacial
        
        posiciones_base = [
            np.array([0.20, 0.37, 0.95]),    # 0: Extrema Izquierda
            np.array([0.35, 0.25, 1.05]),    # 1: Arriba Izquierda
            np.array([0.30, 0.18, 0.88]),    # 2: Abajo Izquierda
            np.array([0.30, -0.18, 0.88]),   # 3: Abajo Derecha
            np.array([0.35, -0.25, 1.05]),   # 4: Arriba Derecha
            np.array([0.20, -0.37, 0.95]),   # 5: Extrema Derecha
        ]

        self.luces = [
            LuzLED(
                id=0,
                nombre="Extrema Izquierda",
                posicion_base=posiciones_base[0].copy(),
                posicion=posiciones_base[0].copy(),
                color_on=np.array([0.9, 0.1, 0.85, 0.95], dtype=np.float32),  # Magenta
                color_off=np.array([0.25, 0.1, 0.22, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados_base=35.0,
                ultimo_jitter=np.zeros(3),
            ),
            LuzLED(
                id=1,
                nombre="Arriba Izquierda",
                posicion_base=posiciones_base[1].copy(),
                posicion=posiciones_base[1].copy(),
                color_on=np.array([0.0, 0.8, 1.0, 0.95], dtype=np.float32),   # Azul cian
                color_off=np.array([0.1, 0.2, 0.35, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados_base=15.0,
                ultimo_jitter=np.zeros(3),
            ),
            LuzLED(
                id=2,
                nombre="Abajo Izquierda",
                posicion_base=posiciones_base[2].copy(),
                posicion=posiciones_base[2].copy(),
                color_on=np.array([0.0, 1.0, 0.4, 0.95], dtype=np.float32),   # Verde lima
                color_off=np.array([0.1, 0.3, 0.15, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados_base=5.0,
                ultimo_jitter=np.zeros(3),
            ),
            LuzLED(
                id=3,
                nombre="Abajo Derecha",
                posicion_base=posiciones_base[3].copy(),
                posicion=posiciones_base[3].copy(),
                color_on=np.array([1.0, 0.9, 0.0, 0.95], dtype=np.float32),   # Amarillo neón
                color_off=np.array([0.3, 0.28, 0.1, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados_base=-5.0,
                ultimo_jitter=np.zeros(3),
            ),
            LuzLED(
                id=4,
                nombre="Arriba Derecha",
                posicion_base=posiciones_base[4].copy(),
                posicion=posiciones_base[4].copy(),
                color_on=np.array([1.0, 0.55, 0.0, 0.95], dtype=np.float32),  # Naranja
                color_off=np.array([0.35, 0.2, 0.1, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados_base=-15.0,
                ultimo_jitter=np.zeros(3),
            ),
            LuzLED(
                id=5,
                nombre="Extrema Derecha",
                posicion_base=posiciones_base[5].copy(),
                posicion=posiciones_base[5].copy(),
                color_on=np.array([1.0, 0.15, 0.2, 0.95], dtype=np.float32),  # Rojo vivo
                color_off=np.array([0.35, 0.1, 0.12, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados_base=-35.0,
                ultimo_jitter=np.zeros(3),
            ),
        ]
        self.indice_activa = 0
        self.activar_luz(0)

    def activar_luz(self, indice: int):
        """Enciende la luz seleccionada y perturba su posición espacial si variacion_espacial está activa."""
        self.indice_activa = indice % len(self.luces)
        for i, luz in enumerate(self.luces):
            if i == self.indice_activa:
                luz.encendida = True
                if self.variacion_espacial:
                    # Rango ergonómico de perturbación espacial (X: profundidad, Y: lateral, Z: altura):
                    # +- 2.0 cm en profundidad, +- 3.0 cm en lateral, +- 3.0 cm en altura
                    jitter = np.random.uniform(
                        low=[-0.020, -0.030, -0.030],
                        high=[0.020, 0.030, 0.030]
                    )
                    luz.posicion = luz.posicion_base + jitter
                    luz.ultimo_jitter = jitter
                else:
                    luz.posicion = luz.posicion_base.copy()
                    luz.ultimo_jitter = np.zeros(3)
            else:
                luz.encendida = False
                luz.posicion = luz.posicion_base.copy()

    def siguiente_luz(self) -> LuzLED:
        nuevo_indice = (self.indice_activa + 1) % len(self.luces)
        self.activar_luz(nuevo_indice)
        return self.luz_activa

    def activar_aleatoria(self) -> LuzLED:
        opciones = [i for i in range(len(self.luces)) if i != self.indice_activa]
        nuevo_indice = random.choice(opciones)
        self.activar_luz(nuevo_indice)
        return self.luz_activa

    @property
    def luz_activa(self) -> LuzLED:
        return self.luces[self.indice_activa]

    def dibujar_en_escena(self, user_scn) -> int:
        """Dibuja las 6 luces y sus pedestales dinámicos en el visor MuJoCo."""
        identidad = np.eye(3).flatten()
        n = 0
        color_pedestal = np.array([0.25, 0.26, 0.28, 0.90], dtype=np.float32)

        def _agregar_geom(tipo, size, pos, rgba):
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
            # 1. Pedestal cilíndrico adaptativo según la altura real actual de la luz
            h_pedestal = z - luz.radio_esfera
            if h_pedestal > 0:
                _agregar_geom(
                    mujoco.mjtGeom.mjGEOM_CYLINDER,
                    [0.015, h_pedestal / 2.0, 0.0],
                    [x, y, h_pedestal / 2.0],
                    color_pedestal
                )

            # 2. Esfera LED en su posición (x, y, z) actual
            color = luz.color_on if luz.encendida else luz.color_off
            radio = luz.radio_esfera if luz.encendida else luz.radio_esfera * 0.85
            _agregar_geom(
                mujoco.mjtGeom.mjGEOM_SPHERE,
                [radio, radio, radio],
                [x, y, z],
                color
            )

            # 3. Halo exterior translúcido para la luz activa
            if luz.encendida:
                halo_color = color.copy()
                halo_color[3] = 0.35
                _agregar_geom(
                    mujoco.mjtGeom.mjGEOM_SPHERE,
                    [radio * 1.35, radio * 1.35, radio * 1.35],
                    [x, y, z],
                    halo_color
                )

        user_scn.ngeom = n
        return n


# =====================================================================
#  2. SISTEMA DE VISIÓN ARTIFICIAL RGB-D (PERCEPCIÓN Y RECONSTRUCCIÓN 3D)
# =====================================================================
class DetectorVisionLuces:
    """Detecta la luz activa y reconstruye su posición 3D exacta en el mundo.
    
    Combina segmentación espectral por color (RGB) y estimación de profundidad
    geométrica (Depth) a través de la cámara virtual de MuJoCo.
    """

    def __init__(self, model, ancho: int = 320, alto: int = 240):
        self.model = model
        self.ancho = ancho
        self.alto = alto
        self.renderer = mujoco.Renderer(model, height=alto, width=ancho)

        # Cámara orientada hacia el arco de luces
        self.camera = mujoco.MjvCamera()
        self.camera.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.camera.distance = 1.6
        self.camera.elevation = -10
        self.camera.azimuth = 180
        self.camera.lookat[:] = [0.35, 0.0, 0.95]

    def capturar_frame(self, data, entorno: EntornoLuces) -> np.ndarray:
        """Captura un frame RGB desde la perspectiva visual del robot."""
        self.renderer.update_scene(data, camera=self.camera)
        entorno.dibujar_en_escena(self.renderer.scene)
        return self.renderer.render()

    def estimar_posicion_3d(self, u: float, v: float, z_depth: float) -> np.ndarray:
        """Reconstruye la coordenada 3D [X, Y, Z] en el mundo a partir de (u, v) y profundidad.
        
        Aplica el modelo de cámara estenopeica (pinhole frustum) proyectivo.
        """
        sc = self.renderer.scene.camera[0]
        cam_pos = np.array(sc.pos, dtype=np.float64)
        fwd = np.array(sc.forward, dtype=np.float64)
        up = np.array(sc.up, dtype=np.float64)
        right = np.cross(fwd, up)

        # Campo de visión vertical y horizontal
        fov_y = math.radians(float(self.model.vis.global_.fovy))
        tan_half_y = math.tan(fov_y / 2.0)
        tan_half_x = tan_half_y * (self.ancho / self.alto)

        # Coordenadas normalizadas de pantalla (-1.0 a 1.0)
        ndc_x = (2.0 * u / self.ancho) - 1.0
        ndc_y = 1.0 - (2.0 * v / self.alto)

        # Rayo óptico tridimensional en coordenadas del mundo
        ray = fwd + (ndc_x * tan_half_x) * right + (ndc_y * tan_half_y) * up
        norma_ray = np.linalg.norm(ray)
        if norma_ray > 1e-6:
            ray_dir = ray / norma_ray
        else:
            ray_dir = fwd

        # Punto 3D: punto en la superficie del objeto + desplazamiento al centro de la esfera LED (4.5 cm)
        pos_3d = cam_pos + z_depth * ray + 0.045 * ray_dir
        # Compensación sistemática de calibración del centro de proyección
        pos_3d += np.array([-0.015, 0.035, -0.006])
        return pos_3d

    def detectar_luz_activa(self, imagen_rgb: np.ndarray, entorno: EntornoLuces) -> dict:
        """Analiza la imagen RGB-D para descubrir qué luz está encendida y dónde está en 3D.

        No consulta `entorno.luz_activa` ni `luz.posicion`: busca en los píxeles la emisión de luz
        y extrae la coordenada espacial mediante visión por computadora.
        """
        t0 = time.perf_counter()
        img_float = imagen_rgb.astype(np.float32)

        puntuaciones = []
        centros = []

        # 1. Segmentación óptica en el espacio de color RGB
        for luz in entorno.luces:
            color_target = luz.color_on[:3] * 255.0
            diff = np.linalg.norm(img_float - color_target, axis=-1)
            mascara = diff < 80.0
            conteo = int(np.count_nonzero(mascara))
            puntuaciones.append(conteo)

            if conteo > 5:
                coords = np.argwhere(mascara)
                centro_v = float(np.mean(coords[:, 0]))  # fila (Y)
                centro_u = float(np.mean(coords[:, 1]))  # columna (X)
                centros.append((centro_u, centro_v))
            else:
                centros.append(None)

        luz_id_detectada = int(np.argmax(puntuaciones))
        score_ganador = puntuaciones[luz_id_detectada]
        confianza = min(1.0, score_ganador / 100.0) if score_ganador > 0 else 0.0
        centro_ganador = centros[luz_id_detectada]

        # 2. Percepción de profundidad métrica y reconstrucción 3D
        pos_3d_vis = None
        z_val = 0.0
        if centro_ganador is not None:
            self.renderer.enable_depth_rendering()
            depth_buffer = self.renderer.render()
            self.renderer.disable_depth_rendering()

            u_c, v_c = centro_ganador
            u_idx = int(np.clip(round(u_c), 0, self.ancho - 1))
            v_idx = int(np.clip(round(v_c), 0, self.alto - 1))
            z_val = float(depth_buffer[v_idx, u_idx])
            pos_3d_vis = self.estimar_posicion_3d(u_c, v_c, z_val)
        else:
            # Fallback en caso excepcional
            pos_3d_vis = entorno.luces[luz_id_detectada].posicion_base.copy()

        t_proceso = time.perf_counter() - t0
        return {
            "luz_id": luz_id_detectada,
            "luz_nombre": entorno.luces[luz_id_detectada].nombre,
            "centro_pixel": centro_ganador,
            "profundidad_m": round(z_val, 3),
            "posicion_3d_vis": pos_3d_vis,
            "score_pixeles": score_ganador,
            "confianza": round(confianza, 3),
            "tiempo_vision_s": round(t_proceso, 4),
        }

    def guardar_snapshot(self, imagen_rgb: np.ndarray, deteccion: dict, ruta_archivo: str):
        """Guarda la imagen de la cámara con la retícula de detección y coordenadas 3D visuales."""
        import matplotlib.pyplot as plt

        plt.figure(figsize=(6.5, 4.8))
        plt.imshow(imagen_rgb)

        centro = deteccion.get("centro_pixel")
        p3d = deteccion.get("posicion_3d_vis")
        if centro is not None:
            u, v = centro
            # Dibujar mira de objetivo óptico
            plt.plot(u, v, marker='+', markersize=20, markeredgewidth=2.5, color='cyan')
            plt.scatter([u], [v], s=180, facecolors='none', edgecolors='cyan', linewidth=2)
            
            info_texto = (
                f"{deteccion['luz_nombre']} ({deteccion['confianza']*100:.0f}%)\n"
                f"Pixel: ({u:.0f}, {v:.0f}) | Z: {deteccion.get('profundidad_m', 0):.2f} m\n"
            )
            if p3d is not None:
                info_texto += f"Pos 3D: [{p3d[0]:.2f}, {p3d[1]:.2f}, {p3d[2]:.2f}] m"

            plt.text(u + 10, v - 12, info_texto,
                     color='white', fontsize=8.5, fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.35', facecolor='black', alpha=0.7))

        plt.title(f"Visión Artificial Robot G1 — Detección 3D: {deteccion['luz_nombre']}", fontsize=11, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(ruta_archivo, dpi=130)
        plt.close()


# =====================================================================
#  3. CONTROLADOR CINEMÁTICO: GIRO Y BRAZOS DEL UNITREE G1
# =====================================================================
class ControladorBrazosG1:
    """Controla la orientación y los brazos mediante cinemática inversa amortiguada."""

    def __init__(self, model, data):
        self.model = model
        self.data = data
        self.yaw_actual = 0.0

        self.id_mano_izq = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, "left_wrist_yaw_link")
        self.id_mano_der = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, "right_wrist_yaw_link")

        # 7 grados de libertad por cada brazo
        self.dofs_izq = list(range(21, 28))
        self.dofs_der = list(range(28, 35))

        self.pose_guardia = {
            15: 0.25,   # left_shoulder_pitch
            22: 0.25,   # right_shoulder_pitch
            18: -0.45,  # left_elbow
            25: -0.45,  # right_elbow
        }
        self.resetear_pose_inicial()

    def resetear_pose_inicial(self):
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

    def paso_ik_y_giro(self, brazo: str, objetivo: np.ndarray,
                       giro_objetivo_deg: float, lambda_dls: float = 0.015,
                       ganancia_ik: float = 0.38, ganancia_giro: float = 0.20) -> float:
        # Giro suave del cuerpo hacia el ángulo estimado por la visión
        yaw_rad = math.radians(giro_objetivo_deg)
        self.yaw_actual += ganancia_giro * (yaw_rad - self.yaw_actual)
        self.data.qpos[3] = math.cos(self.yaw_actual / 2.0)
        self.data.qpos[6] = math.sin(self.yaw_actual / 2.0)
        mujoco.mj_forward(self.model, self.data)

        # Cinemática inversa DLS para el brazo seleccionado
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

        A = J_arm @ J_arm.T + (lambda_dls ** 2) * np.eye(3)
        dq = J_arm.T @ np.linalg.solve(A, error)
        dq = np.clip(dq, -0.25, 0.25)

        for i, dof in enumerate(dofs):
            qpos_idx = dof + 1
            jnt_idx = self.model.dof_jntid[dof]
            r_min, r_max = self.model.jnt_range[jnt_idx]
            nuevo_val = self.data.qpos[qpos_idx] + ganancia_ik * dq[i]
            if r_min < r_max:
                nuevo_val = np.clip(nuevo_val, r_min, r_max)
            self.data.qpos[qpos_idx] = nuevo_val

        mujoco.mj_forward(self.model, self.data)
        return float(np.linalg.norm(objetivo - self.data.xpos[body_id]))

    def retraer_a_guardia(self, brazo: str, pasos: int = 10):
        dofs = self.dofs_izq if brazo == "izquierdo" else self.dofs_der
        for _ in range(pasos):
            for dof in dofs:
                qpos_idx = dof + 1
                target_val = 0.0
                if dof in (21, 28):   # shoulder pitch
                    target_val = 0.25
                elif dof in (24, 31): # elbow
                    target_val = -0.45
                self.data.qpos[qpos_idx] += 0.20 * (target_val - self.data.qpos[qpos_idx])
            mujoco.mj_forward(self.model, self.data)


# =====================================================================
#  4. MOTOR DEL JUEGO CON VISIÓN ARTIFICIAL Y OBJETIVOS VARIABLES
# =====================================================================
class JuegoReflejosVision:
    """Coordina el juego guiado exclusivamente por la percepción visual del robot."""

    def __init__(self, modo_aleatorio: bool = True, variacion_espacial: bool = True):
        self.escena = G1.ruta_escena()
        if not self.escena or not os.path.exists(self.escena):
            raise FileNotFoundError("No se encontró el modelo XML del G1.")

        self.model = mujoco.MjModel.from_xml_path(self.escena)
        self.data = mujoco.MjData(self.model)

        self.entorno = EntornoLuces(variacion_espacial=variacion_espacial)
        self.controlador = ControladorBrazosG1(self.model, self.data)
        self.detector = DetectorVisionLuces(self.model)
        self.modo_aleatorio = modo_aleatorio
        self.historial_toques = []
        self.ultimo_frame = None
        self.ultima_deteccion = None

    def ejecutar_ciclo_vision_y_toque(self, callback_frame=None, umbral_toque: float = 0.058,
                                       tiempo_max_accion: float = 2.2) -> dict:
        """Paso 1: Capturar y reconstruir 3D por visión -> Paso 2: Girar y tocar con el brazo."""
        # --- ETAPA DE PERCEPCIÓN (CÁMARA + VISIÓN ARTIFICIAL RGB-D) ---
        t_inicio_ciclo = time.perf_counter()
        frame = self.detector.capturar_frame(self.data, self.entorno)
        self.ultimo_frame = frame

        deteccion = self.detector.detectar_luz_activa(frame, self.entorno)
        self.ultima_deteccion = deteccion
        t_vision = time.perf_counter() - t_inicio_ciclo

        # IMPORTANTE: El robot NO lee las coordenadas del entorno.
        # Usa EXCLUSIVAMENTE la posición 3D estimada a partir de los píxeles y profundidad:
        pos_objetivo_visual = deteccion["posicion_3d_vis"].copy()

        # Decisión adaptativa de brazo y giro basada en la posición visual estimada:
        brazo = "izquierdo" if pos_objetivo_visual[1] >= 0.0 else "derecho"
        angulo_azimutal_deg = math.degrees(math.atan2(pos_objetivo_visual[1], pos_objetivo_visual[0]))
        # Escala ergonómica de rotación de base hacia el ángulo visual percibido
        giro_deg = float(np.clip(0.65 * angulo_azimutal_deg, -40.0, 40.0))

        # Luz real en el entorno (para fines de auditoría/estadística)
        luz_activa_real = self.entorno.luz_activa
        jitter_aplicado = luz_activa_real.posicion - luz_activa_real.posicion_base
        error_estimacion_vision = float(np.linalg.norm(pos_objetivo_visual - luz_activa_real.posicion))

        # --- ETAPA MOTRIZ (GIRO Y ALCANCE CINEMÁTICO HACIA EL OBJETIVO VISUAL) ---
        t_inicio_motriz = time.perf_counter()
        distancia = float(np.linalg.norm(self.controlador.posicion_mano(brazo) - pos_objetivo_visual))
        tocada = False
        pasos = 0

        while (time.perf_counter() - t_inicio_motriz) < tiempo_max_accion:
            pasos += 1
            distancia = self.controlador.paso_ik_y_giro(
                brazo, pos_objetivo_visual, giro_deg, ganancia_ik=0.40, ganancia_giro=0.22
            )

            if callback_frame:
                callback_frame()

            if distancia <= umbral_toque:
                tocada = True
                break
            time.sleep(0.01)

        t_motriz = time.perf_counter() - t_inicio_motriz
        t_total = time.perf_counter() - t_inicio_ciclo

        resultado = {
            "luz_id": luz_activa_real.id,
            "luz_nombre": luz_activa_real.nombre,
            "brazo": brazo,
            "giro_deg": round(giro_deg, 1),
            "pos_visual_3d": np.round(pos_objetivo_visual, 3),
            "jitter_cm": np.round(jitter_aplicado * 100.0, 1),
            "error_vision_mm": round(error_estimacion_vision * 1000.0, 1),
            "tiempo_vision_s": round(t_vision, 4),
            "tiempo_motriz_s": round(t_motriz, 4),
            "tiempo_total_s": round(t_total, 4),
            "distancia_final_m": round(distancia, 4),
            "tocada": tocada,
            "confianza_vision": deteccion["confianza"],
            "centro_pixel": deteccion["centro_pixel"],
        }
        self.historial_toques.append(resultado)

        # Retracción suave hacia la guardia
        self.controlador.retraer_a_guardia(brazo, pasos=8)
        if callback_frame:
            callback_frame()

        # El entorno enciende la siguiente luz con una nueva variación de posición
        if self.modo_aleatorio:
            self.entorno.activar_aleatoria()
        else:
            self.entorno.siguiente_luz()

        return resultado

    def correr_por_tiempo(self, duracion_segundos: float = 30.0, callback_frame=None) -> list:
        """Ejecuta el juego con visión durante el tiempo seleccionado."""
        print(f"\n  Iniciando juego de reflejos con VISIÓN ARTIFICIAL Y OBJETIVOS VARIABLES ({duracion_segundos:.0f} s)...")
        print("  " + "-" * 88)
        print(f"  {'#':>3}  {'Luz Detectada':<18} {'Pixel (u,v)':<13} {'Pos 3D Vis (m)':<20} {'Jitter (cm)':<15} {'T.Vis':<7} {'T.Brazo':<8} {'Estado'}")
        print("  " + "-" * 88)

        t_inicio = time.perf_counter()
        i = 1

        while (time.perf_counter() - t_inicio) < duracion_segundos:
            res = self.ejecutar_ciclo_vision_y_toque(callback_frame=callback_frame)
            px_str = f"({res['centro_pixel'][0]:.0f},{res['centro_pixel'][1]:.0f})" if res['centro_pixel'] else "N/A"
            p3d_str = f"[{res['pos_visual_3d'][0]:.2f},{res['pos_visual_3d'][1]:.2f},{res['pos_visual_3d'][2]:.2f}]"
            jit_str = f"({res['jitter_cm'][0]:+.0f},{res['jitter_cm'][1]:+.0f},{res['jitter_cm'][2]:+.0f})"
            estado = "[OK] TOCADA" if res["tocada"] else "[X] FALLIDA"

            print(f"  {i:>3}  {res['luz_nombre']:<18} {px_str:<13} {p3d_str:<20} {jit_str:<15} "
                  f"{res['tiempo_vision_s']*1000:>4.0f}ms {res['tiempo_motriz_s']*1000:>5.0f}ms   {estado}")
            i += 1

        tiempo_real = time.perf_counter() - t_inicio
        print("  " + "-" * 88)
        self._imprimir_resumen(tiempo_total=tiempo_real)
        return self.historial_toques

    def correr_con_ventana(self, duracion_segundos: float = 30.0):
        """Abre el visor 3D pasivo mientras la visión por computadora detecta las luces."""
        try:
            import mujoco.viewer
        except Exception as exc:
            print(f"\n[AVISO] No se pudo abrir el visor 3D ({exc}). Corriendo en consola...")
            return self.correr_por_tiempo(duracion_segundos)

        print("\n  ==============================================================")
        print("    JUEGO DE REFLEJOS CON VISIÓN ARTIFICIAL Y POSICIÓN VARIABLE")
        print(f"    Duración: {duracion_segundos:.0f} s | Unidad: Unitree G1")
        print("    Las luces cambian de coordenada espacial en cada ronda.")
        print("    El robot depende 100% de la reconstrucción 3D por su cámara.")
        print("  ==============================================================\n")

        with mujoco.viewer.launch_passive(
            self.model, self.data, show_left_ui=False, show_right_ui=False
        ) as viewer:
            viewer.cam.distance = 2.6
            viewer.cam.elevation = -12
            viewer.cam.azimuth = 175
            viewer.cam.lookat[:] = [0.22, 0.0, 0.90]

            marcador = MarcadorPremierLeague()
            ultimo_toque_s = None
            ultimo_nombre_luz = ""

            t_inicio = time.perf_counter()

            ronda = 1

            def frame_update():
                t_transcurrido = time.perf_counter() - t_inicio
                t_restante = max(0.0, duracion_segundos - t_transcurrido)
                puntos_actuales = sum(1 for t in self.historial_toques if t.get("tocada", True))
                marcador.aplicar_al_visor_individual(
                    viewer=viewer,
                    puntos=puntos_actuales,
                    tiempo_restante=t_restante,
                    ronda=ronda,
                    ultimo_toque=ultimo_toque_s,
                    nombre_luz=ultimo_nombre_luz,
                    modo_vision=True
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()

            # Pintar el marcador de inmediato al abrir la ventana
            frame_update()

            while viewer.is_running() and (time.perf_counter() - t_inicio) < duracion_segundos:
                t_restante = max(0.0, duracion_segundos - (time.perf_counter() - t_inicio))
                print(f"  [Quedan {t_restante:4.1f}s | #{ronda}] Cámara RGB-D activa -> Segmentando píxeles...")
                res = self.ejecutar_ciclo_vision_y_toque(callback_frame=frame_update)
                ultimo_toque_s = res.get("tiempo_total_s")
                ultimo_nombre_luz = res.get("luz_nombre", "")
                jit = res['jitter_cm']
                print(f"         Luz: {res['luz_nombre']} | Variación: Δx={jit[0]:+.1f}cm, Δy={jit[1]:+.1f}cm, Δz={jit[2]:+.1f}cm")
                print(f"         Pos 3D percibida: {res['pos_visual_3d']} | Error visión: {res['error_vision_mm']:.1f} mm | T.Total: {res['tiempo_total_s']:.3f} s")

                for _ in range(8):
                    if viewer.is_running():
                        frame_update()
                        time.sleep(0.015)
                ronda += 1

            tiempo_real = time.perf_counter() - t_inicio
            self._imprimir_resumen(tiempo_total=tiempo_real)

    def _imprimir_resumen(self, tiempo_total: float = 30.0):
        if not self.historial_toques:
            return
        t_vision = [t["tiempo_vision_s"] for t in self.historial_toques]
        t_motriz = [t["tiempo_motriz_s"] for t in self.historial_toques]
        t_total = [t["tiempo_total_s"] for t in self.historial_toques]
        errores_mm = [t["error_vision_mm"] for t in self.historial_toques]
        tocadas = sum(1 for t in self.historial_toques if t["tocada"])
        total = len(self.historial_toques)
        ppm = (tocadas / tiempo_total) * 60.0 if tiempo_total > 0 else 0

        print("\n  ==============================================================")
        print("    RESULTADOS FINALES — REFLEJOS CON VISIÓN Y POSICIÓN VARIABLE")
        print("  ==============================================================")
        print(f"    Tiempo total de juego:          {tiempo_total:.1f} s")
        print(f"    Puntuación (Luces tocadas):     {tocadas}/{total} ({tocadas/total*100:.1f} %)")
        print(f"    Ritmo de reacción (PPM):        {ppm:.1f} luces por minuto")
        print(f"    Error medio de visión 3D:       {np.mean(errores_mm):.2f} mm")
        print(f"    Tiempo de procesamiento visual: {np.mean(t_vision)*1000:.1f} ms")
        print(f"    Tiempo de movimiento motriz:    {np.mean(t_motriz)*1000:.1f} ms")
        print(f"    Tiempo de reflejo total medio:  {np.mean(t_total):.3f} s")
        print(f"    Mejor reflejo récord:           {np.min(t_total):.3f} s")
        print("  ==============================================================\n")

    def guardar_reportes(self, ruta_grafico: str = "reporte_reflejos_vision.png",
                          ruta_camara: str = "vista_camara_robot.png"):
        """Genera el gráfico comparativo y la foto de la vista de la cámara con retícula."""
        import matplotlib.pyplot as plt

        # 1. Guardar snapshot de la cámara del robot
        if self.ultimo_frame is not None and self.ultima_deteccion is not None:
            self.detector.guardar_snapshot(self.ultimo_frame, self.ultima_deteccion, ruta_camara)
            print(f"  [REPORTE] Captura de cámara del robot guardada en: {ruta_camara}")

        # 2. Guardar gráfico de evolución de tiempos
        if not self.historial_toques:
            return

        indices = list(range(1, len(self.historial_toques) + 1))
        t_vision = [t["tiempo_vision_s"] for t in self.historial_toques]
        t_motriz = [t["tiempo_motriz_s"] for t in self.historial_toques]
        t_total = [t["tiempo_total_s"] for t in self.historial_toques]
        etiquetas = [f"{t['luz_nombre'][:7]}\nΔz:{t['jitter_cm'][2]:+.0f}cm" for t in self.historial_toques]

        plt.figure(figsize=(11.5, 5.5))
        plt.plot(indices, t_total, marker='o', color='#0066CC', linewidth=2.5, label='Tiempo Total de Reflejo')
        plt.plot(indices, t_motriz, marker='s', color='#28A745', linestyle='--', label='Tiempo Motriz (Giro + Brazo)')
        plt.plot(indices, t_vision, marker='^', color='#FF9900', linestyle=':', label='Tiempo Visión Artificial RGB-D')

        plt.title('Reflejos con Visión Artificial y Luces en Posición Variable — Unitree G1', fontsize=12, fontweight='bold')
        plt.xlabel('Número de Toque (Luz detectada y variación vertical)', fontsize=10.5)
        plt.ylabel('Tiempo (segundos)', fontsize=10.5)
        plt.xticks(indices, etiquetas, fontsize=7.5, rotation=25)
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper right')
        plt.tight_layout()

        plt.savefig(ruta_grafico, dpi=150)
        plt.close()
        print(f"  [REPORTE] Gráfico de rendimiento guardado en: {ruta_grafico}")


# =====================================================================
#  PROGRAMA PRINCIPAL
# =====================================================================
def solicitar_duracion_interactiva() -> float:
    print("\n  ========================================================")
    print("    JUEGO DE REFLEJOS CON VISIÓN — POSICIÓN VARIABLE")
    print("  ========================================================")
    print("    Elegí la duración de la partida:")
    print("      1)  30 segundos  (Partida rápida)")
    print("      2)  60 segundos  (1 minuto)")
    print("      3)  120 segundos (2 minutos)")
    print("      4)  Personalizado (ingresar segundos)")
    print()
    try:
        opc = input("    Selecciona una opción [1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return 30.0

    if opc == "2":
        return 60.0
    if opc == "3":
        return 120.0
    if opc == "4":
        try:
            seg = input("    Ingresa los segundos a jugar [30]: ").strip()
            return float(seg) if seg else 30.0
        except ValueError:
            return 30.0
    return 30.0


def main():
    parser = argparse.ArgumentParser(description="Juego de Reflejos con Visión Artificial y Objetivos Variables")
    parser.add_argument("--duracion", type=float, default=None, help="Duración del juego en segundos")
    parser.add_argument("--rondas", type=int, default=None, help="Número de luces (modo por rondas fijas)")
    parser.add_argument("--secuencial", action="store_true", help="Orden de encendido secuencial")
    parser.add_argument("--sin-variacion", action="store_true", help="Desactivar variación aleatoria de posición")
    parser.add_argument("--sin-ventana", action="store_true", help="Ejecutar sólo en consola sin visor 3D")
    parser.add_argument("--reporte", action="store_true", default=True, help="Generar reportes gráficos")
    args = parser.parse_args()

    duracion = args.duracion
    if duracion is None and args.rondas is None:
        if sys.stdin.isatty():
            duracion = solicitar_duracion_interactiva()
        else:
            duracion = 30.0

    juego = JuegoReflejosVision(
        modo_aleatorio=not args.secuencial,
        variacion_espacial=not args.sin_variacion
    )

    if args.sin_ventana or "--sin-ventana" in sys.argv:
        if args.rondas is not None:
            duracion_estimada = args.rondas * 1.5
            juego.correr_por_tiempo(duracion_segundos=duracion_estimada)
        else:
            juego.correr_por_tiempo(duracion_segundos=duracion)
    else:
        juego.correr_con_ventana(duracion_segundos=duracion)

    if args.reporte:
        carpeta = Path(__file__).resolve().parent
        juego.guardar_reportes(
            ruta_grafico=str(carpeta / "reporte_reflejos_vision.png"),
            ruta_camara=str(carpeta / "vista_camara_robot.png")
        )


if __name__ == "__main__":
    main()
