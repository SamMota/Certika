import os
import io
import zipfile
import json
import pandas as pd
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageCms
from flask import Flask, render_template, request, send_file, send_from_directory, Response, stream_with_context

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


app = Flask(__name__)

# Configura caminhos relativos para funcionar no Windows e no Render/Linux
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_IMAGENS = os.path.join(BASE_DIR, "image")
FONTE_PADRAO = os.path.join(BASE_DIR, "fonts", "Syne", "static", "Syne-Bold.ttf")

# Variável global temporária para armazenar o último ZIP gerado via streaming
ultimo_zip_bytes = None

# Rota para servir as imagens do modelo para o Live Preview do front-end
@app.route('/image/<filename>')
def serve_image(filename):
    return send_from_directory(PASTA_IMAGENS, filename)

def converter_para_cmyk_icc(imagem_pil):
    """
    Converte uma imagem PIL RGB para CMYK de forma segura.
    """
    if imagem_pil.mode == 'CMYK':
        return imagem_pil

    if imagem_pil.mode != 'RGB':
        imagem_pil = imagem_pil.convert('RGB')

    try:
        return imagem_pil.convert('CMYK')
    except Exception:
        return imagem_pil


def normalizar_texto(texto):
    """Remove acentos e coloca em minúsculas para facilitar a busca por palavras-chave."""
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()


def processar_csv_inteligente(file_storage):
    """Lê um arquivo CSV enviado e retorna uma lista de dicionários com nome e email mapeados dinamicamente."""
    try:
        conteudo = file_storage.read()
        try:
            df = pd.read_csv(io.BytesIO(conteudo), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(conteudo), encoding='latin1')
            
        colunas_originais = df.columns.tolist()
        colunas_normalizadas = [normalizar_texto(col) for col in colunas_originais]
        
        coluna_nome_idx = None
        coluna_email_idx = None
        
        palavras_nome = ['nome', 'participante', 'name', 'aluno', 'colaborador', 'funcionario']
        palavras_email = ['email', 'e-mail', 'correio', 'mail', 'eletronico']
        
        for idx, col in enumerate(colunas_normalizadas):
            if any(p in col for p in palavras_nome) and coluna_nome_idx is None:
                coluna_nome_idx = idx
            elif any(p in col for p in palavras_email) and coluna_email_idx is None:
                coluna_email_idx = idx
                
        if coluna_nome_idx is None and len(colunas_originais) > 0:
            coluna_nome_idx = 0 
        if coluna_email_idx is None and len(colunas_originais) > 1:
            coluna_email_idx = 1 
            
        participantes = []
        for _, row in df.iterrows():
            nome = str(row.iloc[coluna_nome_idx]).strip() if coluna_nome_idx is not None else ""
            email = str(row.iloc[coluna_email_idx]).strip() if coluna_email_idx is not None else ""
            
            if nome and nome.lower() != 'nan':
                participantes.append({
                    'nome': nome,
                    'email': email if email.lower() != 'nan' else ''
                })
                
        return participantes
    except Exception as e:
        print(f"Erro ao processar CSV: {e}")
        return []


