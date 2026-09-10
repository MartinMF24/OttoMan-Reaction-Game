# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  MODO COMPETENCIA DE REFLEJOS — 2 ROBOTS UNITREE G1 ENFRENTADOS
#
#  Dos robots humanoides Unitree G1 (Robot Azul vs Robot Rojo) compiten
#  en tiempo real por tocar las luces LED ubicadas en la zona central.
#  El primer robot en alcanzar la luz suma el punto.
#  Al terminar, se muestra el marcador final, estadísticas y gráficos.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
#  1. MODELO DE LUCES CENTRALES DE LA ARENA
# =====================================================================
@dataclass
class LuzCentral:
    id: int
    nombre: str
    posicion_base: np.ndarray     # [x, y, z] en el plano medio (x=0)
    posicion: np.ndarray          # Posición actual con jitter aleatorio
    color_on: np.ndarray          # RGBA encendido (brillante)
    color_off: np.ndarray         # RGBA apagado (tenue)
    encendida: bool = False
    radio_esfera: float = 0.045
    ultimo_jitter: np.ndarray = None


class EntornoLucesCompetencia:
    """Administra las luces LED situadas en la franja neutral entre ambos robots."""

    def __init__(self, variacion_espacial: bool = True):
        self.variacion_espacial = variacion_espacial

        # Luces alineadas en la línea divisoria central (x = 0.0)
        posiciones = [
            np.array([0.0, -0.22, 0.95]),   # 0: Lateral Derecha (perspectiva R1)
            np.array([0.0, -0.11, 1.05]),   # 1: Media Derecha Alta
            np.array([0.0, -0.04, 0.90]),   # 2: Centro Derecha Baja
            np.array([0.0, +0.04, 0.90]),   # 3: Centro Izquierda Baja
            np.array([0.0, +0.11, 1.05]),   # 4: Media Izquierda Alta
            np.array([0.0, +0.22, 0.95]),   # 5: Lateral Izquierda (perspectiva R1)
        ]

        self.luces = [
            LuzCentral(
                id=0,
                nombre="Lateral Sur",
                posicion_base=posiciones[0].copy(),
                posicion=posiciones[0].copy(),
                color_on=np.array([0.95, 0.1, 0.85, 0.95], dtype=np.float32),  # Magenta
                color_off=np.array([0.25, 0.1, 0.22, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
            LuzCentral(
                id=1,
                nombre="Media Sur Alta",
                posicion_base=posiciones[1].copy(),
                posicion=posiciones[1].copy(),
                color_on=np.array([0.0, 0.85, 1.0, 0.95], dtype=np.float32),  # Azul Cian
                color_off=np.array([0.1, 0.2, 0.35, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
            LuzCentral(
                id=2,
                nombre="Centro Sur Baja",
                posicion_base=posiciones[2].copy(),
                posicion=posiciones[2].copy(),
                color_on=np.array([0.1, 1.0, 0.3, 0.95], dtype=np.float32),   # Verde Lima
                color_off=np.array([0.1, 0.3, 0.15, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
            LuzCentral(
                id=3,
                nombre="Centro Norte Baja",
                posicion_base=posiciones[3].copy(),
                posicion=posiciones[3].copy(),
                color_on=np.array([1.0, 0.92, 0.0, 0.95], dtype=np.float32),  # Amarillo Neón
                color_off=np.array([0.3, 0.28, 0.1, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
            LuzCentral(
                id=4,
                nombre="Media Norte Alta",
                posicion_base=posiciones[4].copy(),
                posicion=posiciones[4].copy(),
                color_on=np.array([1.0, 0.55, 0.0, 0.95], dtype=np.float32),  # Naranja
                color_off=np.array([0.35, 0.2, 0.1, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
            LuzCentral(
                id=5,
                nombre="Lateral Norte",
                posicion_base=posiciones[5].copy(),
                posicion=posiciones[5].copy(),
                color_on=np.array([1.0, 0.15, 0.2, 0.95], dtype=np.float32),  # Rojo Vivo
                color_off=np.array([0.35, 0.1, 0.12, 0.25], dtype=np.float32),
                ultimo_jitter=np.zeros(3),
            ),
        ]
        self.indice_activa = 0
        self.activar_luz(0)

    def activar_luz(self, indice: int):
        self.indice_activa = indice % len(self.luces)
        for i, luz in enumerate(self.luces):
            if i == self.indice_activa:
                luz.encendida = True
                if self.variacion_espacial:
                    # Pequeña variación espacial simétrica en el centro
                    jitter = np.random.uniform(
                        low=[-0.020, -0.025, -0.025],
                        high=[0.020, 0.025, 0.025]
                    )
                    luz.posicion = luz.posicion_base + jitter
                    luz.ultimo_jitter = jitter
                else:
                    luz.posicion = luz.posicion_base.copy()
                    luz.ultimo_jitter = np.zeros(3)
            else:
                luz.encendida = False
                luz.posicion = luz.posicion_base.copy()

    def activar_aleatoria(self) -> LuzCentral:
        opciones = [i for i in range(len(self.luces)) if i != self.indice_activa]
        nuevo_indice = random.choice(opciones)
        self.activar_luz(nuevo_indice)
        return self.luz_activa

    @property
    def luz_activa(self) -> LuzCentral:
        return self.luces[self.indice_activa]

    def dibujar_en_escena(self, user_scn) -> int:
        """Dibuja las luces y pedestales en la zona neutral entre ambos robots."""
        identidad = np.eye(3).flatten()
        n = 0
        color_pedestal = np.array([0.22, 0.24, 0.26, 0.90], dtype=np.float32)

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
            # 1. Pedestal cilíndrico
            h_pedestal = z - luz.radio_esfera
            if h_pedestal > 0:
                _agregar_geom(
                    mujoco.mjtGeom.mjGEOM_CYLINDER,
                    [0.015, h_pedestal / 2.0, 0.0],
                    [x, y, h_pedestal / 2.0],
                    color_pedestal
                )

            # 2. Esfera LED
            color = luz.color_on if luz.encendida else luz.color_off
            radio = luz.radio_esfera if luz.encendida else luz.radio_esfera * 0.85
            _agregar_geom(
                mujoco.mjtGeom.mjGEOM_SPHERE,
                [radio, radio, radio],
                [x, y, z],
                color
            )

            # 3. Halo translúcido para la luz encendida
            if luz.encendida:
                halo = color.copy()
                halo[3] = 0.35
                _agregar_geom(
                    mujoco.mjtGeom.mjGEOM_SPHERE,
                    [radio * 1.35, radio * 1.35, radio * 1.35],
                    [x, y, z],
                    halo
                )

        user_scn.ngeom = n
        return n


# =====================================================================
#  2. ENSAMBLADOR DE ARENA Y CONTROLADOR CINEMÁTICO DUAL
# =====================================================================
class ControladorDualG1:
    """Construye la arena con 2 robots G1 y controla sus brazos y giros independientemente."""

    def __init__(self):
        ruta_escena = G1.ruta_escena()
        if not ruta_escena or not os.path.exists(ruta_escena):
            raise FileNotFoundError("No se encontró el modelo XML del G1.")

        dir_g1 = os.path.dirname(ruta_escena)
        xml_robot = os.path.join(dir_g1, "g1_29dof.xml")

        # Escena base de la arena con plano de piso y luces ambientales
        base_xml = """<mujoco model="arena_competencia_g1">
  <statistic center="0 0 0.5" extent="2.5"/>
  <visual>
    <headlight diffuse="0.65 0.65 0.65" ambient="0.35 0.35 0.35" specular="0.1 0.1 0.1"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="-130" elevation="-20"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.25 0.45 0.65" rgb2="0.05 0.05 0.1" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.18 0.25 0.35" rgb2="0.12 0.16 0.22"
             markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="6 6" reflectance="0.2"/>
  </asset>
  <worldbody>
    <light pos="0 0 2.2" dir="0 0 -1" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"/>
    <frame name="frame_r1" pos="-0.32 0 0" euler="0 0 0"/>
    <frame name="frame_r2" pos="0.32 0 0" euler="0 0 3.14159265"/>
  </worldbody>
</mujoco>"""

        # Ensamble de ambos robots usando MjSpec
        spec = mujoco.MjSpec.from_string(base_xml)
        frame_r1 = spec.frame("frame_r1")
        frame_r2 = spec.frame("frame_r2")

        spec_r1 = mujoco.MjSpec.from_file(xml_robot)
        spec_r2 = mujoco.MjSpec.from_file(xml_robot)

        # -------------------------------------------------------------
        #  DISTINCIÓN VISUAL: ROBOT AZUL (ROBOT 1) vs ROBOT ROJO (ROBOT 2)
        #  Coloración completa de la carrocería sin bandas de clubes
        # -------------------------------------------------------------
        # Robot 1: Azul vibrante
        for g in spec_r1.geoms:
            g.rgba = [0.08, 0.38, 0.88, 1.0]

        # Robot 2: Rojo vibrante
        for g in spec_r2.geoms:
            g.rgba = [0.88, 0.15, 0.15, 1.0]

        # Unir a la arena con sus respectivos prefijos
        spec.attach(spec_r1, prefix="r1_", frame=frame_r1)
        spec.attach(spec_r2, prefix="r2_", frame=frame_r2)

        self.model = spec.compile()
        self.data = mujoco.MjData(self.model)

        # Body IDs de las manos
        self.r1_mano_izq = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "r1_left_wrist_yaw_link")
        self.r1_mano_der = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "r1_right_wrist_yaw_link")
        self.r2_mano_izq = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "r2_left_wrist_yaw_link")
        self.r2_mano_der = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "r2_right_wrist_yaw_link")

        # DOFs de articulaciones de brazos
        self.r1_dofs_izq = self._obtener_dofs_brazo("r1_", "left")
        self.r1_dofs_der = self._obtener_dofs_brazo("r1_", "right")
        self.r2_dofs_izq = self._obtener_dofs_brazo("r2_", "left")
        self.r2_dofs_der = self._obtener_dofs_brazo("r2_", "right")

        # Orientaciones yaw actuales
        self.yaw_r1 = 0.0
        self.yaw_r2 = math.pi

        self.resetear_posicion_arena()

    def _obtener_dofs_brazo(self, prefix: str, lado: str) -> list:
        nombres = [
            f"{lado}_shoulder_pitch_joint",
            f"{lado}_shoulder_roll_joint",
            f"{lado}_shoulder_yaw_joint",
            f"{lado}_elbow_joint",
            f"{lado}_wrist_roll_joint",
            f"{lado}_wrist_pitch_joint",
            f"{lado}_wrist_yaw_joint"
        ]
        dofs = []
        for nom in nombres:
            jnt_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, f"{prefix}{nom}")
            dofs.append(self.model.jnt_dofadr[jnt_id])
        return dofs

    def resetear_posicion_arena(self):
        """Ubica a Robot 1 y Robot 2 en sus respectivas esquinas de la arena."""
        # 1. Robot 1 (Azul / Local) en x = -0.32, mirando hacia +X (yaw = 0)
        self.data.qpos[0:7] = [-0.32, 0.0, 0.793, 1.0, 0.0, 0.0, 0.0]
        self.data.qpos[7:36] = 0.0
        for idx, val in G1.pose_de_pie.items():
            self.data.qpos[7 + idx] = val
        for idx, val in {15: 0.25, 22: 0.25, 18: -0.45, 25: -0.45}.items():
            self.data.qpos[7 + idx] = val
        self.yaw_r1 = 0.0

        # 2. Robot 2 (Rojo / Visitante) en x = +0.32, mirando hacia -X (yaw = pi)
        self.data.qpos[36:43] = [0.32, 0.0, 0.793, 0.0, 0.0, 0.0, 1.0]
        self.data.qpos[43:72] = 0.0
        for idx, val in G1.pose_de_pie.items():
            self.data.qpos[36 + 7 + idx] = val
        for idx, val in {15: 0.25, 22: 0.25, 18: -0.45, 25: -0.45}.items():
            self.data.qpos[36 + 7 + idx] = val
        self.yaw_r2 = math.pi

        mujoco.mj_forward(self.model, self.data)

    def posicion_mano_r1(self, brazo: str) -> np.ndarray:
        b_id = self.r1_mano_izq if brazo == "izquierdo" else self.r1_mano_der
        return self.data.xpos[b_id].copy()

    def posicion_mano_r2(self, brazo: str) -> np.ndarray:
        b_id = self.r2_mano_izq if brazo == "izquierdo" else self.r2_mano_der
        return self.data.xpos[b_id].copy()

    def paso_ik_robot1(self, objetivo: np.ndarray, ganancia_ik: float = 0.40) -> float:
        """Paso motriz para Robot 1 (Azul)."""
        brazo = "izquierdo" if objetivo[1] >= 0.0 else "derecho"
        b_id = self.r1_mano_izq if brazo == "izquierdo" else self.r1_mano_der
        dofs = self.r1_dofs_izq if brazo == "izquierdo" else self.r1_dofs_der

        dx = objetivo[0] - (-0.32)
        dy = objetivo[1]
        angulo_obj = math.atan2(dy, dx)
        giro_deg = np.clip(0.55 * math.degrees(angulo_obj), -30.0, 30.0)
        yaw_rad = math.radians(giro_deg)
        self.yaw_r1 += 0.20 * (yaw_rad - self.yaw_r1)
        self.data.qpos[3] = math.cos(self.yaw_r1 / 2.0)
        self.data.qpos[6] = math.sin(self.yaw_r1 / 2.0)

        pos_mano = self.data.xpos[b_id]
        error = objetivo - pos_mano
        dist = float(np.linalg.norm(error))
        if dist < 1e-4:
            return dist

        jacp = np.zeros((3, self.model.nv))
        mujoco.mj_jacBody(self.model, self.data, jacp, None, b_id)
        J = jacp[:, dofs]
        A = J @ J.T + (0.015**2) * np.eye(3)
        dq = J.T @ np.linalg.solve(A, error)
        dq = np.clip(dq, -0.25, 0.25)

        for i, dof in enumerate(dofs):
            jnt_id = self.model.dof_jntid[dof]
            qpos_idx = self.model.jnt_qposadr[jnt_id]
            rmin, rmax = self.model.jnt_range[jnt_id]
            nuevo = self.data.qpos[qpos_idx] + ganancia_ik * dq[i]
            if rmin < rmax:
                nuevo = np.clip(nuevo, rmin, rmax)
            self.data.qpos[qpos_idx] = nuevo

        return dist

    def paso_ik_robot2(self, objetivo: np.ndarray, ganancia_ik: float = 0.40) -> float:
        """Paso motriz para Robot 2 (Rojo)."""
        brazo = "derecho" if objetivo[1] >= 0.0 else "izquierdo"
        b_id = self.r2_mano_der if brazo == "derecho" else self.r2_mano_izq
        dofs = self.r2_dofs_der if brazo == "derecho" else self.r2_dofs_izq

        dx = -(objetivo[0] - 0.32)
        dy = -objetivo[1]
        angulo_obj = math.atan2(dy, dx)
        giro_deg = np.clip(0.55 * math.degrees(angulo_obj), -30.0, 30.0)
        yaw_rad = math.pi + math.radians(giro_deg)
        self.yaw_r2 += 0.20 * (yaw_rad - self.yaw_r2)
        self.data.qpos[39] = math.cos(self.yaw_r2 / 2.0)
        self.data.qpos[42] = math.sin(self.yaw_r2 / 2.0)

        pos_mano = self.data.xpos[b_id]
        error = objetivo - pos_mano
        dist = float(np.linalg.norm(error))
        if dist < 1e-4:
            return dist

        jacp = np.zeros((3, self.model.nv))
        mujoco.mj_jacBody(self.model, self.data, jacp, None, b_id)
        J = jacp[:, dofs]
        A = J @ J.T + (0.015**2) * np.eye(3)
        dq = J.T @ np.linalg.solve(A, error)
        dq = np.clip(dq, -0.25, 0.25)

        for i, dof in enumerate(dofs):
            jnt_id = self.model.dof_jntid[dof]
            qpos_idx = self.model.jnt_qposadr[jnt_id]
            rmin, rmax = self.model.jnt_range[jnt_id]
            nuevo = self.data.qpos[qpos_idx] + ganancia_ik * dq[i]
            if rmin < rmax:
                nuevo = np.clip(nuevo, rmin, rmax)
            self.data.qpos[qpos_idx] = nuevo

        return dist

    def retraer_ambos_a_guardia(self, pasos: int = 8):
        for _ in range(pasos):
            # R1
            for dof in (self.r1_dofs_izq + self.r1_dofs_der):
                jnt_id = self.model.dof_jntid[dof]
                qpos_idx = self.model.jnt_qposadr[jnt_id]
                tval = 0.25 if "shoulder_pitch" in self.model.jnt(jnt_id).name else (-0.45 if "elbow" in self.model.jnt(jnt_id).name else 0.0)
                self.data.qpos[qpos_idx] += 0.20 * (tval - self.data.qpos[qpos_idx])
            # R2
            for dof in (self.r2_dofs_izq + self.r2_dofs_der):
                jnt_id = self.model.dof_jntid[dof]
                qpos_idx = self.model.jnt_qposadr[jnt_id]
                tval = 0.25 if "shoulder_pitch" in self.model.jnt(jnt_id).name else (-0.45 if "elbow" in self.model.jnt(jnt_id).name else 0.0)
                self.data.qpos[qpos_idx] += 0.20 * (tval - self.data.qpos[qpos_idx])
            mujoco.mj_forward(self.model, self.data)


# =====================================================================
#  3. MOTOR DE LA COMPETENCIA EN TIEMPO REAL
# =====================================================================
class JuegoCompetenciaG1:
    """Modo competencia en el que ambos robots intentan tocar la luz central primero."""

    def __init__(self, variacion_espacial: bool = True):
        self.controlador = ControladorDualG1()
        self.entorno = EntornoLucesCompetencia(variacion_espacial=variacion_espacial)

        self.puntos_r1 = 0
        self.puntos_r2 = 0
        self.historial_rondas = []

    def disputar_luz(self, callback_frame=None, umbral_toque: float = 0.054,
                     tiempo_max_ronda: float = 2.0) -> dict:
        """Una ronda de competencia: ambos robots reaccionan y extienden sus brazos."""
        luz = self.entorno.luz_activa
        objetivo = luz.posicion.copy()

        # Variaciones de latencia y reflejo de cada robot (entre 60ms y 180ms)
        latencia_r1 = random.uniform(0.06, 0.16)
        latencia_r2 = random.uniform(0.06, 0.16)
        ganancia_r1 = random.uniform(0.38, 0.44)
        ganancia_r2 = random.uniform(0.38, 0.44)

        t_inicio = time.perf_counter()
        ganador = None
        t_toque = None
        dist_r1_final = 99.0
        dist_r2_final = 99.0

        while (time.perf_counter() - t_inicio) < tiempo_max_ronda:
            t_transcurrido = time.perf_counter() - t_inicio

            # Paso motriz de Robot 1
            if t_transcurrido >= latencia_r1:
                dist_r1_final = self.controlador.paso_ik_robot1(objetivo, ganancia_ik=ganancia_r1)

            # Paso motriz de Robot 2
            if t_transcurrido >= latencia_r2:
                dist_r2_final = self.controlador.paso_ik_robot2(objetivo, ganancia_ik=ganancia_r2)

            mujoco.mj_forward(self.controlador.model, self.controlador.data)

            if callback_frame:
                callback_frame()

            # Verificación de toque
            toco_r1 = dist_r1_final <= umbral_toque
            toco_r2 = dist_r2_final <= umbral_toque

            if toco_r1 and not toco_r2:
                ganador = "ROBOT AZUL"
                self.puntos_r1 += 1
                t_toque = t_transcurrido
                break
            elif toco_r2 and not toco_r1:
                ganador = "ROBOT ROJO"
                self.puntos_r2 += 1
                t_toque = t_transcurrido
                break
            elif toco_r1 and toco_r2:
                # Toque casi simultáneo: desempate por distancia milimétrica
                if dist_r1_final < dist_r2_final:
                    ganador = "ROBOT AZUL"
                    self.puntos_r1 += 1
                else:
                    ganador = "ROBOT ROJO"
                    self.puntos_r2 += 1
                t_toque = t_transcurrido
                break

            time.sleep(0.01)

        if ganador is None:
            ganador = "NINGUNO (TIMEOUT)"
            t_toque = tiempo_max_ronda

        info_ronda = {
            "ronda": len(self.historial_rondas) + 1,
            "luz_nombre": luz.nombre,
            "ganador": ganador,
            "tiempo_s": round(t_toque, 3),
            "puntos_r1": self.puntos_r1,
            "puntos_r2": self.puntos_r2,
            "dist_r1_cm": round(dist_r1_final * 100.0, 1),
            "dist_r2_cm": round(dist_r2_final * 100.0, 1),
            "jitter_cm": np.round(luz.ultimo_jitter * 100.0, 1),
        }
        self.historial_rondas.append(info_ronda)

        # Retraer a posición de guardia
        self.controlador.retraer_ambos_a_guardia(pasos=8)
        if callback_frame:
            callback_frame()

        # Activar la siguiente luz en la arena
        self.entorno.activar_aleatoria()
        return info_ronda

    def correr_por_tiempo(self, duracion_segundos: float = 30.0, callback_frame=None) -> list:
        """Ejecuta la partida de competencia durante el tiempo especificado."""
        print(f"\n  Iniciando COMPETENCIA DE REFLEJOS — ROBOT AZUL vs ROBOT ROJO ({duracion_segundos:.0f} s)...")
        print("  " + "=" * 84)
        print(f"  {'#':>3}  {'Luz Disputada':<18} {'Ganador del Toque':<18} {'T.Toque':<9} {'Marcador':<16} {'Dist Azul/Rojo'}")
        print("  " + "-" * 84)

        t_inicio = time.perf_counter()
        while (time.perf_counter() - t_inicio) < duracion_segundos:
            res = self.disputar_luz(callback_frame=callback_frame)
            marcador_str = f"AZUL {res['puntos_r1']} - {res['puntos_r2']} ROJO"
            dist_str = f"{res['dist_r1_cm']:.1f} / {res['dist_r2_cm']:.1f} cm"
            print(f"  {res['ronda']:>3}  {res['luz_nombre']:<18} {res['ganador']:<18} {res['tiempo_s']:>6.3f}s   {marcador_str:<16} {dist_str}")

        tiempo_total = time.perf_counter() - t_inicio
        print("  " + "=" * 84)
        self._imprimir_resultados_finales(tiempo_total)
        return self.historial_rondas

    def correr_con_ventana(self, duracion_segundos: float = 30.0):
        """Abre la ventana 3D con vista lateral panorámica de la arena de competencia."""
        try:
            import mujoco.viewer
        except Exception as exc:
            print(f"\n[AVISO] No se pudo abrir el visor 3D ({exc}). Corriendo en consola...")
            return self.correr_por_tiempo(duracion_segundos)

        print("\n  ==============================================================")
        print("    COMPETENCIA DE REFLEJOS — ROBOT AZUL vs ROBOT ROJO")
        print(f"    Duración: {duracion_segundos:.0f} s | UNITREE G1 DUAL")
        print("    ROBOT 1: Azul")
        print("    ROBOT 2: Rojo")
        print("  ==============================================================\n")

        with mujoco.viewer.launch_passive(
            self.controlador.model, self.controlador.data,
            show_left_ui=False, show_right_ui=False
        ) as viewer:
            # Ángulo óptimo para apreciar ambos robots y las luces centrales
            viewer.cam.lookat[:] = [0.0, 0.0, 0.88]
            viewer.cam.distance = 2.1
            viewer.cam.azimuth = 68
            viewer.cam.elevation = -16

            marcador = MarcadorPremierLeague()
            ultimo_ganador = None
            ultimo_tiempo_toque = None

            t_inicio = time.perf_counter()

            ronda = 1

            def frame_update():
                t_transcurrido = time.perf_counter() - t_inicio
                t_restante = max(0.0, duracion_segundos - t_transcurrido)
                marcador.aplicar_al_visor_competencia(
                    viewer=viewer,
                    puntos_r1=self.puntos_r1,
                    puntos_r2=self.puntos_r2,
                    tiempo_restante=t_restante,
                    ronda=ronda,
                    ultimo_ganador=ultimo_ganador,
                    tiempo_toque=ultimo_tiempo_toque
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()

            # Pintar el marcador de inmediato al abrir la ventana
            frame_update()

            while viewer.is_running() and (time.perf_counter() - t_inicio) < duracion_segundos:
                t_restante = max(0.0, duracion_segundos - (time.perf_counter() - t_inicio))
                print(f"  [Quedan {t_restante:4.1f}s | #{ronda}] Luz central activa -> ¡Robots reaccionando!")
                res = self.disputar_luz(callback_frame=frame_update)
                ultimo_ganador = res.get("ganador")
                ultimo_tiempo_toque = res.get("tiempo_s")
                print(f"         >>> ¡PUNTO PARA {res['ganador']}! ({res['tiempo_s']:.3f} s)")
                print(f"         Marcador en vivo: AZUL {res['puntos_r1']} - {res['puntos_r2']} ROJO\n")

                for _ in range(10):
                    if viewer.is_running():
                        frame_update()
                        time.sleep(0.015)
                ronda += 1

            tiempo_total = time.perf_counter() - t_inicio
            self._imprimir_resultados_finales(tiempo_total)

    def _imprimir_resultados_finales(self, tiempo_total: float = 30.0):
        if not self.historial_rondas:
            return

        total_luces = len(self.historial_rondas)
        p1 = self.puntos_r1
        p2 = self.puntos_r2
        pct_p1 = (p1 / total_luces * 100.0) if total_luces > 0 else 0
        pct_p2 = (p2 / total_luces * 100.0) if total_luces > 0 else 0

        tiempos_r1 = [r["tiempo_s"] for r in self.historial_rondas if r["ganador"] == "ROBOT AZUL"]
        tiempos_r2 = [r["tiempo_s"] for r in self.historial_rondas if r["ganador"] == "ROBOT ROJO"]

        t_medio_r1 = np.mean(tiempos_r1) if tiempos_r1 else 0.0
        t_record_r1 = np.min(tiempos_r1) if tiempos_r1 else 0.0
        t_medio_r2 = np.mean(tiempos_r2) if tiempos_r2 else 0.0
        t_record_r2 = np.min(tiempos_r2) if tiempos_r2 else 0.0

        if p1 > p2:
            campeon = "[CAMPEON] *** GANADOR DEL MATCH: ROBOT AZUL ***"
        elif p2 > p1:
            campeon = "[CAMPEON] *** GANADOR DEL MATCH: ROBOT ROJO ***"
        else:
            campeon = "[EMPATE] === EMPATE ENTRE ROBOT AZUL Y ROBOT ROJO ==="

        print("\n  " + "=" * 62)
        print("        RESULTADOS FINALES DE LA COMPETENCIA DE REFLEJOS")
        print("  " + "=" * 62)
        print(f"    {campeon}")
        print("  " + "-" * 62)
        print(f"    ROBOT AZUL:                 {p1:>2} puntos  ({pct_p1:5.1f} %)")
        print(f"    ROBOT ROJO:                 {p2:>2} puntos  ({pct_p2:5.1f} %)")
        print(f"    Luces disputadas:           {total_luces:>2} en {tiempo_total:.1f} segundos")
        print("  " + "-" * 62)
        print(f"    T. Reflejo Medio (Azul):    {t_medio_r1:>6.3f} s  (Récord: {t_record_r1:.3f} s)")
        print(f"    T. Reflejo Medio (Rojo):    {t_medio_r2:>6.3f} s  (Récord: {t_record_r2:.3f} s)")
        print("  " + "=" * 62 + "\n")

    def guardar_reportes(self, ruta_grafico: str = "reporte_competencia.png"):
        """Genera el gráfico comparativo de la competencia entre Robot Azul y Robot Rojo."""
        if not self.historial_rondas:
            return

        import matplotlib.pyplot as plt

        rondas = [r["ronda"] for r in self.historial_rondas]
        pts_r1_acum = [r["puntos_r1"] for r in self.historial_rondas]
        pts_r2_acum = [r["puntos_r2"] for r in self.historial_rondas]
        tiempos = [r["tiempo_s"] for r in self.historial_rondas]
        colores_puntos = ['#0860DD' if r['ganador'] == 'ROBOT AZUL' else '#E01E26' for r in self.historial_rondas]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.5, 7.5), sharex=True)

        # Gráfico 1: Evolución del marcador acumulado
        ax1.plot(rondas, pts_r1_acum, marker='o', color='#0860DD', linewidth=2.5, label=f'Robot Azul ({self.puntos_r1} pts)')
        ax1.plot(rondas, pts_r2_acum, marker='s', color='#E01E26', linewidth=2.5, label=f'Robot Rojo ({self.puntos_r2} pts)')
        ax1.set_title('Competencia de Reflejos: Evolución del Marcador — Robot Azul vs Robot Rojo', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Puntos Acumulados', fontsize=10.5)
        ax1.grid(True, linestyle=':', alpha=0.6)
        ax1.legend(loc='upper left', fontsize=10)

        # Gráfico 2: Tiempos de reacción por ronda
        ax2.scatter(rondas, tiempos, c=colores_puntos, s=80, zorder=3, edgecolors='black', linewidth=0.8)
        ax2.plot(rondas, tiempos, color='#555555', linestyle='--', alpha=0.5, zorder=2)
        ax2.set_title('Tiempos de Reacción por Toque Ganador (Azul: Robot Azul | Rojo: Robot Rojo)', fontsize=11, fontweight='bold')
        ax2.set_xlabel('Ronda / Disputa', fontsize=10.5)
        ax2.set_ylabel('Tiempo (segundos)', fontsize=10.5)
        ax2.grid(True, linestyle=':', alpha=0.6)

        plt.tight_layout()
        plt.savefig(ruta_grafico, dpi=150)
        plt.close()
        print(f"  [REPORTE] Gráfico de la competencia guardado en: {ruta_grafico}")


# =====================================================================
#  PROGRAMA PRINCIPAL
# =====================================================================
def solicitar_duracion_interactiva() -> float:
    print("\n  ========================================================")
    print("    MODO COMPETENCIA — UNITREE G1 (DUELO 1 VS 1)")
    print("  ========================================================")
    print("    Elegí la duración del match:")
    print("      1)  30 segundos  (Match rápido)")
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
    parser = argparse.ArgumentParser(description="Modo Competencia de Reflejos entre 2 Robots G1")
    parser.add_argument("--duracion", type=float, default=None, help="Duración del juego en segundos")
    parser.add_argument("--sin-ventana", action="store_true", help="Ejecutar sólo en consola sin visor 3D")
    parser.add_argument("--reporte", action="store_true", default=True, help="Generar reporte gráfico")
    args = parser.parse_args()

    duracion = args.duracion
    if duracion is None:
        if sys.stdin.isatty():
            duracion = solicitar_duracion_interactiva()
        else:
            duracion = 30.0

    competencia = JuegoCompetenciaG1(variacion_espacial=True)

    if args.sin_ventana or "--sin-ventana" in sys.argv:
        competencia.correr_por_tiempo(duracion_segundos=duracion)
    else:
        competencia.correr_con_ventana(duracion_segundos=duracion)

    if args.reporte:
        carpeta = Path(__file__).resolve().parent
        competencia.guardar_reportes(ruta_grafico=str(carpeta / "reporte_competencia.png"))


if __name__ == "__main__":
    main()
