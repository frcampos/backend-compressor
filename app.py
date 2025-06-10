from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
import io, zipfile, os

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "API de Compressão com Qualidade, Redução e Redimensionamento"

@app.route("/upload", methods=["POST"])
def upload():
    if 'files' not in request.files and 'zip_file' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400

    files = []
    if 'zip_file' in request.files:
        zip_file = request.files['zip_file']
        try:
            with zipfile.ZipFile(zip_file) as zipf:
                for name in zipf.namelist():
                    if name.lower().endswith(('.png', '.jpg', '.jpeg')):
                        files.append((name, io.BytesIO(zipf.read(name))))
        except zipfile.BadZipFile:
            return jsonify({'error': 'Ficheiro ZIP inválido.'}), 400
    else:
        files = [(f.filename, f.stream) for f in request.files.getlist('files')]

    if len(files) == 0 or len(files) > 30:
        return jsonify({'error': 'Envia entre 1 e 30 imagens.'}), 400

    try:
        quality = int(request.form.get("quality", 60))
        quality = min(max(30, quality), 90)
        resize = float(request.form.get("resize", 1.0))
        resize = min(max(0.1, resize), 1.0)
        width = int(request.form.get("width", 0))
        height = int(request.form.get("height", 0))
    except:
        return jsonify({'error': 'Parâmetros inválidos.'}), 400

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename, stream in files:
            try:
                f_bytes = stream.read()
                img = Image.open(io.BytesIO(f_bytes))
                img.load()

                if width > 0 and height > 0:
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                elif resize < 1.0:
                    new_size = (int(img.width * resize), int(img.height * resize))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)


                output_io = io.BytesIO()
                fname, ext = os.path.splitext(filename)
                ext = ext.lower()

                if ext in ['.jpg', '.jpeg']:
                    img.convert("RGB").save(output_io, format="JPEG", quality=quality)
                    ext_out = ".jpg"
                else:
                    img.save(output_io, format="PNG", optimize=True)
                    ext_out = ".png"

                output_io.seek(0)
                new_filename = f"{fname}_conv{ext_out}"
                zipf.writestr(new_filename, output_io.read())

            except UnidentifiedImageError:
                return jsonify({'error': f'Ficheiro inválido: {filename}'}), 400
            except Exception as e:
                return jsonify({'error': f'Erro ao processar {filename}: {str(e)}'}), 500

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name="imagens_comprimidas.zip")


