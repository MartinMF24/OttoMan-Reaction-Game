# =====================================================================
#  TP07 - Inteligencia Artificial / Laboratorio de Robótica UADE
#  MÓDULO DE MARCADOR EN TIEMPO REAL — ESTÉTICA PREMIER LEAGUE
#
#  Proporciona una superposición gráfica en el visor 3D de MuJoCo con
#  la estética de la Premier League (morado oficial #38003C, verde neón
#  #00FF87, cajas de puntos de alto contraste y reloj en vivo).
# =====================================================================

import math
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
        self._cache_cuenta_atras = {}
        self._cache_fin_de_juego = {}
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
        self.f_big_num = _obtener_fuente(76, bold=True)
        self.f_fin_tit = _obtener_fuente(22, bold=True)
        self.f_fin_sub = _obtener_fuente(13, bold=True)
        self.f_fin_pts = _obtener_fuente(34, bold=True)
        self.f_fin_body = _obtener_fuente(12, bold=False)

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

    def renderizar_humano_vs_robot(
        self,
        puntos_humano: int,
        puntos_robot: int,
        tiempo_restante: float,
        cuenta_atras: Optional[float] = None,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None,
        nombre_luz: str = ""
    ) -> np.ndarray:
        """Genera el marcador Premier League para el modo Humano vs Robot G1."""
        deciseg = int(max(0.0, tiempo_restante) * 10)
        cuenta_int = int((cuenta_atras or 0.0) * 10)
        cache_key = (puntos_humano, puntos_robot, deciseg, cuenta_int, ultimo_ganador or "", round(tiempo_toque or 0.0, 3))
        if cache_key in self._cache_competencia:
            return self._cache_competencia[cache_key]

        ahora = time.perf_counter()
        pts_actuales = (puntos_humano, puntos_robot)
        if pts_actuales != self._ultimo_puntos_comp:
            self._ultimo_puntos_comp = pts_actuales
            self._ultimo_punto_tiempo = ahora

        es_flash = (ahora - self._ultimo_punto_tiempo) < 0.45

        w, h = 530, 74
        img = Image.new("RGB", (w, h), COLOR_PANEL_DARK)
        draw = ImageDraw.Draw(img)

        borde_color = COLOR_PL_NEON_GREEN if es_flash else COLOR_BORDER
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=8, outline=borde_color, width=2)

        # 1. Logo Premier League (Izquierda)
        draw.rounded_rectangle([2, 2, 44, 48], radius=6, fill=COLOR_PL_PURPLE)
        draw.rectangle([2, 2, 7, 48], fill=COLOR_PL_NEON_GREEN)
        draw.text((15, 12), "PL", fill=COLOR_PL_NEON_GREEN, font=self.f_logo)
        draw.text((12, 31), "DUEL", fill=COLOR_WHITE, font=self.f_sublogo)

        # 2. Equipo Humano (Verde esmeralda / Cyan)
        color_humano = (0, 140, 160)
        draw.rectangle([44, 2, 145, 48], fill=color_humano)
        draw.text((54, 16), "HUMANO", fill=COLOR_WHITE, font=self.f_team)
        draw.text((54, 33), "TECLADO 1-6", fill=(210, 245, 255), font=self.f_sublogo)

        # 3. Marcador Humano (Caja Blanca)
        draw.rectangle([145, 2, 195, 48], fill=COLOR_WHITE)
        draw.text((154, 10), f"{puntos_humano:02d}", fill=color_humano, font=self.f_pts)

        # 4. Separador Central Oficial Premier League (Morado + Neon)
        draw.rectangle([195, 2, 225, 48], fill=COLOR_PL_PURPLE)
        draw.text((203, 16), "VS", fill=COLOR_PL_NEON_GREEN, font=self.f_logo)

        # 5. Marcador Robot (Caja Blanca)
        draw.rectangle([225, 2, 275, 48], fill=COLOR_WHITE)
        draw.text((234, 10), f"{puntos_robot:02d}", fill=COLOR_RED_TEAM, font=self.f_pts)

        # 6. Equipo Robot (Robot G1 - Rojo)
        draw.rectangle([275, 2, 376, 48], fill=COLOR_RED_TEAM)
        draw.text((285, 16), "ROBOT G1", fill=COLOR_WHITE, font=self.f_team)
        draw.text((285, 33), "UNITREE IA", fill=(255, 210, 220), font=self.f_sublogo)

        # 7. Reloj / Cuenta atrás
        draw.rounded_rectangle([376, 2, w - 3, 48], radius=6, fill=COLOR_PL_PURPLE)
        if cuenta_atras is not None and cuenta_atras > 0.0:
            draw.text((386, 6), "INICIA EN", fill=COLOR_PL_NEON_GREEN, font=self.f_label)
            draw.text((386, 20), f"  {cuenta_atras:.1f} s", fill=COLOR_PL_NEON_GREEN, font=self.f_clock)
        else:
            draw.text((386, 6), "MATCH TIME", fill=(200, 190, 215), font=self.f_label)
            t_pos = max(0.0, tiempo_restante)
            mins = int(t_pos // 60)
            segs = int(t_pos % 60)
            dec = int((t_pos * 10) % 10)
            draw.text((386, 20), f"{mins:02d}:{segs:02d}.{dec}", fill=COLOR_WHITE, font=self.f_clock)

        # 8. Tira inferior de estado (resultado y guía de teclas)
        draw.rectangle([2, 49, w - 3, h - 3], fill=(16, 16, 22))
        if cuenta_atras is not None and cuenta_atras > 0.0:
            txt_status = "¡PREPARATE! TECLAS [1] [2] [3] [4] [5] [6] DE IZQUIERDA A DERECHA"
            draw.text((12, 53), txt_status, fill=COLOR_PL_NEON_GREEN, font=self.f_status)
        elif ultimo_ganador:
            gan_color = COLOR_PL_NEON_GREEN if "HUMANO" in ultimo_ganador.upper() else (255, 110, 120)
            t_str = f" ({tiempo_toque:.3f} s)" if tiempo_toque else ""
            txt_status = f"ULTIMO PUNTO: ¡{ultimo_ganador.upper()}!{t_str} | TECLAS 1-6"
            draw.text((12, 53), txt_status, fill=gan_color, font=self.f_status)
        else:
            draw.text((12, 53), "DUELO EN VIVO: PRESIONA LA TECLA DE LA LUZ ANTES QUE EL ROBOT", fill=(190, 190, 205), font=self.f_status)

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
        """Genera una tarjeta única e integrada Premier League para el modo individual."""
        tit = "G1 VISION (RGB-D)" if modo_vision else "G1 REFLEJOS"
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"

        ult_str = f"{ultimo_toque:.3f} s" if (ultimo_toque and ultimo_toque > 0) else "LISTO"
        luz_str = nombre_luz.upper() if nombre_luz else "EN ESPERA"

        # Tarjeta única Premier League sin divisiones
        tarjeta = (
            f"  [PL] PREMIER LEAGUE  •  UNITREE {tit}\n"
            f"  PUNTOS: [ {puntos:02d} ]      RELOJ: {reloj_str}      RONDA: #{ronda}\n"
            f"  TOQUE EXITOSO: {ult_str}  |  LUZ: {luz_str}"
        )
        return tarjeta, ""

    def generar_texto_competencia(
        self,
        puntos_r1: int,
        puntos_r2: int,
        tiempo_restante: float,
        ronda: int = 1,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None
    ) -> tuple[str, str]:
        """Genera una tarjeta única e integrada Premier League para el modo competencia dual."""
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"

        if puntos_r1 > puntos_r2:
            lider = f"LIDER: AZUL (+{puntos_r1 - puntos_r2})"
        elif puntos_r2 > puntos_r1:
            lider = f"LIDER: ROJO (+{puntos_r2 - puntos_r1})"
        else:
            lider = "EMPATE"

        if ultimo_ganador:
            t_str = f" ({tiempo_toque:.3f} s)" if tiempo_toque else ""
            gan_clean = ultimo_ganador.replace("¡", "").replace("!", "").upper()
            ult_str = f"¡PUNTO PARA {gan_clean}!{t_str}"
        else:
            ult_str = "DUELO EN VIVO (ZONA CENTRAL)"

        tarjeta = (
            f"  [PL] PREMIER LEAGUE MATCH  •  UNITREE G1 DUAL\n"
            f"  [AZUL]  {puntos_r1:02d}   ─── VS ───   {puntos_r2:02d}  [ROJO]    RELOJ: {reloj_str}  (#{ronda})\n"
            f"  {ult_str}  |  {lider}"
        )
        return tarjeta, ""

    def generar_texto_humano_vs_robot(
        self,
        puntos_humano: int,
        puntos_robot: int,
        tiempo_restante: float,
        ronda: int = 1,
        cuenta_atras: Optional[float] = None,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None,
        nombre_luz: str = ""
    ) -> tuple[str, str]:
        """Genera una tarjeta única e integrada Premier League para el duelo Humano vs Robot."""
        t_pos = max(0.0, tiempo_restante)
        mins = int(t_pos // 60)
        segs = int(t_pos % 60)
        dec = int((t_pos * 10) % 10)
        reloj_str = f"{mins:02d}:{segs:02d}.{dec}"

        if cuenta_atras is not None and cuenta_atras > 0.0:
            tarjeta = (
                f"  [PL] PREMIER LEAGUE DUEL  •  HUMANO vs ROBOT G1\n"
                f"  [HUMANO]  00   ─── VS ───   00  [ROBOT G1]    ¡PREPARATE!\n"
                f"  LA PARTIDA COMIENZA EN:  {cuenta_atras:.1f} s ...\n"
                f"  TECLAS: [1][2][3][4][5][6] (de Izquierda a Derecha)"
            )
            return tarjeta, ""

        if ultimo_ganador:
            t_str = f" ({tiempo_toque:.3f} s)" if tiempo_toque else ""
            gan_clean = ultimo_ganador.replace("¡", "").replace("!", "").upper()
            ult_str = f"¡PUNTO PARA {gan_clean}!{t_str}"
        else:
            ult_str = "DUELO EN VIVO: PRESIONA LA TECLA ANTES QUE EL ROBOT TOQUE"

        luz_str = f" | LUZ: {nombre_luz.upper()}" if nombre_luz else ""

        tarjeta = (
            f"  [PL] PREMIER LEAGUE DUEL  •  HUMANO vs ROBOT G1\n"
            f"  [HUMANO]  {puntos_humano:02d}   ─── VS ───   {puntos_robot:02d}  [ROBOT G1]    RELOJ: {reloj_str}  (#{ronda})\n"
            f"  {ult_str}{luz_str}\n"
            f"  TECLAS: [1][2][3][4][5][6] (de Izquierda a Derecha)"
        )
        return tarjeta, ""

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
        """Aplica el marcador Premier League individual como una tarjeta única en el visor."""
        if viewer is None:
            return

        # 1. Overlay Premier League (tarjeta única, 100% visible sin duplicaciones)
        try:
            tarjeta, _ = self.generar_texto_individual(
                puntos=puntos,
                tiempo_restante=tiempo_restante,
                ronda=ronda,
                ultimo_toque=ultimo_toque,
                nombre_luz=nombre_luz,
                modo_vision=modo_vision
            )
            font = mujoco.mjtFontScale.mjFONTSCALE_150
            pos = mujoco.mjtGridPos.mjGRID_TOPLEFT
            viewer.set_texts([(font, pos, tarjeta, "")])
        except Exception:
            pass

        # 2. Overlay gráfico con imagen PIL (para visores que admitan set_images)
        try:
            arr = self.renderizar_individual(
                puntos=puntos,
                tiempo_restante=tiempo_restante,
                ultimo_toque=ultimo_toque,
                nombre_luz=nombre_luz,
                modo_vision=modo_vision
            )
            h_img, w_img = arr.shape[:2]
            v_h = getattr(viewer.viewport, "height", 720) or 720
            v_bottom = getattr(viewer.viewport, "bottom", 0) or 0
            v_left = getattr(viewer.viewport, "left", 0) or 0
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
        """Aplica el marcador Premier League de competencia como una tarjeta única en el visor."""
        if viewer is None:
            return

        # 1. Overlay Premier League (tarjeta única, 100% visible sin duplicaciones)
        try:
            tarjeta, _ = self.generar_texto_competencia(
                puntos_r1=puntos_r1,
                puntos_r2=puntos_r2,
                tiempo_restante=tiempo_restante,
                ronda=ronda,
                ultimo_ganador=ultimo_ganador,
                tiempo_toque=tiempo_toque
            )
            font = mujoco.mjtFontScale.mjFONTSCALE_150
            pos = mujoco.mjtGridPos.mjGRID_TOPLEFT
            viewer.set_texts([(font, pos, tarjeta, "")])
        except Exception:
            pass

        # 2. Overlay gráfico con imagen PIL
        try:
            arr = self.renderizar_competencia(
                puntos_r1=puntos_r1,
                puntos_r2=puntos_r2,
                tiempo_restante=tiempo_restante,
                ultimo_ganador=ultimo_ganador,
                tiempo_toque=tiempo_toque
            )
            h_img, w_img = arr.shape[:2]
            v_h = getattr(viewer.viewport, "height", 720) or 720
            v_bottom = getattr(viewer.viewport, "bottom", 0) or 0
            v_left = getattr(viewer.viewport, "left", 0) or 0
            pos_x = v_left + 15
            pos_y = max(0, v_bottom + v_h - h_img - 15)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            viewer.set_images([(rect, arr)])
        except Exception:
            pass

    def renderizar_cuenta_atras(self, segundo: int) -> np.ndarray:
        """Genera un cartel central prominente con el contador 5, 4, 3, 2, 1."""
        if segundo in self._cache_cuenta_atras:
            return self._cache_cuenta_atras[segundo]

        w, h = 460, 200
        img = Image.new("RGB", (w, h), COLOR_PANEL_DARK)
        draw = ImageDraw.Draw(img)

        # Borde con esquinas redondeadas en verde neón oficial
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, outline=COLOR_PL_NEON_GREEN, width=3)

        # Encabezado Premier League
        draw.rounded_rectangle([3, 3, w - 4, 44], radius=10, fill=COLOR_PL_PURPLE)
        draw.rectangle([3, 3, 10, 44], fill=COLOR_PL_NEON_GREEN)
        draw.text((22, 12), "PREMIER LEAGUE DUEL", fill=COLOR_PL_NEON_GREEN, font=self.f_tit)
        draw.text((290, 15), "¡PREPARATE!", fill=COLOR_WHITE, font=self.f_sublogo)

        # Número gigante del contador
        texto_num = str(segundo) if segundo > 0 else "¡YA!"
        color_num = COLOR_PL_NEON_GREEN if segundo > 0 else COLOR_PL_PINK

        # Centrar el número
        bbox = draw.textbbox((0, 0), texto_num, font=self.f_big_num)
        ancho_num = bbox[2] - bbox[0]
        alto_num = bbox[3] - bbox[1]
        x_num = (w - ancho_num) // 2
        y_num = 48 + (96 - alto_num) // 2
        draw.text((x_num, y_num), texto_num, fill=color_num, font=self.f_big_num)

        # Pie con indicador de teclas
        draw.rectangle([3, 152, w - 4, h - 4], fill=(16, 16, 22))
        pie_txt = "TECLAS [1] [2] [3] [4] [5] [6] DE IZQUIERDA A DERECHA"
        bbox_pie = draw.textbbox((0, 0), pie_txt, font=self.f_subtit)
        w_pie = bbox_pie[2] - bbox_pie[0]
        draw.text(((w - w_pie) // 2, 166), pie_txt, fill=(200, 225, 255), font=self.f_subtit)

        arr = np.array(img, dtype=np.uint8)
        self._cache_cuenta_atras[segundo] = arr
        return arr

    def renderizar_fin_de_juego(
        self,
        puntos_humano: int,
        puntos_robot: int,
        total_rondas: int,
        t_medio_h: float,
        t_medio_r: float,
        t_rec_h: float = 0.0,
        t_rec_r: float = 0.0
    ) -> np.ndarray:
        """Genera una pantalla gráfica completa y destacada de fin de juego con ganador y resultado."""
        cache_key = (puntos_humano, puntos_robot, total_rondas, round(t_medio_h, 3), round(t_medio_r, 3))
        if cache_key in self._cache_fin_de_juego:
            return self._cache_fin_de_juego[cache_key]

        w, h = 580, 320
        img = Image.new("RGB", (w, h), COLOR_PANEL_DARK)
        draw = ImageDraw.Draw(img)

        # Determinar ganador
        if puntos_humano > puntos_robot:
            color_ganador = COLOR_PL_NEON_GREEN
            txt_ganador = "¡¡¡ CAMPEON HUMANO: VICTORIA !!!"
            sub_ganador = "¡FELICITACIONES! GANASTE EL DUELO CONTRA EL ROBOT G1"
            borde_color = COLOR_PL_NEON_GREEN
        elif puntos_robot > puntos_humano:
            color_ganador = COLOR_PL_PINK
            txt_ganador = "VICTORIA ROBOT UNITREE G1"
            sub_ganador = "EL ROBOT G1 SE LLEVA EL MATCH DE REFLEJOS"
            borde_color = COLOR_PL_PINK
        else:
            color_ganador = (255, 215, 0)
            txt_ganador = "¡¡¡ EMPATE EMOCIONANTE !!!"
            sub_ganador = "MATCH IGUALADO — NINGUNO DIO EL BRAZO A TORCER"
            borde_color = (255, 215, 0)

        # Marco exterior redondeado
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, outline=borde_color, width=3)

        # 1. Cabecera Premier League
        draw.rounded_rectangle([3, 3, w - 4, 42], radius=10, fill=COLOR_PL_PURPLE)
        draw.rectangle([3, 3, 10, 42], fill=borde_color)
        draw.text((22, 11), "PREMIER LEAGUE DUEL  •  RESULTADOS FINALES", fill=COLOR_WHITE, font=self.f_tit)

        # 2. Banner de Campeón / Ganador
        draw.rectangle([3, 44, w - 4, 108], fill=(30, 26, 40))
        bbox_gan = draw.textbbox((0, 0), txt_ganador, font=self.f_fin_tit)
        w_gan = bbox_gan[2] - bbox_gan[0]
        draw.text(((w - w_gan) // 2, 52), txt_ganador, fill=color_ganador, font=self.f_fin_tit)

        bbox_sub = draw.textbbox((0, 0), sub_ganador, font=self.f_fin_sub)
        w_sub = bbox_sub[2] - bbox_sub[0]
        draw.text(((w - w_sub) // 2, 84), sub_ganador, fill=COLOR_WHITE, font=self.f_fin_sub)

        # 3. Cajas de Marcador (Humano vs Robot)
        y_box = 114
        h_box = 80

        # Caja Humano
        color_h_bg = (0, 120, 140)
        draw.rounded_rectangle([25, y_box, 260, y_box + h_box], radius=8, fill=color_h_bg)
        draw.text((40, y_box + 8), "HUMANO (TECLAS 1-6)", fill=COLOR_WHITE, font=self.f_label)
        draw.text((40, y_box + 24), f"{puntos_humano:02d} PTS", fill=COLOR_WHITE, font=self.f_fin_pts)
        pct_h = (puntos_humano / max(1, total_rondas)) * 100
        draw.text((160, y_box + 35), f"{pct_h:.1f}%", fill=(210, 245, 255), font=self.f_status)

        # VS central
        draw.text((276, y_box + 28), "VS", fill=borde_color, font=self.f_tit)

        # Caja Robot
        color_r_bg = (180, 15, 40)
        draw.rounded_rectangle([320, y_box, 555, y_box + h_box], radius=8, fill=color_r_bg)
        draw.text((335, y_box + 8), "ROBOT UNITREE G1", fill=COLOR_WHITE, font=self.f_label)
        draw.text((335, y_box + 24), f"{puntos_robot:02d} PTS", fill=COLOR_WHITE, font=self.f_fin_pts)
        pct_r = (puntos_robot / max(1, total_rondas)) * 100
        draw.text((455, y_box + 35), f"{pct_r:.1f}%", fill=(255, 215, 225), font=self.f_status)

        # 4. Estadísticas y telemetría
        y_stats = 202
        draw.rectangle([3, y_stats, w - 4, y_stats + 68], fill=(18, 18, 24))
        rec_h_str = f" | Récord: {t_rec_h:.3f} s" if t_rec_h > 0 else ""
        rec_r_str = f" | Récord: {t_rec_r:.3f} s" if t_rec_r > 0 else ""
        line1 = f"Total Luces Disputadas: {total_rondas}"
        line2 = f"Reflejo Medio Humano: {t_medio_h:.3f} s{rec_h_str}"
        line3 = f"Reflejo Medio Robot G1: {t_medio_r:.3f} s{rec_r_str}"
        draw.text((30, y_stats + 8), line1, fill=(220, 220, 230), font=self.f_fin_body)
        draw.text((30, y_stats + 27), line2, fill=(100, 230, 255), font=self.f_fin_body)
        draw.text((30, y_stats + 46), line3, fill=(255, 130, 150), font=self.f_fin_body)

        # 5. Barra inferior con llamada a la acción
        draw.rounded_rectangle([3, h - 44, w - 4, h - 4], radius=6, fill=COLOR_PL_PURPLE)
        cta_txt = ">> PRESIONA CUALQUIER BOTON O TECLA PARA SALIR <<"
        bbox_cta = draw.textbbox((0, 0), cta_txt, font=self.f_tit)
        w_cta = bbox_cta[2] - bbox_cta[0]
        draw.text(((w - w_cta) // 2, h - 34), cta_txt, fill=COLOR_PL_NEON_GREEN, font=self.f_tit)

        arr = np.array(img, dtype=np.uint8)
        self._cache_fin_de_juego[cache_key] = arr
        return arr

    def generar_texto_fin_de_juego(
        self,
        puntos_humano: int,
        puntos_robot: int,
        total_rondas: int,
        t_medio_h: float,
        t_medio_r: float,
        t_rec_h: float = 0.0,
        t_rec_r: float = 0.0
    ) -> tuple[str, str, str]:
        """Genera los textos para el visor (HUD) al terminar el match."""
        if puntos_humano > puntos_robot:
            titulo = "*** ¡¡¡CAMPEON HUMANO: VICTORIA!!! ***"
        elif puntos_robot > puntos_humano:
            titulo = "*** VICTORIA ROBOT UNITREE G1 ***"
        else:
            titulo = "*** ¡¡¡EMPATE EMOCIONANTE!!! ***"

        rec_h = f" (Record: {t_rec_h:.3f}s)" if t_rec_h > 0 else ""
        rec_r = f" (Record: {t_rec_r:.3f}s)" if t_rec_r > 0 else ""

        tarjeta = (
            f"  [PL] RESULTADO FINAL — DUELO HUMANO vs ROBOT G1\n"
            f"  {titulo}\n"
            f"  [HUMANO] {puntos_humano:02d} PTS   ─── VS ───   {puntos_robot:02d} PTS [ROBOT G1]\n"
            f"  Luces disputadas: {total_rondas}\n"
            f"  T. Reflejo Humano: {t_medio_h:.3f} s{rec_h}  |  Robot: {t_medio_r:.3f} s{rec_r}"
        )
        centro = f"\n\n\n          {titulo}          \n"
        pie = "\n   >> PRESIONA CUALQUIER BOTON O TECLA PARA SALIR <<   \n"
        return tarjeta, centro, pie

    def aplicar_al_visor_humano_vs_robot(
        self,
        viewer,
        puntos_humano: int,
        puntos_robot: int,
        tiempo_restante: float,
        ronda: int = 1,
        cuenta_atras: Optional[float] = None,
        ultimo_ganador: Optional[str] = None,
        tiempo_toque: Optional[float] = None,
        nombre_luz: str = ""
    ):
        """Aplica el marcador Premier League de Humano vs Robot como tarjeta única en el visor."""
        if viewer is None:
            return

        # 1. Overlay Premier League (solo textos centrales, omitimos tarjeta superior)
        try:
            text_items = [] # Inicializamos la lista vacía

            # Si estamos en cuenta regresiva inicial, mostrar el número gigante 5 4 3 2 1
            if cuenta_atras is not None and cuenta_atras > 0.0:
                seg_actual = int(math.ceil(cuenta_atras))
                texto_centro = f"\n\n\n            [  {seg_actual}  ]            \n\n    ¡PREPARATE! TECLAS 1 A 6    "
                text_items.append((mujoco.mjtFontScale.mjFONTSCALE_300, mujoco.mjtGridPos.mjGRID_TOP, texto_centro, ""))

            if text_items:
                viewer.set_texts(text_items)
        except Exception:
            pass

        # 2. Overlay gráfico con imagen PIL
        try:
            images = []
            arr = self.renderizar_humano_vs_robot(
                puntos_humano=puntos_humano,
                puntos_robot=puntos_robot,
                tiempo_restante=tiempo_restante,
                cuenta_atras=cuenta_atras,
                ultimo_ganador=ultimo_ganador,
                tiempo_toque=tiempo_toque,
                nombre_luz=nombre_luz
            )
            h_img, w_img = arr.shape[:2]
            v_w = getattr(viewer.viewport, "width", 1280) or 1280
            v_h = getattr(viewer.viewport, "height", 720) or 720
            v_bottom = getattr(viewer.viewport, "bottom", 0) or 0
            v_left = getattr(viewer.viewport, "left", 0) or 0
            pos_x = v_left + 15
            pos_y = max(0, v_bottom + v_h - h_img - 15)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            images.append((rect, arr))

            # Si hay cuenta regresiva, agregar tarjeta gráfica central 5 4 3 2 1
            if cuenta_atras is not None and cuenta_atras > 0.0:
                seg_actual = int(math.ceil(cuenta_atras))
                arr_cuenta = self.renderizar_cuenta_atras(seg_actual)
                hc, wc = arr_cuenta.shape[:2]
                pos_cx = max(0, v_left + (v_w - wc) // 2)
                pos_cy = max(0, v_bottom + (v_h - hc) // 2)
                images.append((mujoco.MjrRect(pos_cx, pos_cy, wc, hc), arr_cuenta))

            viewer.set_images(images)
        except Exception:
            pass

    def aplicar_visor_fin_de_juego(
        self,
        viewer,
        puntos_humano: int,
        puntos_robot: int,
        historial: list
    ):
        """Aplica la pantalla final interactiva de ganador y resultado al visor MuJoCo."""
        if viewer is None:
            return

        total_rondas = len(historial)
        tiempos_h = [r["tiempo_s"] for r in historial if "HUMANO" in r["ganador"] and "FALLO" not in r["ganador"]]
        tiempos_r = [r["tiempo_s"] for r in historial if "ROBOT" in r["ganador"]]

        t_medio_h = float(np.mean(tiempos_h)) if tiempos_h else 0.0
        t_medio_r = float(np.mean(tiempos_r)) if tiempos_r else 0.0
        t_rec_h = float(min(tiempos_h)) if tiempos_h else 0.0
        t_rec_r = float(min(tiempos_r)) if tiempos_r else 0.0

        # 1. Overlay HUD de textos en pantalla
        try:
            tarjeta, centro, pie = self.generar_texto_fin_de_juego(
                puntos_humano=puntos_humano,
                puntos_robot=puntos_robot,
                total_rondas=total_rondas,
                t_medio_h=t_medio_h,
                t_medio_r=t_medio_r,
                t_rec_h=t_rec_h,
                t_rec_r=t_rec_r
            )
            texts = [
                # Eliminamos la tarjeta superior para que no pise el gráfico de PIL
                (mujoco.mjtFontScale.mjFONTSCALE_300, mujoco.mjtGridPos.mjGRID_TOP, centro, ""),
                (mujoco.mjtFontScale.mjFONTSCALE_200, mujoco.mjtGridPos.mjGRID_BOTTOM, pie, ""),
            ]
            viewer.set_texts(texts)
        except Exception:
            pass

        # 2. Overlay gráfico PIL centrado en pantalla
        try:
            arr = self.renderizar_fin_de_juego(
                puntos_humano=puntos_humano,
                puntos_robot=puntos_robot,
                total_rondas=total_rondas,
                t_medio_h=t_medio_h,
                t_medio_r=t_medio_r,
                t_rec_h=t_rec_h,
                t_rec_r=t_rec_r
            )
            h_img, w_img = arr.shape[:2]
            v_w = getattr(viewer.viewport, "width", 1280) or 1280
            v_h = getattr(viewer.viewport, "height", 720) or 720
            v_bottom = getattr(viewer.viewport, "bottom", 0) or 0
            v_left = getattr(viewer.viewport, "left", 0) or 0

            pos_x = max(0, v_left + (v_w - w_img) // 2)
            pos_y = max(0, v_bottom + (v_h - h_img) // 2)
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
            v_h = getattr(viewer.viewport, "height", 720) or 720
            v_bottom = getattr(viewer.viewport, "bottom", 0) or 0
            v_left = getattr(viewer.viewport, "left", 0) or 0
            pos_x = v_left + margen_x
            pos_y = max(0, v_bottom + v_h - h_img - margen_y)
            rect = mujoco.MjrRect(pos_x, pos_y, w_img, h_img)
            viewer.set_images([(rect, imagen_arr)])
        except Exception:
            pass

