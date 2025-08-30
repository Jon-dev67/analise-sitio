import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import urllib.parse
from datetime import date, datetime
from io import BytesIO

# ================================
# CONFIGURAÇÕES INICIAIS
# ================================
st.set_page_config(
    page_title="🌱 Gerenciador de Produção",
    layout="wide",
    initial_sidebar_state="expanded",
)
plt.style.use("dark_background")

ARQUIVO_DADOS = "colheitas.xlsx"
API_KEY = "eef20bca4e6fb1ff14a81a3171de5cec"  # sua chave OpenWeather
CIDADE_PADRAO = "Londrina"

# ================================
# FUNÇÕES AUXILIARES
# ================================
def carregar_dados():
    try:
        return pd.read_excel(ARQUIVO_DADOS)
    except:
        return pd.DataFrame(columns=["Data","Local","Produto","Caixas","Caixas de Segunda","Temperatura","Umidade","Chuva"])

def salvar_dados(df):
    df.to_excel(ARQUIVO_DADOS, index=False)

def normalizar_colunas(df):
    df = df.copy()
    col_map = {
        "Estufa":"Local",
        "Área":"Local",
        "Produção":"Caixas",
        "Primeira":"Caixas",
        "Segunda":"Caixas de Segunda",
        "Qtd":"Caixas",
        "Quantidade":"Caixas",
    }
    df.rename(columns={c:col_map.get(c,c) for c in df.columns}, inplace=True)
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    for col in ["Caixas","Caixas de Segunda","Temperatura","Umidade","Chuva"]:
        if col not in df.columns:
            df[col] = 0
    if "Local" not in df.columns: df["Local"] = ""
    if "Produto" not in df.columns: df["Produto"] = ""
    return df

def plot_bar(ax, x, y, df, cores, titulo, ylabel):
    df.groupby(x)[y].sum().plot(kind="bar", ax=ax, color=cores, width=0.6)
    ax.set_title(titulo, fontsize=14)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    for p in ax.patches:
        ax.text(p.get_x() + p.get_width()/2, p.get_height() + 0.01*df[y].max(), 
                f"{int(p.get_height())}", ha="center")

def clima_atual(cidade):
    """Busca clima atual no OpenWeather"""
    try:
        city_encoded = urllib.parse.quote(cidade)
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_encoded}&appid={API_KEY}&units=metric&lang=pt_br"
        r = requests.get(url)
        data = r.json()
        if r.status_code != 200:
            return None
        return {
            "temp": data["main"]["temp"],
            "umidade": data["main"]["humidity"],
            "chuva": data.get("rain", {}).get("1h", 0)
        }
    except:
        return None

# ================================
# MENU PRINCIPAL
# ================================
st.sidebar.title("📌 Menu")
pagina = st.sidebar.radio("Escolha a página:", ["Cadastro de Produção","Análise"])

# ================================
# PÁGINA CADASTRO
# ================================
if pagina == "Cadastro de Produção":
    st.title("📝 Cadastro de Produção")
    df = carregar_dados()
    cidade = st.sidebar.text_input("🌍 Cidade para clima", value=CIDADE_PADRAO)

    with st.form("form_cadastro", clear_on_submit=True):
        col1,col2,col3 = st.columns(3)
        with col1:
            data = st.date_input("Data", value=date.today())
            local = st.text_input("Local/Estufa")
        with col2:
            produto = st.text_input("Produto")
            caixas = st.number_input("Caixas (1ª)", min_value=0, step=1)
        with col3:
            caixas2 = st.number_input("Caixas (2ª)", min_value=0, step=1)

        # Busca clima automático
        clima = clima_atual(cidade)
        if clima:
            temperatura = clima["temp"]
            umidade = clima["umidade"]
            chuva = clima["chuva"]
            st.info(f"Clima carregado: 🌡️ {temperatura}°C | 💧 {umidade}% | 🌧️ {chuva}mm")
        else:
            temperatura = st.number_input("Temperatura (°C)", min_value=0.0, step=0.1)
            umidade = st.number_input("Umidade (%)", min_value=0.0, step=0.1)
            chuva = st.number_input("Chuva (mm)", min_value=0.0, step=0.1)

        enviado = st.form_submit_button("Salvar Registro ✅")
        if enviado:
            novo = pd.DataFrame([{
                "Data": pd.to_datetime(data),
                "Local": local,
                "Produto": produto,
                "Caixas": caixas,
                "Caixas de Segunda": caixas2,
                "Temperatura": temperatura,
                "Umidade": umidade,
                "Chuva": chuva
            }])
            df = pd.concat([df, novo], ignore_index=True)
            salvar_dados(df)
            st.success("Registro salvo com sucesso!")

    if not df.empty:
        st.markdown("### 📋 Registros já cadastrados")
        st.dataframe(df.tail(10), use_container_width=True)

