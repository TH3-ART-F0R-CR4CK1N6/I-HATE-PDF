# iHatePdf 📄🔥

Herramientas PDF gratis y de código abierto: unir, dividir, comprimir, rotar,
convertir PDF↔Word, PDF↔imágenes, extraer/eliminar páginas, marca de agua,
numeración, proteger/desbloquear con contraseña y reparar PDFs dañados.

## Herramientas incluidas

- Unir PDF
- Dividir PDF (por página o por rango)
- Comprimir PDF (usa Ghostscript)
- Rotar PDF
- PDF → JPG
- JPG/PNG → PDF
- PDF → Word (.docx)
- Word → PDF (usa LibreOffice)
- Extraer páginas
- Eliminar páginas
- Marca de agua de texto
- Numeración de páginas
- Proteger con contraseña
- Quitar contraseña
- Reparar PDF dañado

> No incluidas en esta versión (mucho más complejas de implementar gratis):
> PDF → Excel/PowerPoint, OCR de texto, firma electrónica legal, comparar PDFs,
> editor visual de texto dentro del PDF. Se pueden agregar más adelante.

## Requisitos técnicos

La app necesita, además de Python, estos programas del sistema:
`poppler-utils`, `ghostscript`, `qpdf` y `libreoffice`. Por eso se despliega
con **Docker** (el `Dockerfile` ya los instala). No funcionará simplemente con
`pip install` en un hosting que no permita Docker ni paquetes de sistema
(por eso PythonAnywhere gratis NO es una buena opción, ver más abajo).

## Opción 1: Desplegar gratis en Render (recomendada)

1. Crea una cuenta en https://render.com (gratis, con GitHub).
2. Sube esta carpeta a un repositorio nuevo en GitHub (público o privado).
3. En Render: **New +** → **Web Service** → conecta tu repo.
4. Render detectará el `render.yaml` automáticamente. Si no, configura a mano:
   - **Environment**: Docker
   - **Plan**: Free
   - **Health Check Path**: `/health`
5. Dale a **Create Web Service** y espera el build (puede tardar varios
   minutos porque instala LibreOffice).
6. Cuando termine, Render te da una URL tipo
   `https://ihatepdf.onrender.com` — esa es tu app ya funcionando.

**Nota sobre el plan gratuito de Render:** el servicio "duerme" tras ~15
minutos sin uso y la primera petición después de dormir tarda unos 30-60
segundos en responder (arranque en frío). Esto es una limitación del plan
gratuito, no de la app.

## Opción 2: Railway (alternativa igual de sencilla)

Railway también soporta Docker y tiene un plan gratuito con créditos
mensuales limitados:

1. Crea cuenta en https://railway.app
2. **New Project** → **Deploy from GitHub repo**
3. Railway detecta el Dockerfile automáticamente y despliega.

## Opción 3: Fly.io

Fly.io permite desplegar contenedores Docker con una capa gratuita reducida:

```bash
curl -L https://fly.io/install.sh | sh
fly launch      # detecta el Dockerfile automáticamente
fly deploy
```

## ¿Por qué NO recomiendo PythonAnywhere para esta app?

El plan gratuito de PythonAnywhere:
- No permite instalar paquetes de sistema (no hay Ghostscript, Poppler ni
  LibreOffice disponibles), así que compresión, PDF→JPG y Word→PDF no
  funcionarían.
- Restringe el acceso saliente a internet a una lista blanca de dominios.
- No soporta Docker.

Es una excelente opción para apps Flask simples sin dependencias de sistema,
pero no para esta aplicación en particular. Si de todas formas quieres
probarla ahí, tendrías que quitar las funciones que dependen de Ghostscript,
Poppler y LibreOffice (compresión avanzada, PDF↔imagen, Word↔PDF) y dejar
solo las que usan librerías 100% Python (unir, dividir, rotar, extraer,
eliminar páginas, marca de agua, numeración, proteger/desbloquear, reparar
con pikepdf).

## Ejecutar en local (para probar antes de desplegar)

Necesitas Docker instalado:

```bash
docker build -t ihatepdf .
docker run -p 10000:10000 ihatepdf
```

Abre http://localhost:10000

Sin Docker (te faltarán algunas funciones si no tienes esos programas
instalados en tu sistema):

```bash
pip install -r requirements.txt
python app.py
```

## Estructura del proyecto

```
ihatepdf/
├── app.py                 # Backend Flask con todas las rutas/API
├── Dockerfile              # Imagen con Python + Ghostscript + Poppler + LibreOffice
├── render.yaml              # Configuración de despliegue en Render
├── requirements.txt         # Dependencias Python
├── templates/index.html     # Interfaz
├── static/style.css         # Estilos
└── static/script.js         # Lógica del frontend
```

## Seguridad y privacidad

- Cada archivo subido se procesa en una carpeta temporal única y se borra
  automáticamente justo después de enviarse la descarga al usuario.
- Límite de subida: 100 MB por archivo/solicitud (configurable en `app.py`,
  variable `MAX_CONTENT_LENGTH`).
- No hay base de datos ni almacenamiento persistente de archivos de usuarios.

## Próximas mejoras posibles

- OCR con Tesseract para hacer PDFs escaneados buscables.
- Conversión PDF → Excel/PowerPoint.
- Editor visual para escribir directamente sobre el PDF.
- Firma electrónica simple (dibujar/subir firma y colocarla en el PDF).
