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

# --- FUNCIONES DE APOYO ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "linear-gradient(135deg, #FFD700 0%, #FDB931 100%)", "#4B3B00", f"{porcentaje}% ¡OFERTA ORO!"
    elif porcentaje >= 5:
        return "linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%)", "#333333", f"{porcentaje}% OFERTA PLATA"
    elif porcentaje >= 1:
        return "linear-gradient(135deg, #CD7F32 0%, #A0522D 100%)", "#ffffff", f"{porcentaje}% PRECIO BRONCE"
    return None, None, None

# --- LÓGICA DE NAVEGACIÓN ---
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS GLOBAL
st.markdown("""
    <style>
    .product-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #eee;
        height: 400px;
        text-align: center;
        transition: 0.3s;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
    }
    .product-card img {
        width: 100%;
        height: 160px;
        object-fit: contain;
        margin-bottom: 10px;
    }
    .badge-dinamico {
        position: absolute;
        top: 8px;
        left: 8px;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 9px;
        font-weight: 900;
        text-transform: uppercase;
        z-index: 10;
    }
    .product-title {
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
        margin: 10px 0;
        line-height: 1.2;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VISTA 2: DETALLE DEL PRODUCTO ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    
    # Carga de datos
    res_prod = supabase.table("Productos").select("id_producto, nombre_tienda, url_tienda, disponibilidad").eq("mi_sku", selected_sku).execute()
    
    if not res_prod.data:
        st.warning("Sin ofertas disponibles.")
        st.stop()

    datos_tabla = []
    historiales_por_id = {}
    
    for p in res_prod.data:
        res_hist = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha", desc=True).execute()
        df_h = pd.DataFrame(res_hist.data)
        if not df_h.empty:
            datos_tabla.append({
                "id_producto": p['id_producto'],
                "Tienda": p['nombre_tienda'], 
                "Precio": df_h.iloc[0]['precio'], 
                "URL": p['url_tienda'],
                "Disponibilidad": p.get('disponibilidad')
            })
            historiales_por_id[p['id_producto']] = df_h.sort_values(by="fecha")

    # Suelo de 30 días
    if historiales_por_id:
        todos_los_precios = pd.concat(historiales_por_id.values())
        suelo_30d = todos_los_precios.groupby('fecha')['precio'].min().tail(30).mean()
    else:
        suelo_30d = 0

    df_precios = pd.DataFrame(datos_tabla).sort_values("Precio")
    
    col_precios, col_grafica = st.columns([1.5, 2.5])

    with col_precios:
        st.subheader("💰 Ofertas")
        for _, row in df_precios.iterrows():
            pct_ahorro = int(((suelo_30d - row['Precio']) / suelo_30d) * 100) if suelo_30d > 0 else 0
            bg_m, txt_m, texto_m = obtener_estilo_metal(pct_ahorro)
            
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                c1.markdown(f"**{row['Tienda']}**")
                c1.caption(f"Status: {row['Disponibilidad']}")
                c2.markdown(f"### ${row['Precio']:,.0f}")
                if bg_m:
                    st.markdown(f'<span style="background:{bg_m}; color:{txt_m}; padding:2px 5px; border-radius:4px; font-size:10px;">{texto_m}</span>', unsafe_allow_html=True)
                st.link_button("Ir a tienda", row['URL'], use_container_width=True)

    with col_grafica:
        st.subheader("📈 Historial")
        fig = go.Figure()
        for tienda, df_h in historiales_por_id.items():
            nombre_t = next(item['Tienda'] for item in datos_tabla if item['id_producto'] == tienda)
            fig.add_trace(go.Scatter(x=df_h['fecha'], y=df_h['precio'], name=nombre_t))
        fig.update_layout(height=450, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

# --- VISTA 1: GALERÍA PRINCIPAL ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto (marca, nombre o SKU)...", placeholder="Ej: Leonardo, Cat it...").strip()

    # Si no hay búsqueda, traemos los destacados o los primeros 20
    if not query:
        res = supabase.table("SKUs_unicos").select("*").limit(20).execute()
    else:
        q = f"%{query}%"
        res = supabase.table("SKUs_unicos").select("*").or_(f"nombre_oficial.ilike.{q},mi_sku.ilike.{q}").execute()

    if res.data:
        df_maestro = pd.DataFrame(res.data)
        
        # Grid de 5 columnas
        cols = st.columns(5)
        for idx, row in df_maestro.iterrows():
            with cols[idx % 5]:
                # Aseguramos que la imagen tenga un fallback si es nula
                img_url = row.get('imagen_url_maestra') or "https://via.placeholder.com/150?text=No+Image"
                nombre = row.get('nombre_oficial', 'Producto sin nombre')
                
                # Renderizado de la tarjeta HTML
                st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_url}">
                        <div class="product-title">{nombre}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón de Streamlit (fuera del HTML para que funcione)
                if st.button("Ver comparativa", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params.sku = row['mi_sku']
                    st.rerun()
    else:
        st.info("No se encontraron productos con esa búsqueda.")
