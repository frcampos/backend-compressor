from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import os
import zipfile
import io
import tempfile

app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    zip_file = request.files.get("zip_file")
    quality = int(request.form.get("quality", 75))
    resize = float(request.form.get("resize", 1.0))
    width = request.form.get("width")
    height = request.form.get("height")
    output_format = request.form.get("output_format", "original")
    dpi = request.form.get("dpi")
    dpi = (int(dpi), int(dpi)) if dpi else None

    width = int(width) if width and width.isdigit() else 0
    height = int(height) if height and height.isdigit() else 0

    if zip_file:
        zip_bytes = io.BytesIO(zip_file.read())
        with zipfile.ZipFile(zip_bytes, 'r') as zip_ref:
            extracted_files = [zip_ref.open(name) for name in zip_ref.namelist()
                               if name.lower().endswith((".png", ".jpg", ".jpeg"))]
    else:
        extracted_files = files[:30]  # máximo 30 ficheiros

    if not extracted_files:
        return jsonify({"error": "Nenhum ficheiro válido fornecido."}), 400

    output_zip = io.BytesIO()
    with zipfile.ZipFile(output_zip, 'w') as zip_out:
        for file in extracted_files:
            try:
                filename = file.filename if hasattr(file, 'filename') else file.name
                with Image.open(file) as img:
                    original_format = img.format
                    img = img.convert("RGB")

                    if resize != 1.0:
                        img = img.resize((int(img.width * resize), int(img.height * resize)))
                    elif width > 0 and height > 0:
                        img = img.resize((width, height))

                    save_kwargs = {"quality": quality}
                    if dpi:
                        save_kwargs["dpi"] = dpi

                    base_name, _ = os.path.splitext(os.path.basename(filename))

                    if output_format == "original" or output_format == "both":
                        buffer_orig = io.BytesIO()
                        img.save(buffer_orig, format=original_format, **save_kwargs)
                        zip_out.writestr(f"{base_name}_compressed.{original_format.lower()}", buffer_orig.getvalue())

                    if output_format == "jpg" or output_format == "both":
                        buffer_jpg = io.BytesIO()
                        img.save(buffer_jpg, format="JPEG", **save_kwargs)
                        zip_out.writestr(f"{base_name}.jpg", buffer_jpg.getvalue())

                    if output_format == "png" or output_format == "both":
                        buffer_png = io.BytesIO()
                        img.save(buffer_png, format="PNG", **save_kwargs)
                        zip_out.writestr(f"{base_name}.png", buffer_png.getvalue())

            except Exception as e:
                return jsonify({"error": f"Erro ao processar {filename}: {str(e)}"}), 400

    output_zip.seek(0)
    return send_file(output_zip, download_name="imagens_comprimidas.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=10000)
