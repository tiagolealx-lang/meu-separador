import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os

st.set_page_config(page_title="Separador de Comprovantes", layout="centered")

# --- CUSTOMIZAÇÃO DE CORES DA EMPRESA ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #0056b3;
        color: white;
    }
    .titulo-empresa {
        font-size: 32px;
        font-weight: bold;
        color: #333333;
        text-align: center;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA INTELIGENTE PARA PEGAR A LOGO ---
# Ele vai procurar qualquer arquivo que comece com o nome 'logo' na sua pasta do GitHub
imagem_logo = None
for arquivo in os.listdir("."):
    if arquivo.lower().startswith("logo") and arquivo.lower().endswith((".png", ".jpg", ".jpeg")):
        imagem_logo = arquivo
        break

if imagem_logo:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(imagem_logo, use_container_width=True)

# Título e textos customizados
st.markdown('<p class="titulo-empresa">SISTEMA DE GESTÃO DE COMPROVANTES</p>', unsafe_allow_html=True)
st.write("---")
st.markdown("""
### 📑 Instruções de Uso:
1. Clique no campo abaixo e selecione **um ou mais arquivos PDF** contendo os comprovantes.
2. Aguarde o carregamento e clique no botão azul para processar.
3. Baixe o arquivo `.ZIP` final com todos os documentos organizados pelo nome de cada favorecido.
""")

uploaded_files = st.file_uploader("Arraste ou escolha os arquivos PDF aqui", type=["pdf"], accept_multiple_files=True)

def extrair_nome(texto):
    padroes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)"]
    for p in padroes:
        res = re.search(p, texto, re.IGNORECASE)
        if res:
            return re.sub(r'[\\/*?:"<>|]', "", res.group(1).strip())[:40]
    return "Favorecido_Nao_Encontrado"

if uploaded_files:
    if st.button("🚀 Processar e Separar Comprovantes"):
        import zipfile
        zip_buffer = io.BytesIO()
        nomes_contagem = {}
        
        barra_progresso = st.progress(0)
        status_texto = st.empty()
        total_arquivos = len(uploaded_files)
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                status_texto.text(f"Processando arquivo {idx+1} de {total_arquivos}...")
                pdf_bytes = uploaded_file.read()
                
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as leitor_txt:
                    pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                    
                    for i in range(len(leitor_txt.pages)):
                        txt = leitor_txt.pages[i].extract_text() or ""
                        nome = extrair_nome(txt)
                        
                        if nome in nomes_contagem:
                            nomes_contagem[nome] += 1
                            nome_final = f"{nome} {nomes_contagem[nome]}"
                        else:
                            nomes_contagem[nome] = 1
                            nome_final = nome
                        
                        escritor = PdfWriter()
                        escritor.add_page(pdf_recortador.pages[i])
                        pag_buf = io.BytesIO()
                        escritor.write(pag_buf)
                        pag_buf.seek(0)
                        
                        zip_file.writestr(f"{nome_final}.pdf", pag_buf.read())
                
                barra_progresso.progress((idx + 1) / total_arquivos)
                        
        status_texto.empty()
        barra_progresso.empty()
        st.success(f"🎉 Sucesso! {total_arquivos} arquivo(s) dividido(s) com precisão.")
        st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes_empresa.zip", "application/zip")
