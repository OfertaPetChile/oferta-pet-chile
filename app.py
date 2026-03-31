import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Oferta Pet Chile",
    page_icon="🐾",
    layout="wide"
)

# 2. CONEXIÓN A SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES DE APOYO ---
def obtener_estilo_metal(porcentaje):
    """Retorna estilos para los badges de oferta."""
    if porcentaje >= 10:
        return "linear-gradient(135deg, #FFD700 0%, #FDB931 100%)", "#4B3B00", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%)", "#333333", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "linear-gradient(135deg, #CD7F32 0%, #A0522D 100%)", "#ffffff", f"{porcentaje}% BRONCE"
    return None, None, None

def calcular_ahorro_galeria(mi_sku):
    """Calcula el ahorro rápido para mostrar badges en la galería principal."""
    try:
        res_p = supabase.table("Productos").select("id_producto").eq("mi_sku", mi_sku).execute()
        ids = [p['id_producto'] for p in res_p.data]
        if not ids: return 0
        
        res_h = supabase.table("Historial_precios").select("fecha, precio").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        if df.empty: return 0
        
        precio_actual = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        return int(((suelo_30d - precio_actual) / suelo_30d) * 100) if suelo_30d > 0 else 0
    except:
        return 0

# --- ESTILOS CSS (SISTEMA DE CAPAS Z-INDEX) ---
st.markdown("""
    <style>
    /* Tarjeta Principal */
    .product-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #eee;
        height: 420px;
        text-align: center;
        position: relative; 
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        z-index: 1;
        transition: transform 0.2s;
    }
    .product-card:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    /* Contenedor de Imagen */
    .img-container {
        width: 100%;
        height: 180px;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        z-index: 2; /* Debajo del badge */
    }
    .img-container img {
        max-width: 100%;
        max-height: 180px;
        object-fit: contain;
    }

    /* Badge Metálico (Capa Superior) */
    .badge-galeria {
        position: absolute;
        top: 12px;
        left: 12px;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 900;
        z-index: 999 !important; /* Asegura estar sobre la imagen */
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        letter-spacing: 0.5px;
    }

    .product-title {
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
        height: 45px;
        line-height: 1.2;
        overflow: hidden;
        margin: 10px 0;
        z-index: 3;
    }

    /* Botones Streamlit Custom */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE NAVEGACIÓN ---
selected_sku = st.query_params.get("sku")

# --- VISTA 2: DETALLE DEL PRODUCTO ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # Obtener nombre oficial
    res_m = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    st.title(f"📊 {res_m.data['nombre_oficial'] if res_m.data else 'Producto'}")
    
    # Cargar ofertas y precios
    res_p = supabase.table("Productos").select("id_producto, nombre_tienda, url_tienda, disponibilidad").eq("mi_sku", selected_sku).execute()
    
    if res_p.data:
        datos_ofertas = []
        historiales = {}
        
        for p in res_p.data:
            res_h = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha", desc=True).execute()
            df_h = pd.DataFrame(res_h.data)
            if not df_h.empty:
                datos_ofertas.append({
                    "Tienda": p['nombre_tienda'],
                    "Precio": df_h.iloc[0]['precio'],
                    "URL": p['url_tienda'],
                    "Disponibilidad": p['disponibilidad'],
                    "id": p['id_producto']
                })
                historiales[p['id_producto']] = df_h.sort_values("fecha")

        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("💰 Mejores Precios")
            df_display = pd.DataFrame(datos_ofertas).sort_values("Precio")
            for _, item in df_display.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{item['Tienda']}**")
                    st.markdown(f"## ${item['Precio']:,.0f}".replace(",", "."))
                    st.caption(f"Stock: {item['Disponibilidad']}")
                    st.link_button("Ver en tienda", item['URL'], use_container_width=True)

        with col2:
            st.subheader("📈 Histórico")
            fig = go.Figure()
            for id_prod, df_plot in historiales.items():
                tienda_nombre = next(i['Tienda'] for i in datos_ofertas if i['id'] == id_prod)
                fig.add_trace(go.Scatter(x=df_plot['fecha'], y=df_plot['precio'], name=tienda_nombre, mode='lines+markers'))
            fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("No se encontraron datos para este producto.")

# --- VISTA 1: GALERÍA PRINCIPAL ---
else:
    st.title("🐾 Oferta Pet Chile")
    search = st.text_input("Busca por marca o producto...", placeholder="Ej: Brit Care, Leonardo...").strip()

    # Carga con búsqueda o inicial (primeros 20)
    if search:
        res = supabase.table("SKUs_unicos").select("*").ilike("nombre_oficial", f"%{search}%").limit(20).execute()
    else:
        res = supabase.table("SKUs_unicos").select("*").limit(20).execute()

    if res.data:
        df_items = pd.DataFrame(res.data)
        cols = st.columns(5)
        
        for idx, row in df_items.iterrows():
            with cols[idx % 5]:
                # 1. Calcular Ahorro y Badge
                ahorro = calcular_ahorro_galeria(row['mi_sku'])
                bg, txt_color, txt_label = obtener_estilo_metal(ahorro)
                badge_html = f'<div class="badge-galeria" style="background:{bg}; color:{txt_color}; border:1px solid rgba(0,0,0,0.1);">{txt_label}</div>' if bg else ""
                
                # 2. Manejo de Imagen con Fallback y Referrer Policy
                img_url = row.get('imagen_url_maestra')
                if not img_url:
                    img_html = '<div style="color:#ccc; font-size:10px;">Imagen no disponible</div>'
                else:
                    img_html = f'<img src="{img_url}" referrerpolicy="no-referrer" loading="lazy">'

                # 3. Renderizado de Tarjeta
                st.markdown(f"""
                    <div class="product-card">
                        <div class="img-container">
                            {img_html}
                        </div>
                        <div class="product-title">{row['nombre_oficial']}</div>
                        <div style="color:#1abc9c; font-weight:700; font-size:12px; margin-bottom:8px;">VER COMPARATIVA</div>
                        {badge_html}
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción
                if st.button("Explorar", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params.sku = row['mi_sku']
                    st.rerun()
    else:
        st.info("No encontramos productos que coincidan con tu búsqueda.")
