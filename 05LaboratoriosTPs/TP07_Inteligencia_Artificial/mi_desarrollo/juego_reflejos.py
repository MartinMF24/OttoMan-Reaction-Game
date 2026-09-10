# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  Juego de Reflejos y Entrenamiento con 6 Luces LED para Unitree G1
#
#  Librerías utilizadas:
#    - mujoco: Motor de simulación 3D, cinemática y renderizado de luces
#    - numpy: Cinemática inversa (Damped Least Squares IK) y álgebra vectorial
#    - matplotlib: Reporte de métricas y tiempos de reacción
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
#  1. MODELO DE LUCES LED (6 LUCES EN ARCO)
# =====================================================================
@dataclass
class LuzLED:
    id: int
    nombre: str
    posicion: np.ndarray          # [x, y, z] en metros en el mundo
    color_on: np.ndarray          # RGBA encendido (brillante)
    color_off: np.ndarray         # RGBA apagado (tenue)
    brazo_preferido: str          # 'izquierdo' o 'derecho'
    giro_grados: float            # Giro corporal requerido hacia la luz
    encendida: bool = False
    radio_esfera: float = 0.045


class EntornoLuces:
    """Administra las 6 luces LED distribuidas en arco alrededor del robot."""

    def __init__(self):
        # 6 luces distribuidas en abanico (arco de -45° a +45°):
        # Obligan al robot a girar su cuerpo para alcanzar las laterales.
        self.luces = [
            LuzLED(
                id=0,
                nombre="Extrema Izquierda",
                posicion=np.array([0.20, 0.37, 0.95]),
                color_on=np.array([0.9, 0.1, 0.85, 0.95], dtype=np.float32),  # Magenta
                color_off=np.array([0.25, 0.1, 0.22, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados=35.0,
            ),
            LuzLED(
                id=1,
                nombre="Arriba Izquierda",
                posicion=np.array([0.35, 0.25, 1.05]),
                color_on=np.array([0.0, 0.8, 1.0, 0.95], dtype=np.float32),   # Azul cian
                color_off=np.array([0.1, 0.2, 0.35, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados=15.0,
            ),
            LuzLED(
                id=2,
                nombre="Abajo Izquierda",
                posicion=np.array([0.30, 0.18, 0.88]),
                color_on=np.array([0.0, 1.0, 0.4, 0.95], dtype=np.float32),   # Verde lima
                color_off=np.array([0.1, 0.3, 0.15, 0.25], dtype=np.float32),
                brazo_preferido="izquierdo",
                giro_grados=5.0,
            ),
            LuzLED(
                id=3,
                nombre="Abajo Derecha",
                posicion=np.array([0.30, -0.18, 0.88]),
                color_on=np.array([1.0, 0.9, 0.0, 0.95], dtype=np.float32),   # Amarillo neón
                color_off=np.array([0.3, 0.28, 0.1, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados=-5.0,
            ),
            LuzLED(
                id=4,
                nombre="Arriba Derecha",
                posicion=np.array([0.35, -0.25, 1.05]),
                color_on=np.array([1.0, 0.55, 0.0, 0.95], dtype=np.float32),  # Naranja
                color_off=np.array([0.35, 0.2, 0.1, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados=-15.0,
            ),
            LuzLED(
                id=5,
                nombre="Extrema Derecha",
                posicion=np.array([0.20, -0.37, 0.95]),
                color_on=np.array([1.0, 0.15, 0.2, 0.95], dtype=np.float32),  # Rojo vivo
                color_off=np.array([0.35, 0.1, 0.12, 0.25], dtype=np.float32),
                brazo_preferido="derecho",
                giro_grados=-35.0,
            ),
        ]
        self.indice_activa = 0
        self.activar_luz(0)

    def activar_luz(self, indice: int):
        self.indice_activa = indice % len(self.luces)
        for i, luz in enumerate(self.luces):
            luz.encendida = (i == self.indice_activa)

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
        """Dibuja las 6 luces y sus pedestales en el visor MuJoCo usando user_scn."""
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
            # 1. Pedestal cilíndrico desde el piso hasta la base de la luz
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
#  2. CONTROLADOR CINEMÁTICO: GIRO CORPORAL Y BRAZOS DEL UNITREE G1
# =====================================================================
class ControladorBrazosG1:
    """Controla la orientación del robot y los brazos con cinemática inversa."""

    def __init__(self, model, data):
        self.model = model
        self.data = data
        self.yaw_actual = 0.0

        # Cuerpos de las manos
        self.id_mano_izq = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, "left_wrist_yaw_link")
        self.id_mano_der = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, "right_wrist_yaw_link")

        # Grados de libertad en qvel
        self.dofs_izq = list(range(21, 28))
        self.dofs_der = list(range(28, 35))

        # Poses articulares de guardia inicial (en radianes)
        self.pose_guardia = {
            15: 0.25,   # left_shoulder_pitch
            22: 0.25,   # right_shoulder_pitch
            18: -0.45,  # left_elbow
            25: -0.45,  # right_elbow
        }
        self.resetear_pose_inicial()

    def resetear_pose_inicial(self):
        """Ubica al robot de pie en postura frontal lista para reaccionar."""
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
                       ganancia_ik: float = 0.35, ganancia_giro: float = 0.18) -> float:
        """Orienta el cuerpo hacia la luz y extiende el brazo mediante IK."""
        # 1. Giro suave del cuerpo hacia la luz
        yaw_rad = math.radians(giro_objetivo_deg)
        self.yaw_actual += ganancia_giro * (yaw_rad - self.yaw_actual)
        self.data.qpos[3] = math.cos(self.yaw_actual / 2.0)
        self.data.qpos[6] = math.sin(self.yaw_actual / 2.0)
        mujoco.mj_forward(self.model, self.data)

        # 2. Cinemática inversa para el brazo correspondiente
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
            nuevo_val = self.data.qpos[qpos_idx] + ganancia_ik * dq[i]
            if r_min < r_max:
                nuevo_val = np.clip(nuevo_val, r_min, r_max)
            self.data.qpos[qpos_idx] = nuevo_val

        mujoco.mj_forward(self.model, self.data)
        return float(np.linalg.norm(objetivo - self.data.xpos[body_id]))

    def retraer_a_guardia(self, brazo: str, pasos: int = 12):
        """Retrae el brazo a la postura de guardia lista para el siguiente reflejo."""
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
#  3. MOTOR DEL JUEGO DE REFLEJOS
# =====================================================================
class JuegoReflejos:
    """Gestiona el juego de reflejos con límite de tiempo y métricas."""

    def __init__(self, modo_aleatorio: bool = True):
        self.escena = G1.ruta_escena()
        if not self.escena or not os.path.exists(self.escena):
            raise FileNotFoundError("No se encontró el modelo XML del G1.")

        self.model = mujoco.MjModel.from_xml_path(self.escena)
        self.data = mujoco.MjData(self.model)

        self.entorno = EntornoLuces()
        self.controlador = ControladorBrazosG1(self.model, self.data)
        self.modo_aleatorio = modo_aleatorio
        self.historial_toques = []

    def ejecutar_toque(self, callback_frame=None, umbral_toque: float = 0.048,
                       tiempo_max: float = 2.5) -> dict:
        """Gira el cuerpo y extiende el brazo para tocar la luz encendida."""
        luz = self.entorno.luz_activa
        brazo = luz.brazo_preferido
        objetivo = luz.posicion.copy()
        giro_deg = luz.giro_grados

        t_inicio = time.perf_counter()
        distancia = float(np.linalg.norm(self.controlador.posicion_mano(brazo) - objetivo))
        tocada = False
        pasos = 0

        while (time.perf_counter() - t_inicio) < tiempo_max:
            pasos += 1
            distancia = self.controlador.paso_ik_y_giro(
                brazo, objetivo, giro_deg, ganancia_ik=0.35, ganancia_giro=0.18
            )

            if callback_frame:
                callback_frame()

            if distancia <= umbral_toque:
                tocada = True
                break
            time.sleep(0.01)

        t_reaccion = time.perf_counter() - t_inicio
        resultado = {
            "luz_id": luz.id,
            "luz_nombre": luz.nombre,
            "brazo": brazo,
            "giro_deg": giro_deg,
            "tiempo_reaccion_s": round(t_reaccion, 4),
            "distancia_final_m": round(distancia, 4),
            "tocada": tocada,
            "pasos": pasos,
        }
        self.historial_toques.append(resultado)

        # Retracción suave hacia la guardia
        self.controlador.retraer_a_guardia(brazo, pasos=10)
        if callback_frame:
            callback_frame()

        # Activar la siguiente luz
        if self.modo_aleatorio:
            self.entorno.activar_aleatoria()
        else:
            self.entorno.siguiente_luz()

        return resultado

    def correr_por_tiempo(self, duracion_segundos: float = 30.0, callback_frame=None) -> list:
        """Ejecuta el juego durante el tiempo seleccionado."""
        print(f"\n  Iniciando juego de reflejos por tiempo ({duracion_segundos:.0f} segundos)...")
        print("  " + "-" * 72)
        print(f"  {'#':>3}  {'Luz LED':<20} {'Giro':<8} {'Brazo':<10} {'Tiempo':<10} {'Distancia':<10} {'Estado'}")
        print("  " + "-" * 72)

        t_inicio_partida = time.perf_counter()
        i = 1

        while (time.perf_counter() - t_inicio_partida) < duracion_segundos:
            res = self.ejecutar_toque(callback_frame=callback_frame)
            estado = "[OK] TOCADA" if res["tocada"] else "[X] FALLIDA"
            print(f"  {i:>3}  {res['luz_nombre']:<20} {res['giro_deg']:>+5.0f}°  {res['brazo']:<10} "
                  f"{res['tiempo_reaccion_s']:>6.3f} s  {res['distancia_final_m']*100:>6.2f} cm   {estado}")
            i += 1

        print("  " + "-" * 72)
        tiempo_real = time.perf_counter() - t_inicio_partida
        self._imprimir_resumen(tiempo_total=tiempo_real)
        return self.historial_toques

    def correr_con_ventana(self, duracion_segundos: float = 30.0):
        """Abre la ventana 3D interactiva con MuJoCo Viewer y ejecuta el juego."""
        try:
            import mujoco.viewer
        except Exception as exc:
            print(f"\n[AVISO] No se pudo abrir el visor 3D ({exc}). Corriendo en modo consola...")
            return self.correr_por_tiempo(duracion_segundos)

        print("\n  ==============================================================")
        print("    JUEGO DE REFLEJOS EN VIVO — 6 LUCES LED (Unitree G1)")
        print(f"    Duración seleccionada: {duracion_segundos:.0f} segundos")
        print("    El robot girará y tocará cada luz que se encienda en el abanico.")
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
                    modo_vision=False
                )
                self.entorno.dibujar_en_escena(viewer.user_scn)
                viewer.sync()

            # Pintar el marcador de inmediato al abrir la ventana
            frame_update()

            while viewer.is_running() and (time.perf_counter() - t_inicio) < duracion_segundos:
                luz_actual = self.entorno.luz_activa
                t_restante = max(0.0, duracion_segundos - (time.perf_counter() - t_inicio))
                print(f"  [Quedan {t_restante:4.1f}s | #{ronda}] Luz: {luz_actual.nombre} ({luz_actual.giro_grados:+2.0f}°) -> Girando y tocando...")
                res = self.ejecutar_toque(callback_frame=frame_update)
                ultimo_toque_s = res.get("tiempo_reaccion_s")
                ultimo_nombre_luz = res.get("luz_nombre", "")
                print(f"         ¡TOCADA en {res['tiempo_reaccion_s']:.3f} s con brazo {res['brazo']}!")

                # Pausa breve mostrando el toque y actualizando el marcador
                for _ in range(8):
                    if viewer.is_running():
                        frame_update()
                        time.sleep(0.015)
                ronda += 1

            tiempo_real = time.perf_counter() - t_inicio
            self._imprimir_resumen(tiempo_total=tiempo_real)

    def _imprimir_resumen(self, tiempo_total: float = 30.0):
        if not self.historial_toques:
            print("  No se registraron toques.")
            return
        tiempos = [t["tiempo_reaccion_s"] for t in self.historial_toques]
        tocadas = sum(1 for t in self.historial_toques if t["tocada"])
        total = len(self.historial_toques)
        ppm = (tocadas / tiempo_total) * 60.0 if tiempo_total > 0 else 0

        print("\n  ==============================================================")
        print("    RESULTADOS FINALES DEL JUEGO DE REFLEJOS")
        print("  ==============================================================")
        print(f"    Tiempo total de juego:       {tiempo_total:.1f} s")
        print(f"    Puntuación (Luces tocadas):  {tocadas}/{total} ({tocadas/total*100:.1f} %)")
        print(f"    Ritmo de reacción (PPM):     {ppm:.1f} luces por minuto")
        print(f"    Tiempo de reacción promedio: {np.mean(tiempos):.3f} s")
        print(f"    Mejor reflejo (récord):      {np.min(tiempos):.3f} s")
        print(f"    Tiempo más lento:            {np.max(tiempos):.3f} s")
        print(f"    Desvío estándar:             {np.std(tiempos):.3f} s")
        print("  ==============================================================\n")

    def guardar_reporte_grafico(self, ruta_imagen: str = "reporte_reflejos.png"):
        """Genera un gráfico de evolución de reflejos con matplotlib."""
        import matplotlib.pyplot as plt

        if not self.historial_toques:
            return

        indices = list(range(1, len(self.historial_toques) + 1))
        tiempos = [t["tiempo_reaccion_s"] for t in self.historial_toques]
        etiquetas = [f"{t['luz_nombre'][:8]}\n({t['giro_deg']:+.0f}°)" for t in self.historial_toques]

        plt.figure(figsize=(11, 5.5))
        plt.plot(indices, tiempos, marker='o', color='#0066CC', linewidth=2.5, markersize=7, label='Tiempo de reacción (s)')
        plt.axhline(y=float(np.mean(tiempos)), color='#FF3300', linestyle='--', label=f'Promedio: {np.mean(tiempos):.2f}s')

        plt.title('Entrenamiento de Reflejos — Robot Unitree G1 (6 Luces LED en Abanico)', fontsize=13, fontweight='bold')
        plt.xlabel('Número de Toque (Luz y Giro)', fontsize=11)
        plt.ylabel('Tiempo de Reacción (segundos)', fontsize=11)
        plt.xticks(indices, etiquetas, fontsize=8, rotation=25)
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper right')
        plt.tight_layout()

        plt.savefig(ruta_imagen, dpi=150)
        plt.close()
        print(f"  [REPORTE] Gráfico de rendimiento guardado en: {ruta_imagen}")


# =====================================================================
#  PROGRAMA PRINCIPAL
# =====================================================================
def solicitar_duracion_interactiva() -> float:
    """Pregunta al usuario cuánto tiempo desea jugar."""
    print("\n  ========================================================")
    print("    JUEGO DE REFLEJOS — UNITREE G1 (6 LUCES LED)")
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
    parser = argparse.ArgumentParser(description="Juego de Reflejos con 6 Luces LED para Unitree G1")
    parser.add_argument("--duracion", type=float, default=None, help="Duración del juego en segundos")
    parser.add_argument("--rondas", type=int, default=None, help="Número de luces (si se desea jugar por rondas fijas)")
    parser.add_argument("--aleatorio", action="store_true", default=True, help="Orden de encendido aleatorio")
    parser.add_argument("--secuencial", action="store_true", help="Orden de encendido secuencial (1 al 6)")
    parser.add_argument("--sin-ventana", action="store_true", help="Ejecutar sólo simulación y cálculo sin ventana 3D")
    parser.add_argument("--reporte", action="store_true", default=True, help="Generar gráfico PNG de rendimiento")
    args = parser.parse_args()

    duracion = args.duracion
    if duracion is None and args.rondas is None:
        # Modo interactivo si estamos en consola
        if sys.stdin.isatty():
            duracion = solicitar_duracion_interactiva()
        else:
            duracion = 30.0

    es_aleatorio = not args.secuencial
    juego = JuegoReflejos(modo_aleatorio=es_aleatorio)

    if args.sin_ventana or "--sin-ventana" in sys.argv:
        if args.rondas is not None:
            # Compatibilidad si piden rondas específicas
            duracion_estimada = args.rondas * 1.5
            juego.correr_por_tiempo(duracion_segundos=duracion_estimada)
        else:
            juego.correr_por_tiempo(duracion_segundos=duracion)
    else:
        juego.correr_con_ventana(duracion_segundos=duracion)

    if args.reporte:
        ruta_img = str(Path(__file__).resolve().parent / "reporte_reflejos.png")
        juego.guardar_reporte_grafico(ruta_img)


if __name__ == "__main__":
    main()
