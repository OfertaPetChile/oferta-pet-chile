import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import random

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "linear-gradient(135deg, #FFD700 0%, #FDB931 100%)", "#4B3B00", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%)", "#333333", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "linear-gradient(135deg, #CD7F32 0%, #A0522D 100%)", "#ffffff", f"{porcentaje}% BRONCE"
    return None, None, None

def obtener_datos_card(mi_sku):
    """Trae una imagen y calcula el ahorro."""
    try:
        # Buscamos en Productos para obtener la url_imagen
        res = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res.data:
            return 0, None
        
        # Imagen: Tomamos la primera que no sea nula
        imagenes = [p['url_imagen'] for p in res.data if p.get('url_imagen')]
        img_final = imagenes[0] if imagenes else None
        
        # Ahorro: Historial
        ids = [p['id_producto'] for p in res.data]
        res_h = supabase.table("Historial_precios").select("fecha, precio").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        
        if df.empty:
            return 0, img_final
            
        precio_actual = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_actual) / suelo_30d) * 100) if suelo_30d > 0 else 0
        
        return ahorro, img_final
    except:
        return 0, None

# --- CSS MEJORADO ---
st.markdown("""
    <style>
    .main-card {
        background: white;
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 15px;
        height: 420px;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .img-container {
        height: 180px;
        width: 100%;
        position: relative;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .img-container img {
        max-height: 100%;
        max-width: 100%;
        object-fit: contain;
    }
    .badge-metal {
        position: absolute;
        top: -5px;
        left: -5px;
        z-index: 99;
        padding: 5px 10px;
        border-radius: 6px;
        font-weight: 900;
        font-size: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .card-title {
        font-size: 14px;
        font-weight: 600;
        color: #333;
        margin: 12px 0;
        height: 40px;
        overflow: hidden;
        line-height: 1.2;
    }
    </style>
""", unsafe_allow_html=True)

# --- NAVEGACIÓN ---
params = st.query_params
if "sku" in params:
    # VISTA DETALLE
    if st.button("⬅️ Volver"):
        st.query_params.clear()
        st.rerun()
    st.title(f"Producto: {params['sku']}")
    # (Tu código de gráficos aquí)
else:
    # VISTA GALERÍA
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Leonardo, Cat it, Brit...").strip()

    # Obtener SKUs
    if query:
        res_skus = supabase.table("SKUs_unicos").select("*").ilike("nombre_oficial", f"%{query}%").limit(20).execute()
    else:
        res_skus = supabase.table("SKUs_unicos").select("*").limit(20).execute()

    if res_skus.data:
        cols = st.columns(5)
        for idx, row in enumerate(res_skus.data):
            with cols[idx % 5]:
                # 1. Obtener imagen y ahorro desde la tabla Productos
                ahorro, img_url = obtener_datos_card(row['mi_sku'])
                
                # 2. Preparar Badge
                bg, txt, label = obtener_estilo_metal(ahorro)
                badge_html = f'<div class="badge-metal" style="background:{bg}; color:{txt};">{label}</div>' if bg else ""
                
                # 3. Fallback de imagen
                if not img_url:
                    img_url = "https://via.placeholder.com/200?text=Sin+Imagen"

                # 4. Renderizado HTML (Todo en un solo bloque para evitar rupturas)
                card_html = f"""
                <div class="main-card">
                    <div class="img-container">
                        {badge_html}
                        <img src="{img_url}" referrerpolicy="no-referrer">
                    </div>
                    <div class="card-title">{row['nombre_oficial']}</div>
                    <div style="color:#1abc9c; font-weight:bold; font-size:12px; margin-bottom:10px;">VER COMPARATIVA</div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Botón de acción de Streamlit
                if st.button("Explorar", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params["sku"] = row['mi_sku']
                    st.rerun()
