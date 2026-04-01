import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

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
    """Retorna el estilo CSS y la etiqueta según el porcentaje de ahorro."""
    if porcentaje >= 10:
        return "background: linear-gradient(135deg, #FFD700, #FDB931); color: #4B3B00;", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "background: linear-gradient(135deg, #E0E0E0, #BDBDBD); color: #333;", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "background: linear-gradient(135deg, #CD7F32, #A0522D); color: #fff;", f"{porcentaje}% BRONCE"
    return None, None

def traer_info_galeria(mi_sku):
    """Obtiene una imagen de 'Productos' y calcula el ahorro vs promedio 30d."""
    try:
        # Buscamos imagen en la tabla Productos
        res_p = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res_p.data:
            return 0, None
        
        # Imagen: Tomamos la primera disponible
        url_img = next((p['url_imagen'].strip() for p in res_p.data if p.get('url_imagen')), None)
        
        # Ahorro: Basado en el historial de todos los productos con ese SKU
        ids = [p['id_producto'] for p in res_p.data]
        res_h = supabase.table("Historial_precios").select("precio, fecha").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        
        if df.empty:
            return 0, url_img
            
        precio_actual = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_actual) / suelo_30d) * 100) if suelo_30d > 0 else 0
        
        return ahorro, url_img
    except:
        return 0, None

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .card-container {
        background: white;
        border: 1px solid #eee;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        height: 380px;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 20px;
    }
    .img-box {
        height: 160px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }
    .img-box img {
        max-height: 160px;
        max-width: 100%;
        object-fit: contain;
    }
    .badge-metal {
        position: absolute;
        top: 0;
        left: 0;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 900;
        font-size: 11px;
        z-index: 10;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .product-title {
        font-size: 14px;
        font-weight: 600;
        color: #333;
        height: 40px;
        overflow: hidden;
        margin: 10px 0;
        line-height: 1.2;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
sku_seleccionado = st.query_params.get("sku")

if sku_seleccionado:
    # VISTA 2: DETALLE
    if st.button("⬅️ Volver a Galería"):
        st.query_params.clear()
        st.rerun()
    
    # Obtener nombre oficial
    res_m = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", sku_seleccionado).single().execute()
    st.title(f"🐾 {res_m.data['nombre_oficial'] if res_m.data else 'Detalle de Producto'}")
    
    # Lógica de ofertas y gráfico (Resumida para brevedad)
    st.info(f"Mostrando análisis para el SKU: {sku_seleccionado}")
    # ... aquí iría tu código de Plotly ...

else:
    # VISTA 1: GALERÍA
    st.title("🐾 Oferta Pet Chile")
    busqueda = st.text_input("Busca tu marca o producto...", placeholder="Ej: Leonardo, Cat it, Brit...").strip()

    # Carga de datos
    query_base = supabase.table("SKUs_unicos").select("*")
    if busqueda:
        query_base = query_base.ilike("nombre_oficial", f"%{busqueda}%")
    res_skus = query_base.limit(20).execute()

    if res_skus.data:
        cols = st.columns(5)
        for i, row in enumerate(res_skus.data):
            with cols[i % 5]:
                # 1. Obtener imagen de 'Productos' y Ahorro
                ahorro, url_imagen = traer_info_galeria(row['mi_sku'])
                estilo_b, label_b = obtener_estilo_metal(ahorro)
                
                # 2. Limpieza de strings para evitar rotura de HTML
                nombre_safe = row['nombre_oficial'].replace("'", "&apos;").replace('"', "&quot;")
                
                # 3. Construcción de HTML
                badge_html = f'<div class="badge-metal" style="{estilo_b}">{label_b}</div>' if estilo_b else ""
                img_tag = f'<img src="{url_imagen}" referrerpolicy="no-referrer">' if url_imagen else '<div style="color:#ccc; font-size:12px;">📷 Sin imagen</div>'

                # 4. Renderizado
                st.markdown(f"""
                    <div class="card-container">
                        <div class="img-box">
                            {badge_html}
                            {img_tag}
                        </div>
                        <div class="product-title">{nombre_safe}</div>
                        <div style="color:#1abc9c; font-weight:bold; font-size:12px; margin-bottom:5px;">VER COMPARATIVA</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón de acción
                if st.button("Explorar", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params["sku"] = row['mi_sku']
                    st.rerun()
    else:
        st.warning("No se encontraron productos.")
