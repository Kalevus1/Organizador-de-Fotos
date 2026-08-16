# -*- coding: utf-8 -*-
"""
Día 3 - Organizador de Fotos  ·  PySide6
----------------------------------------
Ves cada foto en grande y decides, con un clic, a qué carpeta enviarla
(copiar o mover), o la saltas y pasas a la siguiente.

- Agregas tus carpetas destino y quedan en un listado (se recuerdan).
- Eliges por foto: enviarla a una carpeta (copiar/mover) u omitir.
- Botón Deshacer para revertir el último movimiento o copia.
- Soporta formatos de Apple (HEIC/HEIF/AVIF) además de los comunes.
- Atajos: ← → navegar · 1-9 enviar a carpeta · Espacio omitir · C copiar/mover · Ctrl+Z deshacer

Todo local. Ejecuta con "Organizar fotos.bat".
"""

import os
import sys
import json
import shutil

import numpy as np
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()          # habilita HEIC / HEIF / AVIF (fotos de Apple)
except Exception:
    pass

try:
    from send2trash import send2trash   # borrar = enviar a la Papelera (recuperable)
    HAY_PAPELERA = True
except Exception:
    HAY_PAPELERA = False

from PySide6.QtCore import Qt, QSize, QSettings, QRectF
from PySide6.QtGui import (QImage, QPixmap, QKeySequence, QShortcut, QColor,
                           QPainter, QIntValidator)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QHBoxLayout, QVBoxLayout, QScrollArea, QFrame,
    QToolButton, QSizePolicy, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QLineEdit,
)

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tif", ".tiff",
        ".heic", ".heif", ".avif"}

# ---- Paleta clara estilo Instagram (blanco / plomo + degradado) ----
BG, PANEL, PANEL2, LINE = "#fafafa", "#ffffff", "#f5f5f5", "#dbdbdb"
TXT, MUTED = "#262626", "#8e8e8e"
PINK, PURPLE, ERR = "#e1306c", "#c13584", "#ed4956"
# Degradado oficial de Instagram (amarillo -> naranja -> rosa -> morado -> azul)
GRAD = ("qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #feda75, stop:0.25 #fa7e1e, "
        "stop:0.5 #d62976, stop:0.75 #962fbf, stop:1 #4f5bd5)")
GRAD_HOVER = ("qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #fa7e1e, stop:0.5 #d62976, "
              "stop:1 #962fbf)")
FT = "Segoe UI"


def cargar_pixmap(ruta, max_lado=1920):
    """Abre una imagen (con orientación EXIF y formatos Apple) como QPixmap."""
    try:
        with Image.open(ruta) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((max_lado, max_lado))
            arr = np.ascontiguousarray(np.array(im))
        h, w, ch = arr.shape
        qimg = QImage(arr.data, w, h, ch * w, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg.copy())
    except Exception:
        return None


MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt(y, m, d, hora=""):
    try:
        txt = f"{int(d)} {MESES[int(m) - 1]} {int(y)}"
        return txt + (f" · {hora[:5]}" if hora else "")
    except Exception:
        return ""


def fecha_foto(ruta):
    """Fecha en que se tomó la foto (EXIF); si no hay, fecha de creación del archivo."""
    try:
        with Image.open(ruta) as im:
            exif = im.getexif()
            dt = None
            try:
                dt = exif.get_ifd(0x8769).get(36867)   # DateTimeOriginal
            except Exception:
                dt = None
            dt = dt or exif.get(306)                    # DateTime
        if dt:
            fecha, _, hora = str(dt).partition(" ")
            y, m, d = fecha.split(":")
            f = _fmt(y, m, d, hora)
            if f:
                return "📅 " + f
    except Exception:
        pass
    try:
        import datetime
        d = datetime.datetime.fromtimestamp(os.path.getctime(ruta))
        return "📅 " + _fmt(d.year, d.month, d.day, d.strftime("%H:%M"))
    except Exception:
        return ""


def rotar_archivo(ruta, grados):
    """Rota la imagen (grados: 90 izquierda, -90 derecha) y la guarda en el mismo archivo."""
    with Image.open(ruta) as raw:
        im = ImageOps.exif_transpose(raw)      # deja los píxeles bien orientados
    girada = im.rotate(grados, expand=True)
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".jpg", ".jpeg", ".jpe"):
        girada.convert("RGB").save(ruta, quality=95)
    elif ext in (".heic", ".heif", ".avif", ".bmp"):
        girada.convert("RGB").save(ruta)
    else:
        girada.save(ruta)