# --- ROTA DE TESTE DE E-MAIL ---
@app.route('/testar-email', methods=['POST'])
def testar_email():
    try:
        smtp_email = request.form.get('smtp_email', '').strip()
        smtp_senha = request.form.get('smtp_senha', '').strip()
        assunto = request.form.get('email_assunto', 'Certificado de Teste').strip()
        mensagem_modelo = request.form.get('email_mensagem', 'Olá {nome}, este é um teste.').strip()
        
        if not smtp_email or not smtp_senha:
            return {"sucesso": False, "mensagem": "Preencha o e-mail e a senha de aplicativo primeiro."}, 400

        origem_modelo = request.form.get('origem_modelo')
        file_upload = request.files.get('file_upload')

        if origem_modelo == 'upload' and file_upload and file_upload.filename != '':
            img_modelo = Image.open(file_upload.stream).convert('RGB')
        else:
            modelo_sel = request.form.get('modelo_lista')
            caminho_img = os.path.join(PASTA_IMAGENS, modelo_sel) if modelo_sel else None
            if not caminho_img or not os.path.exists(caminho_img):
                imgs = [f for f in os.listdir(PASTA_IMAGENS) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if imgs:
                    caminho_img = os.path.join(PASTA_IMAGENS, imgs[0])
                else:
                    return {"sucesso": False, "mensagem": "Nenhum modelo de certificado encontrado para o teste."}, 400
            img_modelo = Image.open(caminho_img).convert('RGB')

        font_size = int(request.form.get('font_size', 60))
        pos_y_factor = float(request.form.get('pos_y_factor', 2.5))
        
        cor_hex = request.form.get('cor_hex', '#000000').lstrip('#')
        rgb_color = tuple(int(cor_hex[i:i+2], 16) for i in (0, 2, 4))

        try:
            font = ImageFont.truetype(FONTE_PADRAO, font_size)
        except Exception:
            font = ImageFont.load_default()

        nome_exemplo = "Participante de Teste"
        draw = ImageDraw.Draw(img_modelo)
        bbox = draw.textbbox((0, 0), nome_exemplo, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        pos_x = (img_modelo.width - text_width) / 2
        pos_y = (img_modelo.height - text_height) / pos_y_factor
        draw.text((pos_x, pos_y), nome_exemplo, fill=rgb_color, font=font)

        pdf_buffer = io.BytesIO()
        img_modelo.save(pdf_buffer, format="PDF", resolution=100.0)
        pdf_bytes = pdf_buffer.getvalue()

        # Montagem segura do e-mail de teste
        msg = MIMEMultipart('mixed')
        msg['From'] = smtp_email
        msg['To'] = smtp_email
        msg['Subject'] = f"[TESTE] {assunto}"

        corpo_final = mensagem_modelo.replace('{nome}', nome_exemplo)
        parte_texto = MIMEText(corpo_final, 'plain', 'utf-8')
        msg.attach(parte_texto)

        parte_anexo = MIMEBase('application', 'pdf')
        parte_anexo.set_payload(pdf_bytes)
        encoders.encode_base64(parte_anexo)
        parte_anexo.add_header('Content-Disposition', 'attachment', filename='Certificado_Teste.pdf')
        msg.attach(parte_anexo)

        conexao_smtp = smtplib.SMTP('smtp.gmail.com', 587)
        conexao_smtp.starttls()
        conexao_smtp.login(smtp_email, smtp_senha)
        conexao_smtp.sendmail(smtp_email, smtp_email, msg.as_string())
        conexao_smtp.quit()

        return {"sucesso": True, "mensagem": f"E-mail de teste enviado para {smtp_email}!"}
    except Exception as e:
        return {"sucesso": False, "mensagem": str(e)}, 500


@app.route('/', methods=['GET', 'POST'])
def index():
    modelos_existentes = []
    if os.path.exists(PASTA_IMAGENS):
        modelos_existentes = [f for f in os.listdir(PASTA_IMAGENS) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if request.method == 'POST':
        csv_file = request.files.get('csv_file')
        lista_participantes = []

        enviar_emails = request.form.get('enviar_emails') == 'on'
        smtp_email = request.form.get('smtp_email', '').strip()
        smtp_senha = request.form.get('smtp_senha', '').strip()

        if csv_file and csv_file.filename != '':
            lista_participantes = processar_csv_inteligente(csv_file)
        else:
            nomes_raw = request.form.get('nomes', '')
            lista_participantes = [{'nome': n.strip(), 'email': ''} for n in nomes_raw.split('\n') if n.strip()]
        
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

        # Fluxo rápido se o envio de e-mails não estiver ativo
        if not enviar_emails or not smtp_email or not smtp_senha:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for participante in lista_participantes:
                    nome = participante['nome']
                    nome_formatado = nome.upper() if formato_nome == 'upper' else (nome.title() if formato_nome == 'title' else nome)

                    img = img_modelo.copy().convert('RGB')
                    draw = ImageDraw.Draw(img)

                    bbox = draw.textbbox((0, 0), nome_formatado, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    pos_x = (img.width - text_width) / 2
                    pos_y = (img.height - text_height) / pos_y_factor

                    draw.text((pos_x, pos_y), nome_formatado, fill=rgb_color, font=font)

                    if modo_cor == 'CMYK':
                        img = converter_para_cmyk_icc(img)
                        resolucao_pdf = 300.0
                    else:
                        resolucao_pdf = 100.0

                    pdf_buffer = io.BytesIO()
                    img.save(pdf_buffer, format="PDF", resolution=resolucao_pdf)
                    
                    nome_pdf = f"Certificado_{nome_formatado.replace(' ', '_')}.pdf"
                    zipf.writestr(nome_pdf, pdf_buffer.getvalue())

            zip_buffer.seek(0)
            return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='certificados.zip')

        # FLUXO COM ENVIO DE E-MAIL, MENSAGEM PERSONALIZADA E STREAMING EM TEMPO REAL
        def gerar_com_progresso():
            conexao_smtp = None
            try:
                conexao_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                conexao_smtp.starttls()
                conexao_smtp.login(smtp_email, smtp_senha)
            except Exception as e:
                yield f"data: {json.dumps({'status': 'erro', 'mensagem': str(e)})}\n\n"
                return

            total = len(lista_participantes)
            zip_buffer = io.BytesIO()
            
            assunto_email = request.form.get('email_assunto', 'O seu Certificado de Participação')
            mensagem_modelo = request.form.get('email_mensagem', 'Olá {nome}, segue em anexo o seu certificado.')

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for idx, participante in enumerate(lista_participantes, 1):
                    nome = participante['nome']
                    email_destinatario = participante['email']

                    if formato_nome == 'upper':
                        nome_formatado = nome.upper()
                    elif formato_nome == 'title':
                        nome_formatado = nome.title()
                    else:
                        nome_formatado = nome

                    img = img_modelo.copy().convert('RGB')
                    draw = ImageDraw.Draw(img)

                    bbox = draw.textbbox((0, 0), nome_formatado, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    pos_x = (img.width - text_width) / 2
                    pos_y = (img.height - text_height) / pos_y_factor

                    draw.text((pos_x, pos_y), nome_formatado, fill=rgb_color, font=font)

                    if modo_cor == 'CMYK':
                        img = converter_para_cmyk_icc(img)
                        resolucao_pdf = 300.0
                    else:
                        resolucao_pdf = 100.0

                    pdf_buffer = io.BytesIO()
                    img.save(pdf_buffer, format="PDF", resolution=resolucao_pdf)
                    pdf_bytes = pdf_buffer.getvalue()

                    nome_pdf = f"Certificado_{nome_formatado.replace(' ', '_')}.pdf"
                    zipf.writestr(nome_pdf, pdf_bytes)

                    if email_destinatario:
                        try:
                            # Montagem blindada do e-mail com anexo MIME correto
                            msg = MIMEMultipart('mixed')
                            msg['From'] = smtp_email
                            msg['To'] = email_destinatario
                            msg['Subject'] = assunto_email

                            corpo = mensagem_modelo.replace('{nome}', nome_formatado)
                            parte_texto = MIMEText(corpo, 'plain', 'utf-8')
                            msg.attach(parte_texto)

                            parte_anexo = MIMEBase('application', 'pdf')
                            parte_anexo.set_payload(pdf_bytes)
                            encoders.encode_base64(parte_anexo)
                            parte_anexo.add_header('Content-Disposition', 'attachment', filename=nome_pdf)
                            msg.attach(parte_anexo)

                            conexao_smtp.sendmail(smtp_email, email_destinatario, msg.as_string())
                            status_msg = f"Enviado para {nome_formatado} ({idx}/{total})"
                        except smtplib.SMTPRecipientsRefused:
                            status_msg = f"E-mail recusado/inválido: {email_destinatario} ({idx}/{total})"
                        except Exception as ex:
                            erro_str = str(ex)
                            if "getaddrinfo failed" in erro_str or "Name or service not known" in erro_str or "domain" in erro_str.lower():
                                status_msg = f"Domínio incorreto ({email_destinatario}) ({idx}/{total})"
                            else:
                                status_msg = f"Erro ao enviar para {nome_formatado}: {ex}"
                    else:
                        status_msg = f"Gerado (sem e-mail): {nome_formatado} ({idx}/{total})"

                    yield f"data: {json.dumps({'status': 'progresso', 'mensagem': status_msg})}\n\n"

            if conexao_smtp:
                try:
                    conexao_smtp.quit()
                except:
                    pass

            global ultimo_zip_bytes
            ultimo_zip_bytes = zip_buffer.getvalue()
            yield f"data: {json.dumps({'status': 'concluido'})}\n\n"

        return Response(stream_with_context(gerar_com_progresso()), mimetype='text/event-stream')

    return render_template('index.html', modelos=modelos_existentes)


@app.route('/baixar-zip', methods=['GET'])
def baixar_zip():
    global ultimo_zip_bytes
    if 'ultimo_zip_bytes' in globals() and ultimo_zip_bytes:
        return send_file(io.BytesIO(ultimo_zip_bytes), mimetype='application/zip', as_attachment=True, download_name='certificados.zip')
    return "Nenhum arquivo encontrado", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)