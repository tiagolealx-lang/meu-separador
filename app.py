import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Painel de Automação Comercial", layout="centered")

# Arquivo para salvar as certidões
ARQUIVO_CERTIDOES = "dados_certidoes.csv"

# Funções para gerenciar o arquivo de certidões
def carregar_certidoes():
    if os.path.exists(ARQUIVO_CERTIDOES):
        df = pd.read_csv(ARQUIVO_CERTIDOES)
        df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=["Nome", "Link", "Vencimento"])

def salvar_certidoes(df):
    df.to_csv(ARQUIVO_CERTIDOES, index=False)

# Inicializa as certidões no sistema
if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_certidoes()

# --- MENU LATERAL (NO CANTO DO APLICATIVO) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.title("Navigation")
    st.write("Escolha a ferramenta que deseja usar:")
    opcao_menu = st.radio("Menu Principal", ["Separador de Comprovantes", "Controle de Certidões"])

# --- PAGINA 1: SEPARADOR DE COMPROVANTES ---
if opcao_menu == "Separador de Comprovantes":
    st.markdown("<h1 style='text-align: center;'>📄 Separador de Comprovantes</h1>", unsafe_allow_html=True)
    st.write("---")
    
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
            st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- PAGINA 2: CONTROLE DE CERTIDÕES ---
else:
    st.markdown("<h1 style='text-align: center;'>📋 Controle de Certidões</h1>", unsafe_allow_html=True)
    st.write("---")
    
    # Formulário para cadastrar nova certidão
    st.subheader("➕ Cadastrar Nova Certidão")
    with st.form("form_certidao", clear_on_submit=True):
        nome_cert = st.text_input("Nome da Certidão (Ex: FGTS, Municipal, Federal)")
        link_cert = st.text_input("Link da Certidão / Site de Emissão")
        venc_cert = st.date_input("Data de Vencimento", datetime.today().date())
        
        botao_cert = st.form_submit_button("Salvar Certidão")
        
    if botao_cert and nome_cert:
        nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
        st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
        salvar_certidoes(st.session_state.certidoes)
        st.success("Certidão cadastrada com sucesso!")
        st.rerun()
        
    # Exibição das certidões salvas
    st.write("---")
    st.subheader("🔍 Minhas Certidões Salvas")
    
    df_cert = st.session_state.certidoes
    
    if not df_cert.empty:
        lista_exibicao = []
        hoje = datetime.today().date()
        
        # Calcular status visual para cada linha
        for idx, linha in df_cert.iterrows():
            vencimento = linha["Vencimento"]
            if vencimento < hoje:
                status = "🔴 VENCIDA"
            elif (vencimento - hoje).days <= 10:
                status = f"🟡 ATENÇÃO ({ (vencimento - hoje).days } dias)"
            else:
                status = "🟢 EM DIA"
                
            lista_exibicao.append({
                "Status": status,
                "Nome da Certidão": linha["Nome"],
                "Link de Acesso": linha["Link"],
                "Data de Vencimento": vencimento.strftime("%d/%m/%Y")
            })
            
        df_final = pd.DataFrame(lista_exibicao)
        
        # Exibe a tabela bonita na tela. Links ficam clicáveis se o usuário copiar.
        st.dataframe(df_final, use_container_width=True)
        
        # Opção para excluir tudo se quiser recomeçar
        if st.button("⚠️ Apagar Todas as Certidões"):
            st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
            if os.path.exists(ARQUIVO_CERTIDOES):
                os.remove(ARQUIVO_CERTIDOES)
            st.success("Histórico limpo!")
            st.rerun()
    else:
        st.info("Nenhuma certidão cadastrada ainda. Use o formulário acima!")
