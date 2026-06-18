import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os
import pandas as pd
from datetime import datetime

# Configuração da página - Tema Escuro Elegante
st.set_page_config(page_title="Painel de Licitações Pro", layout="wide")

# Estilização CSS para transformar o design do app
st.markdown("""
    <style>
    /* Remover espaços exagerados no topo */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Customização dos Títulos */
    .main-title { font-size: 32px; font-weight: 800; color: #1E90FF; margin-bottom: 5px; }
    .subtitle { font-size: 16px; color: #888888; margin-bottom: 25px; }
    
    /* Cards de Estatísticas */
    .metric-card {
        background-color: #1E1E24;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E90FF;
        text-align: center;
    }
    
    /* Estilo dos Botões e Inputs */
    div.stButton > button:first-child {
        background-color: #1E90FF;
        color: white;
        border-radius: 6px;
        font-weight: bold;
        width: 100%;
        border: none;
        padding: 10px;
    }
    div.stButton > button:first-child:hover { background-color: #0077e6; }
    </style>
""", unsafe_allow_html=True)

# Arquivos de dados salvos
ARQUIVO_CERTIDOES = "dados_certidoes.csv"
ARQUIVO_CONTRATOS = "dados_contratos.csv"

def carregar_dados(arquivo, colunas):
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        if 'Vencimento' in df.columns:
            df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_dados(ARQUIVO_CERTIDOES, ["Nome", "Link", "Vencimento"])

if 'contratos' not in st.session_state:
    st.session_state.contratos = carregar_dados(ARQUIVO_CONTRATOS, ["Cidade", "Contrato", "Modalidade", "Status"])

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.title("💼 Sistema Pro")
    st.write("Escolha o módulo de operação:")
    opcao_menu = st.sidebar.selectbox(
        "Navegação", 
        ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"]
    )

# --- MODULO 1: SEPARADOR DE COMPROVANTES ---
if opcao_menu == "Separador de Comprovantes":
    st.markdown('<p class="main-title">📄 Separador de Comprovantes</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Divisão automática de lotes de PDFs pelo nome do favorecido</p>', unsafe_allow_html=True)
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
        if st.button("🚀 Iniciar Processamento"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            barra_progresso = st.progress(0)
            status_texto = st.empty()
            total_arquivos = len(uploaded_files)
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_texto.text(f"Lendo arquivo {idx+1} de {total_arquivos}...")
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
            st.success("🎉 Arquivos processados com sucesso!")
            st.download_button("📥 Baixar Comprovantes (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- MODULO 2: CONTROLE DE CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.markdown('<p class="main-title">📋 Controle de Certidões Regularizadas</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Gerencie prazos e links de emissão para evitar inabilitações</p>', unsafe_allow_html=True)
    st.write("---")
    
    col_form, col_lista = st.columns([1, 2], gap="large")
    
    with col_form:
        st.markdown("### ➕ Nova Certidão")
        with st.form("form_certidao", clear_on_submit=True):
            nome_cert = st.text_input("Nome do Documento")
            link_cert = st.text_input("Link de Emissão")
            venc_cert = st.date_input("Vencimento", datetime.today().date())
            botao_cert = st.form_submit_button("Salvar")
            
        if botao_cert and nome_cert:
            nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
            st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
            salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
            st.rerun()

    with col_lista:
        st.markdown("### 🔍 Documentos Salvos")
        df_cert = st.session_state.certidoes
        if not df_cert.empty:
            lista_exibicao = []
            hoje = datetime.today().date()
            for idx, linha in df_cert.iterrows():
                vencimento = linha["Vencimento"]
                if vencimento < hoje: status = "🔴 VENCIDA"
                elif (vencimento - hoje).days <= 10: status = f"🟡 ATENÇÃO ({ (vencimento - hoje).days }d)"
                else: status = "🟢 EM DIA"
                lista_exibicao.append({
                    "Status": status,
                    "Certidão": linha["Nome"],
                    "URL": linha["Link"],
                    "Vencimento": vencimento.strftime("%d/%m/%Y")
                })
            st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)
            if st.button("🗑️ Limpar Banco de Dados"):
                st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
                if os.path.exists(ARQUIVO_CERTIDOES): os.remove(ARQUIVO_CERTIDOES)
                st.rerun()
        else:
            st.info("Nenhuma certidão salva.")

# --- MODULO 3: CIDADES GANHAS ---
else:
    st.markdown('<p class="main-title">🏙️ Monitoramento de Cidades & Licitações Ganhas</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Controle diário de Diários Oficiais e execuções de atas</p>', unsafe_allow_html=True)
    st.write("---")
    
    # KPIs Rápidos no Topo
    df_cont = st.session_state.contratos
    total_ativos = len(df_cont[df_cont["Status"] == "Ativo"]) if not df_cont.empty else 0
    
    st.markdown(f"""
        <div class="metric-card">
            <span style='color: #888888; font-size: 14px;'>Contratos Ativos em Monitoramento</span><br>
            <span style='font-size: 28px; font-weight: bold; color: #1E90FF;'>{total_ativos} Cidades</span>
        </div>
        <br>
    """, unsafe_allow_html=True)
    
    col_form_cont, col_lista_cont = st.columns([1, 2], gap="large")
    
    with col_form_cont:
        st.markdown("### ➕ Registrar Contrato")
        with st.form("form_contrato", clear_on_submit=True):
            cidade = st.text_input("Cidade / Órgão")
            num_contrato = st.text_input("Nº do Contrato/Ata")
            modalidade = st.selectbox("Modalidade", [
                "Concorrência Eletrônica", "Concorrência", "Pregão Eletrônico", 
                "Pregão Presencial", "Dispensa de Licitação", "Inexigibilidade"
            ])
            status_contrato = st.selectbox("Status", ["Ativo", "Encerrado"])
            botao_contrato = st.form_submit_button("Salvar")
            
        if botao_contrato and cidade:
            novo_contrato = pd.DataFrame([{
                "Cidade": cidade, "Contrato": num_contrato, 
                "Modalidade": modalidade, "Status": status_contrato
            }])
            st.session_state.contratos = pd.concat([st.session_state.contratos, novo_contrato], ignore_index=True)
            salvar_dados(st.session_state.contratos, ARQUIVO_CONTRATOS)
            st.rerun()

    with col_lista_cont:
        st.markdown("### 📋 Alertas de Verificação Diária")
        if not df_cont.empty:
            lista_contratos_visuais = []
            for idx, linha in df_cont.iterrows():
                if linha["Status"] == "Ativo":
                    alerta_diario = f"👀 Olhar Diário Oficial de {linha['Cidade']}"
                    icone_status = "🟢 Ativo"
                else:
                    alerta_diario = "✅ Finalizado"
                    icone_status = "⚫ Encerrado"
