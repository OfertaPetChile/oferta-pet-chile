import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Configuración de página (Debe ser lo primero)
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# 2. Estilo Visual Personalizado (CSS)
st.markdown("""
    <style>
    .stApp { background-color: #f9f9f9; }
    .product-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #eee;
        height: 480px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .price-text {
        color: #2ecc71;
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
    }
    .product-title {
        font-size: 16px;
        font-weight: 600;
        height: 50px;
        overflow: hidden;
        margin-top: 10px;
    }
    .store-tag {
        background-color: #f1f1f1;
        padding: 4px 8px;
        border-radius: 5px;
        font-size: 12px;
        color: #555;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Cabecera
st.title("🐾 Oferta Pet Chile")
st.write("Encuentra el mejor precio para tu mascota.")

# 4. Buscador
query = st.text_input("Busca un alimento o producto:", "", placeholder="Ej: Cat it, Leonardo, o un SKU...")

if query:
    q = query.strip().upper()
    
    # 1. Buscamos el producto en la tabla maestra
    res_prod = supabase.table("productos_web").select("*").or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

    if res_prod.data:
        skus_encontrados = [str(p["mi_sku"]).strip() for p in res_prod.data]
        res_precios = supabase.table("historial_precios").select("mi_sku, precio").in_("mi_sku", skus_encontrados).execute()
        mapa_precios = {str(p["mi_sku"]).strip(): p["precio"] for p in res_precios.data}

        # 5. Renderizado en cuadrícula (3 columnas)
        cols = st.columns(3)
        
        for idx, p in enumerate(res_prod.data):
            sku_limpio = str(p["mi_sku"]).strip()
            precio_val = mapa_precios.get(sku_limpio, None)
            
            # Formatear precio
            precio_display = f"$ {precio_val:,}" if precio_val else "Próximamente"
            
            # Dibujar tarjeta en la columna correspondiente
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="product-card">
                    <img src="{p['imagen_url']}" style="width:100%; height:180px; object-fit:contain;">
                    <div class="product-title">{p['nombre_producto']}</div>
                    <p class="store-tag">📍 {p.get('nombre_tienda', 'Tienda')}</p>
                    <p style="font-size: 11px; color: #999; margin: 0;">SKU: {sku_limpio}</p>
                    <p class="price-text">{precio_display}</p>
                </div>
                """, unsafe_allow_html=True)
                # Botón real de Streamlit debajo de la tarjeta HTML
                st.link_button("Ver Oferta", p['enlace_tienda'], use_container_width=True)
                st.write("") # Espacio extra
                
    else:
        st.info(f"No hay resultados para '{query}'. Prueba con otra palabra clave.")
