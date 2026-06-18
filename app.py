import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os
import pandas as pd
from datetime import datetime

# Configuração da página e layout
st.set_page_config(page_title="Painel de Licitações Pro", layout="centered", initial_sidebar_state="expanded")

# --- DESIGN PREMIUM EM CSS ---
st.markdown("""
    <style>
    /* Fundo geral e fontes */
    @import url('https://googleapis.com');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #0e1117;
    }
    
    /* Customização da Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #21262d;
    }
    
    /* Estilo dos Blocos/Containers (Cards) */
    div[data-testid="stForm"] {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        padding: 25px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    
    /* Títulos Principais */
    .main-title {
        font-size: 32px;
        font-weight: 700;
        color: #f0f6fc;
        text-align: center;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }
    .sub-title {
        font-size: 14px;
        color: #8b949e;
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* Subtítulos de Seções */
    h3 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        margin-top: 15px !important;
    }
    
    /* Inputs e Caixas de Seleção */
    input, select, textarea, div[data-baseweb="select"] {
        background-color: #0e1117 !important;
        color: #f0f6fc !important;
        border-radius: 8px !important;
    }
    
    /* Botão Principal Salvar */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #1f6feb 0%, #0d59d6 100%) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 3px 8px rgba(31, 111, 235, 0.4) !important;
        width: 100% !important;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 12px rgba(31, 111, 235, 0.6) !important;
    }
    
    /* Tabelas */
    div[data-testid="stDataFrame"] {
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        background-color: #161b22 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Arquivos para salvar os dados
ARQUIVO_CERTIDOES = "dados_certidoes.csv"
ARQUIVO_CONTRATOS = "dados_contratos.csv"

# Funções de carregamento e salvamento
def carregar_dados(arquivo, colunas):
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        if 'Vencimento' in df.columns:
            df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

# Inicializa os dados
if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_dados(ARQUIVO_CERTIDOES, ["Nome", "Link", "Vencimento"])
if 'contratos' not in st.session_state:
    st.session_state.contratos = carregar_dados(ARQUIVO_CONTRATOS, ["Cidade", "Contrato", "Modalidade", "Status"])

# --- MENU LATERAL DE NAVEGAÇÃO ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.markdown("<h2 style='color: #f0f6fc; font-size: 20px; font-weight:600;'>Menu Principal</h2>", unsafe_allow_html=True)
    opcao_menu = st.radio("Selecione a ferramenta:", ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"])

# --- PAGINA 1: SEPARADOR DE COMPROVANTES ---
if opcao_menu == "Separador de Comprovantes":
    st.markdown('<p class="main-title">📄 Separador de Comprovantes</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Divida múltiplos PDFs automaticamente por nome de favorecido</p>', unsafe_allow_html=True)
    
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
            st.success(f"🎉 Sucesso! {total_arquivos} arquivo(s) processado(s).")
            st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- PAGINA 2: CONTROLE DE CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.markdown('<p class="main-title">📋 Controle de Certidões</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Gerencie prazos de validades e links das certidões obrigatórias</p>', unsafe_allow_html=True)
    
    with st.form("form_certidao", clear_on_submit=True):
        st.subheader("➕ Cadastrar Nova Certidão")
        nome_cert = st.text_input("Nome da Certidão (Ex: FGTS, Municipal, Federal)")
        link_cert = st.text_input("Link da Certidão / Site de Emissão")
        venc_cert = st.date_input("Data de Vencimento", datetime.today().date())
        botao_cert = st.form_submit_button("Salvar Certidão")
        
    if botao_cert and nome_cert:
        nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
        st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
        salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
        st.success("Certidão cadastrada com sucesso!")
        st.rerun()
        
    st.write("---")
    st.subheader("🔍 Painel de Validades")
    df_cert = st.session_state.certidoes
    if not df_cert.empty:
        lista_exibicao = []
        hoje = datetime.today().date()
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
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True, hide_index=True)
        if st.button("⚠️ Apagar Todas as Certidões"):
            st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
            if os.path.exists(ARQUIVO_CERTIDOES): os.remove(ARQUIVO_CERTIDOES)
            st.rerun()
    else:
        st.info("Nenhuma certidão cadastrada.")

# --- PAGINA 3: CIDADES GANHAS (CONTRATOS) ---
else:
    st.markdown('<p class="main-title">🏙️ Cidades Ganhas & Contratos</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Lembrete diário para monitoramento de Diários Oficiais</p>', unsafe_allow_html=True)
    
    with st.form("form_contrato", clear_on_submit=True):
        st.subheader("➕ Adicionar Nova Cidade / Contrato Ganho")
        cidade = st.text_input("Cidade / Órgão Público (Ex: Salvador - BA, Prefeitura de Alagoinhas)")
        num_contrato = st.text_input("Número do Contrato ou Ata (Ex: 142/2026)")
        modalidade = st.selectbox("Modalidade da Licitação", [
            "Concorrência", "Concorrência Eletrônica", "Pregão Eletrônico", 
            "Pregão Presencial", "Dispensa de Licitação", "Inexigibilidade", 
