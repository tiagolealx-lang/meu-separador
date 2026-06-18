import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io, re, os
import pandas as pd
from datetime import datetime

# Configuração Base do Aplicativo com Tema Forçado Moderno
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide", initial_sidebar_state="expanded")

# --- DESIGN CORPORATIVO PROFISSIONAL (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA !important; font-family: sans-serif; }
    section[data-testid="stSidebar"] { background-color: #1E293B !important; padding-top: 20px; }
    section[data-testid="stSidebar"] .stMarkdown p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span { color: #F1F5F9 !important; font-weight: 500 !important; }
    .header-painel { font-size: 26px !important; font-weight: 700 !important; color: #0F172A !important; }
    .sub-painel { font-size: 14px !important; color: #64748B !important; margin-bottom: 20px !important; }
    .logo-box { background-color: #EF4444; color: white !important; padding: 10px; border-radius: 6px; font-weight: 700; font-size: 18px; text-align: center; margin-bottom: 25px; }
    div[data-testid="stForm"], .stDropzone, div.block-container > div { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; padding: 20px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; margin-bottom: 20px !important; }
    .stDropzone { border: 2px dashed #CBD5E1 !important; background-color: #F8FAFC !important; }
    div.stButton > button { background-color: #2563EB !important; color: white !important; font-weight: 600 !important; border-radius: 6px !important; width: 100% !important; height: 45px; border: none !important; }
    div.stButton > button:hover { background-color: #1D4ED8 !important; }
    div[data-testid="stDataFrame"] { border-radius: 8px !important; border: 1px solid #E2E8F0 !important; }
    </style>
""", unsafe_allow_html=True)

# Definição e Carregamento estável de arquivos de dados
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

# --- CONSTRUÇÃO DA SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-box">💼 Sistema Pro</div>', unsafe_allow_html=True)
    st.markdown("### Módulos de Operação")
    opcao_menu = st.radio(
        label="Navegação",
        options=["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"],
        label_visibility="collapsed"
    )
    st.write("---")
    st.caption("Versão Corporativa 2.5")

# --- LÓGICA DO CONTEÚDO PRINCIPAL ---

# PÁGINA 1: SEPARADOR
if opcao_menu == "Separador de Comprovantes":
    st.markdown('<div class="header-painel">📄 Separador Inteligente de Comprovantes</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-painel">Divisão otimizada de lotes de PDFs integrados através da extração nominal automatizada do favorecido.</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Upload", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")

    def extrair_nome(texto):
        padroes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)"]
        for p in padroes:
            res = re.search(p, texto, re.IGNORECASE)
            if res: return re.sub(r'[\\/*?:"<>|]', "", res.group(1).strip())[:40]
        return "Favorecido_Nao_Encontrado"

    if uploaded_files:
        if st.button("🚀 Iniciar Separação de Arquivos"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            barra = st.progress(0)
            total = len(uploaded_files)
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
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
                    barra.progress((idx + 1) / total)
            st.success("🎉 Processado com sucesso!")
            st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# PÁGINA 2: CERTIDÕES
elif opcao_menu == "Controle de Certidões":
    st.markdown('<div class="header-painel">📋 Painel de Controle de Certidões</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-painel">Gerencie a validade de certidões federais, estaduais e municipais.</div>', unsafe_allow_html=True)
    
    with st.form("form_certidao", clear_on_submit=True):
        st.markdown("#### ➕ Cadastrar Nova Certidão")
        nome_cert = st.text_input("Nome/Órgão Emissor")
        link_cert = st.text_input("URL / Link Direto de Acesso")
        venc_cert = st.date_input("Data de Vencimento Oficial", datetime.today().date())
        botao_cert = st.form_submit_button("Salvar no Banco de Dados")
        
    if botao_cert and nome_cert:
        nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
        st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
        salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
        st.success("Certidão salva!")
        st.rerun()
        
    st.write("##")
    st.markdown("#### 🔍 Certidões Cadastradas")
    df_cert = st.session_state.certidoes
    if not df_cert.empty:
        lista_exibicao = []
        hoje = datetime.today().date()
        for idx, row in df_cert.iterrows():
            vencimento = row["Vencimento"]
            status = "🔴 VENCIDA" if vencimento < hoje else (f"🟡 ATENÇÃO ({(vencimento - hoje).days} dias)" if (vencimento - hoje).days <= 10 else "🟢 EM DIA")
            lista_exibicao.append({"Status": status, "Nome da Certidão": row["Nome"], "Link de Acesso": row["Link"], "Data de Vencimento": vencimento.strftime("%d/%m/%Y")})
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)
        if st.button("⚠️ Apagar Todas as Certidões"):
            st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
            if os.path.exists(ARQUIVO_CERTIDOES): os.remove(ARQUIVO_CERTIDOES)
            st.rerun()
    else:
        st.info("Nenhuma certidão monitorada.")

# PÁGINA 3: CIDADES GANHAS
else:
    st.markdown('<div class="header-painel">🏙️ Monitoramento de Cidades Ganhas & Atas</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-painel">Controle de praças arrematadas com lembretes para consulta de Diários Oficiais locais.</div>', unsafe_allow_html=True)
    
    with st.form("form_contrato", clear_on_submit=True):
        st.markdown("#### ➕ Registrar Novo Contrato / Localidade")
        cidade = st.text_input("Município / Estado / Órgão Público")
        num_contrato = st.text_input("Identificação do Contrato ou Ata")
        modalidades_lista = ["Concorrência Eletrônica", "Pregão Eletrônico", "Dispensa de Licitação", "Concorrência", "Pregão Presencial", "Inexigibilidade", "Tomada de Preços", "Leilão"]
        modalidade = st.selectbox("Modalidade da Licitação Relacionada", modalidades_lista)
        status_contrato = st.selectbox("Situação Jurídica do Contrato", ["Ativo", "Encerrado"])
        botao_contrato = st.form_submit_button("Salvar Registro Licitatório")
        
    if botao_contrato and cidade:
        novo_contrato = pd.DataFrame([{"Cidade": cidade, "Contrato": num_contrato, "Modalidade": modalidade, "Status": status_contrato}])
        st.session_state.contratos = pd.concat([st.session_state.contratos, novo_contrato], ignore_index=True)
        salvar_dados(st.session_state.contratos, ARQUIVO_CONTRATOS)
        st.success("Contrato registrado!")
        st.rerun()
        
    st.write("##")
    st.markdown("#### 📋 Relatório de Verificação de Diários Oficiais")
    df_cont = st.session_state.contratos
    if not df_cont.empty:
        lista_contratos_visuais = []
        for idx, row in df_cont.iterrows():
            alerta_diario = f"👀 Checar Diário Oficial de {row['Cidade']}" if row["Status"] == "Ativo" else "✅ Finalizado"
            icone_status = "🟢 Ativo" if row["Status"] == "Ativo" else "⚫ Encerrado"
