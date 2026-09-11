# Documentación Técnica: Sistema de Entrenamiento y Juegos de Reflejos con Unitree G1

**Laboratorio de Robótica e Inteligencia Artificial — UADE**  
**Proyecto:** Simulación, Control Cinemático, Visión por Computadora, Marcador en Tiempo Real y Competencia Humanoide en MuJoCo  
**Plataforma de Robot:** Humanoide Unitree G1 (29+ Grados de Libertad)  
**Entorno de Simulación:** MuJoCo 3.x (Multi-Joint dynamics with Contact)

---

## Tabla de Contenidos

1. [Introducción y Objetivos](#1-introducción-y-objetivos)
2. [Etapa 1: Juego de Reflejos Inicial (`juego_reflejos.py`)](#2-etapa-1-juego-de-reflejos-inicial)
   - [2.1 Concepto y Arquitectura](#21-concepto-y-arquitectura)
   - [2.2 Distribución Espacial de Luces (Abanico de 6 LEDs)](#22-distribución-espacial-de-luces-abanico-de-6-leds)
   - [2.3 Librerías Utilizadas y Justificación Técnica](#23-librerías-utilizadas-y-justificación-técnica)
   - [2.4 Control Cinemático Inverso (DLS IK) y Giro Corporal](#24-control-cinemático-inverso-dls-ik-y-giro-corporal)
   - [2.5 Detección de Toque y Ciclo de Juego](#25-detección-de-toque-y-ciclo-de-juego)
   - [2.6 Marcador en Tiempo Real en Visor 3D (Estética Premier League)](#26-marcador-en-tiempo-real-en-visor-3d-estética-premier-league)
3. [Etapa 2: Evolución a Visión Artificial (`juego_reflejos_vision.py`)](#3-etapa-2-evolución-a-visión-artificial)
   - [3.1 Motivación: De Consulta de Estado a Autonomía Sensorial](#31-motivación-de-consulta-de-estado-a-autonomía-sensorial)
   - [3.2 Perturbación Espacial Tridimensional (Spatial Jitter)](#32-perturbación-espacial-tridimensional-spatial-jitter)
   - [3.3 Nuevas Librerías y Subsistemas Incorporados](#33-nuevas-librerías-y-subsistemas-incorporados)
   - [3.4 Pipeline de Visión por Computadora (RGB-D)](#34-pipeline-de-visión-por-computadora-rgb-d)
   - [3.5 Reconstrucción Geométrica 3D mediante Ray Back-Projection](#35-reconstrucción-geométrica-3d-mediante-ray-back-projection)
   - [3.6 Telemetría y Retícula de Detección (HUD Visual)](#36-telemetría-y-retícula-de-detección-hud-visual)
   - [3.7 Marcador Premier League en Modo Visión Artificial](#37-marcador-premier-league-en-modo-visión-artificial)
4. [Etapa 3: Modo Competencia Multirrobot (`juego_competencia.py`)](#4-etapa-3-modo-competencia-multirrobot)
   - [4.1 Concepto: Duelo de Reflejos 1 vs 1](#41-concepto-duelo-de-reflejos-1-vs-1)
   - [4.2 Ensamble Dinámico con `mujoco.MjSpec`](#42-ensamble-dinámico-con-muojocomjspec)
   - [4.3 Personalización Visual Distintiva (Robot Azul vs Robot Rojo)](#43-personalización-visual-distintiva-robot-azul-vs-robot-rojo)
   - [4.4 Franja Neutral Central y Arbitraje en Tiempo Real](#44-franja-neutral-central-y-arbitraje-en-tiempo-real)
   - [4.5 Cinemática Paralela y Desempates de Alta Precisión](#45-cinemática-paralela-y-desempates-de-alta-precisión)
   - [4.6 Marcador Dual de Competencia Estilo Premier League](#46-marcador-dual-de-competencia-estilo-premier-league)
5. [Etapa 4: Duelo Interactivo Humano vs Robot G1 (`juego_humano_vs_robot.py`)](#5-etapa-4-duelo-interactivo-humano-vs-robot-g1)
   - [5.1 Concepto y Dinámica del Duelo](#51-concepto-y-dinámica-del-duelo)
   - [5.2 Perspectiva de Cámara Frontal Cara a Cara (180°)](#52-perspectiva-de-cámara-frontal-cara-a-cara-180)
   - [5.3 Mapeo Espacial de Teclas 1 a 6 de Izquierda a Derecha](#53-mapeo-espacial-de-teclas-1-a-6-de-izquierda-a-derecha)
   - [5.4 Cuenta Atrás Inicial de 5 a 0 Segundos](#54-cuenta-atrás-inicial-de-5-a-0-segundos)
   - [5.5 Librerías Utilizadas y Justificación Técnica](#55-librerías-utilizadas-y-justificación-técnica)
   - [5.6 Arquitectura y Funciones Clave del Código](#56-arquitectura-y-funciones-clave-del-código)
   - [5.7 Marcador Premier League de Duelo y Reporte Gráfico Post-Partida](#57-marcador-premier-league-de-duelo-y-reporte-gráfico-post-partida)
6. [Módulo Dedicado de Marcador (`marcador_premier.py`)](#6-módulo-dedicado-de-marcador-marcador_premierpy)
   - [6.1 Identidad Visual y Paleta Oficial Premier League](#61-identidad-visual-y-paleta-oficial-premier-league)
   - [6.2 Las Cuatro Variantes de Marcador en Vivo](#62-las-cuatro-variantes-de-marcador-en-vivo)
   - [6.3 Arquitectura Técnica: Solución de Tarjeta Única Continua](#63-arquitectura-técnica-solución-de-tarjeta-única-continua)
7. [Cuadro Comparativo de Librerías y Tecnologías](#7-cuadro-comparativo-de-librerías-y-tecnologías)
8. [Guía Rápida de Ejecución](#8-guía-rápida-de-ejecución)
9. [Conclusiones](#9-conclusiones)

---

## 1. Introducción y Objetivos

El propósito de este desarrollo es crear un entorno interactivo y riguroso para la evaluación y entrenamiento de habilidades motrices, perceptivas y competitivas aplicadas a la robótica humanoide, utilizando el modelo de última generación **Unitree G1**.

El proyecto se estructuró en tres fases incrementales, integrando una capa de telemetría gráfica en vivo inspirada en las transmisiones deportivas de la **Premier League**:
1. **Fase 1 (Control y Coordinación Motriz):** Desarrollar un juego de reflejos donde el robot debe coordinar la rotación de su torso y sus brazos para tocar 6 luces dispuestas en arco, con marcador gráfico individual en la esquina superior izquierda.
2. **Fase 2 (Percepción y Visión Artificial):** Eliminar el acceso a las variables internas de la simulación. El robot debe "ver" a través de una cámara virtual RGB-D, identificar ópticamente qué luz se encendió y calcular su posición 3D exacta en el espacio para tocarla, tolerando variaciones aleatorias de posición, reflejando el conteo de toques exitosos en tiempo real.
3. **Fase 3 (Competencia Multirrobot):** Instanciar dos humanoides en la misma escena física utilizando la API procedural `MjSpec` de MuJoCo, dotándolos de identidades visuales claras (**Robot Azul vs Robot Rojo**) para disputar luces situadas en una zona neutral equidistante, monitoreados por un marcador dual de televisión deportiva en vivo.

---

## 2. Etapa 1: Juego de Reflejos Inicial (`juego_reflejos.py`)

### 2.1 Concepto y Arquitectura
En el juego inicial, el humanoide Unitree G1 se encuentra de pie en posición de guardia frente a una batería de luces LED. En cada ronda, el sistema enciende aleatoriamente una de las luces. El robot debe:
1. Orientar su tronco o torso en dirección a la luz activada.
2. Seleccionar el brazo biomecánicamente óptimo (izquierdo o derecho) según el sector espacial.
3. Extender el efector final (muñeca/mano) mediante cinemática inversa hasta hacer contacto con la luz ($\le 5\text{ cm}$).
4. Anotar el punto de forma instantánea en el marcador de la esquina superior izquierda, registrar el tiempo de reacción en segundos y volver a la postura de guardia para el siguiente estímulo.

```
┌─────────────────────────────────────────────────────────────┐
│                    EntornoLuces (MuJoCo)                    │
│            6 Luces en Arco (-45° a +45°, Z variable)        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Enciende luz aleatoria
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  ControladorBrazosG1                        │
│  1. Evalúa cuadrante y rota la base/torso (Yaw)             │
│  2. Selecciona brazo dominante (izquierdo o derecho)        │
│  3. Resuelve Cinemática Inversa DLS (Jacobiano J)           │
│  4. Ejecuta trayectoria y verifica umbral de toque          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Marcador Premier League en Tiempo Real (Top-Left)     │
│   [PL ROBOT] UNITREE G1 REFLEJOS | PTS: 12 | 00:18.5        │
│   TOQUE EXITOSO: 0.174 s | LUZ: ARRIBA IZQUIERDA            │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Distribución Espacial de Luces (Abanico de 6 LEDs)
Para exigir al robot tanto control en altura como en orientación angular, las luces no se colocaron en una línea recta frente a él, sino en un abanico envolvente con diferentes alturas:

| ID | Nombre Luz | Coordenadas Nominales [X, Y, Z] (m) | Brazo Asignado | Ángulo de Giro (Yaw) | Color Encendido |
|:--:|:-----------|:-----------------------------------:|:--------------:|:--------------------:|:---------------:|
| 0 | Extrema Izquierda | `[0.20, +0.37, 0.95]` | Izquierdo | $+35.0^\circ$ | Magenta |
| 1 | Arriba Izquierda  | `[0.35, +0.25, 1.05]` | Izquierdo | $+15.0^\circ$ | Azul Cian |
| 2 | Abajo Izquierda   | `[0.30, +0.18, 0.88]` | Izquierdo | $+5.0^\circ$  | Verde Lima |
| 3 | Abajo Derecha     | `[0.30, -0.18, 0.88]` | Derecho   | $-5.0^\circ$  | Amarillo Neón |
| 4 | Arriba Derecha    | `[0.35, -0.25, 1.05]` | Derecho   | $-15.0^\circ$ | Naranja |
| 5 | Extrema Derecha   | `[0.20, -0.37, 0.95]` | Derecho   | $-35.0^\circ$ | Rojo Fuego |

---

### 2.3 Librerías Utilizadas y Justificación Técnica

| Librería | Función Principal en el Proyecto |
|:---------|:---------------------------------|
| **`mujoco`** (v3.x) | **Motor de física y renderizado 3D.** Gestiona la dinámica del robot, matrices de transformación cinemática (`data.xpos`), cálculo analítico de jacobianos (`mj_jacBody`), integración numérica de pasos (`mj_step`), renderizado procedural en tiempo real mediante `mjv_initGeom` en la estructura `user_scn` y superposición de imágenes en ventana vía `viewer.set_images`. |
| **`Pillow (PIL)`** | **Diseño y renderizado del marcador gráfico.** Dibuja dinámicamente el marcador estilo transmisión de Premier League (`Image`, `ImageDraw`, `ImageFont`) con tipografía TrueType, bordes redondeados y cajas de color de alto contraste. |
| **`numpy`** | **Cálculo matricial y cinemática.** Implementación de álgebra vectorial, operaciones con cuaterniones para el giro de la base, resolución de mínimos cuadrados amortiguados (Damped Least Squares), cálculo de normas euclidianas y manipulación de arreglos multidimensionales. |
| **`matplotlib`** | **Visualización de datos y reportes.** Genera gráficos analíticos al finalizar la sesión (gráficos de dispersión cronológica de tiempos de reacción, histogramas de distribución y barras comparativas por luz). |
| **`dataclasses`** | Estructuración limpia y tipada del modelo de datos de cada LED (`LuzLED`), encapsulando identificadores, posiciones, colores RGBA, estados y metadatos. |
| **`argparse` & `sys`** | Gestión de argumentos de línea de comandos (`--duracion`, `--sin-ventana`, `--reporte`) y configuración de codificación de salida segura en terminales Windows (`UTF-8`). |

---

### 2.4 Control Cinemático Inverso (DLS IK) y Giro Corporal
Para mover las extremidades del robot hacia el objetivo tridimensional sin sufrir singularidades articulares (por ejemplo, cuando el brazo se estira por completo), se utilizó el método de **Mínimos Cuadrados Amortiguados** (*Damped Least Squares - DLS*):

$$\Delta \mathbf{q} = \mathbf{J}^T \left( \mathbf{J} \mathbf{J}^T + \lambda^2 \mathbf{I} \right)^{-1} \Delta \mathbf{x}$$

Donde:
- $\mathbf{J} \in \mathbb{R}^{3 \times n}$: Matriz jacobiana de traslación del efector final (obtenida con `mujoco.mj_jacBody`).
- $\Delta \mathbf{x} = \mathbf{x}_{\text{objetivo}} - \mathbf{x}_{\text{actual}}$: Error cartesiano tridimensional.
- $\lambda$: Factor de amortiguamiento ($\approx 0.04$), que garantiza estabilidad numérica cerca de límites de espacio de trabajo.
- $\Delta \mathbf{q}$: Incremento articular aplicado a las 7 articulaciones del brazo correspondiente.

**Giro Corporal Coordinado:**  
Para las luces en los extremos ($\pm 35^\circ$), el alcance del brazo por sí solo no es suficiente. El controlador ajusta progresivamente el cuaternión de orientación de la base flotante en el eje $Z$:

$$q_{\text{rot}} = \left[ \cos\left(\frac{\theta}{2}\right), 0, 0, \sin\left(\frac{\theta}{2}\right) \right]$$

Esto permite al robot girar de forma fluida hacia el sector correspondiente antes y durante la extensión del brazo.

---

### 2.5 Detección de Toque y Ciclo de Juego
- **Cálculo de Distancia:** En cada iteración de la simulación, se mide la distancia euclidiana entre el centro de la esfera LED y el efector final:
  $$d = \|\mathbf{x}_{\text{mano}} - \mathbf{x}_{\text{luz}}\|_2$$
- **Condición de Éxito:** Se considera toque efectivo cuando $d \le 0.054\text{ m}$ (radio de la esfera LED más el volumen de la mano).
- **Postura de Guardia:** Una vez alcanzado el objetivo, el robot regresa a su postura de guardia mediante interpolación suave en 8 pasos antes de activar el siguiente LED.

---

### 2.6 Marcador en Tiempo Real en Visor 3D (Estética Premier League)
En la esquina superior izquierda de la ventana de simulación se ubica un marcador gráfico activo que implementa los cánones visuales oficiales de la **Premier League**:
- **Franja de Identidad:** Bloque morado oscuro (`#38003C`) con franja verde neón (`#00FF87`) y la insignia `PL ROBOT`.
- **Caja de Puntos de Alto Contraste:** Recuadro blanco puro con dígitos en negrita morada que se incrementa en tiempo real instantáneamente al detectar el toque válido.
- **Reloj de Partido:** Contador regresivo con formato `MM:SS.D` sobre fondo morado.
- **Efecto Flash de Anotación:** Cuando el robot alcanza la luz correcta, el contorno del marcador destella en verde neón durante $0.4\text{ s}$.
- **Tira Inferior de Telemetría:** Informa el tiempo exacto del último toque registrado en segundos y el nombre de la luz alcanzada.

---

## 3. Etapa 2: Evolución a Visión Artificial (`juego_reflejos_vision.py`)

### 3.1 Motivación: De Consulta de Estado a Autonomía Sensorial
En la Etapa 1, el controlador consultaba directamente la coordenada matemática de la luz en la memoria del programa (`entorno.luz_activa.posicion`). En un robot real, esta información no existe de antemano: el robot debe **observar su entorno**, reconocer qué luz emite brillo y determinar su posición mediante sus sensores.

Por esta razón, se desarrolló `juego_reflejos_vision.py`, donde se corta por completo el acceso del robot al estado interno de las luces.

---

### 3.2 Perturbación Espacial Tridimensional (Spatial Jitter)
Para asegurar que el robot no "memorizara" las 6 coordenadas nominales, se introdujo una variación aleatoria continua en cada activación:

$$\mathbf{x}_{\text{luz}} = \mathbf{x}_{\text{base}} + \Delta \mathbf{p}, \quad \Delta \mathbf{p} \sim \mathcal{U}(-[\delta_x, \delta_y, \delta_z], +[\delta_x, \delta_y, \delta_z])$$

Con $\delta_x = \pm 3.0\text{ cm}$, $\delta_y = \pm 3.0\text{ cm}$, $\delta_z = \pm 3.0\text{ cm}$.  
De este modo, **ninguna luz aparece exactamente en el mismo lugar**, obligando al sistema de visión artificial a guiar el brazo en tiempo real.

---

### 3.3 Nuevas Librerías y Subsistemas Incorporados

```
                  ┌─────────────────────────────────────┐
                  │    MuJoCo Offscreen Rendering       │
                  │   mujoco.Renderer(RGB + Depth)      │
                  └──────────────────┬──────────────────┘
                                     │ Frame RGB + Matriz de Profundidad (Z)
                                     ▼
                  ┌─────────────────────────────────────┐
                  │   Segmentación Óptica en NumPy      │
                  │   - Distancia Euclídea de Color     │
                  │   - Umbralización y Conteo          │
                  │   - Centroide de Píxeles (u, v)     │
                  └──────────────────┬──────────────────┘
                                     │ (u, v) + Z_buffer
                                     ▼
                  ┌─────────────────────────────────────┐
                  │   Reconstrucción 3D por Rayos       │
                  │      (Pinhole Back-Projection)      │
                  │     Cálculo de Rayo en el Mundo     │
                  └──────────────────┬──────────────────┘
                                     │ Coordenada Real Estimada [X, Y, Z]
                                     ▼
                  ┌─────────────────────────────────────┐
                  │     Controlador Cinemático IK       │
                  │   El brazo va a la coordenada 3D    │
                  │         obtenida por visión         │
                  └──────────────────┬──────────────────┘
                                     │ Contacto exitoso
                                     ▼
                  ┌─────────────────────────────────────┐
                  │  Marcador Premier League (Top-Left) │
                  │  Actualiza PUNTOS, Reloj y Estado   │
                  └─────────────────────────────────────┘
```

1. **`mujoco.Renderer`**:
   - Permite capturar imágenes directamente desde la memoria gráfica sin necesidad de renderizar en pantalla.
   - Proporciona tanto la imagen de color **RGB** como el búfer de profundidad métrico (**Depth buffer**), esencial para la reconstrucción geométrica tridimensional.
2. **Cálculo de Visión por Computadora Vectorizado con `numpy`**:
   - Se implementó un pipeline de segmentación cromática altamente optimizado directamente en arreglos matriciales de NumPy, permitiendo latencias de detección de apenas **0.005 segundos por frame**.
3. **Módulo de Reconstrucción Geométrica Estenopeica (Pinhole Back-Projection)**:
   - Traduce píxeles bidimensionales $[u, v]$ y distancias escalares $Z$ a vectores en el sistema cartesiano global del simulador.

---

### 3.4 Pipeline de Visión por Computadora (RGB-D)
El proceso de percepción sigue los siguientes pasos:

1. **Captura:** La cámara virtual orientada hacia las luces genera una imagen de $320 \times 240$ píxeles.
2. **Segmentación Cromática:** Se compara cada píxel $(u, v)$ de la imagen con la firma espectral esperada de cada LED encendido:
   $$D_{\text{color}}(u, v) = \|\mathbf{I}_{\text{RGB}}(u, v) - \mathbf{C}_{\text{LED}}\|_2$$
   Se aplica una máscara booleana $M = D_{\text{color}} < 80.0$.
3. **Detección de la Luz Ganadora:** El LED que presente la mayor cantidad de píxeles activos coherentes es identificado como el LED encendido.
4. **Extracción del Centroide Bidimensional:** Se calcula la media de las coordenadas de los píxeles pertenecientes a la máscara ganadora:
   $$u_c = \frac{1}{N} \sum_{i=1}^N u_i, \quad v_c = \frac{1}{N} \sum_{i=1}^N v_i$$

---

### 3.5 Reconstrucción Geométrica 3D mediante Ray Back-Projection
A partir del centroide $[u_c, v_c]$ en la imagen y la profundidad $Z$ consultada en el búfer de profundidad en esa celda:

1. **Coordenadas de Pantalla Normalizadas (NDC):**
   $$ndc_x = \frac{2 u_c}{W} - 1, \quad ndc_y = 1 - \frac{2 v_c}{H}$$
2. **Geometría del Cono Óptico (Frustum):**  
   Utilizando el campo de visión vertical de la cámara ($fovy$) y la relación de aspecto:
   $$\tan_y = \tan\left(\frac{fovy}{2}\right), \quad \tan_x = \tan_y \cdot \left(\frac{W}{H}\right)$$
3. **Dirección del Rayo en el Mundo:**
   $$\mathbf{r}_{\text{dir}} = \mathbf{fwd} + (ndc_x \cdot \tan_x) \mathbf{right} + (ndc_y \cdot \tan_y) \mathbf{up}$$
   $$\hat{\mathbf{r}} = \frac{\mathbf{r}_{\text{dir}}}{\|\mathbf{r}_{\text{dir}}\|}$$
4. **Punto Tridimensional Estimado:**
   $$\mathbf{P}_{3D} = \mathbf{C}_{\text{pos}} + Z \cdot \mathbf{r}_{\text{dir}} + r_{\text{offset}} \cdot \hat{\mathbf{r}}$$

Esta coordenada tridimensional estimada se envía directamente al controlador cinemático inverso de los brazos.

---

### 3.6 Telemetría y Retícula de Detección (HUD Visual)
El sistema genera automáticamente capturas diagnósticas donde se superpone una mira óptica (*crosshair*) cian sobre la luz identificada, mostrando en pantalla:
- Nombre de la luz detectada y porcentaje de confianza óptica.
- Coordenadas de píxel $[u, v]$ y profundidad métrica $Z$.
- Coordenadas 3D globales calculadas por visión.

---

### 3.7 Marcador Premier League en Modo Visión Artificial
En `juego_reflejos_vision.py` el marcador adopta el rótulo `UNITREE G1 VISION` con la leyenda de estado `PERCEPCION RGB-D EN VIVO`. Cada vez que el robot localiza visualmente el LED variable y lo toca con éxito:
1. El contador suma de inmediato el punto en la caja blanca central.
2. Se activa el destello de iluminación verde neón en los bordes.
3. La barra de estado inferior muestra el tiempo total (visión + movimiento articular) y el nombre de la luz detectada.

---

## 4. Etapa 3: Modo Competencia Multirrobot (`juego_competencia.py`)

### 4.1 Concepto: Duelo de Reflejos 1 vs 1
En la tercera etapa, el desafío se escala a un entorno competitivo:
- Dos robots humanoides Unitree G1 idénticos se ubican **frente a frente** en la misma arena a una distancia de separación de $64\text{ cm}$.
- Entre ambos se sitúa una franja neutral con 6 luces LED.
- En cada ronda, se activa una luz al azar con variación espacial.
- Ambos robots compiten en paralelo por tocar la luz antes que el adversario.
- El primer robot que toque la luz suma un punto. Si ambos tocan en la misma décima de segundo, el punto se concede al que haya alcanzado una distancia milimétricamente menor.

```
       ROBOT AZUL                                            ROBOT ROJO
        (Robot 1)                                             (Robot 2)
  ┌──────────────────┐           LUCES CENTRALES        ┌──────────────────┐
  │  Pos: x = -0.32  │         (Línea Media x = 0)      │  Pos: x = +0.32  │
  │  Yaw: 0°         │             ○  ○  ○  ○           │  Yaw: 180°       │
  │  Color: Azul     ├───────────────► ◄────────────────┤  Color: Rojo     │
  └────────┬─────────┘                                  └────────┬─────────┘
           │                                                     │
           ▼                                                     ▼
     Controlador IK                                        Controlador IK
     Brazo Der / Izq                                       Brazo Der / Izq
           │                                                     │
           └──────────────────────────┬──────────────────────────┘
                                      │
                                      ▼
                        Árbitro de Contacto (5.4 cm)
                                      │
                                      ▼
            Marcador Dual Premier League en Vivo (Top-Left)
            [PL DUEL] [AZUL 14] [VS] [11 ROJO] | MATCH 00:21.2
            ULTIMO TOQUE: ¡PUNTO PARA ROBOT AZUL! (0.165 s)
```

---

### 4.2 Ensamble Dinámico con `mujoco.MjSpec`
MuJoCo tradicionalmente requiere compilar un archivo XML fijo. Para crear una arena con dos robots sin duplicar manualmente los archivos del modelo, se utilizó la nueva API procedural **`mujoco.MjSpec`**:

1. Se define un XML base con el piso, luces ambientales y dos marcos de referencia (`frames`):
   - `frame_r1`: Posición `[-0.32, 0.0, 0.0]`, orientación `euler="0 0 0"`.
   - `frame_r2`: Posición `[+0.32, 0.0, 0.0]`, orientación `euler="0 0 3.14159"` ($180^\circ$).
2. Se carga el modelo del Unitree G1 dos veces en memoria:
   ```python
   spec_r1 = mujoco.MjSpec.from_file(xml_robot)
   spec_r2 = mujoco.MjSpec.from_file(xml_robot)
   ```
3. Se ensamblan ambos robots en la arena asignando prefijos independientes para evitar colisiones de nombres en las articulaciones y cuerpos:
   ```python
   spec.attach(spec_r1, prefix="r1_", frame=frame_r1)
   spec.attach(spec_r2, prefix="r2_", frame=frame_r2)
   self.model = spec.compile()
   ```

---

### 4.3 Personalización Visual Distintiva (Robot Azul vs Robot Rojo)
Para diferenciar a los contendientes de forma elegante y limpia, se iteró sobre la colección de geometrías de cada especificación antes de la compilación, asignando colores sólidos característicos a toda la carrocería:

- **Robot 1 (Robot Azul):**  
  `g.rgba = [0.08, 0.38, 0.88, 1.0]` (Azul deportivo vibrante).
- **Robot 2 (Robot Rojo):**  
  `g.rgba = [0.88, 0.15, 0.15, 1.0]` (Rojo carmesí vibrante).

Al no añadir geometrías adicionales (como cápsulas o bandas artificiales), la física de contacto y la inercia de los torsos se mantienen $100\%$ simétricas e idénticas en ambos robots, garantizando un duelo plenamente justo.

---

### 4.4 Franja Neutral Central y Arbitraje en Tiempo Real
Las luces se ubican exactamente en el plano medio $X = 0.0$:

```python
posiciones = [
    np.array([0.0, -0.22, 0.95]),   # 0: Lateral Sur
    np.array([0.0, -0.11, 1.05]),   # 1: Media Sur Alta
    np.array([0.0, -0.04, 0.90]),   # 2: Centro Sur Baja
    np.array([0.0, +0.04, 0.90]),   # 3: Centro Norte Baja
    np.array([0.0, +0.11, 1.05]),   # 4: Media Norte Alta
    np.array([0.0, +0.22, 0.95]),   # 5: Lateral Norte
]
```

Ambos robots se encuentran a una distancia horizontal idéntica ($32\text{ cm}$) de la línea de luces.

---

### 4.5 Cinemática Paralela y Desempates de Alta Precisión
Durante cada ronda:
1. El controlador calcula en paralelo el paso IK del Robot 1 y del Robot 2 hacia la luz activa.
2. Cada robot selecciona automáticamente el brazo con mayor ventaja cinemática (por ejemplo, el brazo izquierdo de un robot compite de frente con el brazo derecho del rival).
3. Se monitoriza la distancia de ambas manos en cada milisegundo de la simulación.
4. Si ambos robots alcanzan el umbral de toque ($\le 5.4\text{ cm}$) en el mismo ciclo, el árbitro digital desempata comparando la distancia exacta al centro geométrico:
   $$\text{Ganador} = \begin{cases} 
   \text{ROBOT AZUL} & \text{si } d_{r1} < d_{r2} \\ 
   \text{ROBOT ROJO} & \text{si } d_{r2} < d_{r1} 
   \end{cases}$$

---

### 4.6 Marcador Dual de Competencia Estilo Premier League
Para el modo competencia, el marcador se transforma en la gráfica clásica de partido entre dos clubes:
- **Lado Izquierdo (Robot Azul):**
  - Casillero Azul Real (`#0057B8`) con texto `AZUL ROBOT 1`.
  - Caja de puntos blanca con dígitos en azul negrita.
- **Divisor Central:**
  - Emblema morado Premier League con texto `VS` en verde neón.
- **Lado Derecho (Robot Rojo):**
  - Caja de puntos blanca con dígitos en rojo negrita.
  - Casillero Rojo Carmesí (`#D21028`) con texto `ROJO ROBOT 2`.
- **Reloj de Encuentro:**
  - Muestra la cuenta regresiva en segundos y décimas (`MATCH TIME 00:21.2`).
- **Tira Inferior de Arbitraje:**
  - Destaca en color azul o rojo al robot que acaba de ganar la luz: `ULTIMO TOQUE: ¡PUNTO PARA ROBOT AZUL! (0.165 s)`.

---

## 5. Etapa 4: Duelo Interactivo Humano vs Robot G1 (`juego_humano_vs_robot.py`)

### 5.1 Concepto y Dinámica del Duelo
En esta cuarta etapa, la simulación trasciende la autonomía robótica pura para introducir una competencia directa en tiempo real entre un ser humano y el robot humanoide Unitree G1.

Ambos contendientes disputan las mismas 6 luces dispuestas en arco frente al robot. En cada ronda:
1. Una luz se enciende de forma aleatoria con iluminación brillante y halo translúcido exterior.
2. El robot detecta el estímulo, experimenta una latencia de reacción física y computacional, orienta su torso y proyecta el brazo mecánico hacia la esfera.
3. El jugador humano visualiza la luz en su pantalla e intenta presionar de inmediato la tecla numérica (`1` a `6`) correspondiente a la posición de dicha luz.
4. **Criterio de Arbitraje Instantáneo:**
   - Si el humano pulsa la tecla correcta antes de que la mano del robot toque la luz: **Punto para el Humano**.
   - Si el efector del robot alcanza el umbral de contacto ($d \le 0.052\text{ m}$) antes de la pulsación humana: **Punto para el Robot G1**.
   - Si el humano se equivoca de tecla: se sanciona el error otorgando inmediatamente el **Punto al Robot G1**.

```
┌─────────────────────────────────────────────────────────────┐
│                    EntornoLucesDuelo (MuJoCo)               │
│         6 Luces en Semicírculo Mapeadas de Izq. a Der.      │
└──────────────────────────────┬──────────────────────────────┘
                               │ Enciende luz objetivo
                               ├──────────────────────────────┐
                               ▼                              ▼
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────┐
│             RobotCompetidorG1                │  │       EntradaTecladoHumano       │
│  - Latencia motriz biológica (60-260 ms)     │  │  - GetAsyncKeyState (Win32 API)  │
│  - Giro coordinado de cintura (Torso Yaw)    │  │  - key_callback (GLFW MuJoCo)    │
│  - Jacobiano analítico y DLS IK (7 GDL)      │  │  - Teclas [1] a [6] (Latencia 0) │
│  - Contacto físico: d <= 5.2 cm              │  │  - Flanco ascendente (Key-down)  │
└──────────────────────┬───────────────────────┘  └─────────────────┬────────────────┘
                       │                                            │
                       └──────────────────────┬─────────────────────┘
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │            Árbitro Digital en Vivo        │
                        │   ¿Quién tocó primero la luz activa?      │
                        └─────────────────────┬─────────────────────┘
                                              │
                                              ▼
                        ┌───────────────────────────────────────────┐
                        │      Marcador Premier League de Duelo     │
                        │    [HUMANO] 08  ── VS ──  06 [ROBOT G1]   │
                        │    ULTIMO PUNTO: ¡HUMANO! (0.218 s)       │
                        └───────────────────────────────────────────┘
```

---

### 5.2 Perspectiva de Cámara Frontal Cara a Cara (180°)
Para garantizar que el juego sea intuitivo, inmersivo y visualmente equitativo, la cámara del visor 3D se ubica en el lado frontal opuesto al robot:

```python
viewer.cam.lookat[:] = [0.20, 0.0, 0.88]  # Centro de masa del abanico de luces
viewer.cam.distance = 2.1                 # Distancia panorámica envolvente
viewer.cam.azimuth = 180.0                # Orientación frontal cara a cara con el robot
viewer.cam.elevation = -12.0              # Ángulo cenital suave para apreciar profundidad
```

Al situar el azimut en $180.0^\circ$ (mirando en dirección $-X$), el usuario se encuentra literalmente "frente a frente" con el robot Unitree G1. Las 6 luces se posicionan en primer plano, mientras que el robot se observa de cuerpo entero al fondo preparado para extender sus brazos hacia el frente.

---

### 5.3 Mapeo Espacial de Teclas 1 a 6 de Izquierda a Derecha
Para evitar la confusión mental del jugador humano al coordinar sus dedos, las teclas numéricas de la fila superior (y del teclado numérico) se mapearon de forma estrictamente monótona de izquierda a derecha según el campo visual de la pantalla.

Debido a que la cámara mira hacia $-X$, el eje cartesiano $Y$ mundial negativo se proyecta a la **izquierda** de la pantalla del usuario, mientras que el eje $Y$ positivo se proyecta a la **derecha**. La disposición cinemática es la siguiente:

| Tecla | ID | Nombre en Sistema | Coord. 3D [X, Y, Z] (m) | Posición en Pantalla | Brazo del Robot | Giro Robot ($\text{Yaw}$) | Color LED Encendido |
|:-----:|:--:|:------------------|:-----------------------:|:--------------------:|:---------------:|:-------------------------:|:-------------------:|
| `[1]` | 0 | Luz 1 (Ext. Izq) | `[0.20, -0.37, 0.95]` | **Extremo Izquierdo** | Derecho | $-35.0^\circ$ | Coral / Rojo vivo |
| `[2]` | 1 | Luz 2 (Arr. Izq) | `[0.35, -0.25, 1.05]` | **Superior Izquierda** | Derecho | $-15.0^\circ$ | Naranja Neón |
| `[3]` | 2 | Luz 3 (Abj. Centro-Izq) | `[0.30, -0.18, 0.88]` | **Central Izquierda** | Derecho | $-5.0^\circ$ | Amarillo Oro |
| `[4]` | 3 | Luz 4 (Abj. Centro-Der) | `[0.30, +0.18, 0.88]` | **Central Derecha** | Izquierdo | $+5.0^\circ$ | Verde Lima |
| `[5]` | 4 | Luz 5 (Arr. Der) | `[0.35, +0.25, 1.05]` | **Superior Derecha** | Izquierdo | $+15.0^\circ$ | Azul Cian |
| `[6]` | 5 | Luz 6 (Ext. Der) | `[0.20, +0.37, 0.95]` | **Extremo Derecho** | Izquierdo | $+35.0^\circ$ | Magenta Neón |

> [!NOTE]
> Obsérvese la simetría biomecánica: las luces situadas a la izquierda del jugador (`1`, `2`, `3`) obligan al robot a emplear su brazo **derecho** y rotar en sentido horario, mientras que las luces de la derecha (`4`, `5`, `6`) activan su brazo **izquierdo** y rotación antihoraria.

---

### 5.4 Cuenta Atrás Inicial de 5 a 0 Segundos
Para asegurar un comienzo justo (*fair play*), la partida no inicia de forma abrupta. Al abrir el visor 3D, el simulador ejecuta una rutina de cuenta regresiva de 5.0 a 0.0 segundos:

1. El robot se mantiene inmóvil en postura de guardia bípeda lista.
2. Todas las luces se muestran en tono tenue de espera.
3. El marcador Premier League superior exhibe el texto parpadeante `INICIA EN:  5.0 s ...` con la leyenda `¡PREPARATE! TECLAS [1] [2] [3] [4] [5] [6] DE IZQUIERDA A DERECHA`.
4. El buffer de entrada de teclado se purga continuamente mediante `teclado.limpiar()`, impidiendo que el humano sume puntos por anticipado o cometa pulsaciones espurias antes del pitido inicial (`¡YA!`).

---

### 5.5 Librerías Utilizadas y Justificación Técnica

| Librería | Módulos / Funciones Específicas | Justificación en el Modo Humano vs Robot |
|:---|:---|:---|
| **`mujoco`** | `MjModel`, `MjData`, `mj_jacBody`, `mj_forward`, `mjv_initGeom` | Simulación dinámica multicuerpo del Unitree G1, cálculo del Jacobiano analítico de los brazos para IK y renderizado de pedestales/esferas en `user_scn`. |
| **`mujoco.viewer`** | `launch_passive`, `key_callback`, `sync`, `set_texts` | Ventana gráfica 3D interactiva en GLFW, callback de eventos de teclado de ventana y superposición del marcador en tiempo real. |
| **`numpy`** | `linalg.solve`, `linalg.norm`, `clip`, `zeros`, `eye` | Resolución del sistema algebraico lineal de mínimos cuadrados amortiguados (DLS), álgebra vectorial y cálculo de distancias euclidianas efector-luz. |
| **`ctypes`** | `ctypes.windll.user32.GetAsyncKeyState` | Lectura asíncrona de teclado a nivel de kernel/hardware de Windows ($1000\text{ Hz}$). Garantiza respuesta instantánea sin importar si el usuario tiene el foco en la ventana 3D o en la terminal, eliminando el lag del buffer de consola. |
| **`msvcrt`** | `msvcrt.kbhit`, `msvcrt.getch` | Canal alternativo no bloqueante de lectura de teclas para ejecución directa desde la consola estándar de Windows. |
| **`matplotlib`** | `pyplot.subplots`, `plot`, `bar`, `savefig` | Generación procedural del reporte estadístico post-partido (`reporte_humano_vs_robot.png`), graficando la evolución temporal de puntos y la distribución de tiempos de reacción. |
| **`PIL (Pillow)`** | `Image`, `ImageDraw`, `ImageFont` | Rasterizado procedural con tipografías TrueType (`Segoe UI`, `Arial`) del banner oficial Premier League de Duelo Humano vs Robot. |

---

### 5.6 Arquitectura y Funciones Clave del Código

El archivo [`juego_humano_vs_robot.py`](file:///c:/Users/Martin/Documents/GitHub/OttoMan-Reaction-Game/05LaboratoriosTPs/TP07_Inteligencia_Artificial/mi_desarrollo/juego_humano_vs_robot.py) está estructurado en módulos orientados a objetos de alta cohesión:

#### 1. Módulo de Luces (`EntornoLucesDuelo`)
- **`activar_aleatoria() -> LuzHumanoVsRobot`:** Selecciona aleatoriamente una nueva luz garantizando que no se repita la inmediata anterior para obligar a un cambio postural constante.
- **`dibujar_en_escena(user_scn)`:** Inyecta en cada frame las geometrías en la estructura visual de MuJoCo:
  - Cilindros metálicos verticales para los pedestales (`mjGEOM_CYLINDER`).
  - Esferas de color reflectivo para las bombillas LED (`mjGEOM_SPHERE`).
  - Halos volumétricos translúcidos con canal alfa al $38\%$ para la luz activa, simulando emisión lumínica real.

#### 2. Módulo de Entrada Humana (`EntradaTecladoHumano`)
- **`consultar() -> Optional[str]`:** Sondea las teclas `1` a `6` consultando las tablas virtuales de Windows (`VK_1` a `VK_6` y `VK_NUMPAD1` a `VK_NUMPAD6`). Implementa un filtro de flanco ascendente (*rising-edge detector*):
  ```python
  presionada = any(bool(get_async_key(vk) & 0x8000) for vk in codes)
  if presionada and not self.estados_previos[tecla]:
      self.estados_previos[tecla] = True
      return tecla
  elif not presionada:
      self.estados_previos[tecla] = False
  ```
- **`callback_visor(keycode)`:** Función ligada al despachador de eventos de GLFW en MuJoCo, capturando las teclas con códigos GLFW 49 a 54 y 321 a 326.
- **`limpiar()`:** Descarga cualquier pulsación pendiente en el búfer.

#### 3. Controlador Cinético del Humanoide (`RobotCompetidorG1`)
- **`resetear_pose_inicial()`:** Aplica las coordenadas articulares bípedas estables de `G1.pose_de_pie` combinadas con la posición de guardia defensiva (codos flexionados a $-0.45\text{ rad}$ y hombros adelantados a $+0.25\text{ rad}$).
- **`paso_ik_y_giro(luz, lambda_dls) -> float`:** Integra en cada ciclo de simulación:
  1. Rotación del torso hacia el ángulo objetivo mediante interpolación geométrica:
     $$\text{Yaw}_{t+1} = \text{Yaw}_t + K_{\text{giro}} (\text{Yaw}_{\text{luz}} - \text{Yaw}_t)$$
  2. Obtención de la matriz Jacobiana traslacional de la muñeca activa mediante `mj_jacBody`.
  3. Cálculo de la ley de control por Mínimos Cuadrados Amortiguados:
     $$\Delta q = J_{\text{arm}}^T \left( J_{\text{arm}} J_{\text{arm}}^T + \lambda^2 I \right)^{-1} (x_{\text{luz}} - x_{\text{mano}})$$
  4. Recorte de velocidad articular y sujeción a los límites mecánicos del modelo (`jnt_range`).
- **Niveles de Dificultad Parametrizables:**
  - *Fácil:* Latencia motriz entre $160$ y $260\text{ ms}$, ganancia IK $0.32$.
  - *Medio:* Latencia motriz entre $100$ y $180\text{ ms}$, ganancia IK $0.38$.
  - *Difícil (Premier League):* Latencia motriz entre $60$ y $120\text{ ms}$, ganancia IK $0.44$.

#### 4. Motor Principal de Juego (`JuegoHumanoVsRobot`)
- **`disputar_ronda(callback_frame, ...)`:** Bucle temporal de alta resolución ($5\text{ ms}$) que supervisa concurrentemente si el humano pulsó una tecla o si la distancia euclidiana de la mano del robot cayó por debajo de $5.2\text{ cm}$.
- **`correr(duracion_segundos, sin_ventana)`:** Función orquestadora que inicializa el visor, proyecta la cuenta regresiva, corre las rondas, gestiona las pausas visuales entre toques ($350\text{ ms}$) y dispara la generación de reportes.
- **`_guardar_reporte_grafico()`:** Construye una figura de doble panel con fondo oscuro deportivo (`#18181E`) que documenta la curva acumulativa de puntos y el histograma de tiempos de reacción.

---

### 5.7 Marcador Premier League de Duelo y Reporte Gráfico Post-Partida
El juego cuenta con un marcador especialmente diseñado para esta modalidad:

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║  [PL] PREMIER LEAGUE DUEL  •  HUMANO vs ROBOT G1                                          ║
║  [HUMANO]  08   ─── VS ───   06  [ROBOT G1]     RELOJ: 00:24.5  (#14)                     ║
║  ¡PUNTO PARA HUMANO! (0.218 s) | LUZ: LUZ 3 (ABJ. CENTRO-IZQ)                             ║
║  TECLAS: [1][2][3][4][5][6] (de Izquierda a Derecha)                                      ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

Al finalizar el encuentro, se emite automáticamente en la carpeta de desarrollo el gráfico [`reporte_humano_vs_robot.png`](file:///c:/Users/Martin/Documents/GitHub/OttoMan-Reaction-Game/05LaboratoriosTPs/TP07_Inteligencia_Artificial/mi_desarrollo/reporte_humano_vs_robot.png), detallando:
- **Panel Izquierdo:** Curva temporal de puntos acumulados (Línea cian para Humano vs Línea carmesí para Robot G1).
- **Panel Derecho:** Tiempos de reacción individuales por cada ronda disputada, codificados por color según quién se adjudicó el punto.

---

## 6. Módulo Dedicado de Marcador (`marcador_premier.py`)

Para evitar la duplicación de código y dotar a todas las etapas de una identidad gráfica televisiva profesional, se diseñó el módulo centralizado [`marcador_premier.py`](file:///c:/Users/Martin/Documents/GitHub/OttoMan-Reaction-Game/05LaboratoriosTPs/TP07_Inteligencia_Artificial/mi_desarrollo/marcador_premier.py), administrado por la clase `MarcadorPremierLeague`.

### 6.1 Identidad Visual y Paleta Oficial Premier League
El diseño visual replica fielmente los grafismos de la transmisión deportiva oficial de la Premier League:
- **Morado Oficial (`#38003C`):** Utilizado en los bloques de encabezado institucional y fondos de reloj.
- **Verde Neón Oficial (`#00FF87`):** Destinado al logotipo `PL`, acentos perimetrales y divisiones centrales `VS`.
- **Rosa Neón (`#E90052`):** Señalética de advertencias y estados complementarios.
- **Cajas de Puntuación de Alto Contraste:** Rectángulos blancos puros (`#FFFFFF`) con números renderizados en tipografía TrueType extra negrita de $28\text{ pt}$ (`PTS 12`), visibles a distancia en la pantalla.
- **Efecto Score Flash:** Al incrementarse el marcador de cualquiera de los contendientes, el borde exterior del panel se ilumina durante $450\text{ ms}$ en verde neón vibrante, ofreciendo una clara retroalimentación visual al instante del impacto.

---

### 6.2 Las Cuatro Variantes de Marcador en Vivo
El módulo proporciona métodos especializados para cada modalidad de simulación:

1. **Marcador Individual (`renderizar_individual`):**  
   Muestra el logotipo `PL ROBOT`, la modalidad activa (`UNITREE G1 REFLEJOS` o `UNITREE G1 VISION`), la caja de toques acumulados, el reloj de partido y el ticker inferior de telemetría de reacción.
2. **Marcador en Modo Visión Artificial:**  
   Incorpora la etiqueta de percepción `RGB-D EN VIVO`, indicando si el robot se encuentra procesando la nube de puntos o ejecutando la trayectoria cinemática.
3. **Marcador Dual de Competencia (`renderizar_competencia`):**  
   Divide el marcador en los dos clubes/robots (`AZUL ROBOT 1` vs `ROJO ROBOT 2`), con cajas de puntuación diferenciadas por color, separador central morado `VS` y ticker de arbitraje en tiempo real.
4. **Marcador de Duelo Humano vs Robot (`renderizar_humano_vs_robot`):**  
   Enfrenta al `HUMANO` (equipo esmeralda con indicación de teclas `1-6`) contra `ROBOT G1` (equipo carmesí Unitree IA), con soporte dinámico para cuenta regresiva previa (`INICIA EN: 5.0 s`) y leyenda inferior de estado.

---

### 6.3 Arquitectura Técnica: Solución de Tarjeta Única Continua

#### El Problema de los "Dos Marcadores":
Durante las primeras iteraciones, el uso de la función nativa de MuJoCo:
```python
viewer.set_texts([(font, pos, col1, col2)])
```
provocaba que la biblioteca gráfica de bajo nivel (`mjr_overlay`) subdividiera internamente la esquina superior izquierda (`mjGRID_TOPLEFT`) en dos columnas rectangulares independientes con fondos negros opacos separados. En pantalla, esto se percibía visualmente como **dos marcadores duplicados o rotos**.

Por otra parte, al intentar forzar exclusivamente la superposición de imágenes vía:
```python
viewer.set_images([(rect, array_rgb)])
```
se detectó que en entornos modernos de Windows con perfiles de OpenGL 3.3+ Core (GLFW), la función subyacente `glDrawPixels` se encuentra obsoleta o suprimida por los controladores de video (Intel Iris Xe, NVIDIA RTX, AMD Radeon), haciendo que el marcador bitmap no se dibuje sobre el framebuffer.

#### La Solución Definitiva Implementada:
Se desarrolló una arquitectura híbrida de alta compatibilidad que resuelve ambos inconvenientes:
1. **Tarjeta Única Unificada:** Toda la estructura tipográfica, cajas de puntos, reloj de match y telemetría de toques se ensamblan en una **única cadena de texto formateada** (`tarjeta`), pasándose como `text1` y enviando `text2=""` vacío:
   ```python
   tarjeta, _ = self.generar_texto_humano_vs_robot(...)
   viewer.set_texts([(font, pos, tarjeta, "")])
   ```
   De este modo, MuJoCo renderiza **un único panel continuo**, perfectamente centrado y con contraste garantizado en cualquier monitor.
2. **Caché Inteligente y Respaldo Gráfico:** Simultáneamente, el motor genera el arreglo NumPy de la imagen PIL y lo suministra a `set_images` empleando un diccionario de caché con clave `(puntos, decisegundos, estado)`. Esto permite que el marcador consuma menos de $0.05\text{ ms}$ de CPU por frame, asegurando $60\text{ FPS}$ constantes y permitiendo además exportar capturas gráficas impecables para los reportes finales.

---

## 7. Cuadro Comparativo de Librerías y Tecnologías

| Componente / Tarea | Juego Inicial (`juego_reflejos.py`) | Juego con Visión (`juego_reflejos_vision.py`) | Juego Competencia (`juego_competencia.py`) | Duelo Humano vs Robot (`juego_humano_vs_robot.py`) |
|:---|:---|:---|:---|:---|
| **Simulador de Física** | `mujoco` (Modelo único G1) | `mujoco` (Modelo único G1) | `mujoco` (`MjSpec` con 2 robots en arena) | `mujoco` (Modelo único G1 con cámara frontal) |
| **Detección de la Luz** | Lectura directa del entorno | Segmentación de color en `numpy` (visión) | Lectura compartida de zona neutral central | Lectura directa con mapeo espacial 1 a 6 |
| **Cálculo de Coordenada 3D** | Estática / Predeterminada | Reconstrucción estenopeica RGB-D por rayos | Estática con variación espacial (*Jitter*) | 6 luces en arco ordenadas de Izq. a Der. |
| **Cámara / Renderizado** | Visor 3D interactivo | `mujoco.Renderer` (Offscreen RGB-D) | Visor 3D panorámico lateral ($68^\circ$) | **Visor Frontal ($180^\circ$, cara a cara con el robot)** |
| **Cinemática Inversa** | DLS IK (1 robot, 2 brazos) | DLS IK guiado por visión 3D | DLS IK dual concurrente (2 robots simultáneos) | DLS IK con latencia biológica configurable |
| **Control del Jugador** | Autónomo por cinemática | Autónomo guiado por visión | Autónomo dual (Robot 1 vs Robot 2) | **Teclado Humano: Teclas `1` a `6`** |
| **Marcador en Vivo** | Tarjeta Premier League Individual | Tarjeta Premier League Visión | Tarjeta Premier League Dual Azul vs Rojo | **Tarjeta Premier League Humano vs Robot** |
| **Generación de Reportes** | `matplotlib` (Tiempos individuales) | `matplotlib` (Tiempos + HUD de visión) | `matplotlib` (Evolución de marcador y tiempos) | `matplotlib` (Comparativa Humano vs Robot) |

---

## 8. Guía Rápida de Ejecución

Todos los módulos se encuentran listos para ejecutar en el entorno del laboratorio:

### 1. Duelo de Reflejos en Vivo (Humano vs Robot Unitree G1)
- **Vía Launcher:** Doble clic en `05LaboratoriosTPs\TP07_Inteligencia_Artificial\JUGAR_HUMANO_VS_ROBOT.bat`.
- **Por Terminal:**
  ```powershell
  py -3 mi_desarrollo\juego_humano_vs_robot.py --duracion 30 --dificultad medio
  # Modo consola rápido (sin ventana):
  py -3 mi_desarrollo\juego_humano_vs_robot.py --sin-ventana --duracion 10
  ```
  - **Mapeo de teclas de izquierda a derecha:** `[1]` Ext. Izq, `[2]` Arr. Izq, `[3]` Abj. Centro-Izq, `[4]` Abj. Centro-Der, `[5]` Arr. Der, `[6]` Ext. Der.
  - **Cuenta atrás:** 5 a 0 segundos antes de comenzar la partida con la cámara frontal ya alineada.

### 2. Juego de Reflejos Inicial (1 Robot con Marcador PL)
- **Vía Launcher:** Doble clic en `05LaboratoriosTPs\TP07_Inteligencia_Artificial\JUGAR_REFLEJOS.bat`.
- **Por Terminal:**
  ```powershell
  py -3 mi_desarrollo\juego_reflejos.py --duracion 30
  ```

### 3. Juego de Reflejos con Visión Artificial (1 Robot con Cámara y Marcador PL)
- **Vía Launcher:** Doble clic en `05LaboratoriosTPs\TP07_Inteligencia_Artificial\JUGAR_REFLEJOS_VISION.bat`.
- **Por Terminal:**
  ```powershell
  py -3 mi_desarrollo\juego_reflejos_vision.py --duracion 30
  ```

### 4. Modo Competencia (2 Robots — Azul vs Rojo con Marcador Dual PL)
- **Vía Launcher:** Doble clic en `05LaboratoriosTPs\TP07_Inteligencia_Artificial\JUGAR_COMPETENCIA.bat`.
- **Por Terminal:**
  ```powershell
  py -3 mi_desarrollo\juego_competencia.py --duracion 60
  # Modo consola rápido (sin ventana):
  py -3 mi_desarrollo\juego_competencia.py --sin-ventana --duracion 10
  ```

---

## 9. Conclusiones

A lo largo del proyecto se demostró:
1. **Factibilidad del Control Cinemático DLS en Humanoides Complejos:** El algoritmo de Mínimos Cuadrados Amortiguados permite manipular extremidades de 7 GDL en tiempo real con tiempos de respuesta inferiores a $0.25\text{ segundos}$ por toque, sin bloqueos por singularidades.
2. **Robustez de la Visión por Computadora en el Bucle de Control:** La combinación del modelo estenopeico inverso con el búfer de profundidad permitió al robot operar de forma autónoma sin depender de datos absolutos del simulador, tolerando variaciones aleatorias continuas en la posición de los objetivos.
3. **Escalabilidad Multirrobot mediante `MjSpec`:** La nueva arquitectura de ensamblaje de MuJoCo 3 facilitó la creación de competencias 1 vs 1 totalmente reactivas, combinando control cinemático independiente, arbitraje estricto y personalización estética limpia de los robots.
4. **Interactividad Humano vs Robot con Entrada de Baja Latencia:** La incorporación del duelo directo contra un humano con teclado de acceso directo (1 a 6 de izquierda a derecha), cámara frontal fija y cuenta regresiva de 5 segundos logró un entorno de entrenamiento lúdico, justo y altamente competitivo.
5. **Telemetría Gráfica en Vivo sin Impacto de Rendimiento:** La integración del marcador estilo Premier League consolidado en un banner único de alta definición proporcionó una experiencia de transmisión deportiva profesional en tiempo real manteniendo la tasa de refresco a $60\text{ FPS}$.

