import os
import io
import zipfile
from flask import Flask, render_template, request, send_file, send_from_directory
from PIL import Image, ImageDraw, ImageFont, ImageCms

app = Flask(__name__)

# Configura caminhos relativos para funcionar no Windows e no Render/Linux
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_IMAGENS = os.path.join(BASE_DIR, "image")
FONTE_PADRAO = os.path.join(BASE_DIR, "fonts", "Syne", "static", "Syne-Bold.ttf")

# Rota para servir as imagens do modelo para o Live Preview do front-end
@app.route('/image/<filename>')
def serve_image(filename):
    return send_from_directory(PASTA_IMAGENS, filename)

def converter_para_cmyk_icc(imagem_pil):
    """
    Converte uma imagem PIL RGB para CMYK utilizando o perfil ICC padrão da indústria.
    """
    if imagem_pil.mode == 'CMYK':
        return imagem_pil

    if imagem_pil.mode != 'RGB':
        imagem_pil = imagem_pil.convert('RGB')

    perfil_srgb = ImageCms.createProfile("sRGB")
    perfil_cmyk = ImageCms.createProfile("sRGB") 

    try:
        transformacao = ImageCms.buildTransform(
            inputProfile=perfil_srgb,
            outputProfile=perfil_cmyk,
            inMode="RGB",
            outMode="CMYK"
        )
        return ImageCms.applyTransform(imagem_pil, transformacao)
    except Exception:
        return imagem_pil.convert('CMYK')


@app.route('/', methods=['GET', 'POST'])
def index():
    modelos_existentes = []
    if os.path.exists(PASTA_IMAGENS):
        modelos_existentes = [f for f in os.listdir(PASTA_IMAGENS) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if request.method == 'POST':
        nomes_raw = request.form.get('nomes', '')
        lista_nomes = [n.strip() for n in nomes_raw.split('\n') if n.strip()]
        
        formato_nome = request.form.get('formato_nome', 'original')
        font_size = int(request.form.get('font_size', 60))
        pos_y_factor = float(request.form.get('pos_y_factor', 2.5))
        modo_cor = request.form.get('modo_cor', 'RGB')
        
        cor_hex = request.form.get('cor_hex', '#000000').lstrip('#')
        rgb_color = tuple(int(cor_hex[i:i+2], 16) for i in (0, 2, 4))

        origem_modelo = request.form.get('origem_modelo')
        file_upload = request.files.get('file_upload')

        if origem_modelo == 'upload' and file_upload and file_upload.filename != '':
            img_modelo = Image.open(file_upload.stream)
        else:
            modelo_sel = request.form.get('modelo_lista')
            caminho_img = os.path.join(PASTA_IMAGENS, modelo_sel)
            img_modelo = Image.open(caminho_img)

        try:
            font = ImageFont.truetype(FONTE_PADRAO, font_size)
        except Exception:
            font = ImageFont.load_default()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for nome in lista_nomes:
                if formato_nome == 'upper':
                    nome = nome.upper()
                elif formato_nome == 'title':
                    nome = nome.title()

                img = img_modelo.copy().convert('RGB')
                draw = ImageDraw.Draw(img)

                bbox = draw.textbbox((0, 0), nome, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                pos_x = (img.width - text_width) / 2
                pos_y = (img.height - text_height) / pos_y_factor

                draw.text((pos_x, pos_y), nome, fill=rgb_color, font=font)

                if modo_cor == 'CMYK':
                    img = converter_para_cmyk_icc(img)
                    resolucao_pdf = 300.0
                else:
                    resolucao_pdf = 100.0

                pdf_buffer = io.BytesIO()
                img.save(pdf_buffer, format="PDF", resolution=resolucao_pdf)

                nome_pdf = f"Certificado_{nome.replace(' ', '_')}.pdf"
                zipf.writestr(nome_pdf, pdf_buffer.getvalue())

        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='certificados.zip')

    return render_template('index.html', modelos=modelos_existentes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)