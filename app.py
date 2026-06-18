import streamlit as st
from pypdf import PdfWriter, PdfReader
import io
import re
import os
import pandas as pd
from datetime import datetime

# Configuração Base do Aplicativo
st.set_page_config(page_title="Sistema Pro - Licitações", layout="wide")

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

# --- EXTRATOR DIRETO APENAS DO NOME DO FAVORECIDO ---
def extrair_nome_comprovante(pagina_pdf):
    try:
        texto = pagina_pdf.extract_text()
        if not texto:
            return None
            
        # Padrões diretos para capturar apenas o que vem após a palavra indicadora
        padroes = [
            r"Favorecido:\s*([^\n]+)",
            r"Nome do Favorecido:\s*([^\n]+)",
            r"Nome:\s*([^\n]+)",
            r"Recebedor:\s*([^\n]+)",
            r"Beneficiário:\s*([^\n]+)"
        ]
        
        for padrao in padroes:
            resultado = re.search(padrao, texto, re.IGNORECASE)
            if resultado:
                nome = resultado.group(1).strip()
                # Remove apenas caracteres proibidos pelo Windows em nomes de arquivos (Ex: / \ * ?)
                nome_limpo = re.sub(r'[\\/*?:"<>|]', "", nome)
                if len(nome_limpo) > 2:
                    return nome_limpo.strip().upper()
    except:
        pass
    return None

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("💼 Sistema Pro")
    opcao_menu = st.radio("Navegação", ["Separador de Comprovantes", "Controle de Certidões", "Cidades Ganhas (Contratos)"])

# --- PÁGINA 1: SEPARADOR ---
if opcao_menu == "Separador de Comprovantes":
    st.title("📄 Separador Inteligente de Comprovantes")
    st.write("Recorte de PDFs em lote com identificação e renomeação automática de favorecidos.")
    
    uploaded_files = st.file_uploader("Selecione os arquivos PDF", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 Iniciar Processamento e Salvar"):
            import zipfile
            zip_buffer = io.BytesIO()
            nomes_contagem = {}
            barra = st.progress(0)
            total = len(uploaded_files)
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
                    pdf_bytes = uploaded_file.read()
                    leitor = PdfReader(io.BytesIO(pdf_bytes))
                    total_paginas = len(leitor.pages)
                    
                    for i in range(total_paginas):
                        pagina = leitor.pages[i]
                        nome = extrair_nome_comprovante(pagina)
                        
                        # Se não achar de jeito nenhum, coloca um aviso padrão temporário
                        if not nome:
                            nome = f"FAVORECIDO_NAO_ENCONTRADO_PAG_{i+1}"
                        
                        # Se o nome já existir no lote, apenas adiciona o número para não sobrescrever
                        if nome in nomes_contagem:
                            nomes_contagem[nome] += 1
                            nome_final = f"{nome} {nomes_contagem[nome]}"
                        else:
                            nomes_contagem[nome] = 1
                            nome_final = nome
                        
                        escritor = PdfWriter()
                        escritor.add_page(pagina)
                        pag_buf = io.BytesIO()
                        escritor.write(pag_buf)
                        pag_buf.seek(0)
                        zip_file.writestr(f"{nome_final}.pdf", pag_buf.read())
                        
                    barra.progress((idx + 1) / total)
            
            st.success("🎉 Processamento concluído!")
            st.download_button("📥 Baixar Comprovantes Salvos (.ZIP)", zip_buffer.getvalue(), "comprovantes.zip", "application/zip")

# --- PÁGINA 2: CERTIDÕES ---
elif opcao_menu == "Controle de Certidões":
    st.title("📋 Painel de Controle de Certidões")
    nome_cert = st.text_input("Nome / Órgão Emissor")
    link_cert = st.text_input("URL / Link Direto de Acesso")
    venc_cert = st.date_input("Data de Vencimento Oficial", datetime.today().date())
    
    if st.button("Salvar Certidão no Banco"):
        if nome_cert:
            nova_cert = pd.DataFrame([{"Nome": nome_cert, "Link": link_cert, "Vencimento": venc_cert}])
            st.session_state.certidoes = pd.concat([st.session_state.certidoes, nova_cert], ignore_index=True)
            salvar_dados(st.session_state.certidoes, ARQUIVO_CERTIDOES)
            st.success("Certidão salva!")
            st.rerun()
            
    df_cert = st.session_state.certidoes
    if not df_cert.empty:
        lista_exibicao = []
        hoje = datetime.today().date()
        for idx, row in df_cert.iterrows():
            vencimento = row["Vencimento"]
            status = "🔴 VENCIDA" if vencimento < hoje else (f"🟡 ATENÇÃO ({(vencimento - hoje).days} dias)" if (vencimento - hoje).days <= 10 else "🟢 EM DIA")
            lista_exibicao.append({"Status": status, "Nome da Certidão": row["Nome"], "Link de Acesso": row["Link"], "Data de Vencimento": vencimento.strftime("%d/%m/%Y")})
        st.dataframe(pd.DataFrame(lista_exibicao), use_container_width=True)

# --- PÁGINA 3: CIDADES GANHAS ---
else:
    st.title("🏙️ Monitoramento de Cidades Ganhas & Atas")
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
            
    df_cont = st.session_state.contratos
    if not df_cont.empty:
        lista_contratos_visuais = []
        for idx, row in df_cont.iterrows():
            alerta_diario = f"👀 Checar Diário Oficial de {row['Cidade']}" if row["Status"] == "Ativo" else "✅ Finalizado"
            lista_contratos_visuais.append({"Ação Diária Obrigatória": alerta_diario, "Status": "🟢 Ativo" if row["Status"] == "Ativo" else "⚫ Encerrado", "Cidade / Órgão": row["Cidade"], "Nº do Contrato": row["Contrato"]})
        st.dataframe(pd.DataFrame(lista_contratos_visuais), use_container_width=True)
