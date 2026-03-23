import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Configuración de página
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# 2. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE NAVEGACIÓN ---
# Revisamos si hay un SKU seleccionado en la URL
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS
st.markdown("""
    <style>
    .product-card {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #eee;
        height: 320px;
        text-align: center;
        margin-bottom: 10px;
    }
    .product-title {
        font-size: 13px;
        font-weight: 600;
        height: 40px;
        overflow: hidden;
        margin-top: 8px;
        color: #333;
    }
    .price-range {
        color: #2ecc71;
        font-size: 16px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VISTA 2: DETALLE DEL PRODUCTO ---
if selected_sku:
    if st.button("⬅️ Volver al inicio"):
        st.query_params.clear()
        st.rerun()

    # Aquí llamarías a tu gráfica de precios e historial (Paso siguiente)
    st.title(f"Detalle del Producto: {selected_sku}")
    st.info("Aquí insertaremos la gráfica de 3 meses y la lista de tiendas oficiales.")
    # (Lógica de historial de precios irá aquí)

# --- VISTA 1: GALERÍA PRINCIPAL ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    if query:
        q = query.strip().upper()
        # Traemos productos únicos agrupados por mi_sku en la mente de Python
        res = supabase.table("productos_web").select("*").or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

        if res.data:
            df = pd.DataFrame(res.data)
            # Agrupamos para mostrar solo una tarjeta por SKU
            df_unicos = df.drop_duplicates(subset=['mi_sku'])
            
            # 5 Columnas para que sea compacto
            cols = st.columns(5)
            
            for idx, row in df_unicos.iterrows():
                with cols[idx % 5]:
                    with st.container():
                        st.markdown(f"""
                        <div class="product-card">
                            <img src="{row['imagen_url']}" style="width:100%; height:150px; object-fit:contain;">
                            <div class="product-title">{row['nombre_producto']}</div>
                            <p class="price-range">Ver comparativa</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Al hacer clic, actualizamos la URL con el SKU
                        if st.button("Ver detalle", key=row['mi_sku'], use_container_width=True):
                            st.query_params.sku = row['mi_sku']
                            st.rerun()
        else:
            st.info("No encontramos ese producto.")
