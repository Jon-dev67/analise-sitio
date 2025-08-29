import streamlit as st
import pandas as pd
import datetime
import requests
import plotly.express as px
import urllib.parse

# ================================
# CONFIGURAÇÕES INICIAIS
# ================================
st.set_page_config(
    page_title="🌱 Painel Integrado de Produção",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌱 Painel Integrado de Produção")
st.write("Ferramenta para acompanhar **fenologia, adubação, colheita e clima**.")

# ================================
# 1. DEFINIÇÃO DOS ESTÁGIOS FENOLÓGICOS
# ================================
st.sidebar.header("⚙️ Configurações")

st.subheader("📊 Curva de absorção de nutrientes (adubo por estágio)")

num_estagios = st.sidebar.number_input("Quantos estágios fenológicos?", min_value=1, max_value=10, value=4)
estagios = {}
for i in range(num_estagios):
    nome = st.sidebar.text_input(f"Nome do estágio {i+1}", value=f"Estágio {i+1}")
    dias = st.sidebar.text_input(f"Intervalo de dias do estágio {i+1}", value=f"{i*20}-{(i+1)*20}")
    adubo = st.sidebar.number_input(
        f"Adubo recomendado (kg) para {nome}",
        value=(i+1)*2,
        step=1  # apenas inteiros
    )
    estagios[f"{dias} ({nome})"] = adubo

fenologia_df = pd.DataFrame({"Estágio": list(estagios.keys()), "Adubo (kg)": list(estagios.values())})
st.dataframe(fenologia_df, use_container_width=True)

fig = px.line(fenologia_df, x="Estágio", y="Adubo (kg)", markers=True, title="Curva de absorção de nutrientes")
st.plotly_chart(fig, use_container_width=True)

# ================================
# 2. UPLOAD DE COLHEITAS
# ================================
st.subheader("📦 Registro de colheitas")
uploaded_file = st.file_uploader("Envie a planilha de colheitas (xlsx)", type=["xlsx"])
df_colheita = None
if uploaded_file:
    df_colheita = pd.read_excel(uploaded_file)

    # Normalizar datas
    if "Data" in df_colheita.columns:
        df_colheita["Data"] = pd.to_datetime(df_colheita["Data"], errors="coerce")
    
    st.dataframe(df_colheita, use_container_width=True)

    if "Data" in df_colheita.columns and "Caixas" in df_colheita.columns:
        # Gráfico mais legível: barras
        fig2 = px.bar(
            df_colheita.sort_values("Data"), 
            x="Data", 
            y="Caixas", 
            title="Produção ao longo do tempo",
            labels={"Caixas": "Caixas colhidas", "Data": "Data"},
            color="Caixas",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig2, use_container_width=True)

# ================================
# 3. CLIMA - OpenWeather
# ================================
st.subheader("🌤️ Dados Climáticos")
api_key = st.sidebar.text_input("API Key OpenWeather")
city = st.sidebar.text_input("Cidade", value="Londrina")

if api_key and city:
    try:
        city_encoded = urllib.parse.quote(city)
        # Clima atual
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city_encoded}&appid={api_key}&units=metric&lang=pt_br"
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            st.error(f"Erro API: {data.get('message', 'Não foi possível buscar o clima')}")
        else:
            temp = data["main"]["temp"]
            hum = data["main"]["humidity"]
            st.metric("🌡️ Temperatura atual", f"{temp} °C")
            st.metric("💧 Umidade", f"{hum}%")

        # Previsão 5 dias
        url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?q={city_encoded}&appid={api_key}&units=metric&lang=pt_br"
        forecast = requests.get(url_forecast).json()

        if forecast.get("cod") != "200":
            st.warning(f"Erro na previsão: {forecast.get('message','')}")
        else:
            previsoes = []
            for item in forecast["list"][:10]:  # próximas 10 entradas
                previsoes.append({
                    "Data": item["dt_txt"],
                    "Temp (°C)": item["main"]["temp"],
                    "Umidade (%)": item["main"]["humidity"]
                })
            previsao_df = pd.DataFrame(previsoes)
            st.dataframe(previsao_df, use_container_width=True)

            fig_forecast = px.line(previsao_df, x="Data", y="Temp (°C)", markers=True, title="Previsão de Temperatura (próximos dias)")
            st.plotly_chart(fig_forecast, use_container_width=True)

    except Exception as e:
        st.error(f"Erro de conexão: {e}")

# ================================
# 4. RELATÓRIOS E EFICIÊNCIA DE ADUBO
# ================================
st.subheader("📈 Relatórios e análises")

if df_colheita is not None:
    total_caixas = df_colheita["Caixas"].sum()
    total_adubo = sum(estagios.values())
    eficiencia = None

    if total_adubo > 0:
        eficiencia = total_caixas / total_adubo

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total de Caixas Colhidas", total_caixas)
    col2.metric("🧪 Total de Adubo Aplicado (kg)", total_adubo)
    if eficiencia:
        col3.metric("⚖️ Eficiência (Caixas/kg Adubo)", round(eficiencia, 2))

    # Relação adubo x produção
    relacao_df = pd.DataFrame({
        "Categoria": ["Produção (Caixas)", "Adubo (kg)"],
        "Valor": [total_caixas, total_adubo]
    })
    fig_rel = px.bar(relacao_df, x="Categoria", y="Valor", title="Comparativo Produção x Adubo")
    st.plotly_chart(fig_rel, use_container_width=True)

else:
    st.info("Envie uma planilha de colheita para gerar relatórios completos.")
