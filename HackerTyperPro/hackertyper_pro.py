import pygame
import random
import sys
import os
import math
import time

# =========================================================================
# CONFIGURACIÓN GENERAL DE LA TERMINAL DE INTELIGENCIA TÁCTICA
# =========================================================================
ANCHO_VENTANA = 1024
ALTO_VENTANA = 650
FPS = 30

ANCHO_MATRIZ = 58
ALTO_MATRIZ = 20

COLOR_FONDO = (0, 5, 0)
COLOR_LINEA_VIVA = (50, 255, 50)   # Verde brillante activo
COLOR_TEXTO_OPAC = (0, 80, 0)      # Verde oscuro para la lluvia Matrix de fondo
COLOR_VENTANA_BORD = (0, 180, 0)   # Bordes tácticos
COLOR_BOTON_ACTIVO = (100, 255, 100)
COLOR_ALERTA = (255, 70, 70)
COLOR_AMBAR = (255, 200, 60)


# =========================================================================
# UTILIDADES
# =========================================================================
class CacheGlifos:
    """Guarda cada letra ya renderizada (letra + color) para no redibujarla cada frame."""
    def __init__(self, fuente):
        self.fuente = fuente
        self.cache = {}

    def get(self, caracter, color):
        clave = (caracter, color)
        s = self.cache.get(clave)
        if s is None:
            s = self.fuente.render(caracter, True, color)
            self.cache[clave] = s
        return s


