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

## Uso de código abierto: 

- Puedes robarme el código para mejorarlo o montar tu herramienta propia.
- Si quieres hacer una pull request o tienes ideas de mejora contactame al:
- discord: _destrozaabuelas
> (Si demoro en contestar es que soy un muerto en redes sociales) 
