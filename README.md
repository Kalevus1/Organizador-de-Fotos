# 🗂️ Organizador de Fotos

Clasifica tus fotos rápidamente: ves cada una en grande y decides, con un
clic, a qué carpeta enviarla (copiar o mover) o si la saltas y pasas a la siguiente.

Se acabó el ir y venir en el Explorador: abrir, buscar, copiar, cambiar de carpeta, pegar.
Aquí defines tus carpetas destino una vez y clasificas foto por foto en segundos.

- 🖼️ Visor grande que muestra cada foto de la carpeta, una tras otra.
- 📅 **Fecha de la foto** en una esquina (cuándo se tomó, según EXIF; si no, la de creación).
- 🔍 **Zoom** con la rueda del mouse (dentro del recuadro) o botones **+ / −**, **⊙** para
  centrar, y **arrastrar** para mover la foto. El zoom se reinicia al cambiar de foto.
- 📂 Lista de **carpetas destino** (con su **ruta debajo del nombre**; se recuerdan entre sesiones).
- ↔️ Eliges **Copiar** o **Mover** por foto.
- 🔄 **Rotar** la foto a izquierda o derecha (se guarda el cambio).
- 🗑️ **Borrar** la foto → va a la **Papelera de reciclaje** (recuperable).
- 🔢 **Salta a cualquier foto** escribiendo su número (junto al contador) y pulsando Enter.
- ↩️ **Recuerda dónde te quedaste** en cada carpeta: al reabrirla, retoma en esa foto.
- ⏭️ Puedes **omitir** una foto y seguir.
- ↶ **Deshacer** el último movimiento o copia (por si te equivocas).
- 🍎 Lee formatos de Apple (HEIC/HEIF/AVIF) y los comunes (JPG, PNG, WEBP, GIF, TIF…).
- 🔒 Todo local; no sube nada a internet.

## ▶️ Cómo usarlo

1. Doble clic en **`Organizar fotos.bat`**.
2. Pulsa **📁 Elegir carpeta de origen** (la carpeta desordenada, p. ej. *Descargas*).
3. Pulsa **➕ Agregar** para añadir tus carpetas destino (Capturas, WhatsApp, etc.).
   Quedan guardadas para la próxima vez.
4. Elige **Mover** o **Copiar**.
5. Por cada foto: haz **clic en la carpeta destino** para enviarla, o **⏭ Omitir** para
   dejarla y pasar a la siguiente.

## ⌨️ Atajos de teclado

| Tecla | Acción |
|-------|--------|
| **← / →** | Foto anterior / siguiente |
| **1 – 9** | Enviar la foto a la carpeta destino N |
| **R / L** | Rotar a la derecha / izquierda |
| **Supr** | Borrar (a la Papelera de reciclaje) |
| **Espacio** | Omitir (siguiente) |
| **C** | Cambiar entre Copiar / Mover |
| **Ctrl + Z** | Deshacer la última acción |

## 🛠️ Instalación (desde cero o GitHub)

```
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

O simplemente doble clic en **`instalar.bat`**. Luego abre con **`Organizar fotos.bat`**.

> Este proyecto reutiliza el mismo entorno que Face Finder (Día 2) si existe
> (`..\.venv_face`); si no, crea su propio `.venv` con `instalar.bat`.

## ⚙️ Tecnología

- **Python 3.12** + **PySide6** (Qt 6) para la interfaz.
- **Pillow** + **pillow-heif** para leer imágenes (incluidos formatos de Apple).
- **NumPy** para convertir las imágenes a la pantalla.
- Las carpetas destino y el modo Copiar/Mover se guardan con `QSettings`.
