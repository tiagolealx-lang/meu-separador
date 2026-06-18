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
    """
    Busca padrões comuns de nomes de favorecidos no texto.
    Ajuste as palavras-chave conforme o padrão do seu banco.
    """
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
            return nome_limpo[:50].strip() # Limita a 50 caracteres
            
    return "Favorecido_Nao_Encontrado"

if uploaded_file is not None:
    # Ler o PDF enviado usando bytes na memória
    pdf_bytes = uploaded_file.read()
    
    if st.button("Processar e Separar Comprovantes"):
        # Criar um arquivo ZIP na memória para download
        import zipfile
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Abrir o PDF com pdfplumber para ler o texto
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf_leitor_texto:
                # Abrir o PDF com pypdf para recortar as páginas
                pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                
                total_paginas = len(pdf_leitor_texto.pages)
                barra_progresso = st.progress(0)
                
                for i in range(total_paginas):
                    pagina_texto = pdf_leitor_texto.pages[i].extract_text()
                    
                    # Identificar o favorecido
                    nome_favorecido = extrair_nome_favorecido(pagina_texto)
                    nome_arquivo = f"{nome_favorecido}_comprovante_{i+1}.pdf"
                    
                    # Criar um novo PDF apenas com esta página
                    escritor = PdfWriter()
                    escritor.add_page(pdf_recortador.pages[i])
                    
                    # Salvar a página em um buffer de memória
                    pdf_pagina_buffer = io.BytesIO()
                    escritor.write(pdf_pagina_buffer)
                    pdf_pagina_buffer.seek(0)
                    
                    # Adicionar ao arquivo ZIP final
                    zip_file.writestr(nome_arquivo, pdf_pagina_buffer.read())
                    
                    # Atualizar progresso
                    barra_progresso.progress((i + 1) / total_paginas)
                    
        st.success("🎉 Todos os comprovantes foram processados com sucesso!")
        
        # Botão para baixar tudo organizado dentro de um ZIP
        st.download_button(
            label="📥 Baixar Comprovantes Separados (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="comprovantes_organizados.zip",
            mime="application/zip"
        )
