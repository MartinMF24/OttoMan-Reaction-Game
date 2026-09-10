# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  MÓDULO DE MARCADOR EN TIEMPO REAL — ESTÉTICA PREMIER LEAGUE
#
#  Proporciona una superposición gráfica en el visor 3D de MuJoCo con
#  la estética de la Premier League (morado oficial #38003C, verde neón
#  #00FF87, cajas de puntos de alto contraste y reloj en vivo).
# =====================================================================

import time
from typing import Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import mujoco
except ImportError:
    mujoco = None


# Colores de la paleta oficial Premier League
COLOR_PL_PURPLE = (56, 0, 60)       # #38003C
COLOR_PL_NEON_GREEN = (0, 255, 135) # #00FF87
COLOR_PL_PINK = (233, 0, 82)        # #E90052
COLOR_PANEL_DARK = (24, 24, 30)     # Fondo oscuro del panel
COLOR_PANEL_HEADER = (34, 34, 42)   # Encabezado intermedio
COLOR_WHITE = (255, 255, 255)
COLOR_BORDER = (80, 75, 95)
COLOR_BLUE_TEAM = (0, 87, 184)      # Royal Blue para Robot Azul
COLOR_RED_TEAM = (210, 16, 40)      # Crimson Red para Robot Rojo


def _obtener_fuente(tamanio: int, bold: bool = True):
    """Carga fuentes TrueType disponibles en Windows o recurre a la fuente por defecto."""
    candidatos = (
        ['segoeuib.ttf', 'arialbd.ttf', 'calibrib.ttf', 'tahomabd.ttf']
        if bold else
        ['segoeui.ttf', 'arial.ttf', 'calibri.ttf', 'tahoma.ttf']
    )
    for c in candidatos:
        try:
            return ImageFont.truetype(c, tamanio)
        except Exception:
            pass
    return ImageFont.load_default()


