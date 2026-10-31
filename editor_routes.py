import os
import io
import re
import json
import base64
import tempfile
import fitz
from PIL import Image, ImageDraw, ImageFont
from flask import render_template, request, send_file, jsonify


def _hex_rgb(value):
    value = str(value or "#e53950")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        value = "#e53950"
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def _draw_annotations(page, annotations):
    if not annotations:
        return
    width = max(1, int(page.rect.width * 2))
    height = max(1, int(page.rect.height * 2))
    layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    def xy(point):
        return (int(max(0, min(1, float(point.get("x", 0)))) * width),
                int(max(0, min(1, float(point.get("y", 0)))) * height))

    for item in annotations[:300]:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        rgb = _hex_rgb(item.get("color"))
        opacity = max(0.1, min(1.0, float(item.get("opacity", 0.4))))
        stroke = max(1, min(60, int(float(item.get("width", 3)) * width / 900)))
        x = max(0, min(1, float(item.get("x", 0)))) * width
        y = max(0, min(1, float(item.get("y", 0)))) * height
        x2 = max(0, min(1, float(item.get("x2", x / width)))) * width
        y2 = max(0, min(1, float(item.get("y2", y / height)))) * height

        if kind in ("pen", "highlight"):
            pts = [xy(p) for p in item.get("points", [])[:4000] if isinstance(p, dict)]
            if len(pts) >= 2:
                alpha = int(255 * opacity) if kind == "highlight" else 255
                draw.line(pts, fill=(*rgb, alpha), width=max(stroke, 8 if kind == "highlight" else stroke), joint="curve")
                radius = max(1, stroke // 2)
                for px, py in (pts[0], pts[-1]):
                    draw.ellipse((px-radius, py-radius, px+radius, py+radius), fill=(*rgb, alpha))
        elif kind == "line":
            draw.line((x, y, x2, y2), fill=(*rgb, 255), width=stroke)
        elif kind == "rect":
            draw.rectangle((x, y, x2, y2), outline=(*rgb, 255), width=stroke)
        elif kind == "ellipse":
            draw.ellipse((x, y, x2, y2), outline=(*rgb, 255), width=stroke)
        elif kind == "text":
            text = str(item.get("text", ""))[:500]
            if text:
                size = max(8, min(160, int(float(item.get("fontSize", 18)) * width / 900)))
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", size)
                except OSError:
                    font = ImageFont.load_default()
                draw.text((x, y), text, fill=(*rgb, 255), font=font)
        elif kind == "image":
            data = str(item.get("data", ""))
            match = re.fullmatch(r"data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)", data)
            if not match:
                continue
            try:
                raw = base64.b64decode(match.group(1), validate=True)
                if len(raw) > 5 * 1024 * 1024:
                    continue
                with Image.open(io.BytesIO(raw)) as source:
                    source.load()
                    image = source.convert("RGBA")
                box_w = max(1, int(float(item.get("w", .25)) * width))
                box_h = max(1, int(float(item.get("h", .18)) * height))
                image.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
                layer.alpha_composite(image, (int(x), int(y)))
            except Exception:
                continue

    buffer = io.BytesIO()
    layer.save(buffer, format="PNG")
    page.insert_image(page.rect, stream=buffer.getvalue(), overlay=True)


def register_editor(app):
    @app.get("/editor")
    def visual_editor():
        return render_template("editor.html")

    @app.post("/api/editor/save")
    def save_visual_editor():
        uploaded = request.files.get("file")
        if not uploaded:
            return jsonify({"error": "Selecciona un PDF."}), 400
        if uploaded.filename and not uploaded.filename.lower().endswith(".pdf"):
            return jsonify({"error": "El archivo debe ser un PDF."}), 400
        try:
            raw_operations = request.form.get("operations", "[]")
            if len(raw_operations) > 8 * 1024 * 1024:
                return jsonify({"error": "El proyecto de edición es demasiado grande."}), 413
            operations = json.loads(raw_operations)
            if not isinstance(operations, list) or not operations or len(operations) > 500:
                return jsonify({"error": "Operaciones no válidas."}), 400
            with tempfile.TemporaryDirectory() as work:
                source = os.path.join(work, "source.pdf")
                output = os.path.join(work, "edited.pdf")
                uploaded.save(source)
                if os.path.getsize(source) > 100 * 1024 * 1024:
                    return jsonify({"error": "El PDF supera el límite de 100 MB."}), 413
                doc = fitz.open(source)
                if doc.needs_pass:
                    doc.close()
                    return jsonify({"error": "El PDF está protegido. Desbloquéalo antes de editarlo."}), 400
                valid = [p for p in operations if isinstance(p, dict) and not p.get("deleted")]
                indices = [int(p.get("original", -1)) for p in valid]
                if not indices or any(i < 0 or i >= doc.page_count for i in indices) or len(set(indices)) != len(indices):
                    doc.close()
                    return jsonify({"error": "El orden de páginas no es válido."}), 400
                doc.select(indices)
                for idx, op in enumerate(valid):
                    page = doc[idx]
                    rotation = int(op.get("rotation", 0)) % 360
                    if rotation not in (0, 90, 180, 270):
                        rotation = 0
                    page.set_rotation(rotation)
                    _draw_annotations(page, op.get("annotations", []))
                doc.save(output, garbage=4, deflate=True)
                doc.close()
                with open(output, "rb") as result_file:
                    pdf_bytes = io.BytesIO(result_file.read())
                pdf_bytes.seek(0)
                return send_file(pdf_bytes, as_attachment=True, download_name="documento_editado.pdf", mimetype="application/pdf")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return jsonify({"error": "Los datos de edición no son válidos: " + str(exc)}), 400
        except Exception as exc:
            return jsonify({"error": "No se pudo editar el PDF: " + str(exc)}), 400
