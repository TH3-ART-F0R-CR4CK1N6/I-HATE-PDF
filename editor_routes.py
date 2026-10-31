import os
import json
import tempfile
import fitz
from flask import render_template, request, send_file, jsonify


def register_editor(app):
    @app.get("/editor")
    def visual_editor():
        return render_template("editor.html")

    @app.post("/api/editor/save")
    def save_visual_editor():
        uploaded = request.files.get("file")
        if not uploaded:
            return jsonify({"error": "Selecciona un PDF."}), 400
        try:
            operations = json.loads(request.form.get("operations", "[]"))
            if not isinstance(operations, list) or len(operations) > 500:
                return jsonify({"error": "Operaciones no válidas."}), 400
            with tempfile.TemporaryDirectory() as work:
                source = os.path.join(work, "source.pdf")
                output = os.path.join(work, "edited.pdf")
                uploaded.save(source)
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
                    for item in op.get("texts", [])[:50]:
                        text = str(item.get("text", ""))[:180]
                        if not text:
                            continue
                        cw = max(1, float(item.get("canvasWidth", 1)))
                        ch = max(1, float(item.get("canvasHeight", 1)))
                        x = float(item.get("x", 0)) / cw * page.rect.width
                        y = float(item.get("y", 0)) / ch * page.rect.height
                        x = min(max(12, x), page.rect.width - 12)
                        y = min(max(18, y), page.rect.height - 12)
                        page.insert_text((x, y), text, fontsize=14, color=(0.85, 0.12, 0.2), overlay=True)
                doc.save(output, garbage=4, deflate=True)
                doc.close()
                return send_file(output, as_attachment=True, download_name="documento_editado.pdf", mimetype="application/pdf")
        except Exception as exc:
            return jsonify({"error": "No se pudo editar el PDF: " + str(exc)}), 400
