import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 1. Configuración de página
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# 2. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE NAVEGACIÓN ---
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS (Ajustados para Card Unificada)
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
    /* Estilo para que el botón de Streamlit parezca parte de la card */
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

# --- VISTA 2: HOJA DE DETALLE (Con Indicador de Color en Tarjeta) ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
       st.query_params.clear()
       st.rerun()

    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.divider()

    # 1. Carga y Preparación de Datos
    res_prod = supabase.table("Productos").select("id_producto, nombre_tienda, url_tienda").eq("mi_sku", selected_sku).execute()
    
    if not res_prod.data:
        st.warning("Sin ofertas disponibles.")
        st.stop()

    datos_tabla = []
    historiales_completos = {}
    
    for p in res_prod.data:
        res_hist = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha", desc=True).execute()
        df_h = pd.DataFrame(res_hist.data)
        if not df_h.empty:
            tienda = p['nombre_tienda']
            datos_tabla.append({"Tienda": tienda, "Precio": df_h.iloc[0]['precio'], "URL": p['url_tienda']})
            historiales_completos[tienda] = df_h.sort_values(by="fecha")

    # 2. Asignación de Colores Fijos por Tienda
    # Usamos la paleta cualitativa de Plotly para que coincidan con el gráfico
    colores_disponibles = px.colors.qualitative.Plotly # Azul, Rojo, Verde, Morado, Naranja, etc.
    df_ord = pd.DataFrame(datos_tabla).sort_values(by="Precio")
    
    # Creamos un diccionario: Tienda -> Color
    mapa_colores = {tienda: colores_disponibles[i % len(colores_disponibles)] 
                    for i, tienda in enumerate(df_ord['Tienda'].unique())}

    # --- 3. DISEÑO DE COLUMNAS ---
    col_precios, col_grafica = st.columns([1.4, 2.6], gap="large")
    seleccion_tiendas = {}

    with col_precios:
        st.markdown("#### 💰 Ofertas Actuales")
        
        for i, row in df_ord.iterrows():
            tienda = row['Tienda']
            precio_cl = f"$ {row['Precio']:,.0f}".replace(",", ".")
            color_tienda = mapa_colores[tienda]
            es_top = (i == 0)
            
            # Columnas internas para separar el Checkbox de la Tarjeta
            c_check, c_card = st.columns([0.1, 0.9])
            
            with c_check:
                # El checkbox controla qué línea se ve en la gráfica
                seleccion_tiendas[tienda] = st.checkbox("", value=(i < 5), key=f"ch_{tienda}_{selected_sku}")

            with c_card:
                # Renderizamos la tarjeta. Importante: f-string para las variables
                st.markdown(f"""
                    <div style="
                        display: flex; 
                        justify-content: space-between; 
                        align-items: center; 
                        background-color: {'#f0fff4' if es_top else 'white'}; 
                        padding: 8px 12px; 
                        border-radius: 8px; 
                        border: 1px solid {'#2ecc71' if es_top else '#eee'}; 
                        margin-bottom: 8px; 
                        height: 50px;
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.02);
                    ">
                        <div style="display: flex; align-items: center; width: 100px; flex-shrink: 0;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {color_tienda}; margin-right: 8px;"></div>
                            <div style="font-size: 11px; font-weight: bold; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                {tienda}
                            </div>
                        </div>
                        
                        <div style="flex-grow: 1; text-align: right; margin-right: 15px;">
                            <span style="font-size: 15px; font-weight: 800; color: #2c3e50;">{precio_cl}</span>
                        </div>
                        
                        <a href="{row['URL']}" target="_blank" style="
                            background-color: #1abc9c; 
                            color: white; 
                            padding: 6px 14px; 
                            border-radius: 6px; 
                            text-decoration: none; 
                            font-weight: bold; 
                            font-size: 11px;
                            white-space: nowrap;
                        ">
                            Ver oferta
                        </a>
                    </div>
                """, unsafe_allow_html=True)

    with col_grafica:
        st.markdown("#### 📈 Evolución Histórica")
        tiendas_activas = [t for t, activo in seleccion_tiendas.items() if activo]
        
        if tiendas_activas:
            fig = go.Figure()
            for tienda in tiendas_activas:
                if tienda in historiales_completos:
                    df = historiales_completos[tienda]
                    fig.add_trace(go.Scatter(
                        x=df['fecha'], y=df['precio'], 
                        name=tienda, mode='lines+markers',
                        line=dict(color=mapa_colores[tienda], width=2.5),
                        marker=dict(size=6)
                    ))
            
            fig.update_layout(
                template="plotly_white", height=500, margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                xaxis_title="Fecha", yaxis_title="Precio ($)", separators=",."
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecciona tiendas a la izquierda para comparar precios.")
                
# --- VISTA 1: GALERÍA PRINCIPAL (Corregida con nuevos nombres de columna) ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    if query:
        q = query.strip().upper()
        
        # CAMBIO CLAVE: Cambiamos 'nombre_maestro' por 'nombre_oficial'
        res = supabase.table("SKUs_unicos")\
            .select("*")\
            .or_(f"nombre_oficial.ilike.%{q}%,mi_sku.ilike.%{q}%")\
            .execute()

        if res.data:
            df_maestro = pd.DataFrame(res.data)
            
            # Configuramos 5 columnas para la galería
            cols = st.columns(5)
            
            for idx, row in df_maestro.iterrows():
                with cols[idx % 5]:
                    # Usamos 'nombre_oficial' también para el texto de la card
                    nombre_card = row.get('nombre_oficial', 'Producto sin nombre')
                    img_url = row.get('imagen_url_maestra', '') # Verifica si este es el nombre en SKUs_unicos
                    
                    # Render de la Card HTML
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_url}" style="width:100%; height:160px; object-fit:contain;">
                        <div>
                            <div class="product-title">{nombre_card}</div>
                            <div class="ver-detalle-text">Ver comparativa</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón de acción
                    if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                        st.query_params.sku = row['mi_sku']
                        st.rerun()
        else:
            st.info("No encontramos coincidencias con 'nombre_oficial' en el catálogo.")
