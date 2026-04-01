import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# 2. CONEXIÓN A SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES DE APOYO ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "linear-gradient(135deg, #FFD700 0%, #FDB931 100%)", "#4B3B00", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "linear-gradient(135deg, #E0E0E0 0%, #BDBDBD 100%)", "#333333", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "linear-gradient(135deg, #CD7F32 0%, #A0522D 100%)", "#ffffff", f"{porcentaje}% BRONCE"
    return None, None, None

def calcular_ahorro_y_foto(mi_sku):
    """Obtiene una imagen aleatoria y calcula el ahorro actual."""
    try:
        # Traemos productos asociados a este SKU
        res = supabase.table("Productos").select("id_producto, url_imagen").eq("mi_sku", mi_sku).execute()
        if not res.data:
            return 0, None
        
        # 1. Elegimos la primera imagen válida que encontremos
        imagen = next((p['url_imagen'] for p in res.data if p.get('url_imagen')), None)
        
        # 2. Calculamos ahorro (promedio 30d)
        ids = [p['id_producto'] for p in res.data]
        res_h = supabase.table("Historial_precios").select("fecha, precio").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        
        if df.empty:
            return 0, imagen
            
        precio_actual = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_actual) / suelo_30d) * 100) if suelo_30d > 0 else 0
        
        return ahorro, imagen
    except:
        return 0, None

# --- ESTILOS CSS (CAPAS CORREGIDAS) ---
st.markdown("""
    <style>
    .product-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #eee;
        height: 400px;
        text-align: center;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .img-box {
        width: 100%;
        height: 180px;
        position: relative; /* Contexto para el badge */
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fdfdfd;
    }
    .img-box img {
        max-height: 180px;
        max-width: 100%;
        object-fit: contain;
    }
    .badge-float {
        position: absolute;
        top: 0;
        left: 0;
        z-index: 999 !important;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 900;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.15);
    }
    .product-title {
        font-size: 14px;
        font-weight: 600;
        color: #2c3e50;
        height: 45px;
        overflow: hidden;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
selected_sku = st.query_params.get("sku")

if selected_sku:
    # --- VISTA 2: DETALLE ---
    if st.button("⬅️ Volver"):
        st.query_params.clear()
        st.rerun()
    
    # (Aquí va tu lógica de detalle que ya funciona...)
    st.info(f"Mostrando comparativa para SKU: {selected_sku}")

else:
    # --- VISTA 1: GALERÍA ---
    st.title("🐾 Oferta Pet Chile")
    search = st.text_input("Busca marca o producto...", placeholder="Ej: Leonardo, Brit...").strip()

    if search:
        res = supabase.table("SKUs_unicos").select("*").ilike("nombre_oficial", f"%{search}%").limit(20).execute()
    else:
        res = supabase.table("SKUs_unicos").select("*").limit(20).execute()

    if res.data:
        cols = st.columns(5)
        for idx, row in enumerate(res.data):
            with cols[idx % 5]:
                # 1. Obtener imagen de la tabla Productos y calcular ahorro
                ahorro, img_url = calcular_ahorro_y_foto(row['mi_sku'])
                
                # 2. Configurar Badge
                bg, txt_c, label = obtener_estilo_metal(ahorro)
                badge_html = f'<div class="badge-float" style="background:{bg}; color:{txt_c};">{label}</div>' if bg else ""
                
                # 3. Validar Imagen
                if img_url:
                    display_img = f'<img src="{img_url}" referrerpolicy="no-referrer">'
                else:
                    display_img = '<div style="color:#ccc; font-size:10px;">Buscando imagen...</div>'

                # 4. Render Card
                st.markdown(f"""
                    <div class="product-card">
                        <div class="img-box">
                            {badge_html}
                            {display_img}
                        </div>
                        <div class="product-title">{row['nombre_oficial']}</div>
                        <div style="color:#1abc9c; font-weight:bold; font-size:12px; margin-bottom:10px;">VER COMPARATIVA</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params.sku = row['mi_sku']
                    st.rerun()
    else:
        st.info("No se encontraron productos.")
