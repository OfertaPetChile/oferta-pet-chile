import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# Conexión Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES CORE ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "background: linear-gradient(135deg, #FFD700, #FDB931); color: #4B3B00;", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "background: linear-gradient(135deg, #E0E0E0, #BDBDBD); color: #333;", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "background: linear-gradient(135deg, #CD7F32, #A0522D); color: #fff;", f"{porcentaje}% BRONCE"
    return None, None

def traer_info_producto(mi_sku):
    """Obtiene imagen de la tabla Productos y calcula el ahorro."""
    try:
        res_p = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res_p.data: return 0, None
        
        # Imagen aleatoria de cualquiera de las tiendas que tenga ese SKU
        img = next((p['url_imagen'].strip() for p in res_p.data if p.get('url_imagen')), None)
        
        # Ahorro promedio 30 días
        ids = [p['id_producto'] for p in res_p.data]
        res_h = supabase.table("Historial_precios").select("precio, fecha").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        if df.empty: return 0, img
        
        precio_act = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_act) / suelo_30d) * 100) if suelo_30d > 0 else 0
        return ahorro, img
    except:
        return 0, None

# --- CSS GLOBAL ---
st.markdown("""
    <style>
    .card-pro {
        background: white; border: 1px solid #eee; border-radius: 12px;
        padding: 15px; text-align: center; height: 380px;
        position: relative; display: flex; flex-direction: column; justify-content: space-between;
    }
    .img-container {
        height: 160px; width: 100%; position: relative;
        display: flex; align-items: center; justify-content: center;
    }
    .img-container img { max-height: 160px; max-width: 100%; object-fit: contain; }
    .badge-metal {
        position: absolute; top: 0; left: 0; padding: 4px 10px;
        border-radius: 6px; font-weight: 900; font-size: 10px; z-index: 99;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .product-title {
        font-size: 14px; font-weight: 600; color: #333;
        height: 40px; overflow: hidden; margin: 10px 0; line-height: 1.2;
    }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE NAVEGACIÓN ---
selected_sku = st.query_params.get("sku")

if selected_sku:
    # --- VISTA 2: DETALLE DEL PRODUCTO ---
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # 1. Obtener nombre e imagen
    res_m = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre = res_m.data['nombre_oficial'] if res_m.data else "Producto"
    st.title(f"📊 {nombre}")

    # 2. Obtener tiendas y ofertas
    res_off = supabase.table("Productos").select("*").eq("mi_sku", selected_sku).execute()
    
    if res_off.data:
        col_list, col_graph = st.columns([1, 2])
        historiales = {}
        precios_lista = []

        for p in res_off.data:
            res_h = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha").execute()
            if res_h.data:
                df_h = pd.DataFrame(res_h.data)
                historiales[p['nombre_tienda']] = df_h
                precios_lista.append({
                    "Tienda": p['nombre_tienda'], 
                    "Precio": df_h.iloc[-1]['precio'], 
                    "URL": p['url_tienda'],
                    "Stock": p.get('disponibilidad', 'N/A')
                })

        with col_list:
            st.subheader("Mejores Ofertas")
            for item in sorted(precios_lista, key=lambda x: x['Precio']):
                with st.container(border=True):
                    st.markdown(f"**{item['Tienda']}**")
                    st.markdown(f"### ${item['Precio']:,.0f}".replace(",", "."))
                    st.caption(f"Disponibilidad: {item['Stock']}")
                    st.link_button("Ir a la tienda", item['URL'], use_container_width=True)

        with col_graph:
            st.subheader("Historial de Precios")
            fig = go.Figure()
            for tienda, df_p in historiales.items():
                fig.add_trace(go.Scatter(x=df_p['fecha'], y=df_p['precio'], name=tienda, mode='lines+markers'))
            fig.update_layout(height=450, hovermode="x unified", margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay ofertas registradas para este producto.")

else:
    # --- VISTA 1: GALERÍA DE INICIO ---
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Brit Care...").strip()

    # Carga de SKUs
    if query:
        res = supabase.table("SKUs_unicos").select("*").ilike("nombre_oficial", f"%{query}%").limit(20).execute()
    else:
        res = supabase.table("SKUs_unicos").select("*").limit(20).execute()

    if res.data:
        cols = st.columns(5)
        for i, row in enumerate(res.data):
            with cols[i % 5]:
                # Datos variables (Imagen desde Productos y Ahorro)
                ahorro, img_url = traer_info_producto(row['mi_sku'])
                estilo_b, label_b = obtener_estilo_metal(ahorro)
                
                # Sanitización de nombre para evitar rotura de HTML
                nombre_clean = row['nombre_oficial'].replace("'", "&apos;").replace('"', "&quot;")
                
                # HTML de la Tarjeta
                badge_html = f'<div class="badge-metal" style="{estilo_b}">{label_b}</div>' if estilo_b else ""
                img_tag = f'<img src="{img_url}" referrerpolicy="no-referrer">' if img_url else '<div style="color:#ccc; font-size:11px;">📷 Sin foto</div>'

                st.markdown(f"""
                    <div class="card-pro">
                        <div class="img-container">
                            {badge_html}
                            {img_tag}
                        </div>
                        <div class="product-title">{nombre_clean}</div>
                        <div style="color:#1abc9c; font-weight:bold; font-size:11px;">VER COMPARATIVA</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if st.button("Explorar", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params["sku"] = row['mi_sku']
                    st.rerun()
    else:
        st.info("No se encontraron resultados.")
