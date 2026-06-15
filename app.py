import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re

st.set_page_config(page_title="Separador de Comprovantes", layout="centered")
st.title("📄 Separador de Comprovantes")
st.write("Arraste seu PDF aqui para separar por nome de favorecido.")

uploaded_file = st.file_uploader("Escolha o arquivo PDF", type=["pdf"])

def extrair_nome(texto):
    padroes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)"]
    for p in padroes:
        res = re.search(p, texto, re.IGNORECASE)
        if res:
            return re.sub(r'[\\/*?:"<>|]', "", res.group(1).strip())[:40]
    return "Favorecido_Nao_Encontrado"

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    if st.button("Separar PDF agora"):
        import zipfile
        zip_buffer = io.BytesIO()
        
        # Dicionário para controlar se o nome já apareceu e evitar arquivos duplicados
        nomes_contagem = {}
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as leitor_txt:
                pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                
                for i in range(len(leitor_txt.pages)):
                    txt = leitor_txt.pages[i].extract_text() or ""
                    nome = extrair_nome(txt)
                    
                    # Se a pessoa já tiver um comprovante, adiciona um número sutil (ex: Antonio 2)
                    # Se for o primeiro comprovante dela, fica só o nome puro!
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
                    
                    # Salva o arquivo com o nome limpo conforme solicitado
                    zip_file.writestr(f"{nome_final}.pdf", pag_buf.read())
                    
        st.success("🎉 Pronto!")
        st.download_button("📥 Baixar Arquivos (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")
