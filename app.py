import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA E DO TEMA CORPORATIVO CLARO
st.set_page_config(
    page_title="Sistema Pro - Gestão Integrada", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização CSS Avançada para forçar um ambiente claro, limpo e executivo
st.markdown("""
    <style>
    /* Forçar fundo claro e fontes profissionais */
    .stApp {
        background-color: #F8F9FA;
        color: #212529;
    }
    /* Estilização dos blocos e caixas (Cards) */
    .card-indicador {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0056B3;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    .card-indicador h3 {
        margin: 0;
        font-size: 14px;
        color: #6C757D;
        text-transform: uppercase;
    }
    .card-indicador p {
        margin: 5px 0 0 0;
        font-size: 28px;
        font-weight: bold;
        color: #1C1C1E;
    }
    /* Alinhamento do título principal para evitar cortes */
    .header-painel {
        padding-top: 5px;
        padding-bottom: 20px;
        border-bottom: 2px solid #E9ECEF;
        margin-bottom: 25px;
    }
    .header-painel h1 {
        color: #002D62;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .header-painel p {
        color: #495057;
        font-size: 14px;
        margin: 0;
    }
    /* Customização de Botões */
    div.stButton > button:first-child {
        background-color: #0056B3;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #004085;
        color: white;
    }
    /* Customização do Menu Lateral */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E9ECEF;
    }
    section[data-testid="stSidebar"] h1 {
        color: #002D62 !important;
        font-size: 20px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Nomes dos arquivos de persistência de dados
ARQUIVO_CERTIDOES = "dados_certidoes.csv"
ARQUIVO_CONTRATOS = "dados_contratos.csv"

# Funções auxiliares para leitura e escrita dos bancos de dados locais (CSV)
def carregar_dados(arquivo, colunas):
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        if 'Vencimento' in df.columns:
            df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

# Inicialização segura dos estados das tabelas
if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_dados(ARQUIVO_CERTIDOES, ["Nome", "Link", "Vencimento"])

if 'contratos' not in st.session_state:
    st.session_state.contratos = carregar_dados(ARQUIVO_CONTRATOS, ["Cidade", "Contrato", "Modalidade", "Status"])

# --- MENU LATERAL DE NAVEGAÇÃO PRO ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h2 style='color: #0056B3; font-weight: bold;'>💼 Sistema Pro</h2>", unsafe_allow_html=True)
    
    st.write("---")
    st.markdown("### 🗺️ Módulos de Operação")
    opcao_menu = st.selectbox(
        "Selecione a ferramenta desejada:", 
        ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas & Contratos"]
    )
    st.write("---")
    st.markdown("<p style='font-size: 11px; color: #9A9A9A; text-align: center;'>Versão Corporate 2026</p>", unsafe_allow_html=True)

# --- MÓDULO 1: SEPARADOR DE COMPROVANTES ---
if opcao_menu == "Separador de Comprovantes":
    st.markdown("""
        <div class='header-painel'>
            <h1>📄 Separador Inteligente de Comprovantes</h1>
            <p>Divisão otimizada de lotes de PDFs integrados através da extração nominal automatizada do favorecido.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Organização em containers brancos limpos
    with st.container():
        st.markdown("### 📤 Upload de Arquivos")
        uploaded_files = st.file_uploader("Arraste seus PDFs consolidados ou clique para selecionar múltiplos arquivos:", type=["pdf"], accept_multiple_files=True)

    def extrair_nome(texto):
        padroes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)"]
        for p in padroes:
            res = re.search(p, texto, re.IGNORECASE)
            if res:
                return re.sub(r'[\\/*?:"<>|]', "", res.group(1).strip())[:40]
        return "Favorecido_Nao_Encontrado"

    if uploaded_files:
        st.write("---")
        if st.button("🚀 Iniciar Processamento dos Documentos"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            barra_progresso = st.progress(0)
            status_texto = st.empty()
            total_arquivos = len(uploaded_files)
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_texto.text(f"Analisando estrutura do documento {idx+1} de {total_arquivos}...")
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
            st.success(f"🎉 Processamento concluído com êxito! {total_arquivos} lote(s) mapeado(s).")
            st.download_button("📥 Baixar Arquivos Separados (.ZIP)", zip_buffer.getvalue(), "comprovantes_organizados.zip", "application/zip")

# --- MÓDULO 2: CONTROLE DE CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.markdown("""
        <div class='header-painel'>
            <h1>📋 Gerenciamento de Certidões Negativas</h1>
            <p>Monitore prazos de validade regulatórios para evitar inabilitações preventivas em certames públicos.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_form, col_espacio = st.columns([2, 1])
    with col_form:
        st.markdown("### ➕ Cadastrar Certidão")
        with st.form("form_certidao", clear_on_submit=True):
            nome_cert = st.text_input("Nome do Documento / Certidão (Ex: FGTS, Receita Federal)")
            link_cert = st.text_input("URL / Link Direto para Emissão Rápida")
            venc_cert = st.date_input("Data Limite de Vencimento", datetime.today().date())
            botao_cert = st.form_submit_button("Salvar no Banco de Dados")
            
        if botao_cert and nome_cert:
            nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
            st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
            salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
            st.success("Certidão registrada no painel!")
            st.rerun()
            
    st.write("---")
    st.markdown("### 🔍 Histórico de Regularidade")
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
                "Status Operacional": status,
                "Nome do Documento": linha["Nome"],
                "Link de Acesso": linha["Link"],
                "Data de Vencimento": vencimento.strftime("%d/%m/%Y")
            })
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)
        
        if st.button("⚠️ Limpar Histórico de Certidões"):
            st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
            if os.path.exists(ARQUIVO_CERTIDOES): os.remove(ARQUIVO_CERTIDOES)
            st.rerun()
    else:
        st.info("Nenhum documento regulatório cadastrado até o momento.")

# --- MÓDULO 3: CIDADES GANHAS & CONTRATOS ---
else:
    st.markdown("""
        <div class='header-painel'>
            <h1>🏙️ Painel de Contratos Ganhos & Diários Oficiais</h1>
            <p>Controle estratégico de praças homologadas e lembretes imperativos de monitoramento de publicações de Diários Oficiais.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- PAINEL EXECUTIVO DE INDICADORES (CARDS PROFISSIONAIS) ---
