import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io, re, os
import pandas as pd
from datetime import datetime

# Configuração estável e limpa do painel
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide")

# Inicialização e carregamento seguro dos bancos de dados
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

# --- FUNÇÕES AUXILIARES ---
def limpar_texto(t):
    return re.sub(r'[^a-zA-Z0-9]', '', str(t).upper().strip())

def extrair_dados_pdf(texto):
    nome = "Favorecido_Nao_Encontrado"
    p_nomes = [r"Favorecido:\s*([^\n]+)", r"Nome:\s*([^\n]+)", r"Recebedor:\s*([^\n]+)", r"Nome do Favorecido:\s*([^\n]+)"]
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

def processar_auditoria_excel(excel_file, aba_selecionada, dados_extraidos_pdf):
    try:
        df_excel = pd.read_excel(excel_file, sheet_name=aba_selecionada)
        colunas_necessarias = ['Nome', 'Conta', 'Valor']
        if not all(col in df_excel.columns for col in colunas_necessarias):
            st.error(f"Atenção: A aba '{aba_selecionada}' precisa ter as colunas: 'Nome', 'Conta' e 'Valor'")
            return
        
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
    except:
        st.error("Erro ao cruzar os dados com a planilha.")

# --- BARRA LATERAL NATIVA (SIDEBAR) ---
with st.sidebar:
    st.title("💼 Sistema Pro")
    st.write("Escolha o módulo de operação:")
    opcao_menu = st.sidebar.radio(
        "Navegação", 
        ["Separador e Conferência", "Controle de Certidões", "Cidades Ganhas (Contratos)"]
    )
    st.write("---")
    st.caption("Versão 3.7 • Correção de Nomes")

# --- CONTEÚDO PRINCIPAL ---

if opcao_menu == "Separador e Conferência":
    st.title("📄 Separador & Conferência Inteligente")
    st.write("Envie os PDFs e selecione a aba específica do seu Excel para realizar a auditoria automática.")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        st.subheader("📤 1. Comprovantes (PDF)")
        uploaded_files = st.file_uploader("Selecione os arquivos PDF", type=["pdf"], accept_multiple_files=True)
    with col_up2:
        st.subheader("📊 2. Planilha (Excel)")
        excel_file = st.file_uploader("Selecione a planilha .xlsx", type=["xlsx"], accept_multiple_files=False)

    aba_selecionada = None
    if excel_file is not None:
        try:
            xl = pd.ExcelFile(excel_file)
            abas_disponiveis = xl.sheet_names
            st.subheader("📑 3. Escolha a Aba da Planilha")
            aba_selecionada = st.selectbox("Selecione a aba desejada para conferência:", abas_disponiveis)
        except:
            st.error("Erro ao carregar abas do arquivo Excel.")

    if uploaded_files:
        st.write("")
        if st.button("🚀 Processar, Separar e Conferir"):
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
            
            st.success("🎉 Separação concluída com sucesso!")
            st.download_button("📥 Baixar Arquivos Organizados (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")
            
            if excel_file is not None and aba_selecionada is not None:
                st.write("---")
                st.subheader(f"📊 Relatório de Auditoria — Aba: {aba_selecionada}")
                processar_auditoria_excel(excel_file, aba_selecionada, dados_extraidos_pdf)

elif opcao_menu == "Controle de Certidões":
    st.title("📋 Painel de Controle de Certidões")
    with st.form("form_certidao", clear_on_submit=True):
        st.write("### ➕ Cadastrar Nova Certidão")
        nome_cert = st.text_input("Nome / Órgão Emissor")
        link_cert = st.text_input("URL / Link Direto de Acesso")
        venc_cert = st.date_input("Data de Vencimento Oficial", datetime.today().date())
        botao_cert = st.form_submit_button("Salvar Certidão")
        
    if botao_cert and nome_cert:
        nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
        st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
        salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
        st.success("Certidão salva com sucesso!")
        st.rerun()
        
    st.write("---")
    st.write("### 🔍 Certidões Monitoradas")
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
    st.title("🏙️ Monitoramento de Cidades Ganhas & Atas")
    with st.form("form_contrato", clear_on_submit=True):
        st.write("### ➕ Registrar Novo Contrato / Localidade")
        cidade = st.text_input("Município / Estado / Órgão Público")
        num_contrato = st.text_input("Identificação do Contrato ou Ata")
        modalidade = st.selectbox("Modalidade", ["Concorrência Eletrônica", "Pregão Eletrônico", "Dispensa de Licitação", "Concorrência", "Pregão Presencial"])
        status_contrato = st.selectbox("Situação", ["Ativo", "Encerrado"])
        botao_contrato = st.form_submit_button("Salvar Registro Licitatório")
        
    if botao_contrato and cidade:
