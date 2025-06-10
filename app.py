from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import os
import zipfile
import io
import numpy as np
import cv2

app = Flask(__name__)
CORS(app)

def ocultar_rostos(imagem_pil):
    imagem_cv = cv2.cvtColor(np.array(imagem_pil), cv2.COLOR_RGB2BGR)
    classificador = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    rostos = classificador.detectMultiScale(imagem_cv, scaleFactor=1.1, minNeighbors=5)

    for (x, y, w, h) in rostos:
        rosto = imagem_cv[y:y+h, x:x+w]
        rosto_blur = cv2.GaussianBlur(rosto, (99, 99), 30)
        imagem_cv[y:y+h, x:x+w] = rosto_blur

    return Image.fromarray(cv2.cvtColor(imagem_cv, cv2.COLOR_BGR2RGB))

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    zip_file = request.files.get("zip_file")
    quality = int(request.form.get("quality", 75))
    width = request.form.get("width")
    height = request.form.get("height")
    output_format = request.form.get("output_format", "original")
    dpi = request.form.get("dpi")
    ocultar_faces = request.form.get("ocultar_faces", "false") == "true"

    # DPI padrão a 72 se não fornecido ou inválido
    try:
        dpi = int(dpi)
        if dpi <= 0:
            dpi = 72
    except (TypeError, ValueError):
        dpi = 72

    # Validar largura e altura, ignorar se inválido ou <= 0
    try:
        width = int(width)
        if width <= 0:
            width = None
    except (TypeError, ValueError):
        width = None

    try:
        height = int(height)
        if height <= 0:
            height = None
    except (TypeError, ValueError):
        height = None

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

                    if ocultar_faces:
                        img = ocultar_rostos(img)

                    # Redimensionar se largura e altura definidas, senão mantém original
                    if width and height:
                        img = img.resize((width, height), Image.LANCZOS)

                    save_kwargs = {"quality": quality, "dpi": (dpi, dpi)}

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
