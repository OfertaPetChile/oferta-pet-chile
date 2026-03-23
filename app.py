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

# --- VISTA 2: HOJA DE DETALLE (Comparativa) ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # Buscamos el nombre oficial en Maestro_SKU
    res_maestro = supabase.table("Maestro_SKU").select("nombre_maestro").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_maestro"] if res_maestro.data else "Producto"

    st.title(f"📊 Comparativa: {nombre_oficial}")
    st.write(f"Viendo historial de precios para el SKU: {selected_sku}")
    
    # Aquí irá tu lógica de historial de 3 meses en el siguiente paso
    st.info("Próximo paso: Gráfica de evolución y lista de tiendas oficiales.")

# --- VISTA 1: GALERÍA PRINCIPAL (Maestro_SKU) ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    if query:
        q = query.strip().upper()
        
        # BUSQUEDA EN MAESTRO_SKU (Nombres oficiales)
        res = supabase.table("Maestro_SKU").select("*").or_(f"nombre_maestro.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

        if res.data:
            df_maestro = pd.DataFrame(res.data)
            
            # 5 Columnas
            cols = st.columns(5)
            
            for idx, row in df_maestro.iterrows():
                with cols[idx % 5]:
                    # La Card HTML
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{row['imagen_url_maestra']}" style="width:100%; height:160px; object-fit:contain;">
                        <div>
                            <div class="product-title">{row['nombre_maestro']}</div>
                            <div class="ver-detalle-text">Ver comparativa</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # El botón justo debajo, pero visualmente "pegado" por el diseño
                    if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                        st.query_params.sku = row['mi_sku']
                        st.rerun()
        else:
            st.info("No encontramos coincidencias en el catálogo maestro.")
