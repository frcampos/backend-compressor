from flask import Flask, request, send_file, jsonify
from PIL import Image
from io import BytesIO
import zipfile
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_images():
    if 'images' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400

    files = request.files.getlist('images')
    if len(files) > 10:
        return jsonify({'error': 'Máximo de 10 imagens permitido'}), 400

    zip_buffer = BytesIO()
    zip_file = zipfile.ZipFile(zip_buffer, 'w')

    for file in files:
        image = Image.open(file.stream)
        img_format = 'JPEG' if image.mode != 'RGBA' else 'PNG'
        image = image.convert('RGB') if img_format == 'JPEG' else image

        buffer = BytesIO()
        if img_format == 'JPEG':
            image.save(buffer, format='JPEG', quality=60)
        else:
            image.save(buffer, format='PNG', optimize=True)

        buffer.seek(0)
        filename = f"{os.path.splitext(file.filename)[0]}_compressed.{img_format.lower()}"
        zip_file.writestr(filename, buffer.getvalue())

    zip_file.close()
    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='imagens_comprimidas.zip'
    )

@app.route('/')
def index():
    return 'API de compressão de imagens ativa.'

if __name__ == '__main__':
    app.run(debug=True)
