import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io, re, os
import pandas as pd
from datetime import datetime

# Configuração Base estável do painel
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide")

# Inicialização e carregamento estável dos bancos de dados salvos
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

# --- FUNÇÃO AVANÇADA DE EXTRAÇÃO DE NOME ---
def extrair_nome(texto):
    if not texto or not texto.strip():
        return "Comprovante_Sem_Texto"
        
    # 1. Tenta buscar pelas palavras-chave tradicionais e variações comuns de bancos
    padroes = [
        r"(?:Favorecido|Nome do Favorecido|Recebedor|Beneficiário|Nome|Destinatário|Pessoa):\s*([^\n]+)",
        r"(?:Para|Pagar para|Crédito para):\s*([^\n]+)"
    ]
    
    for p in padroes:
        res = re.search(p, texto, re.IGNORECASE)
        if res:
            nome = res.group(1).strip()
            nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
            if len(nome_limpo) > 2:
                return nome_limpo[:40].strip()
                
    # 2. Se não achou palavra-chave, pega as primeiras linhas que pareçam um nome (letras maiúsculas)
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    for linha in linhas[:5]:  # Analisa as primeiras 5 linhas do documento
        # Se a linha tiver palavras grandes em maiúsculo (comum em nomes de pessoas/empresas no topo)
        if re.match(r'^[A-ZÁÉÍÓÚÂÊÔÀ🎨 ]+$', linha) and len(linha) > 5:
            nome_limpo = re.sub(r'[\\/*?:"<>|]', "", linha)
            return nome_limpo[:40].strip()
            
    # 3. Última tentativa: pega a segunda ou terceira linha do PDF (onde os bancos costumam colocar o cabeçalho)
    if len(linhas) > 1:
        nome_linha = linhas[1] if len(linhas) > 1 else linhas[0]
        nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome_linha)
        return nome_limpo[:40].strip()
        
    return "Favorecido_Nao_Detectado"

# --- CONSTRUÇÃO DO MENU LATERAL ---
with st.sidebar:
    st.title("💼 Sistema Pro")
    st.write("Abas de operação do painel:")
    opcao_menu = st.radio(
        "Navegação", 
        ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"],
        label_visibility="collapsed"
    )
    st.write("---")
    st.caption("Versão 4.2 • Correção de Leitura")

# --- CONTEÚDO DA PÁGINA 1: APENAS SEPARADOR ---
if opcao_menu == "Separador de Comprovantes":
    st.title("📄 Separador Inteligente de Comprovantes")
    st.write("Insira um ou mais arquivos PDF para recortar e renomear automaticamente pelo nome do favorecido.")
    
    uploaded_files = st.file_uploader("Selecione os arquivos PDF", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        st.write("")
        if st.button("🚀 Iniciar Processamento e Salvar"):
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
            
            st.success("🎉 Processamento concluído com sucesso!")
            st.download_button("📥 Baixar Comprovantes Salvos (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- CONTEÚDO DA PÁGINA 2: CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.title("📋 Painel de Controle de Certidões")
    
    st.write("### ➕ Cadastrar Nova Certidão")
    nome_cert = st.text_input("Nome / Órgão Emissor")
    link_cert = st.text_input("URL / Link Direto de Acesso")
    venc_cert = st.date_input("Data de Vencimento Oficial", datetime.today().date())
    
    if st.button("Salvar Certidão no Banco"):
        if nome_cert:
            nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
            st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
            salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
            st.success("Certidão salva com sucesso!")
            st.rerun()
        else:
            st.error("Digite o nome da certidão.")
        
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
        st.info("Nenhuma certidão cadastrada.")

# --- CONTEÚDO DA PÁGINA 3: CIDADES GANHAS ---
else:
    st.title("🏙️ Monitoramento de Cidades Ganhas & Atas")
    
    st.write("### ➕ Registrar Novo Contrato / Localidade")
    cidade = st.text_input("Município / Estado / Órgão Público")
    num_contrato = st.text_input("Identificação do Contrato ou Ata")
    modalidade = st.selectbox("Modalidade", ["Concorrência Eletrônica", "Pregão Eletrônico", "Dispensa de Licitação", "Concorrência", "Pregão Presencial"])
    status_contrato = st.selectbox("Situação", ["Ativo", "Encerrado"])
    
    if st.button("Salvar Registro Licitatório"):
        if cidade:
            novo_contrato = pd.DataFrame([{"Cidade": cidade, "Contrato": num_contrato, "Modalidade": modalidade, "Status": status_contrato}])
            st.session_state.contratos = pd.concat([st.session_state.contratos, novo_contrato], ignore_index=True)
            salvar_dados(st.session_state.contratos, ARQUIVO_CONTRATOS)
            st.success("Contrato registrado!")
            st.rerun()
        else:
            st.error("Digite o nome da cidade.")
        
    st.write("---")
    st.write("### 📋 Relatório de Verificação de Diários Oficiais")
    df_cont = st.session_state.contratos
    if not df_cont.empty:
        lista_contratos_visuais = []
        for idx, row in df_cont.iterrows():
            alerta_diario = f"👀 Checar Diário Oficial de {row['Cidade']}" if row["Status"] == "Ativo" else "✅ Finalizado"
            lista_contratos_visuais.append({"Ação Diária Obrigatória": alerta_diario, "Status": "🟢 Ativo" if row["Status"] == "Ativo" else "⚫ Encerrado", "Cidade / Órgão": row["Cidade"], "Nº do Contrato": row["Contrato"]})
        st.dataframe(pd.DataFrame(lista_contratos_visuais), use_container_width=True)
        
        if st.button("⚠️ Apagar Lista de Contratos"):
            st.session_state.contratos = pd.DataFrame(columns=["Cidade", "Contrato", "Modalidade", "Status"])
            if os.path.exists(ARQUIVO_CONTRATOS): os.remove(ARQUIVO_CONTRATOS)
            st.rerun()
    else:
        st.info("Nenhuma praça registrada para acompanhamento.")
