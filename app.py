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
    rostos = classificador.detectMultiScale(imagem_cv, scaleFactor=1.07, minNeighbors=8)

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
        dpi_val = int(dpi)
        if dpi_val <= 0:
            dpi_val = 72
    except:
        dpi_val = 72
    dpi_tuple = (dpi_val, dpi_val)

    # Validar largura e altura
    try:
        width_int = int(width) if width and int(width) > 0 else None
    except:
        width_int = None
    try:
        height_int = int(height) if height and int(height) > 0 else None
    except:
        height_int = None

    # Extrair ficheiros
    if zip_file:
        try:
            zip_bytes = io.BytesIO(zip_file.read())
            with zipfile.ZipFile(zip_bytes, 'r') as zip_ref:
                extracted_files = [zip_ref.open(name) for name in zip_ref.namelist()
                                   if name.lower().endswith((".png",".jpg",".jpeg"))]
        except zipfile.BadZipFile:
            return jsonify({"error": "Ficheiro ZIP inválido."}), 400
    else:
        extracted_files = files[:30]

    if not extracted_files:
        return jsonify({"error": "Nenhum ficheiro válido fornecido."}), 400

    output_zip = io.BytesIO()
    errors = []
    with zipfile.ZipFile(output_zip, 'w') as zip_out:
        for file in extracted_files:
            try:
                filename = getattr(file, 'filename', getattr(file, 'name', 'image'))
                with Image.open(file) as img:
                    original_format = img.format or 'PNG'
                    img = img.convert("RGB")

                    if ocultar_faces:
                        img = ocultar_rostos(img)

                    # Redimensionar
                    if width_int and height_int:
                        img = img.resize((width_int, height_int), Image.LANCZOS)

                    save_kwargs = {"quality": quality, "dpi": dpi_tuple}
                    base, _ = os.path.splitext(os.path.basename(filename))

                    # Formato original
                    if output_format in ("original", "both"):
                        buf = io.BytesIO()
                        img.save(buf, format=original_format, **save_kwargs)
                        zip_out.writestr(f"{base}_orig.{original_format.lower()}", buf.getvalue())
                    # JPG
                    if output_format in ("jpg", "both"):
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", **save_kwargs)
                        zip_out.writestr(f"{base}.jpg", buf.getvalue())
                    # PNG
                    if output_format in ("png", "both"):
                        buf = io.BytesIO()
                        img.save(buf, format="PNG", **save_kwargs)
                        zip_out.writestr(f"{base}.png", buf.getvalue())
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
                # Continua para o próximo ficheiro sem abortar
                continue

    output_zip.seek(0)
    response = send_file(output_zip, download_name="imagens_comprimidas.zip", as_attachment=True)
    # Incluir no header ou corpo lista de erros, se existirem
    if errors:
        response.headers['X-Processing-Errors'] = '; '.join(errors)
    return response
    
   

if __name__ == "__main__":
    # Em produção (no Render), o gunicorn (start command) é quem lança a app.
    # Em ambiente local, arrancar sem debug para poupar memória:
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)

