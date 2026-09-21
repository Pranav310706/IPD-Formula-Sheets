from flask import Flask, request, jsonify, send_file
from pix2tex.cli import LatexOCR
from PIL import Image
import io
import os
import json
import base64

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

app = Flask(__name__)

print("Loading Pix2Tex model...")
model = LatexOCR()
print("Pix2Tex model loaded successfully!")

FORMULAS_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "formulas_data.json")

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "service": "Pix2Tex Formula OCR"
    })

@app.route("/api/formula", methods=["POST"])
def formula_ocr():

    try:

        print("=" * 60)
        print("Content-Type:", request.content_type)
        print("Files:", request.files)
        print("Form:", request.form)
        print("JSON:", request.get_json(silent=True))
        print("=" * 60)

        img = None

        # --------------------------
        # Accept uploaded file
        # --------------------------
        uploaded = request.files.get("file") or request.files.get("image")

        if uploaded:

            print("Image received:", uploaded.filename)

            img = Image.open(uploaded.stream).convert("RGB")

        # --------------------------
        # Accept Base64 JSON
        # --------------------------
        elif request.is_json:

            data = request.get_json()

            if data and "image_base64" in data:

                image_data = data["image_base64"]

                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]

                img_bytes = base64.b64decode(image_data)

                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # --------------------------
        # No image supplied
        # --------------------------
        if img is None:

            return jsonify({
                "success": False,
                "error": "Upload using field 'file' or 'image', or send image_base64."
            }), 400

        # --------------------------
        # OCR
        # --------------------------
        latex = model(img)

        return jsonify({
            "success": True,
            "latex": latex
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# -----------------------------------------------------------------
# Formula Sheet PDF Generator  (NEW)
# -----------------------------------------------------------------
# Renders each LaTeX formula from formulas_data.json into an image
# with matplotlib, then lays them out as a numbered PDF with reportlab.
# -----------------------------------------------------------------

def render_latex_to_image(latex_str, fontsize=20, dpi=200):
    """Render a LaTeX string to a transparent PNG in memory."""
    fig = plt.figure(figsize=(6, 1))
    fig.patch.set_alpha(0)
    fig.text(0, 0.5, f"${latex_str}$", fontsize=fontsize, va="center", ha="left")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True,
                bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buf.seek(0)
    return buf


def build_formula_sheet_pdf(formulas, output_path, title="Formula Sheet"):
    """Build a numbered PDF formula sheet from a list of {name, latex} dicts."""
    page_w, page_h = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    margin = 2 * cm
    y = page_h - margin

    def draw_header():
        nonlocal y
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, y, title)
        y -= 0.9 * cm
        c.setLineWidth(1)
        c.line(margin, y, page_w - margin, y)
        y -= 1.0 * cm

    draw_header()

    for i, item in enumerate(formulas, start=1):

        img_buf = render_latex_to_image(item["latex"])
        img = ImageReader(img_buf)
        iw, ih = img.getSize()
        max_w = page_w - 2 * margin - 1 * cm
        max_h = 1.6 * cm
        scale = min(max_w / iw, max_h / ih)
        draw_w, draw_h = iw * scale, ih * scale

        row_height = 0.6 * cm + draw_h + 0.5 * cm

        # start a new page if this formula won't fit
        if y - row_height < margin:
            c.showPage()
            y = page_h - margin
            draw_header()

        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, f"{i}. {item['name']}")
        y -= 0.6 * cm

        c.drawImage(img, margin + 0.5 * cm, y - draw_h, width=draw_w, height=draw_h,
                    preserveAspectRatio=True, mask="auto")
        y -= (draw_h + 0.5 * cm)

    c.save()


@app.route("/api/formula-sheet", methods=["GET"])
def formula_sheet():
    """
    Generates a numbered PDF formula sheet from formulas_data.json
    and returns it as a downloadable file.

    Optional query params:
      ?title=My+Title   -> custom title on the PDF (default: "Trigonometry Formula Sheet")
    """
    try:
        if not os.path.exists(FORMULAS_DATA_PATH):
            return jsonify({
                "success": False,
                "error": f"Formula data file not found at {FORMULAS_DATA_PATH}"
            }), 404

        with open(FORMULAS_DATA_PATH, "r", encoding="utf-8") as f:
            formulas = json.load(f)

        if not formulas:
            return jsonify({"success": False, "error": "Formula data file is empty."}), 400

        title = request.args.get("title", "Trigonometry Formula Sheet")

        output_path = os.path.join("/tmp", "formula_sheet.pdf")
        build_formula_sheet_pdf(formulas, output_path, title=title)

        return send_file(
            output_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="formula_sheet.pdf"
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------
# Start Server
# -----------------------------
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5050,
        debug=True
    )
