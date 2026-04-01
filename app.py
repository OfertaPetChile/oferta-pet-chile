import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIONES DE LÓGICA ---
def obtener_estilo_metal(porcentaje):
    if porcentaje >= 10:
        return "linear-gradient(135deg, #FFD700, #FDB931)", "#4B3B00", f"{porcentaje}% ORO"
    elif porcentaje >= 5:
        return "linear-gradient(135deg, #E0E0E0, #BDBDBD)", "#333", f"{porcentaje}% PLATA"
    elif porcentaje >= 1:
        return "linear-gradient(135deg, #CD7F32, #A0522D)", "#fff", f"{porcentaje}% BRONCE"
    return None, None, None

def traer_datos_galeria(mi_sku):
    """Obtiene imagen de Productos y ahorro para la tarjeta."""
    try:
        res = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res.data: return 0, None
        img = next((p['url_imagen'].strip() for p in res.data if p.get('url_imagen')), None)
        
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

# --- NAVEGACIÓN ---
sku_query = st.query_params.get("sku")

if sku_query:
    # ==========================================
    # VISTA 2: DETALLE DEL PRODUCTO
    # ==========================================
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # Obtener nombre oficial e imagen representativa
    res_m = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", sku_query).single().execute()
    nombre_prod = res_m.data['nombre_oficial'] if res_m.data else "Producto"
    
    st.title(f"📊 {nombre_prod}")
    st.caption(f"SKU Interno: {sku_query}")

    # Obtener todas las tiendas que venden este SKU
    res_p = supabase.table("Productos").select("*").eq("mi_sku", sku_query).execute()
    
    if res_p.data:
        col_list, col_graph = st.columns([1.2, 2])
        historiales_dict = {}
        cards_data = []

        for p in res_p.data:
            # Traer historial de cada tienda
            res_h = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha").execute()
            if res_h.data:
                df_h = pd.DataFrame(res_h.data)
                historiales_dict[p['nombre_tienda']] = df_h
                cards_data.append({
                    "Tienda": p['nombre_tienda'],
                    "Precio": df_h.iloc[-1]['precio'],
                    "URL": p['url_tienda'],
                    "Stock": p.get('disponibilidad', 'Desconocido')
                })

        with col_list:
            st.subheader("Opciones de Compra")
            for item in sorted(cards_data, key=lambda x: x['Precio']):
                with st.container(border=True):
                    c1, c2 = st.columns([2, 1])
                    c1.markdown(f"**{item['Tienda']}**")
                    c1.caption(f"Stock: {item['Stock']}")
                    c2.markdown(f"### ${item['Precio']:,.0f}".replace(",", "."))
                    st.link_button("Ir a la tienda ➔", item['URL'], use_container_width=True)

        with col_graph:
            st.subheader("Evolución de Precios")
            fig = go.Figure()
            for tienda, df_plot in historiales_dict.items():
                fig.add_trace(go.Scatter(
                    x=df_plot['fecha'], 
                    y=df_plot['precio'], 
                    name=tienda, 
                    mode='lines+markers',
                    line=dict(width=3)
                ))
            fig.update_layout(
                height=500, 
                hovermode="x unified", 
                margin=dict(l=0,r=0,b=0,t=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se encontraron ofertas activas para este producto.")

else:
    # ==========================================
    # VISTA 1: GALERÍA DE INICIO
    # ==========================================
    st.title("🐾 Oferta Pet Chile")
    busqueda = st.text_input("Buscar producto o marca...", placeholder="Ej: Leonardo, Brit, Cat it...").strip()

    # Consulta a Supabase
    query_skus = supabase.table("SKUs_unicos").select("*")
    if busqueda:
        query_skus = query_skus.ilike("nombre_oficial", f"%{busqueda}%")
    res_skus = query_skus.limit(20).execute()

    if res_skus.data:
        cols = st.columns(5)
        for i, row in enumerate(res_skus.data):
            with cols[i % 5]:
                # 1. Obtener imagen de 'Productos' y Ahorro
                ahorro, url_img = traer_datos_galeria(row['mi_sku'])
                bg, txt, label = obtener_estilo_metal(ahorro)
                
                # 2. Sanitización (Limpiar comillas que rompen el HTML)
                nombre_clean = row['nombre_oficial'].replace("'", "").replace('"', "")

                # 3. HTML mediante componentes (Para evitar que se vea como texto)
                badge_html = f'<div style="position: absolute; top: 10px; left: 10px; background: {bg}; color: {txt}; padding: 4px 10px; border-radius: 6px; font-size: 10px; font-weight: 900; z-index: 100; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">{label}</div>' if bg else ""
                
                card_html = f"""
                <div style="font-family: sans-serif; border: 1px solid #eee; border-radius: 12px; padding: 15px; height: 320px; position: relative; background: white; display: flex; flex-direction: column; align-items: center; justify-content: space-between;">
                    {badge_html}
                    <div style="height: 160px; display: flex; align-items: center; justify-content: center;">
                        <img src="{url_img if url_img else ''}" style="max-height: 160px; max-width: 100%; object-fit: contain;" referrerpolicy="no-referrer">
                    </div>
                    <div style="font-size: 13px; font-weight: 600; text-align: center; color: #333; margin: 10px 0; height: 35px; overflow: hidden; line-height: 1.2;">{nombre_clean}</div>
                    <div style="color: #1abc9c; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;">VER COMPARATIVA</div>
                </div>
                """
                components.html(card_html, height=340)
                
                # 4. Botón real de Streamlit para la navegación
                if st.button("Explorar", key=f"btn_{row['mi_sku']}", use_container_width=True):
                    st.query_params["sku"] = row['mi_sku']
                    st.rerun()
    else:
        st.info("No hay productos que coincidan con tu búsqueda.")
