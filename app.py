import streamlit as st
from pypdf import PdfWriter, PdfReader
import io
import re

# Configuração simples e direta do site
st.set_page_config(page_title="Separador de Comprovantes", layout="centered")
st.title("📄 Separador de Comprovantes")
st.write("Insira o seu PDF para separar e salvar as páginas por nome do favorecido.")

# Campo único para envio do arquivo
uploaded_file = st.file_uploader("Escolha o arquivo PDF", type=["pdf"])

def extrair_nome_favorecido(pagina_pdf):
    try:
        texto = pagina_pdf.extract_text()
        if not texto:
            return None
            
        # Padrões diretos para capturar apenas o nome do favorecido
        padroes = [
            r"Favorecido:\s*([^\n]+)",
            r"Nome do Favorecido:\s*([^\n]+)",
            r"Nome:\s*([^\n]+)",
            r"Recebedor:\s*([^\n]+)",
            r"Beneficiário:\s*([^\n]+)"
        ]
        
        for padrao in padroes:
            resultado = re.search(padrao, texto, re.IGNORECASE)
            if resultado:
                nome = resultado.group(1).strip()
                # Remove apenas caracteres proibidos pelo Windows para nomes de arquivos
                nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
                if len(nome_limpo) > 2:
                    return nome_limpo.strip().upper()
    except:
        pass
    return None

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    
    if st.button("🚀 Separar e Salvar"):
        import zipfile
        zip_buffer = io.BytesIO()
        nomes_contagem = {}
        
        leitor = PdfReader(io.BytesIO(pdf_bytes))
        total_paginas = len(leitor.pages)
        barra_progresso = st.progress(0)
        
        # O segredo está aqui: o bloco 'with' garante que o ZIP feche e salve certinho
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(total_paginas):
                pagina = leitor.pages[i]
                nome = extrair_nome_favorecido(pagina)
                
                # Se não encontrar o nome na página, usa um padrão numérico simples
                if not nome:
                    nome = f"COMPROVANTE_PAGINA_{i+1}"
                
                # Se o nome já existir, adiciona o número para salvar individualmente na pasta sem substituir
                if nome in nomes_contagem:
                    nomes_contagem[nome] += 1
                    nome_final = f"{nome} {nomes_contagem[nome]}"
                else:
                    nomes_contagem[nome] = 1
                    nome_final = nome
                
                # Recorta a página e prepara para salvar
                escritor = PdfWriter()
                escritor.add_page(pagina)
                pag_buf = io.BytesIO()
                escritor.write(pag_buf)
                pag_buf.seek(0)
                
                # Salva o arquivo um por um no arquivo final
                zip_file.writestr(f"{nome_final}.pdf", pag_buf.read())
                barra_progresso.progress((i + 1) / total_paginas)
                
        # Move o ponteiro do buffer para o início para que o download consiga ler os dados inteiros
        zip_data = zip_buffer.getvalue()
                
        st.success("🎉 Todos os comprovantes foram separados!")
        st.download_button(
            label="📥 Baixar Pasta de Comprovantes (.ZIP)",
            data=zip_data,
            file_name="comprovantes_salvos.zip",
            mime="application/zip"
        )