def ruta_unica(destino, nombre):
    """Evita sobrescribir: si ya existe, añade _1, _2, ..."""
    final = os.path.join(destino, nombre)
    base, ext = os.path.splitext(nombre)
    c = 1
    while os.path.exists(final):
        final = os.path.join(destino, f"{base}_{c}{ext}")
        c += 1
    return final


class FilaDestino(QFrame):
    """Una carpeta destino en el listado. Clic = enviar la foto actual."""

    def __init__(self, numero, nombre, ruta, on_send, on_remove):
        super().__init__()
        self.setObjectName("dest")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on_send = on_send
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 8, 8, 8)
        h.setSpacing(8)
        badge = QLabel(str(numero))
        badge.setObjectName("badge")
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        col = QVBoxLayout()
        col.setSpacing(1)
        nom = QLabel(nombre)
        nom.setObjectName("destname")
        nom.setToolTip(ruta)
        cam = QLabel()
        cam.setObjectName("destpath")
        cam.setToolTip(ruta)
        cam.setText(cam.fontMetrics().elidedText(ruta, Qt.TextElideMode.ElideMiddle, 232))
        col.addWidget(nom)
        col.addWidget(cam)

        x = QToolButton()
        x.setText("✕")
        x.setObjectName("del")
        x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        x.clicked.connect(on_remove)

        h.addWidget(badge)
        h.addLayout(col, 1)
        h.addWidget(x)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._on_send()


class Visor(QGraphicsView):
    """Visor de imagen con zoom (rueda/botones), desplazamiento y controles tipo mapa."""

    def __init__(self):
        super().__init__()
        self.setObjectName("visor")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.escena = QGraphicsScene(self)
        self.setScene(self.escena)
        self.item = QGraphicsPixmapItem()
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.escena.addItem(self.item)
        self.setBackgroundBrush(QColor("#efefef"))
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._fit = True
        self._min = 0.01
        self._max = 10.0

        # superposiciones
        self.fecha = QLabel("", self)
        self.fecha.setObjectName("fecha")
        self.fecha.hide()
        self.msg = QLabel("", self)
        self.msg.setObjectName("msg")
        self.msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg.setWordWrap(True)
        self.b_mas = QPushButton("+", self)
        self.b_menos = QPushButton("−", self)
        self.b_centro = QPushButton("⊙", self)
        for b in (self.b_mas, self.b_menos, self.b_centro):
            b.setObjectName("mapctl")
            b.setFixedSize(34, 34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.b_mas.clicked.connect(lambda: self._zoom(1.25))
        self.b_menos.clicked.connect(lambda: self._zoom(1 / 1.25))
        self.b_centro.clicked.connect(self.centrar)
        self._mostrar_controles(False)

    def _mostrar_controles(self, si):
        for b in (self.b_mas, self.b_menos, self.b_centro):
            b.setVisible(si)

    def mostrar_imagen(self, pm):
        self.msg.hide()
        self.item.setPixmap(pm)
        self.setSceneRect(QRectF(pm.rect()))
        self._mostrar_controles(True)
        self.centrar()

    def mostrar_mensaje(self, texto):
        self.item.setPixmap(QPixmap())
        self.fecha.hide()
        self._mostrar_controles(False)
        self.msg.setText(texto)
        self.msg.show()
        self._colocar()

    def set_fecha(self, texto):
        if texto:
            self.fecha.setText(texto)
            self.fecha.adjustSize()
            self.fecha.show()
        else:
            self.fecha.hide()
        self._colocar()

    def centrar(self):
        if self.item.pixmap().isNull():
            return
        self.resetTransform()
        self.fitInView(self.item, Qt.AspectRatioMode.KeepAspectRatio)
        self._min = self.transform().m11()
        self._fit = True

    def _escala(self):
        return self.transform().m11()

    def _zoom(self, factor, bajo_mouse=False):
        if self.item.pixmap().isNull():
            return
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse if bajo_mouse
            else QGraphicsView.ViewportAnchor.AnchorViewCenter)
        actual = self._escala()
        nueva = actual * factor
        if nueva < self._min * 1.001:
            self.centrar()
            return
        if nueva > self._max:
            factor = self._max / actual
        self.scale(factor, factor)
        self._fit = False

    def wheelEvent(self, e):
        if self.item.pixmap().isNull():
            return
        self._zoom(1.18 if e.angleDelta().y() > 0 else 1 / 1.18, bajo_mouse=True)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._fit:
            self.centrar()
        self._colocar()

    def _colocar(self):
        m = 10
        vw = self.viewport().width()
        vh = self.viewport().height()
        self.fecha.move(m, m)
        self.msg.setGeometry(0, 0, vw, vh)
        bs, gap = 34, 6
        x = vw - bs - m
        y0 = vh - (bs * 3 + gap * 2) - m
        self.b_mas.move(x, y0)
        self.b_menos.move(x, y0 + bs + gap)
        self.b_centro.move(x, y0 + 2 * (bs + gap))


