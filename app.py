import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

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

# --- VISTA 2: HOJA DE DETALLE (Diseño con Checkbox Integrado) ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # 1. Datos básicos
    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.divider()

    # 2. Carga de Datos
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

    # --- 3. DISEÑO DE COLUMNAS ---
    col_precios, col_grafica = st.columns([1.3, 2.7], gap="large")

    # Diccionario para capturar la selección
    seleccion_tiendas = {}

    with col_precios:
        st.markdown("#### 💰 Ofertas Actuales")
        df_ord = pd.DataFrame(datos_tabla).sort_values(by="Precio")
        
        st.markdown("<p style='font-size: 11px; color: #7f8c8d; margin-bottom: 10px;'>Selecciona para comparar en la gráfica:</p>", unsafe_allow_html=True)
        
        for i, row in df_ord.iterrows():
            tienda = row['Tienda']
            precio_cl = f"$ {row['Precio']:,.0f}".replace(",", ".")
            es_top = (i == df_ord.index[0])
            
            # Layout: Checkbox + Card de información
            c_check, c_card = st.columns([0.15, 0.85])
            
            with c_check:
                # Marcamos por defecto las primeras 5 más baratas
                def_val = True if i < 5 else False
                seleccion_tiendas[tienda] = st.checkbox("", value=def_val, key=f"ch_{tienda}_{selected_sku}")

            with c_card:
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; 
                                background-color: {'#f0fff4' if es_top else 'white'}; 
                                padding: 6px 10px; border-radius: 6px; 
                                border: 1px solid {'#2ecc71' if es_top else '#eee'}; 
                                margin-bottom: 5px; height: 38px;">
                        <div style="flex: 1; font-size: 11px; font-weight: bold; color: #555; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            {tienda}
                        </div>
                        <div style="font-size: 13px; font-weight: 800; color: #2c3e50; margin-right: 5px;">
                            {precio_cl}
                        </div>
                        <a href="{row['URL']}" target="_blank" style="background-color: #1abc9c; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 10px;">🛒 Ver</a>
                    </div>
                """, unsafe_allow_html=True)

    with col_grafica:
        st.markdown("#### 📈 Evolución Histórica")
        
        # Filtramos las seleccionadas
        tiendas_a_graficar = [t for t, activo in seleccion_tiendas.items() if activo]
        
        if tiendas_a_graficar:
            fig = go.Figure()
            for tienda in tiendas_a_graficar:
                if tienda in historiales_completos:
                    df = historiales_completos[tienda]
                    fig.add_trace(go.Scatter(
                        x=df['fecha'], 
                        y=df['precio'], 
                        name=tienda, 
                        mode='lines+markers'
                    ))
            
            fig.update_layout(
                template="plotly_white",
                height=480,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.5,
                    xanchor="center",
                    x=0.5
                ),
                xaxis_title="Fecha",
                yaxis_title="Precio ($)",
                separators=",."
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selecciona al menos una tienda a la izquierda para ver la gráfica.")  
            
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