class Particulas:
    """Chispas que salen al teclear, acertar o fallar."""
    def __init__(self):
        self.lista = []

    def emitir(self, x, y, cantidad, color, vel=3.5):
        for _ in range(cantidad):
            ang = random.uniform(0, math.tau)
            v = random.uniform(0.5, vel)
            self.lista.append([x, y, math.cos(ang) * v, math.sin(ang) * v - 0.6,
                               random.randint(10, 26), color])

    def actualizar(self):
        for p in self.lista:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.09
            p[4] -= 1
        self.lista = [p for p in self.lista if p[4] > 0]

    def dibujar(self, superficie):
        for p in self.lista:
            t = max(1, p[4] // 7)
            pygame.draw.rect(superficie, p[5], (int(p[0]), int(p[1]), t, t))


def cargar_mascara_desde_png(ruta_imagen):
    """Lee un archivo PNG del usuario y lo convierte automáticamente en una máscara de 58x20."""
    mascara = [[0 for _ in range(ANCHO_MATRIZ)] for _ in range(ALTO_MATRIZ)]
    cargada = False
    if os.path.exists(ruta_imagen):
        try:
            img = pygame.image.load(ruta_imagen).convert_alpha()
            img_escalada = pygame.transform.scale(img, (ANCHO_MATRIZ, ALTO_MATRIZ))
            for y in range(ALTO_MATRIZ):
                for x in range(ANCHO_MATRIZ):
                    color = img_escalada.get_at((x, y))
                    # Validar la opacidad del canal alfa para mapear el contorno real de la silueta
                    if color[3] > 50 and (color[0] > 20 or color[1] > 20 or color[2] > 20):
                        mascara[y][x] = 1
                        cargada = True
        except Exception as e:
            print(f"Error procesando {ruta_imagen}: {e}")

    if not cargada:
        # Si no existe la imagen (o quedó vacía), activa una figura de prueba: un cuadrado central
        for y in range(4, 16):
            for x in range(12, 46):
                mascara[y][x] = 1
    return mascara


def crear_overlay_crt():
    """Scanlines + viñeta, se calculan UNA sola vez."""
    overlay = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
    for y in range(0, ALTO_VENTANA, 3):
        pygame.draw.line(overlay, (0, 0, 0, 55), (0, y), (ANCHO_VENTANA, y))

    w, h = 64, 40
    pequena = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            dx = (x / (w - 1) - 0.5) * 2
            dy = (y / (h - 1) - 0.5) * 2
            d = min(1.0, math.sqrt(dx * dx + dy * dy) / 1.414)
            pequena.set_at((x, y), (0, 0, 0, int((d ** 2.2) * 170)))
    vineta = pygame.transform.smoothscale(pequena, (ANCHO_VENTANA, ALTO_VENTANA))
    overlay.blit(vineta, (0, 0))
    return overlay


def aplicar_bloom(lienzo):
    """Resplandor verde: reduce, agranda y suma la imagen sobre sí misma."""
    chica = pygame.transform.smoothscale(lienzo, (ANCHO_VENTANA // 4, ALTO_VENTANA // 4))
    grande = pygame.transform.smoothscale(chica, (ANCHO_VENTANA, ALTO_VENTANA))
    grande.fill((85, 85, 85), special_flags=pygame.BLEND_RGB_MULT)
    lienzo.blit(grande, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# =========================================================================
# COMPONENTES VISUALES
# =========================================================================
class LluviaFondoConsola:
    def __init__(self, x_inicio, y_inicio, ancho, alto):
        self.rect = pygame.Rect(x_inicio, y_inicio, ancho, alto)
        self.columnas = [random.uniform(-25, 0) for _ in range(ANCHO_MATRIZ)]
        self.velocidades = [random.uniform(0.3, 0.9) for _ in range(ANCHO_MATRIZ)]
        self.largos = [random.randint(4, 9) for _ in range(ANCHO_MATRIZ)]
        self.caracteres = "0123456789X%#@*+=-"

    def actualizar(self):
        for i in range(len(self.columnas)):
            self.columnas[i] += self.velocidades[i]
            if self.columnas[i] - self.largos[i] > ALTO_MATRIZ:
                self.columnas[i] = random.uniform(-12, 0)
                self.velocidades[i] = random.uniform(0.3, 0.9)
                self.largos[i] = random.randint(4, 9)

    def dibujar(self, superficie, cache):
        for x_idx, cabeza in enumerate(self.columnas):
            cab = int(cabeza)
            largo = self.largos[x_idx]
            for k in range(largo):
                y_idx = cab - k
                if 0 <= y_idx < ALTO_MATRIZ:
                    if k == 0:
                        color = (40, 170, 40)           # cabeza de la gota
                    else:
                        v = 1 - k / largo
                        color = (0, int(18 + 62 * v), 0)  # estela que se apaga
                    txt = cache.get(random.choice(self.caracteres), color)
                    superficie.blit(txt, (self.rect.x + 15 + (x_idx * 12), self.rect.y + 35 + (y_idx * 21)))


class PlanetaSatelite:
    def __init__(self, cx, cy, radio):
        self.cx = cx
        self.cy = cy
        self.radio = radio
        self.angulo = 0.0
        self.orbita = 0.0
        self.estela = []

    def actualizar(self):
        self.angulo += 0.04
        self.orbita += 0.05
        r = self.radio + 24
        px = self.cx + math.cos(self.orbita) * r
        py = self.cy + math.sin(self.orbita) * r * 0.35
        self.estela.append((px, py, math.sin(self.orbita) < 0))
        if len(self.estela) > 14:
            self.estela.pop(0)

    def dibujar(self, superficie, fuente):
        r = self.radio
        pygame.draw.circle(superficie, COLOR_VENTANA_BORD, (self.cx, self.cy), r, 1)

        # Paralelos (latitudes)
        for lat in (-60, -30, 0, 30, 60):
            rad = math.radians(lat)
            y = self.cy - int(r * math.sin(rad))
            mitad = int(r * math.cos(rad))
            pygame.draw.line(superficie, (0, 55, 0), (self.cx - mitad, y), (self.cx + mitad, y), 1)

        # Meridianos (longitudes) que giran
        for i in range(4):
            ancho = int(abs(math.cos(self.angulo + i * math.pi / 4)) * r * 2)
            if ancho > 2:
                pygame.draw.ellipse(superficie, COLOR_TEXTO_OPAC,
                                    (self.cx - ancho // 2, self.cy - r, ancho, r * 2), 1)

        # Anillo de órbita
        ro = r + 24
        pygame.draw.ellipse(superficie, (0, 60, 0),
                            (self.cx - ro, self.cy - int(ro * 0.35), ro * 2, int(ro * 0.7)), 1)

        # Satélite con estela (se oculta cuando pasa detrás del planeta)
        for i, (px, py, detras) in enumerate(self.estela):
            if detras and abs(px - self.cx) < r:
                continue
            v = int(70 + 185 * i / max(1, len(self.estela)))
            pygame.draw.circle(superficie, (0, v, 0), (int(px), int(py)), 3 if i == len(self.estela) - 1 else 1)

        # Telemetría
        lat = 21.16 + math.sin(self.orbita) * 0.05
        lon = -86.85 + math.cos(self.orbita) * 0.08
        intens = 80 + int(15 * math.sin(self.orbita * 2))
        t1 = fuente.render(f"LAT {lat:8.4f}  LON {lon:8.4f}", True, COLOR_LINEA_VIVA)
        t2 = fuente.render(f"LINK: SECURE   SIG {intens}%", True, COLOR_TEXTO_OPAC)
        superficie.blit(t1, (self.cx - t1.get_width() // 2, self.cy + r + 14))
        superficie.blit(t2, (self.cx - t2.get_width() // 2, self.cy + r + 32))


class GraficoFrecuencia:
    def __init__(self, x, y, ancho, alto):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.fase = 0.0

    def actualizar(self):
        self.fase += 0.25

    def dibujar(self, superficie, fuente):
        r = self.rect
        pygame.draw.rect(superficie, (0, 12, 0), r)
        pygame.draw.rect(superficie, COLOR_VENTANA_BORD, r, 1)

        # Rejilla
        for gx in range(r.x + 26, r.right, 26):
            pygame.draw.line(superficie, (0, 35, 0), (gx, r.y + 1), (gx, r.bottom - 2))
        for gy in range(r.y + 16, r.bottom, 16):
            pygame.draw.line(superficie, (0, 35, 0), (r.x + 1, gy), (r.right - 2, gy))

        # Onda principal + armónico + ruido
        puntos = []
        cy = r.y + r.height / 2
        for x_pos in range(r.x + 4, r.right - 4, 3):
            y_pos = (cy
                     + math.sin((x_pos * 0.07) + self.fase) * (r.height * 0.25)
                     + math.sin((x_pos * 0.19) - self.fase * 1.7) * (r.height * 0.12)
                     + random.uniform(-1.5, 1.5))
            puntos.append((x_pos, int(y_pos)))
        if len(puntos) > 1:
            pygame.draw.lines(superficie, COLOR_LINEA_VIVA, False, puntos, 1)

        # Barra de barrido
        sx = r.x + int((self.fase * 6) % r.width)
        pygame.draw.line(superficie, (120, 255, 120), (sx, r.y + 1), (sx, r.bottom - 2), 1)

        mhz = 88.0 + abs(math.sin(self.fase * 0.1)) * 20
        txt = fuente.render(f"{mhz:6.2f} MHz", True, COLOR_BOTON_ACTIVO)
        superficie.blit(txt, (r.x + 6, r.y + 3))


class BotonTactico:
    def __init__(self, x, y, ancho, alto, texto, id_accion):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.texto = texto
        self.id_accion = id_accion
        self.hover = False
        self.activo = False

    def actualizar(self, pos_mouse):
        self.hover = self.rect.collidepoint(pos_mouse)

    def dibujar(self, superficie, fuente):
        resaltado = self.hover or self.activo
        color = COLOR_BOTON_ACTIVO if resaltado else COLOR_VENTANA_BORD
        relleno = (0, 70, 0) if self.activo else ((0, 40, 0) if self.hover else (0, 20, 0))
        pygame.draw.rect(superficie, relleno, self.rect)
        pygame.draw.rect(superficie, color, self.rect, 1)

        # Esquinas tácticas
        r = self.rect
        for (cx, cy, dx, dy) in ((r.left, r.top, 1, 1), (r.right - 1, r.top, -1, 1),
                                 (r.left, r.bottom - 1, 1, -1), (r.right - 1, r.bottom - 1, -1, -1)):
            pygame.draw.line(superficie, color, (cx, cy), (cx + 6 * dx, cy), 2)
            pygame.draw.line(superficie, color, (cx, cy), (cx, cy + 6 * dy), 2)

        # Pulso suave cuando está activo
        if self.activo and (pygame.time.get_ticks() // 300) % 2 == 0:
            pygame.draw.rect(superficie, color, r.inflate(4, 4), 1)

        txt_render = fuente.render(self.texto, True, color)
        txt_rect = txt_render.get_rect(center=self.rect.center)
        superficie.blit(txt_render, txt_rect)


class VentanaMilitar:
    def __init__(self, x, y, ancho, alto, titulo):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.titulo = titulo
        self.altura_barra = 26

    def dibujar(self, superficie, fuente):
        pygame.draw.rect(superficie, (0, 5, 0), self.rect)
        pygame.draw.rect(superficie, (0, 60, 0), self.rect.inflate(6, 6), 1)   # halo exterior
        pygame.draw.rect(superficie, COLOR_VENTANA_BORD, self.rect, 2)
        barra_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.altura_barra)
        pygame.draw.rect(superficie, COLOR_VENTANA_BORD, barra_rect)

        texto_titulo = fuente.render(self.titulo, True, (0, 0, 0))
        superficie.blit(texto_titulo, (self.rect.x + 10, self.rect.y + 5))

        # LED parpadeante junto al título
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            pygame.draw.rect(superficie, (0, 0, 0),
                             (self.rect.x + 16 + texto_titulo.get_width(), self.rect.y + 9, 7, 7))

        bx = self.rect.x + self.rect.width - 55
        txt_botones = fuente.render("_  []  X", True, (0, 0, 0))
        superficie.blit(txt_botones, (bx, self.rect.y + 5))


class PanelHackerFlujoDinamico:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.matriz_texto = [[" " for _ in range(ANCHO_MATRIZ)] for _ in range(ALTO_MATRIZ)]
        self.marcas = [[0 for _ in range(ANCHO_MATRIZ)] for _ in range(ALTO_MATRIZ)]
        self.tick = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.modo_binario = False
        self.mascara_activa = None
        self.flash = 0   # aviso "IMAGE DECODED"

    def actualizar_mascara(self, nueva_mascara):
        self.mascara_activa = nueva_mascara
        self.limpiar_lienzo()

    def limpiar_lienzo(self):
        self.cursor_x = 0
        self.cursor_y = 0
        self.matriz_texto = [[" " for _ in range(ANCHO_MATRIZ)] for _ in range(ALTO_MATRIZ)]

    def posicion_pantalla_cursor(self):
        return (self.x + 15 + self.cursor_x * 12, self.y + 35 + self.cursor_y * 21)

    def inyectar_caracter(self, c):
        if c in ['\n', '\r', '\t']:
            return

        if self.modo_binario:
            self.matriz_texto[self.cursor_y][self.cursor_x] = random.choice(["0", "1"])
            self.marcas[self.cursor_y][self.cursor_x] = self.tick
            self.avanzar_cursor()
        else:
            while self.cursor_y < ALTO_MATRIZ:
                if self.mascara_activa[self.cursor_y][self.cursor_x] == 1:
                    self.matriz_texto[self.cursor_y][self.cursor_x] = c
                    self.marcas[self.cursor_y][self.cursor_x] = self.tick
                    self.avanzar_cursor()
                    break
                else:
                    self.matriz_texto[self.cursor_y][self.cursor_x] = " "
                    self.avanzar_cursor()

    def avanzar_cursor(self):
        self.cursor_x += 1
        if self.cursor_x >= ANCHO_MATRIZ:
            self.cursor_x = 0
            self.cursor_y += 1
        if self.cursor_y >= ALTO_MATRIZ:
            self.flash = 24
            self.limpiar_lienzo()

    def dibujar(self, superficie, cache, fuente_grande):
        self.tick += 1
        base = (180, 255, 180) if self.modo_binario else COLOR_LINEA_VIVA
        for y_pos in range(ALTO_MATRIZ):
            for x_pos in range(ANCHO_MATRIZ):
                char = self.matriz_texto[y_pos][x_pos]
                if char != " ":
                    edad = self.tick - self.marcas[y_pos][x_pos]
                    if edad < 8:   # letra recién escrita: blanca y se enfría a verde
                        t = 1 - edad / 8
                        color = (int(base[0] + (255 - base[0]) * t), 255,
                                 int(base[2] + (255 - base[2]) * t))
                    else:
                        color = base
                    superficie.blit(cache.get(char, color),
                                    (self.x + 15 + (x_pos * 12), self.y + 35 + (y_pos * 21)))

        # Cursor parpadeante
        if (pygame.time.get_ticks() // 250) % 2 == 0 and self.cursor_y < ALTO_MATRIZ:
            cx, cy = self.posicion_pantalla_cursor()
            pygame.draw.rect(superficie, COLOR_BOTON_ACTIVO, (cx, cy + 14, 9, 3))

        if self.flash > 0:
            self.flash -= 1
            if self.flash % 6 < 4:
                txt = fuente_grande.render("[ IMAGE DECODED ]", True, (255, 255, 255))
                rect = txt.get_rect(center=(self.x + 370, self.y + 250))
                fondo = rect.inflate(30, 14)
                pygame.draw.rect(superficie, (0, 40, 0), fondo)
                pygame.draw.rect(superficie, COLOR_BOTON_ACTIVO, fondo, 2)
                superficie.blit(txt, rect)


class PanelLog:
    """Registro del sistema + barras de estado en la parte inferior."""
    MENSAJES = [
        "Handshake completado con nodo 10.4.22.7",
        "Firewall perimetral: 3 intentos bloqueados",
        "Desencriptando paquete AES-256 ...",
        "Sincronizando reloj atomico con satelite",
        "Puerto 8443 abierto - escuchando",
        "Rotando claves de sesion",
        "Escaneo de vulnerabilidades: 0 criticas",
        "Tunel VPN estable - latencia 42 ms",
        "Subiendo payload a sector 7G",
        "Anomalia detectada en subred 192.168.3.x",
    ]
    ETIQUETAS = ["CPU", "MEM", "NET", "THR"]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.lineas = []
        self.valores = [0.4, 0.55, 0.3, 0.15]
        self.objetivos = [0.4, 0.55, 0.3, 0.15]
        self.agregar("Sistema iniciado. Interfaz operativa.")

    def agregar(self, texto):
        self.lineas.append((time.strftime("%H:%M:%S"), texto))
        self.lineas = self.lineas[-4:]

    def actualizar(self):
        if random.random() < 0.035:
            self.agregar(random.choice(self.MENSAJES))
        for i in range(4):
            if random.random() < 0.08:
                self.objetivos[i] = random.random()
            self.valores[i] += (self.objetivos[i] - self.valores[i]) * 0.08

    def dibujar(self, superficie, fuente):
        for i, (hora, texto) in enumerate(self.lineas):
            brillo = 70 + int(130 * (i + 1) / len(self.lineas))
            color = (0, brillo, 0)
            t = fuente.render(f"[{hora}] > {texto}", True, color)
            superficie.blit(t, (self.x + 12, self.y + 34 + i * 19))

        for i, etiqueta in enumerate(self.ETIQUETAS):
            by = self.y + 34 + i * 19
            bx = self.x + 540
            v = self.valores[i]
            color = COLOR_ALERTA if v > 0.85 else (COLOR_AMBAR if v > 0.65 else COLOR_LINEA_VIVA)
            superficie.blit(fuente.render(etiqueta, True, COLOR_VENTANA_BORD), (bx - 40, by))
            pygame.draw.rect(superficie, COLOR_VENTANA_BORD, (bx, by + 2, 170, 12), 1)
            pygame.draw.rect(superficie, color, (bx + 2, by + 4, int(166 * v), 8))


class MiniJuegoHack:
    """NODE BREACHER: acierta la zona roja. Combos, niveles, vidas y objetivo que se mueve."""
    def __init__(self, x, y, ancho, alto):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.activo = False
        self.mejor = 0
        self.izq = self.rect.left + 30
        self.der = self.rect.right - 30
        self.ty = self.rect.y + 170   # altura central de la pista
        self.reiniciar()

    def reiniciar(self):
        self.score = 0
        self.combo = 0
        self.vidas = 3
        self.nivel = 1
        self.aciertos_nivel = 0
        self.vel = 5
        self.dir = 1
        self.zona = self.zona_para_nivel()
        self.jugador_x = float(self.izq)
        self.deriva_dir = random.choice([-1, 1])
        self.estela = []
        self.flash = 0
        self.flash_color = (0, 255, 0)
        self.mensaje = ""
        self.mensaje_t = 0
        self.game_over = False
        self.nuevo_objetivo()

    def zona_para_nivel(self):
        return max(12, 32 - (self.nivel - 1) * 3)

    def nuevo_objetivo(self):
        self.objetivo_x = float(random.randint(self.izq + self.zona + 10, self.der - self.zona - 10))

    def actualizar(self):
        if not self.activo:
            return
        if self.flash > 0:
            self.flash -= 1
        if self.mensaje_t > 0:
            self.mensaje_t -= 1
        if self.game_over:
            return

        self.jugador_x += self.vel * self.dir
        if self.jugador_x >= self.der:
            self.jugador_x = self.der
            self.dir = -1
        elif self.jugador_x <= self.izq:
            self.jugador_x = self.izq
            self.dir = 1

        self.estela.append(self.jugador_x)
        if len(self.estela) > 9:
            self.estela.pop(0)

        # A partir del nivel 3 el objetivo se desplaza
        if self.nivel >= 3:
            self.objetivo_x += self.deriva_dir * (0.8 + 0.4 * (self.nivel - 3))
            if self.objetivo_x > self.der - self.zona - 5:
                self.deriva_dir = -1
            elif self.objetivo_x < self.izq + self.zona + 5:
                self.deriva_dir = 1

    def presionar_espacio(self):
        """Devuelve: None, 'perfect', 'hit', 'miss', 'over' o 'restart'."""
        if not self.activo:
            return None
        if self.game_over:
            self.reiniciar()
            return "restart"

        dist = abs(self.jugador_x - self.objetivo_x)
        if dist <= self.zona:
            perfecto = dist <= 6
            self.combo += 1
            pts = 10 * self.combo * (2 if perfecto else 1)
            self.score += pts
            self.mejor = max(self.mejor, self.score)
            self.aciertos_nivel += 1
            self.mensaje = ("PERFECT! " if perfecto else "HIT ") + f"+{pts}"
            self.mensaje_t = 26
            self.flash = 8
            self.flash_color = (0, 255, 0)
            if self.aciertos_nivel >= 5:
                self.nivel += 1
                self.aciertos_nivel = 0
                self.vel = min(14, self.vel + 1)
                self.zona = self.zona_para_nivel()
                self.mensaje = f"LEVEL {self.nivel} - FIREWALL MAS FUERTE"
                self.mensaje_t = 40
            self.nuevo_objetivo()
            return "perfect" if perfecto else "hit"

        self.combo = 0
        self.vidas -= 1
        self.flash = 10
        self.flash_color = (255, 40, 40)
        self.mensaje = "MISS"
        self.mensaje_t = 20
        if self.vidas <= 0:
            self.game_over = True
            return "over"
        return "miss"

    def dibujar(self, superficie, fuente, grande):
        r = self.rect
        pygame.draw.rect(superficie, (4, 18, 4), r)

        # Cuadrícula de fondo
        for gx in range(r.left, r.right, 40):
            pygame.draw.line(superficie, (0, 32, 0), (gx, r.top), (gx, r.bottom))
        for gy in range(r.top, r.bottom, 40):
            pygame.draw.line(superficie, (0, 32, 0), (r.left, gy), (r.right, gy))
        pygame.draw.rect(superficie, COLOR_VENTANA_BORD, r, 2)

        # Cabecera
        titulo = grande.render("NODE BREACHER", True, COLOR_LINEA_VIVA)
        superficie.blit(titulo, (r.x + 15, r.y + 8))
        marcador = fuente.render(f"LEVEL {self.nivel}   SCORE {self.score:05d}   BEST {self.mejor:05d}",
                                 True, COLOR_BOTON_ACTIVO)
        superficie.blit(marcador, (r.right - marcador.get_width() - 15, r.y + 14))
        inst = fuente.render("[ESPACIO] cuando la linea verde entre en la zona roja. Centro = PERFECT x2",
                             True, COLOR_VENTANA_BORD)
        superficie.blit(inst, (r.x + 15, r.y + 44))

        # Integridad y combo
        superficie.blit(fuente.render("INTEGRITY", True, COLOR_VENTANA_BORD), (r.x + 15, r.y + 70))
        for i in range(3):
            caja = pygame.Rect(r.x + 105 + i * 28, r.y + 70, 22, 12)
            if i < self.vidas:
                pygame.draw.rect(superficie, COLOR_LINEA_VIVA, caja)
            else:
                pygame.draw.rect(superficie, (90, 20, 20), caja, 1)
        color_combo = COLOR_AMBAR if self.combo >= 3 else COLOR_VENTANA_BORD
        superficie.blit(fuente.render(f"COMBO x{self.combo}", True, color_combo), (r.x + 215, r.y + 70))

        # Pista con marcas
        pygame.draw.line(superficie, COLOR_VENTANA_BORD, (self.izq, self.ty), (self.der, self.ty), 2)
        for tx in range(self.izq, self.der + 1, 20):
            largo = 8 if (tx - self.izq) % 100 == 0 else 4
            pygame.draw.line(superficie, COLOR_TEXTO_OPAC, (tx, self.ty - largo), (tx, self.ty + largo))

        # Zona objetivo (translucida, con borde y centro PERFECT)
        zona_surf = pygame.Surface((int(self.zona * 2), 70), pygame.SRCALPHA)
        zona_surf.fill((255, 60, 60, 70))
        superficie.blit(zona_surf, (int(self.objetivo_x - self.zona), self.ty - 35))
        for ex in (self.objetivo_x - self.zona, self.objetivo_x + self.zona):
            pygame.draw.line(superficie, COLOR_ALERTA, (int(ex), self.ty - 38), (int(ex), self.ty + 38), 2)
        pygame.draw.line(superficie, (255, 255, 130), (int(self.objetivo_x), self.ty - 20),
                         (int(self.objetivo_x), self.ty + 20), 1)

        # Estela + cursor
        for i, ex in enumerate(self.estela):
            v = int(40 + 130 * i / max(1, len(self.estela)))
            pygame.draw.line(superficie, (0, v, 0), (int(ex), self.ty - 42), (int(ex), self.ty + 42), 1)
        pygame.draw.line(superficie, COLOR_LINEA_VIVA, (int(self.jugador_x), self.ty - 48),
                         (int(self.jugador_x), self.ty + 48), 3)

        # Progreso al siguiente nivel
        by = r.bottom - 38
        superficie.blit(fuente.render("NEXT LEVEL", True, COLOR_VENTANA_BORD), (r.x + 15, by))
        pygame.draw.rect(superficie, COLOR_VENTANA_BORD, (r.x + 125, by + 2, 300, 12), 1)
        pygame.draw.rect(superficie, COLOR_LINEA_VIVA,
                         (r.x + 127, by + 4, int(296 * self.aciertos_nivel / 5), 8))

        # Mensaje flotante
        if self.mensaje_t > 0 and not self.game_over:
            col = COLOR_ALERTA if self.mensaje == "MISS" else COLOR_BOTON_ACTIVO
            m = grande.render(self.mensaje, True, col)
            superficie.blit(m, m.get_rect(center=(r.centerx, r.y + 112)))

        # Destello al acertar / fallar
        if self.flash > 0:
            f = pygame.Surface(r.size, pygame.SRCALPHA)
            f.fill((*self.flash_color, self.flash * 9))
            superficie.blit(f, r.topleft)

        # Game over
        if self.game_over:
            f = pygame.Surface(r.size, pygame.SRCALPHA)
            f.fill((40, 0, 0, 190))
            superficie.blit(f, r.topleft)
            t1 = grande.render("TRACE DETECTED", True, COLOR_ALERTA)
            t2 = fuente.render(f"SCORE FINAL {self.score:05d}   -   [ESPACIO] para reintentar", True, COLOR_AMBAR)
            superficie.blit(t1, t1.get_rect(center=(r.centerx, r.centery - 15)))
            superficie.blit(t2, t2.get_rect(center=(r.centerx, r.centery + 22)))


# =========================================================================
# SECUENCIA DE ARRANQUE
# =========================================================================
def secuencia_arranque(pantalla, reloj, fuente, sonido):
    lineas = [
        "QUANTUM CYBERNETIC STATION  v3.7",
        "Verificando integridad del nucleo ............ OK",
        "Cargando modulos criptograficos .............. OK",
        "Montando mascaras de imagen .................. OK",
        "Estableciendo enlace satelital ............... OK",
        "Evadiendo firewall perimetral ................ OK",
        "Inyectando protocolos de acceso ............... OK",
    ]
    mostradas = 0
    frames_linea = 7
    total = len(lineas) * frames_linea + 25
    for frame in range(total):
        reloj.tick(FPS)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return

        nuevas = min(len(lineas), frame // frames_linea + 1)
        if nuevas > mostradas:
            mostradas = nuevas
            if sonido:
                sonido.play()

        pantalla.fill((0, 0, 0))
        for i in range(mostradas):
            color = COLOR_BOTON_ACTIVO if i == 0 else COLOR_LINEA_VIVA
            pantalla.blit(fuente.render(lineas[i], True, color), (50, 50 + i * 26))

        progreso = min(1.0, frame / (total - 22))
        pygame.draw.rect(pantalla, COLOR_VENTANA_BORD, (50, 50 + len(lineas) * 26 + 20, 500, 18), 2)
        pygame.draw.rect(pantalla, COLOR_LINEA_VIVA,
                         (53, 50 + len(lineas) * 26 + 23, int(494 * progreso), 12))

        if progreso >= 1.0 and (frame // 4) % 2 == 0:
            ac = fuente.render(">>> ACCESS GRANTED <<<", True, (255, 255, 255))
            pantalla.blit(ac, (50, 50 + len(lineas) * 26 + 60))

        pygame.display.flip()


# =========================================================================
# PROGRAMA PRINCIPAL
# =========================================================================
def main():
    os.environ['SDL_VIDEO_WINDOW_POS'] = "center"   # debe ir ANTES de crear la ventana
    pygame.init()
    pygame.mixer.init()
    pantalla = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
    pygame.display.set_caption("QUANTUM CYBERNETIC STATION - OPERATIONAL INTERFACE")
    reloj = pygame.time.Clock()
    lienzo = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA))

    fuente_interfaz = pygame.font.SysFont("consolas", 14, bold=True)
    fuente_grande = pygame.font.SysFont("consolas", 26, bold=True)
    fuente_boot = pygame.font.SysFont("consolas", 18, bold=True)
    cache = CacheGlifos(fuente_interfaz)

    sonido_clic = None
    if os.path.exists("click.wav"):
        sonido_clic = pygame.mixer.Sound("click.wav")
        print("[ AUDIO ]: Archivo 'click.wav' cargado con exito.")
    else:
        print("[ ADVERTENCIA ]: 'click.wav' no encontrado. Corriendo en modo silencioso.")

    secuencia_arranque(pantalla, reloj, fuente_boot, sonido_clic)

    mascaras_imagenes = [
        cargar_mascara_desde_png("imagen1.png"),
        cargar_mascara_desde_png("imagen2.png"),
        cargar_mascara_desde_png("imagen3.png"),
        cargar_mascara_desde_png("imagen4.png")
    ]
    indice_imagen_actual = 0

    satelite = PlanetaSatelite(890, 130, 55)
    radar = GraficoFrecuencia(786, 300, 208, 94)
    lluvia_interna = LluviaFondoConsola(20, 20, 740, 480)

    v_consola = VentanaMilitar(20, 20, 740, 480, "Program Console")
    v_satelite = VentanaMilitar(780, 20, 220, 240, "Satellite Connection")
    v_radar = VentanaMilitar(780, 270, 220, 130, "Frequency Scan")
    v_telemetria = VentanaMilitar(780, 415, 220, 215, "System Core Actions")
    v_log = VentanaMilitar(20, 515, 740, 115, "System Log")

    panel_hacker = PanelHackerFlujoDinamico(20, 20)
    panel_hacker.actualizar_mascara(mascaras_imagenes[indice_imagen_actual])
    panel_log = PanelLog(20, 515)
    particulas = Particulas()

    juego_interno = MiniJuegoHack(70, 110, 620, 300)

    botones = [
        BotonTactico(795, 455, 90, 32, "IMG NEXT", "sig_img"),
        BotonTactico(900, 455, 90, 32, "BINARY", "cambiar_binario"),
        BotonTactico(795, 500, 195, 32, "LAUNCH MINI-GAME", "abrir_juego"),
        BotonTactico(795, 545, 195, 32, "CLOSE PANEL / RESET", "cerrar_paneles")
    ]

    codigo_fuente = "Estableciendo protocolos de inyeccion... Acceso concedido.\n"
    if os.path.exists("codigo_falso.txt"):
        with open("codigo_falso.txt", "r", encoding="utf-8", errors="ignore") as f:
            t = f.read()
            if t.strip():
                codigo_fuente = t

    posicion_archivo = 0
    tamano_codigo = len(codigo_fuente)

    overlay_crt = crear_overlay_crt()
    efectos = True       # F2 los activa/desactiva (útil en PCs lentas)
    sacudida = 0

    while True:
        reloj.tick(FPS)
        pos_mouse = pygame.mouse.get_pos()

        # ------------------------------ EVENTOS ------------------------------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    for btn in botones:
                        if btn.hover:
                            if sonido_clic:
                                sonido_clic.play()

                            if btn.id_accion == "sig_img":
                                juego_interno.activo = False
                                panel_hacker.modo_binario = False
                                indice_imagen_actual = (indice_imagen_actual + 1) % 4
                                panel_hacker.actualizar_mascara(mascaras_imagenes[indice_imagen_actual])
                                panel_log.agregar(f"Mascara imagen{indice_imagen_actual + 1}.png cargada")
                            elif btn.id_accion == "cambiar_binario":
                                juego_interno.activo = False
                                panel_hacker.modo_binario = not panel_hacker.modo_binario
                                panel_hacker.limpiar_lienzo()
                                estado = "ON" if panel_hacker.modo_binario else "OFF"
                                panel_log.agregar(f"Modo binario {estado}")
                            elif btn.id_accion == "abrir_juego":
                                juego_interno.activo = True
                                panel_log.agregar("Modulo NODE BREACHER en linea")
                            elif btn.id_accion == "cerrar_paneles":
                                juego_interno.activo = False
                                panel_hacker.modo_binario = False
                                panel_hacker.limpiar_lienzo()
                                panel_log.agregar("Paneles reiniciados")

            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    pygame.image.save(pantalla, "evidencia_python.png")
                    pygame.quit()
                    sys.exit()

                if evento.key == pygame.K_F2:
                    efectos = not efectos
                    panel_log.agregar("Efectos CRT " + ("ON" if efectos else "OFF"))
                    continue

                if juego_interno.activo:
                    if evento.key == pygame.K_SPACE:
                        resultado = juego_interno.presionar_espacio()
                        if sonido_clic:
                            sonido_clic.play()
                        px, py = juego_interno.jugador_x, juego_interno.ty
                        if resultado == "perfect":
                            particulas.emitir(px, py, 40, (255, 255, 160), 5)
                        elif resultado == "hit":
                            particulas.emitir(px, py, 22, COLOR_LINEA_VIVA, 4)
                        elif resultado == "miss":
                            particulas.emitir(px, py, 18, COLOR_ALERTA, 4)
                            sacudida = 8
                        elif resultado == "over":
                            particulas.emitir(px, py, 60, COLOR_ALERTA, 6)
                            sacudida = 18
                            panel_log.agregar(f"TRACE DETECTED - score {juego_interno.score}")
                        elif resultado == "restart":
                            panel_log.agregar("Reintentando intrusion...")
                else:
                    if sonido_clic:
                        sonido_clic.play()
                    for _ in range(4):
                        if posicion_archivo >= tamano_codigo:
                            posicion_archivo = 0
                        cx, cy = panel_hacker.posicion_pantalla_cursor()
                        char = codigo_fuente[posicion_archivo]
                        panel_hacker.inyectar_caracter(char)
                        posicion_archivo += 1
                    particulas.emitir(cx, cy + 8, 3, COLOR_BOTON_ACTIVO, 2)

        # ---------------------------- ACTUALIZACIÓN ----------------------------
        satelite.actualizar()
        radar.actualizar()
        panel_log.actualizar()
        particulas.actualizar()
        if not juego_interno.activo:
            lluvia_interna.actualizar()
        else:
            juego_interno.actualizar()

        v_consola.titulo = "Program Console // BREACH MODE" if juego_interno.activo else "Program Console"
        botones[1].activo = panel_hacker.modo_binario
        botones[2].activo = juego_interno.activo

        # ------------------------------ DIBUJO ------------------------------
        lienzo.fill((0, 0, 0))

        v_consola.dibujar(lienzo, fuente_interfaz)
        v_satelite.dibujar(lienzo, fuente_interfaz)
        v_radar.dibujar(lienzo, fuente_interfaz)
        v_telemetria.dibujar(lienzo, fuente_interfaz)
        v_log.dibujar(lienzo, fuente_interfaz)

        for btn in botones:
            btn.actualizar(pos_mouse)
            btn.dibujar(lienzo, fuente_interfaz)

        satelite.dibujar(lienzo, fuente_interfaz)
        radar.dibujar(lienzo, fuente_interfaz)
        panel_log.dibujar(lienzo, fuente_interfaz)

        if juego_interno.activo:
            juego_interno.dibujar(lienzo, fuente_interfaz, fuente_grande)
        else:
            lluvia_interna.dibujar(lienzo, cache)
            panel_hacker.dibujar(lienzo, cache, fuente_grande)

        particulas.dibujar(lienzo)

        if efectos:
            aplicar_bloom(lienzo)

        # Sacudida de pantalla
        dx = dy = 0
        if sacudida > 0:
            amp = min(6, sacudida // 2 + 1)
            dx = random.randint(-amp, amp)
            dy = random.randint(-amp, amp)
            sacudida -= 1

        pantalla.fill((0, 0, 0))
        pantalla.blit(lienzo, (dx, dy))

        if efectos:
            pantalla.blit(overlay_crt, (0, 0))
            if random.random() < 0.06:   # parpadeo ocasional de monitor viejo
                parpadeo = pygame.Surface((ANCHO_VENTANA, ALTO_VENTANA), pygame.SRCALPHA)
                parpadeo.fill((0, 0, 0, random.randint(8, 22)))
                pantalla.blit(parpadeo, (0, 0))

        pygame.display.flip()


if __name__ == "__main__":
    main()