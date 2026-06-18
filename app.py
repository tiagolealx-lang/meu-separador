import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io, re, os
import pandas as pd
from datetime import datetime

# Configuração Base do Aplicativo com Tema Escuro Forçado
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide", initial_sidebar_state="expanded")

# --- DESIGN PREMIUM DARK MODE (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A !important; font-family: 'Segoe UI', Roboto, sans-serif; }
    section[data-testid="stSidebar"] { background-color: #1E293B !important; padding-top: 20px; border-right: 1px solid #334155 !important; }
    section[data-testid="stSidebar"] .stMarkdown p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span { color: #F8FAFC !important; font-weight: 600 !important; }
    .header-painel { font-size: 28px !important; font-weight: 700 !important; color: #F8FAFC !important; margin-top: 10px !important; }
    .sub-painel { font-size: 14px !important; color: #94A3B8 !important; margin-bottom: 25px !important; }
    .logo-box { background-color: #EF4444; color: white !important; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 18px; text-align: center; margin-bottom: 30px; }
    div[data-testid="stForm"], .stDropzone, div.block-container > div { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 25px !important; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important; margin-bottom: 25px !important; }
    label, p, h4 { color: #F1F5F9 !important; }
    .stDropzone { border: 2px dashed #475569 !important; background-color: #0F172A !important; }
    div.stButton > button { background-color: #2563EB !important; color: #FFFFFF !important; font-weight: 600 !important; border-radius: 8px !important; width: 100% !important; height: 48px; border: none !important; }
    div.stButton > button:hover { background-color: #1D4ED8 !important; }
    div[data-testid="stDataFrame"] { border-radius: 8px !important; border: 1px solid #334155 !important; background-color: #1E293B !important; }
    </style>
""", unsafe_allow_html=True)

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

with st.sidebar:
    st.markdown('<div class="logo-box">💼 Sistema Pro</div>', unsafe_allow_html=True)
    st.markdown("### Módulos de Operação")
    opcao_menu = st.radio(label="Navegação", options=["Separador e Conferência", "Controle de Certidões", "Cidades Ganhas (Contratos)"], label_visibility="collapsed")
    st.write("---")
    st.caption("Versão Corporativa 3.2 • Premium Dark")

# PÁGINA 1: SEPARADOR E CONFERÊNCIA COM EXCEL
if opcao_menu == "Separador e Conferência":
    st.markdown('<div class="header-painel">📄 Separador & Conferência Inteligente</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-painel">Envie os PDFs dos comprovantes e selecione a aba específica do seu Excel para realizar a conferência.</div>', unsafe_allow_html=True)
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.markdown("#### 📤 1. Arquivos de Comprovantes (PDF)")
        uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    with col_up2:
        st.markdown("#### 📊 2. Planilha de Conferência (Excel)")
        excel_file = st.file_uploader("Upload Excel", type=["xlsx"], accept_multiple_files=False, label_visibility="collapsed")

    # Sistema inteligente para ler as abas do Excel antes de processar
    aba_selecionada = None
    if excel_file is not None:
        try:
            xl = pd.ExcelFile(excel_file)
            abas_disponiveis = xl.sheet_names
            st.markdown("#### 📑 3. Selecione a Aba da Planilha para Conferir")
            aba_selecionada = st.selectbox("Escolha uma aba para analisar:", abas_disponiveis)
        except Exception as e:
            st.error(f"Erro ao ler as abas do arquivo Excel: {e}")

    def limpar_texto(t):
        return re.sub(r'[^a-zA-Z0-9]', '', str(t).upper().strip())

    def extrair_dados_pdf(texto):
        nome = "Nao_Encontrado"
        p_nomes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)"]
        for p in p_nomes:
            res = re.search(p, texto, re.IGNORECASE)
            if res:
                nome = re.sub(r'[\\/*?:"<>|]', "", res.group(1).strip())[:40]
                break
        valores = re.findall(r'(?:R\$\s*)?(\d+(?:\.\d{3})*,\d{2})', texto)
        valor_achado = valores[0] if valores else "0,00"
        contas = re.findall(r'(?:Conta|C/C|Agência/Conta):\s*([0-9Xx-]+)', texto, re.IGNORECASE)
        conta_achada = contas[0] if contas else "Nao_Encontrada"
        return nome, valor_achado, conta_achada

    if uploaded_files:
        st.write("")
        if st.button("🚀 Processar, Separar e Conferir com Aba Selecionada"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            barra = st.progress(0)
            total = len(uploaded_files)
            dados_extraidos_pdf = []
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
                    pdf_bytes = uploaded_file.read()
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as leitor_txt:
                        pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                        for i in range(len(leitor_txt.pages)):
                            txt = leitor_txt.pages[i].extract_text() or ""
                            nome, val, conta = extrair_dados_pdf(txt)
                            dados_extraidos_pdf.append({"Nome_PDF": nome, "Valor_PDF": val, "Conta_PDF": conta})
                            
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
            
            st.success("🎉 Separação dos PDFs concluída!")
            st.download_button("📥 Baixar Comprovantes Separados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")
            
            # Cruzamento de dados focado estritamente na aba escolhida
            if excel_file is not None and aba_selecionada is not None:
                st.write("---")
                st.markdown(f"### 📊 Relatório de Auditoria — Aba: `{aba_selecionada}`")
                try:
                    df_excel = pd.read_excel(excel_file, sheet_name=aba_selecionada)
                    colunas_necessarias = ['Nome', 'Conta', 'Valor']
                    if not all(col in df_excel.columns for col in colunas_necessarias):
                        st.error(f"Atenção: A aba '{aba_selecionada}' precisa ter exatamente as colunas: 'Nome', 'Conta' e 'Valor'")
                    else:
                        relatorio_final = []
                        for _, linha_ex in df_excel.iterrows():
                            ex_nome = str(linha_ex['Nome']).strip()
                            ex_conta = str(linha_ex['Conta']).strip()
                            try:
                                ex_valor = f"{float(linha_ex['Valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            except:
                                ex_valor = "0,00"
                            
                            status = "🔴 Não Encontrado"
                            for pdf_item in dados_extraidos_pdf:
                                nome_bate = limpar_texto(ex_nome) in limpar_texto(pdf_item["Nome_PDF"]) or limpar_texto(pdf_item["Nome_PDF"]) in limpar_texto(ex_nome)
                                valor_bate = limpar_texto(ex_valor) == limpar_texto(pdf_item["Valor_PDF"])
                                
                                if nome_bate and valor_bate:
                                    status = "🟢 Confirmado"
                                    break
                                elif nome_bate and not valor_bate:
                                    status = "🟡 Valor Divergente"
                                    break
                            
                            relatorio_final.append({
                                "Resultado": status,
                                "Nome Planilha": ex_nome,
                                "Conta Planilha": ex_conta,
                                "Valor Planilha": f"R$ {ex_valor}"
                            })
                        st.dataframe(pd.DataFrame(relatorio_final), use_container_width=True)
                except Exception as e:
