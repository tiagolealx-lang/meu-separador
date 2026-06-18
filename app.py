import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="Separador de Comprovantes", page_icon="📄")
st.title("📄 Separador Automático de Comprovantes")
st.write("Insira o PDF para separar as páginas pelo nome do favorecido (Suporta Bradesco e Banco do Brasil).")

# Upload do arquivo original
uploaded_file = st.file_uploader("Escolha o arquivo PDF", type=["pdf"])

def buscar_nome_no_texto(texto):
    """Procura os padrões de nome dentro de um bloco de texto extraído."""
    if not texto:
        return None
    padroes = [
        r"Favorecido:\s*([^\n]+)",
        r"Nome do favorecido:\s*([^\n]+)",
        r"Recebedor:\s*([^\n]+)",
        r"Nome:\s*([^\n]+)",
        r"BENEFICIÁRIO:\s*([^\n]+)"
    ]
    for padrao in padroes:
        resultado = re.search(padrao, texto, re.IGNORECASE)
        if resultado:
            nome = resultado.group(1).strip()
            nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
            return nome_limpo[:50].strip().upper()
    return None

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    
    if st.button("Processar e Separar Comprovantes"):
        import zipfile
        zip_buffer = io.BytesIO()
        nomes_contagem = {}
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf_leitor_texto:
                pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                total_paginas = len(pdf_leitor_texto.pages)
                barra_progresso = st.progress(0)
                
                for i in range(total_paginas):
                    # Método 1: Tenta extrair texto direto (Estilo Bradesco)
                    pagina_texto = pdf_leitor_texto.pages[i].extract_text()
                    nome_favorecido = buscar_nome_no_texto(pagina_texto)
                    
                    # Método 2: Se falhar/não copiar (Estilo Banco do Brasil), aplica o OCR na imagem
                    if not nome_favorecido:
                        try:
                            # Converte apenas a página atual em imagem na memória
                            imagens = convert_from_bytes(pdf_bytes, first_page=i+1, last_page=i+1)
                            if imagens:
                                texto_da_imagem = pytesseract.image_to_string(imagens[0], lang='por')
                                nome_favorecido = buscar_nome_no_texto(texto_da_imagem)
                        except:
                            pass
                    
                    # Se mesmo assim não achar, define o padrão de segurança
                    if not nome_favorecido:
                        nome_favorecido = f"FAVORECIDO_NAO_ENCONTRADO_PAG_{i+1}"
                    
                    # Evita sobreposição de arquivos com nomes idênticos
                    if nome_favorecido in nomes_contagem:
                        nomes_contagem[nome_favorecido] += 1
                        nome_arquivo = f"{nome_favorecido} {nomes_contagem[nome_favorecido]}.pdf"
                    else:
                        nomes_contagem[nome_favorecido] = 1
                        nome_arquivo = f"{nome_favorecido}.pdf"
                    
                    escritor = PdfWriter()
                    escritor.add_page(pdf_recortador.pages[i])
                    
                    pdf_pagina_buffer = io.BytesIO()
                    escritor.write(pdf_pagina_buffer)
                    pdf_pagina_buffer.seek(0)
                    
                    zip_file.writestr(nome_arquivo, pdf_pagina_buffer.read())
                    barra_progresso.progress((i + 1) / total_paginas)
                    
        st.success("🎉 Todos os comprovantes foram processados com sucesso!")
        st.download_button(
            label="📥 Baixar Comprovantes Separados (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="comprovantes_organizados.zip",
            mime="application/zip"
        )
