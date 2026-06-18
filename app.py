import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re

st.set_page_config(page_title="Separador de Comprovantes", page_icon="📄")
st.title("📄 Separador Automático de Comprovantes")
st.write("Insira um PDF com vários comprovantes para separá-los pelo nome do favorecido.")

# Upload do arquivo original
uploaded_file = st.file_uploader("Escolha o arquivo PDF", type=["pdf"])

def extrair_nome_favorecido(texto_pagina):
    # Procura por termos comuns seguidos pelo nome
    padroes = [
        r"Favorecido:\s*([^\n]+)",
        r"Nome do favorecido:\s*([^\n]+)",
        r"Recebedor:\s*([^\n]+)",
        r"Nome:\s*([^\n]+)"
    ]
    
    for padrao in padroes:
        resultado = re.search(padrao, texto_pagina, re.IGNORECASE)
        if resultado:
            nome = resultado.group(1).strip()
            # Limpa caracteres que não podem ser usados em nomes de arquivos
            nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
            return nome_limpo[:50].strip().upper()
            
    return "FAVORECIDO_NAO_ENCONTRADO"

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    
    if st.button("Processar e Separar Comprovantes"):
        import zipfile
        zip_buffer = io.BytesIO()
        
        # Dicionário para controlar repetições de nomes e evitar substituição de arquivos
        nomes_contagem = {}
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf_leitor_texto:
                pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                total_paginas = len(pdf_leitor_texto.pages)
                barra_progresso = st.progress(0)
                
                for i in range(total_paginas):
                    pagina_texto = pdf_leitor_texto.pages[i].extract_text() or ""
                    nome_favorecido = extrair_nome_favorecido(pagina_texto)
                    
                    # Ajuste fino: Se o nome já apareceu no lote, coloca um número sutil, se for o primeiro, fica o nome puro!
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
