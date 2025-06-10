from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
import io, zipfile, os

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "API de Compressão Ativa"

@app.route("/upload", methods=["POST"])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400

    files = request.files.getlist('files')

    if len(files) == 0 or len(files) > 10:
        return jsonify({'error': 'Envia entre 1 e 10 imagens.'}), 400

    zip_buffer = io.BytesIO()
    stats = []

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            try:
                f_bytes = f.read()
                img = Image.open(io.BytesIO(f_bytes))
                img.load()
                original_size = len(f_bytes)

                output_io = io.BytesIO()
                filename, ext = os.path.splitext(f.filename)
                ext = ext.lower()

                if ext in ['.jpg', '.jpeg']:
                    img.convert("RGB").save(output_io, format="JPEG", quality=60)
                    ext_out = ".jpg"
                else:
                    img.save(output_io, format="PNG", optimize=True)
                    ext_out = ".png"

                output_io.seek(0)
                new_filename = f"{filename}_conv{ext_out}"
                zipf.writestr(new_filename, output_io.read())

                compressed_size = len(output_io.getvalue())
                stats.append({
                    'ficheiro': f.filename,
                    'original_kb': round(original_size / 1024, 1),
                    'comprimido_kb': round(compressed_size / 1024, 1)
                })

            except UnidentifiedImageError:
                return jsonify({'error': f'Ficheiro inválido: {f.filename}'}), 400
            except Exception as e:
                return jsonify({'error': f'Erro ao processar {f.filename}: {str(e)}'}), 500

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name="imagens_comprimidas.zip")


if __name__ == '__main__':
    app.run(debug=True)