class Organizador(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🗂️  Organizador de Fotos")
        self.resize(1280, 820)
        self.setMinimumSize(1040, 660)

        self.ajustes = QSettings("KaleviApps", "OrganizadorFotos")
        self.origen = ""
        self.imagenes = []
        self.idx = -1
        self.acciones = []                     # pila para Deshacer
        self.destinos = self._cargar_destinos()
        self.posiciones = self._cargar_pos()   # última foto vista por carpeta

        self._ui()
        self._reconstruir_destinos()
        self._mostrar()

    # ---------------- persistencia ----------------
    def _cargar_destinos(self):
        guard = self.ajustes.value("destinos", [])
        if isinstance(guard, str):
            guard = [guard]
        out = []
        for item in (guard or []):
            # compatibilidad: antes se guardaba (nombre, ruta); ahora solo la ruta
            ruta = item[-1] if isinstance(item, (list, tuple)) and item else item
            if isinstance(ruta, str) and os.path.isdir(ruta):
                out.append((os.path.basename(ruta) or ruta, ruta))
        return out

    def _guardar_destinos(self):
        self.ajustes.setValue("destinos", [ruta for _, ruta in self.destinos])

    def _cargar_pos(self):
        try:
            return json.loads(self.ajustes.value("posiciones", "{}")) or {}
        except Exception:
            return {}

    def _guardar_pos(self):
        if self.origen and 0 <= self.idx < len(self.imagenes):
            self.posiciones[self.origen] = self.idx
            try:
                self.ajustes.setValue("posiciones", json.dumps(self.posiciones))
            except Exception:
                pass

    # ---------------- interfaz ----------------
    def _ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(16, 14, 16, 14)
        raiz.setSpacing(10)

        # encabezado
        cab = QHBoxLayout()
        marca = QLabel("🗂️  ORGANIZADOR DE FOTOS")
        marca.setObjectName("brand")
        self.lbl_origen = QLabel("Sin carpeta de origen")
        self.lbl_origen.setObjectName("muted")
        btn_origen = QPushButton("📁  Elegir carpeta de origen")
        btn_origen.setObjectName("primary")
        btn_origen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_origen.clicked.connect(self._elegir_origen)
        cab.addWidget(marca)
        cab.addSpacing(12)
        cab.addWidget(self.lbl_origen, 1)
        cab.addWidget(btn_origen)
        raiz.addLayout(cab)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(14)
        raiz.addLayout(cuerpo, 1)

        # ----- visor (izquierda) -----
        izq = QVBoxLayout()
        izq.setSpacing(8)
        cuerpo.addLayout(izq, 1)

        self.visor = Visor()
        self.visor.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # que no robe el foco del teclado
        self.visor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        izq.addWidget(self.visor, 1)

        info = QHBoxLayout()
        self.btn_prev = QPushButton("◀  Anterior")
        self.btn_prev.setObjectName("ghost")
        self.btn_prev.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_prev.clicked.connect(self._anterior)
        self.lbl_nombre = QLabel("")
        self.lbl_nombre.setObjectName("filename")
        self.lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_idx = QLineEdit()
        self.num_idx.setObjectName("idx")
        self._validador = QIntValidator(1, 1, self)
        self.num_idx.setValidator(self._validador)      # solo números
        self.num_idx.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.num_idx.setFixedWidth(64)
        self.num_idx.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.num_idx.setToolTip("Escribe un número y pulsa Enter para saltar a esa foto")
        self.num_idx.returnPressed.connect(self._ir_a)
        self.num_idx.editingFinished.connect(self._sync_num)  # si no cambias, se queda igual
        self.lbl_total = QLabel("/ 0")
        self.lbl_total.setObjectName("muted")
        self.btn_next = QPushButton("Siguiente  ▶")
        self.btn_next.setObjectName("ghost")
        self.btn_next.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_next.clicked.connect(self._siguiente)
        info.addWidget(self.btn_prev)
        info.addStretch()
        info.addWidget(self.lbl_nombre)
        info.addSpacing(10)
        info.addWidget(self.num_idx)
        info.addWidget(self.lbl_total)
        info.addStretch()
        info.addWidget(self.btn_next)
        izq.addLayout(info)

        # rotar / borrar la foto actual
        acc_img = QHBoxLayout()
        acc_img.addStretch()
        self.btn_rot_izq = QPushButton("⟲  Rotar")
        self.btn_rot_der = QPushButton("Rotar  ⟳")
        for b, g in ((self.btn_rot_izq, 90), (self.btn_rot_der, -90)):
            b.setObjectName("ghost")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False, gg=g: self._rotar(gg))
            acc_img.addWidget(b)
        acc_img.addSpacing(24)
        self.btn_borrar = QPushButton("🗑  Borrar")
        self.btn_borrar.setObjectName("danger")
        self.btn_borrar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_borrar.clicked.connect(self._borrar)
        acc_img.addWidget(self.btn_borrar)
        acc_img.addStretch()
        izq.addLayout(acc_img)

        # ----- panel derecho -----
        der = QFrame()
        der.setObjectName("panel")
        der.setFixedWidth(340)
        pd = QVBoxLayout(der)
        pd.setContentsMargins(14, 14, 14, 14)
        pd.setSpacing(10)
        cuerpo.addWidget(der)

        fila_t = QHBoxLayout()
        t = QLabel("CARPETAS DESTINO")
        t.setObjectName("h1")
        add = QPushButton("➕ Agregar")
        add.setObjectName("ghost")
        add.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        add.clicked.connect(self._agregar_destino)
        fila_t.addWidget(t)
        fila_t.addStretch()
        fila_t.addWidget(add)
        pd.addLayout(fila_t)

        pista = QLabel("Haz clic en una carpeta para enviar la foto actual (o usa 1-9).")
        pista.setObjectName("muted")
        pista.setWordWrap(True)
        pd.addWidget(pista)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cont_dest = QWidget()
        self.cont_dest.setObjectName("flowHost")
        self.lay_dest = QVBoxLayout(self.cont_dest)
        self.lay_dest.setContentsMargins(4, 4, 4, 4)
        self.lay_dest.setSpacing(6)
        self.lay_dest.addStretch()
        self.scroll.setWidget(self.cont_dest)
        pd.addWidget(self.scroll, 1)

        # modo copiar / mover
        modo = QHBoxLayout()
        etq = QLabel("Acción:")
        etq.setObjectName("muted")
        self.rb_mover = QRadioButton("Mover")
        self.rb_copiar = QRadioButton("Copiar")
        grupo = QButtonGroup(self)
        grupo.addButton(self.rb_mover)
        grupo.addButton(self.rb_copiar)
        for rb in (self.rb_mover, self.rb_copiar):
            rb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if self.ajustes.value("modo", "mover") == "copiar":
            self.rb_copiar.setChecked(True)
        else:
            self.rb_mover.setChecked(True)
        self.rb_mover.toggled.connect(self._guardar_modo)
        modo.addWidget(etq)
        modo.addWidget(self.rb_mover)
        modo.addWidget(self.rb_copiar)
        modo.addStretch()
        pd.addLayout(modo)

        # omitir / deshacer
        acc = QHBoxLayout()
        self.btn_omitir = QPushButton("⏭  Omitir")
        self.btn_omitir.setObjectName("ghost")
        self.btn_omitir.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_omitir.clicked.connect(self._siguiente)
        self.btn_deshacer = QPushButton("↶  Deshacer")
        self.btn_deshacer.setObjectName("ghost")
        self.btn_deshacer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_deshacer.setEnabled(False)
        self.btn_deshacer.clicked.connect(self._deshacer)
        acc.addWidget(self.btn_omitir)
        acc.addWidget(self.btn_deshacer)
        pd.addLayout(acc)

        self.estado = QLabel("Agrega tus carpetas destino con ➕ Agregar.")
        self.estado.setObjectName("muted")
        self.estado.setWordWrap(True)
        pd.addWidget(self.estado)

    def keyPressEvent(self, e):
        # Si el campo numérico tiene el foco, deja que reciba los dígitos y flechas.
        k = e.key()
        t = e.text().lower()
        if k == Qt.Key.Key_Right:
            self._siguiente()
        elif k == Qt.Key.Key_Left:
            self._anterior()
        elif k == Qt.Key.Key_Space:
            self._siguiente()
        elif k == Qt.Key.Key_Delete:
            self._borrar()
        elif k == Qt.Key.Key_Z and (e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._deshacer()
        elif t == "r":
            self._rotar(-90)
        elif t == "l":
            self._rotar(90)
        elif t == "c":
            self._alternar_modo()
        elif t in "123456789":
            self._enviar(int(t) - 1)
        else:
            super().keyPressEvent(e)
            return
        e.accept()

    # ---------------- destinos ----------------
    def _reconstruir_destinos(self):
        # limpia (deja el stretch final)
        while self.lay_dest.count() > 1:
            it = self.lay_dest.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not self.destinos:
            vacio = QLabel("Aún no agregaste carpetas.")
            vacio.setObjectName("muted")
            self.lay_dest.insertWidget(0, vacio)
            return
        for i, (nombre, ruta) in enumerate(self.destinos):
            fila = FilaDestino(i + 1, nombre, ruta,
                               on_send=lambda k=i: self._enviar(k),
                               on_remove=lambda k=i: self._quitar_destino(k))
            self.lay_dest.insertWidget(i, fila)

    def _agregar_destino(self):
        ruta = QFileDialog.getExistingDirectory(self, "Elige una carpeta destino")
        if not ruta:
            return
        if any(r == ruta for _, r in self.destinos):
            self.estado.setText("Esa carpeta ya está en la lista.")
            return
        self.destinos.append((os.path.basename(ruta) or ruta, ruta))
        self._guardar_destinos()
        self._reconstruir_destinos()
        self.estado.setText(f"Carpeta agregada: {os.path.basename(ruta)}")

    def _quitar_destino(self, k):
        if 0 <= k < len(self.destinos):
            nombre = self.destinos[k][0]
            del self.destinos[k]
            self._guardar_destinos()
            self._reconstruir_destinos()
            self.estado.setText(f"Carpeta quitada: {nombre}")

    # ---------------- origen e imágenes ----------------
    def _elegir_origen(self):
        ruta = QFileDialog.getExistingDirectory(self, "Elige la carpeta con las fotos a organizar")
        if not ruta:
            return
        self._guardar_pos()          # guarda la posición de la carpeta anterior
        self.origen = ruta
        self.lbl_origen.setText(ruta)
        self.imagenes = sorted(
            os.path.join(ruta, n) for n in os.listdir(ruta)
            if os.path.splitext(n)[1].lower() in EXTS
            and os.path.isfile(os.path.join(ruta, n)))
        self.acciones.clear()
        self.btn_deshacer.setEnabled(False)
        if not self.imagenes:
            self.idx = -1
            self._mostrar()
            self.estado.setText("Esa carpeta no tiene imágenes.")
            return
        guardado = self.posiciones.get(ruta, 0)
        if isinstance(guardado, int) and 0 < guardado < len(self.imagenes):
            self.idx = guardado
            self.estado.setText(
                f"↩️ Retomando en la foto {guardado + 1} de {len(self.imagenes)} "
                f"(donde lo dejaste).")
        else:
            self.idx = 0
            self.estado.setText(f"{len(self.imagenes)} fotos para organizar.")
        self._mostrar()

    def _mostrar(self):
        hay = 0 <= self.idx < len(self.imagenes)
        self.btn_prev.setEnabled(self.idx > 0)
        self.btn_next.setEnabled(self.idx < len(self.imagenes) - 1)
        for b in (self.btn_rot_izq, self.btn_rot_der, self.btn_borrar):
            b.setEnabled(hay)
        if not hay:
            self.visor.mostrar_mensaje(
                "🎉 No hay más fotos.\n\nElige otra carpeta de origen."
                if self.origen else "Elige una carpeta de origen para empezar.")
            self.visor.set_fecha("")
            self.lbl_nombre.setText("")
            self._actualizar_contador()
            return
        ruta = self.imagenes[self.idx]
        pm = cargar_pixmap(ruta, 3000)
        if pm is None:
            self.visor.mostrar_mensaje("No se pudo abrir esta imagen.")
            self.visor.set_fecha("")
        else:
            self.visor.mostrar_imagen(pm)
            self.visor.set_fecha(fecha_foto(ruta))
        self.lbl_nombre.setText(os.path.basename(ruta))
        self._actualizar_contador()
        self._guardar_pos()

    def _actualizar_contador(self):
        n = len(self.imagenes)
        self.num_idx.setEnabled(n > 0)
        self._validador.setTop(max(1, n))
        self._sync_num()
        self.lbl_total.setText(f"/ {n}")

    def _sync_num(self):
        # muestra el número actual (revierte si escribiste algo pero no saltaste)
        self.num_idx.setText(str(self.idx + 1) if 0 <= self.idx < len(self.imagenes) else "")

    def _ir_a(self):
        txt = self.num_idx.text().strip()
        if txt.isdigit():
            idx = int(txt) - 1
            if 0 <= idx < len(self.imagenes) and idx != self.idx:
                self.idx = idx
                self._mostrar()
        self._sync_num()
        self.num_idx.clearFocus()   # devuelve el teclado a la navegación

    # ---------------- navegación y acciones ----------------
    def _siguiente(self):
        if self.idx < len(self.imagenes) - 1:
            self.idx += 1
            self._mostrar()

    def _anterior(self):
        if self.idx > 0:
            self.idx -= 1
            self._mostrar()

    def _alternar_modo(self):
        self.rb_copiar.setChecked(not self.rb_copiar.isChecked())

    def _rotar(self, grados):
        if not (0 <= self.idx < len(self.imagenes)):
            return
        ruta = self.imagenes[self.idx]
        try:
            rotar_archivo(ruta, grados)
        except Exception as ex:
            self.estado.setText(f"No se pudo rotar: {ex}")
            return
        pm = cargar_pixmap(ruta, 3000)
        if pm is not None:
            self.visor.mostrar_imagen(pm)
        self.estado.setText("Foto rotada.")

    def _borrar(self):
        if not (0 <= self.idx < len(self.imagenes)):
            return
        if not HAY_PAPELERA:
            self.estado.setText("Borrar no disponible: falta la librería 'send2trash'.")
            return
        ruta = self.imagenes[self.idx]
        try:
            send2trash(os.path.abspath(ruta))
        except Exception as ex:
            self.estado.setText(f"No se pudo borrar: {ex}")
            return
        del self.imagenes[self.idx]
        if self.idx >= len(self.imagenes):
            self.idx = len(self.imagenes) - 1
        self.estado.setText("🗑️ Enviada a la Papelera de reciclaje (recuperable desde ahí).")
        self._mostrar()

    def closeEvent(self, e):
        self._guardar_pos()
        e.accept()

    def _guardar_modo(self):
        self.ajustes.setValue("modo", "mover" if self.rb_mover.isChecked() else "copiar")

    def _enviar(self, k):
        if not (0 <= self.idx < len(self.imagenes)):
            return
        if not (0 <= k < len(self.destinos)):
            return
        origen = self.imagenes[self.idx]
        nombre, carpeta = self.destinos[k]
        if not os.path.isdir(carpeta):
            self.estado.setText(f"La carpeta '{nombre}' ya no existe.")
            return
        final = ruta_unica(carpeta, os.path.basename(origen))
        mover = self.rb_mover.isChecked()
        try:
            if mover:
                shutil.move(origen, final)
            else:
                shutil.copy2(origen, final)
        except Exception as ex:
            self.estado.setText(f"Error: {ex}")
            return

        self.acciones.append({"tipo": "mover" if mover else "copiar",
                              "origen": origen, "destino": final, "idx": self.idx})
        self.btn_deshacer.setEnabled(True)
        verbo = "Movida" if mover else "Copiada"
        self.estado.setText(f"{verbo} a «{nombre}».")

        if mover:
            del self.imagenes[self.idx]
            if self.idx >= len(self.imagenes):
                self.idx = len(self.imagenes) - 1
            self._mostrar()
        else:
            self._siguiente()

    def _deshacer(self):
        if not self.acciones:
            return
        a = self.acciones.pop()
        try:
            if a["tipo"] == "copiar":
                if os.path.exists(a["destino"]):
                    os.remove(a["destino"])
                self.idx = min(a["idx"], max(0, len(self.imagenes) - 1))
            else:  # mover: regresar el archivo a su lugar
                shutil.move(a["destino"], a["origen"])
                self.imagenes.insert(min(a["idx"], len(self.imagenes)), a["origen"])
                self.idx = a["idx"]
        except Exception as ex:
            self.estado.setText(f"No se pudo deshacer: {ex}")
            return
        self.btn_deshacer.setEnabled(bool(self.acciones))
        self.estado.setText("Última acción deshecha.")
        self._mostrar()


ESTILO = f"""
* {{ font-family: '{FT}'; }}
QWidget {{ background: {BG}; color: {TXT}; font-size: 12px; }}
QLabel {{ background: transparent; }}
QLabel#brand {{ color: {PURPLE}; font-size: 18px; font-weight: 800; letter-spacing: 1px; }}
QLabel#h1 {{ color: {TXT}; font-size: 13px; font-weight: 700; letter-spacing: 1px; }}
QLabel#muted {{ color: {MUTED}; font-size: 11px; }}
QLabel#filename {{ color: {TXT}; font-size: 12px; font-weight: 600; }}
QLineEdit#idx {{ background: white; border: 1px solid {LINE}; border-radius: 8px; padding: 4px 6px; color: {TXT}; font-weight: 700; }}
QLineEdit#idx:focus {{ border: 1px solid {PINK}; }}
#visor {{ border: 1px solid {LINE}; border-radius: 16px; }}
QLabel#msg {{ color: {MUTED}; font-size: 14px; background: transparent; }}
QLabel#fecha {{ background: rgba(0,0,0,60%); color: white; border-radius: 8px; padding: 4px 9px; font-size: 11px; font-weight: 600; }}
QPushButton#mapctl {{ background: rgba(255,255,255,92%); color: {TXT}; border: 1px solid {LINE}; border-radius: 17px; font-size: 17px; font-weight: 700; }}
QPushButton#mapctl:hover {{ border: 1px solid {PINK}; color: {PINK}; }}
#panel {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 18px; }}
QPushButton#primary {{ background: {GRAD}; color: white; border: none; border-radius: 10px;
    padding: 10px 18px; font-weight: 700; }}
QPushButton#primary:hover {{ background: {GRAD_HOVER}; }}
QPushButton#ghost {{ background: {PANEL}; color: {TXT}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 8px 14px; font-weight: 600; }}
QPushButton#ghost:hover {{ border: 1px solid {PINK}; color: {PINK}; }}
QPushButton#ghost:disabled {{ color: #c7c7c7; border-color: #ececec; }}
QPushButton#danger {{ background: {ERR}; color: white; border: none; border-radius: 10px;
    padding: 8px 14px; font-weight: 700; }}
QPushButton#danger:hover {{ background: #f76e79; }}
QPushButton#danger:disabled {{ background: #f2c4c8; color: #ffffff; }}
QRadioButton {{ color: {TXT}; spacing: 6px; }}
QRadioButton::indicator {{ width: 15px; height: 15px; border: 2px solid #c7c7c7; border-radius: 9px; background: white; }}
QRadioButton::indicator:checked {{ border: 2px solid {PINK}; background: {PINK}; }}
#scroll, QScrollArea {{ background: {PANEL2}; border: 1px solid {LINE}; border-radius: 12px; }}
#flowHost {{ background: transparent; }}
#dest {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 12px; }}
#dest:hover {{ border: 1px solid {PINK}; }}
QLabel#destname {{ color: {TXT}; font-size: 12px; font-weight: 600; }}
QLabel#destpath {{ color: {MUTED}; font-size: 9px; }}
QLabel#badge {{ background: {GRAD}; color: white; border-radius: 11px; font-weight: 700; font-size: 11px; }}
QToolButton#del {{ background: transparent; color: {MUTED}; border: none; font-size: 13px; }}
QToolButton#del:hover {{ color: {ERR}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #c7c7c7; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {PINK}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QMessageBox, QFileDialog {{ background: {PANEL}; color: {TXT}; }}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)
    v = Organizador()
    v.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
