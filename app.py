from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import os
import io
import zipfile
import uuid

app = Flask(__name__)
CORS(app)  # <- Esta linha ativa o CORS

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "API de compressão de imagens ativa."

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'Nenhum ficheiro enviado.'}), 400

    files = request.files.getlist('files')
    if len(files) > 10:
        return jsonify({'error': 'Número máximo de 10 ficheiros excedido.'}), 400

    compressed_images = []
    stats = []

    for f in files:
        try:
            img = Image.open(f.stream)
            original_size = f.content_length or 0

            output_io = io.BytesIO()
            filename, ext = os.path.splitext(f.filename)
            ext = ext.lower()

            # Guardar como JPG ou PNG comprimido
            if ext in ['.jpg', '.jpeg']:
                img.convert("RGB").save(output_io, format="JPEG", quality=60)
                ext_out = '.jpg'
            else:
                img.save(output_io, format="PNG", optimize=True)
                ext_out = '.png'

            output_io.seek(0)
            new_filename = f"{filename}_conv{ext_out}"
            compressed_images.append((new_filename, output_io))

            compressed_size = len(output_io.getvalue())

            stats.append({
                'ficheiro': f.filename,
                'original_kb': round(original_size / 1024, 1),
                'comprimido_kb': round(compressed_size / 1024, 1)
            })

        except Exception as e:
            return jsonify({'error': f'Erro ao processar {f.filename}: {str(e)}'}), 500

    # Criar ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for filename, img_io in compressed_images:
            zipf.writestr(filename, img_io.getvalue())

    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='comprimidos.zip')

if __name__ == '__main__':
    app.run(debug=True)

