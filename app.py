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

# Inicializa os dados no sistema
if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_dados(ARQUIVO_CERTIDOES, ["Nome", "Link", "Vencimento"])

if 'contratos' not in st.session_state:
    st.session_state.contratos = carregar_dados(ARQUIVO_CONTRATOS, ["Cidade", "Contrato", "Modalidade", "Status"])

# --- MENU LATERAL ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.title("Painel de Controle")
    st.write("Escolha a ferramenta:")
    opcao_menu = st.radio("Menu Principal", ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"])

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
            st.success(f"🎉 Sucesso! {total_arquivos} arquivo(s) processado(s).")
            st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- PAGINA 2: CONTROLE DE CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.markdown("<h1 style='text-align: center;'>📋 Controle de Certidões</h1>", unsafe_allow_html=True)
    st.write("---")
    
    st.subheader("➕ Cadastrar Nova Certidão")
    with st.form("form_certidao", clear_on_submit=True):
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
    st.subheader("🔍 Minhas Certidões Salvas")
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
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)
        if st.button("⚠️ Apagar Todas as Certidões"):
            st.session_state.certidoes = pd.DataFrame(columns=["Nome", "Link", "Vencimento"])
            if os.path.exists(ARQUIVO_CERTIDOES): os.remove(ARQUIVO_CERTIDOES)
            st.rerun()
    else:
        st.info("Nenhuma certidão cadastrada.")

# --- PAGINA 3: CIDADES GANHAS (CONTRATOS E DIÁRIOS OFICIAIS) ---
else:
    st.markdown("<h1 style='text-align: center;'>🏙️ Cidades Ganhas & Contratos</h1>", unsafe_allow_html=True)
    st.write("Lembrete diário para monitorar os Diários Oficiais das cidades com contratos ativos.")
    st.write("---")
    
    st.subheader("➕ Adicionar Nova Cidade / Contrato Ganho")
    with st.form("form_contrato", clear_on_submit=True):
        cidade = st.text_input("Cidade / Órgão Público (Ex: Salvador - BA, Prefeitura de Alagoinhas)")
        num_contrato = st.text_input("Número do Contrato ou Ata (Ex: 142/2026)")
        
        modalidade = st.selectbox("Modalidade da Licitação", [
            "Concorrência", 
            "Concorrência Eletrônica", 
            "Pregão Eletrônico", 
            "Pregão Presencial", 
            "Dispensa de Licitação", 
            "Inexigibilidade", 
            "Tomada de Preços", 
            "Leilão"
        ])
        
        status_contrato = st.selectbox("Status Atual do Contrato", ["Ativo", "Encerrado"])
        botao_contrato = st.form_submit_button("Salvar Registro")
        
    if botao_contrato and cidade:
        novo_contrato = pd.DataFrame([{
            "Cidade": cidade, 
            "Contrato": num_contrato, 
            "Modalidade": modalidade, 
            "Status": status_contrato
        }])
        st.session_state.contratos = pd.concat([st.session_state.contratos, novo_contrato], ignore_index=True)
        salvar_dados(st.session_state.contratos, ARQUIVO_CONTRATOS)
        st.success("Cidade e contrato salvos com sucesso!")
        st.rerun()
        
    st.write("---")
    st.subheader("📋 Cidades Ativas para Olhar Diário Oficial")
    
    df_cont = st.session_state.contratos
    if not df_cont.empty:
        lista_contratos_visuais = []
        for idx, linha in df_cont.iterrows():
            # Cria o texto de alerta apenas para contratos ativos
            if linha["Status"] == "Ativo":
                alerta_diario = f"👀 Olhar Diário Oficial de {linha['Cidade']}"
                icone_status = "🟢 Ativo"
            else:
                alerta_diario = "✅ Contrato Concluído"
                icone_status = "⚫ Encerrado"
                
            lista_contratos_visuais.append({
                "Acompanhamento": alerta_diario,
                "Status": icone_status,
                "Cidade / Órgão": linha["Cidade"],
                "Nº do Contrato": linha["Contrato"],
                "Modalidade": linha["Modalidade"]
            })
            
        st.dataframe(pd.DataFrame(lista_contratos_visuais), use_container_width=True)
        
        if st.button("⚠️ Apagar Histórico de Cidades"):
            st.session_state.contratos = pd.DataFrame(columns=["Cidade", "Contrato", "Modalidade", "Status"])
            if os.path.exists(ARQUIVO_CONTRATOS): os.remove(ARQUIVO_CONTRATOS)
            st.rerun()
    else:
        st.info("Nenhuma cidade ou contrato cadastrado ainda.")
