import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES DE LÓGICA ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "background: linear-gradient(135deg, #FFD700, #FDB931); color: #4B3B00;", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "background: linear-gradient(135deg, #E0E0E0, #BDBDBD); color: #333;", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "background: linear-gradient(135deg, #CD7F32, #A0522D); color: #fff;", f"{porcentaje}% BRONCE"
    return None, None

def traer_info_producto(mi_sku):
    """Busca imagen en tabla Productos y calcula ahorro."""
    try:
        res = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res.data:
            return 0, None
        
        # Imagen (limpieza de URL por si acaso)
        img = next((p['url_imagen'].strip() for p in res.data if p.get('url_imagen')), None)
        
        # Ahorro
        ids = [p['id_producto'] for p in res.data]
        res_h = supabase.table("Historial_precios").select("precio, fecha").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        if df.empty: return 0, img
        
        precio_act = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_act) / suelo_30d) * 100) if suelo_30d > 0 else 0
        return ahorro, img
    except:
        return 0, None

# --- CSS (Mantenlo simple) ---
st.markdown("""
    <style>
    .st-card {
        background: white;
        border: 1px solid #eeeeee;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        height: 380px;
        position: relative;
    }
    .img-frame {
        height: 160px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 15px;
    }
    .img-frame img {
        max-height: 160px;
        max-width: 100%;
        object-fit: contain;
    }
    .badge-metal {
        position: absolute;
        top: 10px;
        left: 10px;
        padding: 5px 12px;
        border-radius: 8px;
        font-weight: 900;
        font-size: 11px;
        z-index: 100;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .product-name {
        font-size: 14px;
        font-weight: 600;
        color: #333;
        height: 40px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- NAVEGACIÓN ---
if "sku" in st.query_params:
    if st.button("⬅️ Volver a Galería"):
        st.query_params.clear()
        st.rerun()
    st.title(f"Detalle: {st.query_params['sku']}")
    # Tu lógica de detalles...
else:
    st.title("🐾 Oferta Pet Chile")
    busqueda = st.text_input("Buscar...", placeholder="Ej: Leonardo").strip()

    # Obtener SKUs base
    if busqueda:
        res_skus = supabase.table("SKUs_unicos").select("*").ilike("nombre_oficial", f"%{busqueda}%").limit(20).execute()
    else:
        res_skus = supabase.table("SKUs_unicos").select("*").limit(20).execute()

    if res_skus.data:
        cols = st.columns(5)
        for i, row in enumerate(res_skus.data):
            with cols[i % 5]:
                # 1. Obtener datos variables
                ahorro, url_img = traer_info_producto(row['mi_sku'])
                estilo_b, label_b = obtener_estilo_metal(ahorro)
                
                # 2. Construir Badge e Imagen
                badge_html = f'<div class="badge-metal" style="{estilo_b}">{label_b}</div>' if estilo_b else ""
                img_tag = f'<img src="{url_img}" referrerpolicy="no-referrer">' if url_img else '<div style="color:#ddd;">📷 Sin foto</div>'

                # 3. Renderizar la tarjeta
                st.markdown(f"""
                <div class="st-card">
                    {badge_html}
                    <div class="img-frame">
                        {img_tag}
                    </div>
                    <div class="product-name">{row['nombre_oficial']}</div>
                    <p style="color:#1abc9c; font-size:12px; font-weight:700;">VER OFERTAS</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 4. Botón de Streamlit (Separado del HTML)
                if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params["sku"] = row['mi_sku']
                    st.rerun()