# ================================
# PÁGINA ANÁLISE
# ================================
if pagina == "Análise":
    st.title("📊 Análise")
    st.markdown("Escolha a fonte de dados:")
    fonte = st.radio("Fonte de dados:", ["Usar dados cadastrados no app","Enviar um arquivo Excel"], horizontal=True)

    df_raw = None
    if fonte == "Usar dados cadastrados no app":
        df_raw = carregar_dados()
    else:
        arquivo = st.file_uploader("Selecione um arquivo Excel", type=["xlsx","xls"])
        if arquivo:
            df_raw = pd.read_excel(arquivo)

    if df_raw is None or df_raw.empty:
        st.warning("Nenhum dado disponível.")
        st.stop()

    df_norm = normalizar_colunas(df_raw)

    # FILTROS
    st.sidebar.markdown("## 🔎 Filtros")
    min_date = df_norm["Data"].min().date() if not df_norm["Data"].isna().all() else date.today()
    max_date = df_norm["Data"].max().date() if not df_norm["Data"].isna().all() else date.today()
    date_range = st.sidebar.date_input("Período", value=(min_date,max_date), min_value=min_date, max_value=max_date)

    locais_all = sorted(df_norm["Local"].dropna().unique())
    locais_sel = st.sidebar.multiselect("Local (todos se vazio)", locais_all, default=locais_all)

    produtos_all = sorted(df_norm["Produto"].dropna().unique())
    produtos_sel = st.sidebar.multiselect("Produto (todos se vazio)", produtos_all, default=produtos_all)

    df_filt = df_norm.copy()
    try:
        start_date, end_date = date_range
    except:
        start_date = end_date = date_range
    df_filt = df_filt[(df_filt["Data"] >= pd.to_datetime(start_date)) & (df_filt["Data"] <= pd.to_datetime(end_date))]

    if locais_sel:
        df_filt = df_filt[df_filt["Local"].isin(locais_sel)]
    if produtos_sel:
        df_filt = df_filt[df_filt["Produto"].isin(produtos_sel)]

    if df_filt.empty:
        st.warning("Nenhum dado após aplicar os filtros.")
        st.stop()

    df_filt["Total"] = df_filt["Caixas"] + df_filt["Caixas de Segunda"]

    # KPIs
    total = df_filt["Total"].sum()
    media = df_filt["Total"].mean()
    maior = df_filt["Total"].max()
    menor = df_filt["Total"].min()

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total de Caixas", f"{total:,.0f}")
    k2.metric("Média por Registro", f"{media:,.2f}")
    k3.metric("Máximo em 1 Registro", f"{maior:,.0f}")
    k4.metric("Mínimo em 1 Registro", f"{menor:,.0f}")

    st.markdown("---")

    # GRÁFICOS
    st.subheader("🏭 Total por Local")
    fig, ax = plt.subplots(figsize=(12,6))
    plot_bar(ax,"Local","Total",df_filt,cores=sns.color_palette("tab20", n_colors=len(df_filt["Local"].unique())),
             titulo="Total de Caixas por Local", ylabel="Total de Caixas")
    st.pyplot(fig)

    st.subheader("🍅 Total por Produto")
    fig, ax = plt.subplots(figsize=(10,5))
    plot_bar(ax,"Produto","Total",df_filt,cores=sns.color_palette("Set2", n_colors=len(df_filt["Produto"].unique())),
             titulo="Total de Caixas por Produto", ylabel="Total de Caixas")
    st.pyplot(fig)

    # Comparativo 1ª vs 2ª
    st.subheader("📊 Comparativo Caixas 1ª vs 2ª")
    for tipo in ["Local","Produto"]:
        if tipo in df_filt.columns:
            df_comp = df_filt.groupby(tipo)[["Caixas","Caixas de Segunda"]].sum().reset_index()
            fig, ax = plt.subplots(figsize=(12,6))
            df_comp.plot(kind="bar", x=tipo, ax=ax, width=0.7)
            ax.set_ylabel("Quantidade de Caixas")
            ax.set_title(f"Caixas de Primeira vs Segunda por {tipo}")
            ax.grid(axis="y")
            ax.legend(["Caixas (1ª)","Caixas de Segunda"])
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            for p in ax.patches:
                ax.text(p.get_x()+p.get_width()/2,p.get_height()+max(df_filt["Total"])*0.01,f'{int(p.get_height())}',ha='center')
            st.pyplot(fig)

    # Insights
    st.markdown("---")
    st.markdown("### 🧠 Insights")
    total_segunda = df_filt["Caixas de Segunda"].sum()
    pct_segunda = total_segunda/total*100 if total>0 else 0
    st.markdown(f"- Taxa de Segunda Linha: {pct_segunda:.1f}% do total ({int(total_segunda):,} caixas de 2ª)")

    media_prod = df_filt.groupby("Produto")["Total"].mean().sort_values(ascending=False)
    if not media_prod.empty:
        st.markdown(f"- Produto com maior média por registro: {media_prod.index[0]} ({media_prod.iloc[0]:.1f} caixas/registro)")

    top_local_val = df_filt.groupby("Local")["Total"].sum().sort_values(ascending=False)
    if not top_local_val.empty:
        st.markdown(f"- Top local: {top_local_val.index[0]} ({int(top_local_val.iloc[0]):,} caixas)")

    # Download filtrado
    st.markdown("---")
    buffer = BytesIO()
    df_filt.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button("📥 Baixar dados filtrados em Excel", data=buffer,
                       file_name="colheitas_filtradas.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
