import streamlit as st
import pdfplumber
from pypdf import PdfWriter, PdfReader
import io
import re
import os

# Configuração estável do painel principal
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide")

# Arquivos de banco de dados locais para salvar suas informações
ARQUIVO_CERTIDOES = "dados_certidoes.csv"
ARQUIVO_CONTRATOS = "dados_contratos.csv"

def carregar_dados(arquivo, colunas):
    import pandas as pd
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        if 'Vencimento' in df.columns:
            df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

# Inicializa as tabelas na memória do sistema
if 'certidoes' not in st.session_state:
    st.session_state.certidoes = carregar_dados(ARQUIVO_CERTIDOES, ["Nome", "Link", "Vencimento"])
if 'contratos' not in st.session_state:
    st.session_state.contratos = carregar_dados(ARQUIVO_CONTRATOS, ["Cidade", "Contrato", "Modalidade", "Status"])

# --- FUNÇÕES DO SEPARADOR DE COMPROVANTES ---
def buscar_nome_no_texto(texto):
    if not texto:
        return None
    padroes = [
        r"Favorecido:\s*([^\n]+)",
        r"Nome do favorecido:\s*([^\n]+)",
        r"Recebedor:\s*([^\n]+)",
        r"Nome:\s*([^\n]+)",
        r"BENEFICIÁRIO:\s*([^\n]+)"
    ]
    for padrao in padroes:
        resultado = re.search(padrao, texto, re.IGNORECASE)
        if resultado:
            nome = resultado.group(1).strip()
            nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
            return nome_limpo[:50].strip().upper()
    return None

# --- BARRA LATERAL NATIVA DE NAVEGAÇÃO ---
with st.sidebar:
    st.title("💼 Sistema Pro")
    st.write("Escolha o módulo de operação:")
    opcao_menu = st.radio(
        "Navegação", 
        ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"]
    )
    st.write("---")
    st.caption("Versão 4.5 • Sistema Completo")

# --- PÁGINA 1: SEPARADOR DE COMPROVANTES ---
if opcao_menu == "Separador de Comprovantes":
    st.title("📄 Separador Automático de Comprovantes")
    st.write("Insira o seu PDF para separar as páginas pelo nome puro do favorecido (Suporta Bradesco e Banco do Brasil).")
    
    uploaded_file = st.file_uploader("Escolha o arquivo PDF", type=["pdf"])

    if uploaded_file is not None:
        pdf_bytes = uploaded_file.read()
        
        if st.button("Processar e Separar Comprovantes"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf_leitor_texto:
                    pdf_recortador = PdfReader(io.BytesIO(pdf_bytes))
                    total_paginas = len(pdf_leitor_texto.pages)
                    barra_progresso = st.progress(0)
                    
                    for i in range(total_paginas):
                        # Método 1: Texto Direto (Bradesco)
                        pagina_texto = pdf_leitor_texto.pages[i].extract_text()
                        nome_favorecido = buscar_nome_no_texto(pagina_texto)
                        
                        # Método 2: Imagem/OCR (Banco do Brasil)
                        if not nome_favorecido:
                            try:
                                from pdf2image import convert_from_bytes
                                import pytesseract
                                imagens = convert_from_bytes(pdf_bytes, first_page=i+1, last_page=i+1)
                                if imagens:
                                    texto_da_imagem = pytesseract.image_to_string(imagens, lang='por')
                                    nome_favorecido = buscar_nome_no_texto(texto_da_imagem)
                            except:
                                pass
                        
                        if not nome_favorecido:
                            nome_favorecido = f"FAVORECIDO_NAO_ENCONTRADO_PAG_{i+1}"
                        
                        if nome_favorecido in nomes_contagem:
                            nomes_contagem[nome_favorecido] += 1
                            nome_arquivo = f"{nome_favorecido} {nomes_contagem[nome_favorecido]}.pdf"
                        else:
                            nomes_contagem[nome_favorecido] = 1
                            nome_arquivo = f"{nome_favorecido}.pdf"
                        
                        escritor = PdfWriter()
                        escritor.add_page(pdf_recortador.pages[i])
                        
                        pdf_pagina_buffer = io.BytesIO()
                        escritor.write(pdf_pagina_buffer)
                        pdf_pagina_buffer.seek(0)
                        
                        zip_file.writestr(nome_arquivo, pdf_pagina_buffer.read())
                        barra_progresso.progress((i + 1) / total_paginas)
                        
            st.success("🎉 Todos os comprovantes foram processados!")
            st.download_button(
                label="📥 Baixar Comprovantes Separados (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="comprovantes_organizados.zip",
                mime="application/zip"
            )

# --- PÁGINA 2: CONTROLE DE CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    import pandas as pd
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

# --- PÁGINA 3: CIDADES GANHAS ---
else:
    import pandas as pd
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
