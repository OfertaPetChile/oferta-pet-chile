import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc

# 1. Configuración de página
st.set_page_config(
   page_title="Oferta Pet Chile",
   page_icon="🐾",
   layout="wide"
)

# 2. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE NAVEGACIÓN ---
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS
st.markdown("""
    <style>
    .product-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #eee;
        height: 380px;
        text-align: center;
        transition: 0.3s;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .product-card:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .product-title {
        font-size: 14px;
        font-weight: 600;
        height: 45px;
        overflow: hidden;
        margin-top: 10px;
        color: #2c3e50;
        line-height: 1.2;
    }
    .ver-detalle-text {
        color: #1abc9c;
        font-weight: bold;
        font-size: 15px;
        margin-top: 5px;
    }
    div.stButton > button {
        border-radius: 8px;
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        color: #333;
    }
    div.stButton > button:hover {
        background-color: #1abc9c;
        color: white;
        border-color: #1abc9c;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VISTA 2: HOJA DE DETALLE ---
# --- 1. FUNCIÓN PARA CARGAR EL HISTORIAL (NUEVO) ---
@st.cache_data(ttl=3600)  # Se actualiza cada hora
def cargar_historial_json():
    import json
    import requests
    # Aquí pones la URL de tu JSON en GitHub (Raw)
    url_json = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/historial_web_180d.json"
    try:
        response = requests.get(url_json)
        return response.json()
    except:
        return {}

# --- VISTA 2: HOJA DE DETALLE ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # Cargamos el diccionario gigante de una vez
    historial_maestro = cargar_historial_json()

    # Buscamos nombre en Supabase (esto es rápido por ser una sola fila)
    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.divider()

    # Obtenemos ofertas actuales de Supabase
    res_prod = supabase.table("Productos").select("nombre_tienda, url_tienda, disponibilidad, precio_actual").eq("mi_sku", selected_sku).execute()
    
    if not res_prod.data:
        st.warning("Sin ofertas disponibles.")
        st.stop()

    # Procesamos los datos para las tarjetas
    tiendas_agrupadas = {}
    for p in res_prod.data:
        t = p['nombre_tienda']
        if t not in tiendas_agrupadas:
            tiendas_agrupadas[t] = []
        tiendas_agrupadas[t].append({
            "Tienda": t,
            "Precio": p['precio_actual'],
            "URL": p['url_tienda'],
            "Disponibilidad": p['disponibilidad']
        })

    # Resumen para las tarjetas laterales
    resumen_tiendas = []
    for tienda, opciones in tiendas_agrupadas.items():
        opciones_ord = sorted(opciones, key=lambda x: x['Precio'])
        resumen_tiendas.append({
            "Tienda": tienda,
            "Precio_Min": opciones_ord[0]['Precio'],
            "Disponibilidad": opciones_ord[0]['Disponibilidad'],
            "Opciones": opciones_ord
        })

    df_resumen = pd.DataFrame(resumen_tiendas)
    
    # --- MAPA DE COLORES Y PRIORIDAD ---
    mapa_colores = {t: colores_fijos.get(t, pc.qualitative.Alphabet[i % 26]) 
                    for i, t in enumerate(df_resumen['Tienda'].unique())}
    
    df_resumen['Dispo_limpia'] = df_resumen['Disponibilidad'].astype(str).str.strip().str.capitalize()
    df_resumen['prioridad_stock'] = df_resumen['Dispo_limpia'].apply(lambda x: 0 if "Disponible" in x or "Stock" in x else 1)
    df_resumen = df_resumen.sort_values(by=['prioridad_stock', 'Precio_Min'], ascending=[True, True]).reset_index(drop=True)

    # --- RENDERIZADO ---
    col_precios, col_grafica = st.columns([1.4, 2.6], gap="large")
    seleccion_tiendas = {}

    with col_precios:
        st.markdown("#### 💰 Ofertas Actuales")
        # (Aquí mantienes tus estilos CSS de tarjetas y el bucle for i, row in df_resumen.iterrows())
        # NOTA: El checkbox ahora solo activará la tienda en la gráfica
        for i, row in df_resumen.iterrows():
            tienda = row['Tienda']
            # ... (Toda tu lógica de dibujo de tarjetas que ya tienes) ...
            
            with c_check:
                # El checkbox ya no depende de un ID de producto de Supabase
                check_val = (i < 5 and "Disponible" in row['Dispo_limpia'])
                seleccion_tiendas[tienda] = st.checkbox("", value=check_val, key=f"ch_{tienda}_{selected_sku}")

    with col_grafica:
        st.markdown("#### 📈 Evolución Histórica")
        
        # OBTENEMOS DATA DEL JSON PARA ESTE SKU
        data_sku = historial_maestro.get(selected_sku, {})
        puntos_historial = data_sku.get("h", []) # "h" es la llave compacta que definimos
        
        if puntos_historial:
            df_plot = pd.DataFrame(puntos_historial)
            # f: fecha, p: precio, t: tienda
            df_plot['f'] = pd.to_datetime(df_plot['f'], dayfirst=True)
            df_plot = df_plot.sort_values('f')

            fig = go.Figure()
            
            for tienda in df_resumen['Tienda'].unique():
                if seleccion_tiendas.get(tienda):
                    # Filtramos los puntos del JSON que pertenecen a esta tienda (incluyendo Socio si aplica)
                    # El JSON ya tiene los nombres de tienda procesados (ej: "Petvet Socio")
                    df_tienda = df_plot[df_plot['t'] == tienda]
                    
                    if not df_tienda.empty:
                        fig.add_trace(go.Scatter(
                            x=df_tienda['f'], 
                            y=df_tienda['p'], 
                            name=tienda,
                            mode='lines+markers',
                            line=dict(color=mapa_colores.get(tienda, "#333"), width=3),
                            connectgaps=False # Importante: No une puntos si hay días sin stock
                        ))
            
            fig.update_layout(
                template="plotly_white", 
                height=500, 
                margin=dict(l=0,r=0,t=10,b=0), 
                showlegend=True, # Ahora sí mostramos leyenda porque es más limpio
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos históricos acumulados para este producto aún.")
           
# --- VISTA 1: GALERÍA PRINCIPAL ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    if query:
        q = query.strip().upper()
        res = supabase.table("SKUs_unicos").select("*").or_(f"nombre_oficial.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

        if res.data:
            df_maestro = pd.DataFrame(res.data)
            cols = st.columns(5)
            for idx, row in df_maestro.iterrows():
                with cols[idx % 5]:
                    nombre_card = row.get('nombre_oficial', 'Producto')
                    img_url = row.get('imagen_url_maestra', '')
                    st.markdown(f'''
                        <div class="product-card">
                            <img src="{img_url}" style="width:100%; height:160px; object-fit:contain;">
                            <div>
                                <div class="product-title">{nombre_card}</div>
                                <div class="ver-detalle-text">Ver comparativa</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                    if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                        st.query_params.sku = row['mi_sku']
                        st.rerun()
        else:
            st.info("No hay resultados.")