class MarcadorPremierLeague:
    """Administra la generación y renderizado del marcador Premier League en MuJoCo."""

    def __init__(self):
        self._cache_individual = {}
        self._cache_competencia = {}
        self._ultimo_punto_tiempo = 0.0
        self._ultimo_puntos_ind = -1
        self._ultimo_puntos_comp = (-1, -1)

        # Pre-cargar fuentes para rendimiento óptimo
        self.f_logo = _obtener_fuente(16, bold=True)
        self.f_sublogo = _obtener_fuente(9, bold=True)
        self.f_tit = _obtener_fuente(14, bold=True)
        self.f_subtit = _obtener_fuente(9, bold=True)
        self.f_pts = _obtener_fuente(28, bold=True)
        self.f_clock = _obtener_fuente(17, bold=True)
        self.f_label = _obtener_fuente(9, bold=True)
        self.f_status = _obtener_fuente(11, bold=True)
        self.f_team = _obtener_fuente(14, bold=True)

    def renderizar_individual(
        self,
        puntos: int,
        tiempo_restante: float,
        ultimo_toque: Optional[float] = None,
        nombre_luz: str = "",
        modo_vision: bool = False
    ) -> np.ndarray:
        """Genera el marcador Premier League para el modo individual."""
        # Clave de caché para evitar redibujar si no ha cambiado el estado visual significativo
        deciseg = int(max(0.0, tiempo_restante) * 10)
        cache_key = (puntos, deciseg, round(ultimo_toque or 0.0, 3), nombre_luz, modo_vision)
        if cache_key in self._cache_individual:
            return self._cache_individual[cache_key]

        # Detectar si acaba de sumar punto para efecto de iluminación
        ahora = time.perf_counter()
        if puntos > self._ultimo_puntos_ind:
            self._ultimo_puntos_ind = puntos
            self._ultimo_punto_tiempo = ahora

        es_flash = (ahora - self._ultimo_punto_tiempo) < 0.45

        w, h = 420, 68
        img = Image.new("RGB", (w, h), COLOR_PANEL_DARK)
        draw = ImageDraw.Draw(img)

        borde_color = COLOR_PL_NEON_GREEN if es_flash else COLOR_BORDER
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=8, outline=borde_color, width=2)

        # 1. Bloque de Marca Premier League (Izquierda)
        draw.rounded_rectangle([2, 2, 54, 46], radius=6, fill=COLOR_PL_PURPLE)
        draw.rectangle([2, 2, 7, 46], fill=COLOR_PL_NEON_GREEN)
        draw.text((16, 12), "PL", fill=COLOR_PL_NEON_GREEN, font=self.f_logo)
        draw.text((15, 31), "ROBOT", fill=COLOR_WHITE, font=self.f_sublogo)

        # 2. Nombre del Robot y Modo
        tit = "UNITREE G1 VISION" if modo_vision else "UNITREE G1 REFLEJOS"
        draw.rectangle([54, 2, 215, 46], fill=COLOR_PANEL_HEADER)
        draw.text((64, 8), tit, fill=COLOR_WHITE, font=self.f_tit)
        sub_desc = "PERCEPCION RGB-D EN VIVO" if modo_vision else "COORDINACION CINEMATICA"
        draw.text((64, 29), sub_desc, fill=COLOR_PL_NEON_GREEN, font=self.f_subtit)

        # 3. Caja de Puntos (Score Box estilo Premier League)
        box_pts_color = (235, 255, 245) if es_flash else COLOR_WHITE
        draw.rectangle([215, 2, 288, 46], fill=box_pts_color)
        draw.text((220, 5), "PUNTOS", fill=COLOR_PL_PURPLE, font=self.f_label)
        pts_str = f"{puntos:02d}"
        draw.text((238, 12), pts_str, fill=COLOR_PL_PURPLE, font=self.f_pts)

        # 4. Reloj de Match (Countdown)
        draw.rounded_rectangle([288, 2, w - 3, 46], radius=6, fill=COLOR_PL_PURPLE)
        draw.text((298, 6), "TIEMPO RESTANTE", fill=(200, 190, 215), font=self.f_label)
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"
        draw.text((298, 20), reloj_str, fill=COLOR_WHITE, font=self.f_clock)

        # 5. Tira inferior de estado / telemetría
        draw.rectangle([2, 47, w - 3, h - 3], fill=(16, 16, 22))
        if ultimo_toque is not None and ultimo_toque > 0:
            sub_txt = f"TOQUE EXITOSO: {ultimo_toque:.3f} s"
            if nombre_luz:
                sub_txt += f" | LUZ: {nombre_luz.upper()}"
            draw.text((12, 50), sub_txt, fill=COLOR_PL_NEON_GREEN, font=self.f_status)
        else:
            draw.text((12, 50), "LISTO PARA REACCIONAR A LA PROXIMA LUZ", fill=(180, 180, 195), font=self.f_status)

        arr = np.array(img, dtype=np.uint8)
        if len(self._cache_individual) > 30:
            self._cache_individual.clear()
        self._cache_individual[cache_key] = arr
        return arr

    def renderizar_competencia(
        self,
        puntos_r1: int,
        puntos_r2: int,
        tiempo_restante: float,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None
    ) -> np.ndarray:
        """Genera el marcador Premier League para el modo competencia (Robot Azul vs Robot Rojo)."""
        deciseg = int(max(0.0, tiempo_restante) * 10)
        cache_key = (puntos_r1, puntos_r2, deciseg, ultimo_ganador or "", round(tiempo_toque or 0.0, 3))
        if cache_key in self._cache_competencia:
            return self._cache_competencia[cache_key]

        ahora = time.perf_counter()
        pts_actuales = (puntos_r1, puntos_r2)
        if pts_actuales != self._ultimo_puntos_comp:
            self._ultimo_puntos_comp = pts_actuales
            self._ultimo_punto_tiempo = ahora

        es_flash = (ahora - self._ultimo_punto_tiempo) < 0.45

        w, h = 500, 72
        img = Image.new("RGB", (w, h), COLOR_PANEL_DARK)
        draw = ImageDraw.Draw(img)

        borde_color = COLOR_PL_NEON_GREEN if es_flash else COLOR_BORDER
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=8, outline=borde_color, width=2)

        # 1. Logo Premier League (Izquierda)
        draw.rounded_rectangle([2, 2, 44, 48], radius=6, fill=COLOR_PL_PURPLE)
        draw.rectangle([2, 2, 7, 48], fill=COLOR_PL_NEON_GREEN)
        draw.text((15, 12), "PL", fill=COLOR_PL_NEON_GREEN, font=self.f_logo)
        draw.text((13, 31), "DUEL", fill=COLOR_WHITE, font=self.f_sublogo)

        # 2. Equipo Azul (Robot 1)
        draw.rectangle([44, 2, 135, 48], fill=COLOR_BLUE_TEAM)
        draw.text((54, 16), "AZUL", fill=COLOR_WHITE, font=self.f_team)
        draw.text((54, 33), "ROBOT 1", fill=(190, 220, 255), font=self.f_sublogo)

        # 3. Marcador Robot Azul (Caja Blanca)
        draw.rectangle([135, 2, 185, 48], fill=COLOR_WHITE)
        draw.text((144, 10), f"{puntos_r1:02d}", fill=COLOR_BLUE_TEAM, font=self.f_pts)

        # 4. Separador Central Oficial Premier League (Morado + Neon)
        draw.rectangle([185, 2, 215, 48], fill=COLOR_PL_PURPLE)
        draw.text((193, 16), "VS", fill=COLOR_PL_NEON_GREEN, font=self.f_logo)

        # 5. Marcador Robot Rojo (Caja Blanca)
        draw.rectangle([215, 2, 265, 48], fill=COLOR_WHITE)
        draw.text((224, 10), f"{puntos_r2:02d}", fill=COLOR_RED_TEAM, font=self.f_pts)

        # 6. Equipo Rojo (Robot 2)
        draw.rectangle([265, 2, 356, 48], fill=COLOR_RED_TEAM)
        draw.text((275, 16), "ROJO", fill=COLOR_WHITE, font=self.f_team)
        draw.text((275, 33), "ROBOT 2", fill=(255, 210, 220), font=self.f_sublogo)

        # 7. Reloj de Match Oficial
        draw.rounded_rectangle([356, 2, w - 3, 48], radius=6, fill=COLOR_PL_PURPLE)
        draw.text((366, 6), "MATCH TIME", fill=(200, 190, 215), font=self.f_label)
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        draw.text((366, 20), f"{mins:02d}:{segs:02d}.{dec}", fill=COLOR_WHITE, font=self.f_clock)

        # 8. Tira inferior de estado (último punto concedido)
        draw.rectangle([2, 49, w - 3, h - 3], fill=(16, 16, 22))
        if ultimo_ganador:
            gan_color = COLOR_PL_NEON_GREEN
            if "AZUL" in ultimo_ganador.upper():
                gan_color = (100, 175, 255)
            elif "ROJO" in ultimo_ganador.upper():
                gan_color = (255, 110, 120)
            t_str = f" ({tiempo_toque:.3f} s)" if tiempo_toque else ""
            txt_status = f"ULTIMO TOQUE: ¡PUNTO PARA {ultimo_ganador.upper()}!{t_str}"
            draw.text((12, 53), txt_status, fill=gan_color, font=self.f_status)
        else:
            draw.text((12, 53), "DUELO EN VIVO — EL PRIMER ROBOT EN TOCAR LA LUZ SUMA", fill=(190, 190, 205), font=self.f_status)

        arr = np.array(img, dtype=np.uint8)
        if len(self._cache_competencia) > 30:
            self._cache_competencia.clear()
        self._cache_competencia[cache_key] = arr
        return arr

    def generar_texto_individual(
        self,
        puntos: int,
        tiempo_restante: float,
        ronda: int = 1,
        ultimo_toque: Optional[float] = None,
        nombre_luz: str = "",
        modo_vision: bool = False
    ) -> tuple[str, str]:
        """Genera las columnas de texto para el overlay nativo de MuJoCo (mjr_overlay)."""
        tit = "G1 VISION (RGB-D)" if modo_vision else "G1 REFLEJOS"
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"

        ult_str = f"{ultimo_toque:.3f} s" if (ultimo_toque and ultimo_toque > 0) else "---"
        luz_str = nombre_luz.upper() if nombre_luz else "EN ESPERA"

        col1 = (
            f"[PL] {tit}\n"
            f"PUNTOS:   {puntos:02d} TOCADAS\n"
            f"ULTIMO:   {ult_str}"
        )
        col2 = (
            f"RELOJ:  {reloj_str}\n"
            f"RONDA:  #{ronda}\n"
            f"LUZ:    {luz_str}"
        )
        return col1, col2

    def generar_texto_competencia(
        self,
        puntos_r1: int,
        puntos_r2: int,
        tiempo_restante: float,
        ronda: int = 1,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None
    ) -> tuple[str, str]:
        """Genera las columnas de texto para el overlay de competencia (Robot Azul vs Robot Rojo)."""
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"

        if puntos_r1 > puntos_r2:
            lider = f"AZUL (+{puntos_r1 - puntos_r2})"
        elif puntos_r2 > puntos_r1:
            lider = f"ROJO (+{puntos_r2 - puntos_r1})"
        else:
            lider = "EMPATE"

        if ultimo_ganador:
            t_str = f" ({tiempo_toque:.3f}s)" if tiempo_toque else ""
            gan_clean = ultimo_ganador.replace("¡", "").replace("!", "").upper()
            ult_str = f"PUNTO {gan_clean}{t_str}"
        else:
            ult_str = "DUELO EN VIVO"

        col1 = (
            f"[PL] DUELO DE REFLEJOS\n"
            f"[AZUL]  {puntos_r1:02d}  -  {puntos_r2:02d}  [ROJO]\n"
            f"ULTIMO: {ult_str}"
        )
        col2 = (
            f"RELOJ:  {reloj_str}\n"
            f"LIDER:  {lider}\n"
            f"RONDA:  #{ronda}"
        )
        return col1, col2

    def aplicar_al_visor_individual(
        self,
        viewer,
        puntos: int,
        tiempo_restante: float,
        ronda: int = 1,
        ultimo_toque: Optional[float] = None,
        nombre_luz: str = "",
        modo_vision: bool = False
    ):
        """Aplica el marcador individual en la esquina superior izquierda del visor."""
        if viewer is None:
            return

        # 1. Overlay nativo de MuJoCo en TOPLEFT (100% visible y garantizado)
        try:
            col1, col2 = self.generar_texto_individual(
                puntos=puntos,
                tiempo_restante=tiempo_restante,
                ronda=ronda,
                ultimo_toque=ultimo_toque,
                nombre_luz=nombre_luz,
                modo_vision=modo_vision
            )
            font = mujoco.mjtFontScale.mjFONTSCALE_150
            pos = mujoco.mjtGridPos.mjGRID_TOPLEFT
            viewer.set_texts([(font, pos, col1, col2)])
        except Exception:
            pass

        # 2. Overlay gráfico con imagen PIL (si el viewport lo permite)
        try:
            arr = self.renderizar_individual(
                puntos=puntos,
                tiempo_restante=tiempo_restante,
                ultimo_toque=ultimo_toque,
                nombre_luz=nombre_luz,
                modo_vision=modo_vision
            )
            h_img, w_img = arr.shape[:2]
            v_h = viewer.viewport.height
            v_bottom = viewer.viewport.bottom
            v_left = viewer.viewport.left
            pos_x = v_left + 15
            pos_y = max(0, v_bottom + v_h - h_img - 15)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            viewer.set_images([(rect, arr)])
        except Exception:
            pass

    def aplicar_al_visor_competencia(
        self,
        viewer,
        puntos_r1: int,
        puntos_r2: int,
        tiempo_restante: float,
        ronda: int = 1,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None
    ):
        """Aplica el marcador dual de competencia en la esquina superior izquierda del visor."""
        if viewer is None:
            return

        # 1. Overlay nativo de MuJoCo en TOPLEFT (100% visible y garantizado)
        try:
            col1, col2 = self.generar_texto_competencia(
                puntos_r1=puntos_r1,
                puntos_r2=puntos_r2,
                tiempo_restante=tiempo_restante,
                ronda=ronda,
                ultimo_ganador=ultimo_ganador,
                tiempo_toque=tiempo_toque
            )
            font = mujoco.mjtFontScale.mjFONTSCALE_150
            pos = mujoco.mjtGridPos.mjGRID_TOPLEFT
            viewer.set_texts([(font, pos, col1, col2)])
        except Exception:
            pass

        # 2. Overlay gráfico con imagen PIL (si el viewport lo permite)
        try:
            arr = self.renderizar_competencia(
                puntos_r1=puntos_r1,
                puntos_r2=puntos_r2,
                tiempo_restante=tiempo_restante,
                ultimo_ganador=ultimo_ganador,
                tiempo_toque=tiempo_toque
            )
            h_img, w_img = arr.shape[:2]
            v_h = viewer.viewport.height
            v_bottom = viewer.viewport.bottom
            v_left = viewer.viewport.left
            pos_x = v_left + 15
            pos_y = max(0, v_bottom + v_h - h_img - 15)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            viewer.set_images([(rect, arr)])
        except Exception:
            pass

    def aplicar_al_visor(self, viewer, imagen_arr: np.ndarray, margen_x: int = 15, margen_y: int = 15):
        """Método de retrocompatibilidad directa para inyectar imagen."""
        if viewer is None or not hasattr(viewer, "set_images"):
            return
        h_img, w_img = imagen_arr.shape[:2]
        try:
            v_h = viewer.viewport.height
            v_bottom = viewer.viewport.bottom
            v_left = viewer.viewport.left
            pos_x = v_left + margen_x
            pos_y = max(0, v_bottom + v_h - h_img - margen_y)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            viewer.set_images([(rect, imagen_arr)])
        except Exception:
            pass

