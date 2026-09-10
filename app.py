import os
import io
import uuid
import shutil
import zipfile
import subprocess
import tempfile

from flask import Flask, request, render_template, send_file, jsonify, after_this_request

from pypdf import PdfReader, PdfWriter
import pikepdf
from pdf2image import convert_from_path
import img2pdf
from PIL import Image
from pdf2docx import Converter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB por request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def work_dir():
    d = os.path.join(TMP_DIR, uuid.uuid4().hex)
    os.makedirs(d, exist_ok=True)
    return d


def cleanup(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


def send_and_cleanup(filepath, download_name, wd):
    @after_this_request
    def _cleanup(response):
        cleanup(wd)
        return response
    return send_file(filepath, as_attachment=True, download_name=download_name)


def parse_ranges(ranges_str, total_pages):
    """'1-3,5,7-9' -> lista de indices 0-based"""
    pages = set()
    ranges_str = (ranges_str or "").strip()
    if not ranges_str:
        return list(range(total_pages))
    for part in ranges_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            a, b = int(a), int(b)
            for p in range(a, b + 1):
                if 1 <= p <= total_pages:
                    pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


@app.route("/")
def index():
    return render_template("index.html")


# ---------- MERGE ----------
@app.route("/api/merge", methods=["POST"])
def api_merge():
    files = request.files.getlist("files")
    if len(files) < 2:
        return jsonify({"error": "Sube al menos 2 archivos PDF"}), 400
    wd = work_dir()
    writer = PdfWriter()
    try:
        for f in files:
            path = os.path.join(wd, f.filename)
            f.save(path)
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
        out_path = os.path.join(wd, "unido.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "unido.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- SPLIT ----------
@app.route("/api/split", methods=["POST"])
def api_split():
    f = request.files.get("file")
    mode = request.form.get("mode", "all")  # 'all' = una por página, 'ranges' = rangos
    ranges_str = request.form.get("ranges", "")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)
        total = len(reader.pages)
        zip_path = os.path.join(wd, "dividido.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            if mode == "all":
                for i in range(total):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    part_path = os.path.join(wd, f"pagina_{i+1}.pdf")
                    with open(part_path, "wb") as out:
                        writer.write(out)
                    zf.write(part_path, f"pagina_{i+1}.pdf")
            else:
                idxs = parse_ranges(ranges_str, total)
                writer = PdfWriter()
                for i in idxs:
                    writer.add_page(reader.pages[i])
                part_path = os.path.join(wd, "seleccion.pdf")
                with open(part_path, "wb") as out:
                    writer.write(out)
                zf.write(part_path, "seleccion.pdf")
        return send_and_cleanup(zip_path, "dividido.zip", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- COMPRESS ----------
@app.route("/api/compress", methods=["POST"])
def api_compress():
    f = request.files.get("file")
    level = request.form.get("level", "medium")  # low, medium, high
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        out_path = os.path.join(wd, "comprimido.pdf")

        quality_map = {
            "low": "/printer",
            "medium": "/ebook",
            "high": "/screen",
        }
        gs_setting = quality_map.get(level, "/ebook")

        cmd = [
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={gs_setting}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={out_path}", in_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=280)
        if result.returncode != 0 or not os.path.exists(out_path):
            # fallback con pikepdf si ghostscript falla
            pdf = pikepdf.open(in_path)
            pdf.save(out_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        return send_and_cleanup(out_path, "comprimido.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- ROTATE ----------
@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    f = request.files.get("file")
    angle = int(request.form.get("angle", "90"))
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.rotate(angle)
            writer.add_page(page)
        out_path = os.path.join(wd, "rotado.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "rotado.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- PDF TO JPG ----------
@app.route("/api/pdf-to-jpg", methods=["POST"])
def api_pdf_to_jpg():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        images = convert_from_path(in_path, dpi=150)
        zip_path = os.path.join(wd, "imagenes.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i, img in enumerate(images):
                img_path = os.path.join(wd, f"pagina_{i+1}.jpg")
                img.save(img_path, "JPEG")
                zf.write(img_path, f"pagina_{i+1}.jpg")
        return send_and_cleanup(zip_path, "imagenes.zip", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- IMAGES TO PDF ----------
@app.route("/api/jpg-to-pdf", methods=["POST"])
def api_jpg_to_pdf():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Sube al menos una imagen"}), 400
    wd = work_dir()
    try:
        img_paths = []
        for f in files:
            path = os.path.join(wd, f.filename)
            f.save(path)
            # Convertir a RGB por si es PNG con transparencia
            img = Image.open(path).convert("RGB")
            fixed_path = path + "_rgb.jpg"
            img.save(fixed_path, "JPEG")
            img_paths.append(fixed_path)
        out_path = os.path.join(wd, "imagenes.pdf")
        with open(out_path, "wb") as out:
            out.write(img2pdf.convert(img_paths))
        return send_and_cleanup(out_path, "imagenes.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- PDF TO WORD ----------
@app.route("/api/pdf-to-word", methods=["POST"])
def api_pdf_to_word():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        out_path = os.path.join(wd, "convertido.docx")
        cv = Converter(in_path)
        cv.convert(out_path)
        cv.close()
        return send_and_cleanup(out_path, "convertido.docx", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- WORD TO PDF ----------
@app.route("/api/word-to-pdf", methods=["POST"])
def api_word_to_pdf():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Sube un archivo Word (.docx)"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        cmd = [
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", wd, in_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=280, check=True)
        base_name = os.path.splitext(f.filename)[0]
        out_path = os.path.join(wd, base_name + ".pdf")
        if not os.path.exists(out_path):
            raise RuntimeError("La conversión con LibreOffice falló")
        return send_and_cleanup(out_path, base_name + ".pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- EXTRACT PAGES ----------
@app.route("/api/extract", methods=["POST"])
def api_extract():
    f = request.files.get("file")
    ranges_str = request.form.get("ranges", "")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)
        total = len(reader.pages)
        idxs = parse_ranges(ranges_str, total)
        writer = PdfWriter()
        for i in idxs:
            writer.add_page(reader.pages[i])
        out_path = os.path.join(wd, "extraido.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "extraido.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- REMOVE PAGES ----------
@app.route("/api/remove-pages", methods=["POST"])
def api_remove_pages():
    f = request.files.get("file")
    ranges_str = request.form.get("ranges", "")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)
        total = len(reader.pages)
        remove_idxs = set(parse_ranges(ranges_str, total))
        writer = PdfWriter()
        for i in range(total):
            if i not in remove_idxs:
                writer.add_page(reader.pages[i])
        out_path = os.path.join(wd, "sin_paginas.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "sin_paginas.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- WATERMARK ----------
@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    f = request.files.get("file")
    text = request.form.get("text", "CONFIDENCIAL")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)

        wm_path = os.path.join(wd, "wm.pdf")
        page0 = reader.pages[0]
        w, h = float(page0.mediabox.width), float(page0.mediabox.height)
        c = canvas.Canvas(wm_path, pagesize=(w, h))
        c.saveState()
        c.setFont("Helvetica-Bold", 50)
        c.setFillGray(0.6, 0.35)
        c.translate(w / 2, h / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, text)
        c.restoreState()
        c.save()

        wm_reader = PdfReader(wm_path)
        wm_page = wm_reader.pages[0]

        writer = PdfWriter()
        for page in reader.pages:
            page.merge_page(wm_page)
            writer.add_page(page)
        out_path = os.path.join(wd, "marca_de_agua.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "marca_de_agua.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- PAGE NUMBERS ----------
@app.route("/api/page-numbers", methods=["POST"])
def api_page_numbers():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        reader = PdfReader(in_path)
        writer = PdfWriter()
        total = len(reader.pages)
        for i, page in enumerate(reader.pages):
            w, h = float(page.mediabox.width), float(page.mediabox.height)
            overlay_path = os.path.join(wd, f"num_{i}.pdf")
            c = canvas.Canvas(overlay_path, pagesize=(w, h))
            c.setFont("Helvetica", 10)
            c.drawCentredString(w / 2, 20, f"{i + 1} / {total}")
            c.save()
            overlay_reader = PdfReader(overlay_path)
            page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)
        out_path = os.path.join(wd, "numerado.pdf")
        with open(out_path, "wb") as out:
            writer.write(out)
        return send_and_cleanup(out_path, "numerado.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- PROTECT (add password) ----------
@app.route("/api/protect", methods=["POST"])
def api_protect():
    f = request.files.get("file")
    password = request.form.get("password", "")
    if not f or not password:
        return jsonify({"error": "Sube un PDF y define una contraseña"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        pdf = pikepdf.open(in_path)
        out_path = os.path.join(wd, "protegido.pdf")
        pdf.save(out_path, encryption=pikepdf.Encryption(user=password, owner=password, R=4))
        return send_and_cleanup(out_path, "protegido.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- UNLOCK (remove password) ----------
@app.route("/api/unlock", methods=["POST"])
def api_unlock():
    f = request.files.get("file")
    password = request.form.get("password", "")
    if not f:
        return jsonify({"error": "Sube un PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        pdf = pikepdf.open(in_path, password=password)
        out_path = os.path.join(wd, "desbloqueado.pdf")
        pdf.save(out_path)
        return send_and_cleanup(out_path, "desbloqueado.pdf", wd)
    except pikepdf.PasswordError:
        cleanup(wd)
        return jsonify({"error": "Contraseña incorrecta"}), 400
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


# ---------- REPAIR ----------
@app.route("/api/repair", methods=["POST"])
def api_repair():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Sube un archivo PDF"}), 400
    wd = work_dir()
    try:
        in_path = os.path.join(wd, f.filename)
        f.save(in_path)
        out_path = os.path.join(wd, "reparado.pdf")
        cmd = ["qpdf", "--decrypt", "--object-streams=disable", in_path, out_path]
        result = subprocess.run(cmd, capture_output=True, timeout=200)
        if not os.path.exists(out_path):
            pdf = pikepdf.open(in_path)
            pdf.save(out_path)
        return send_and_cleanup(out_path, "reparado.pdf", wd)
    except Exception as e:
        cleanup(wd)
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
