import streamlit as st
from supabase import create_client
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾")

# Conexión a Supabase (usando los Secrets que pondrás en Streamlit)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🐾 Oferta Pet Chile")
st.write("Encuentra el mejor precio para tu mascota.")

# Buscador
query = st.text_input("Busca un alimento o producto:", "")

if query:
    # 1. Separamos la búsqueda en palabras (ej: "Leonardo" y "Senior")
    palabras = query.split()
    
    # 2. Iniciamos la consulta
    rpc_query = supabase.table("productos_web").select("*")
    
    # 3. FILTRO MULTI-COLUMNA: 
    # Para cada palabra que escriba el usuario, buscamos coincidencias en 
    # nombre_producto, nombre_tienda (si la tienes) y mi_sku.
    for palabra in palabras:
        # Usamos .or_ para que busque en cualquiera de esas columnas
        # Si tienes una columna con el nombre original de la tienda, agrégala aquí
        condicion = f"nombre_producto.ilike.%{palabra}%,mi_sku.ilike.%{palabra}%"
        rpc_query = rpc_query.or_(condicion)
    
    res = rpc_query.execute()

    if res.data:
        df = pd.DataFrame(res.data)
        
        # 4. Agrupamos por mi_sku para que el usuario vea la "Ficha Única"
        # y debajo o al lado vea las diferentes ofertas.
        st.success(f"Resultados encontrados:")

        for sku, grupo in df.groupby("mi_sku"):
            with st.container():
                # Mostramos un encabezado por cada producto único (mi_sku)
                col1, col2 = st.columns([1, 4])
                
                # Intentamos sacar la imagen del primer registro del grupo
                with col1:
                    img = grupo["imagen_url"].iloc[0] if "imagen_url" in grupo.columns else None
                    if img:
                        st.image(img, width=100)
                
                with col2:
                    nombre_principal = grupo["nombre_producto"].iloc[0]
                    st.subheader(f"{nombre_principal}")
                    st.caption(f"SKU Interno: {sku}")
                
                # Mostramos la tablita de precios de las distintas tiendas para ESE SKU
                columnas_tienda = ["nombre_tienda", "precio", "url_producto"] # Ajusta según tus nombres
                df_tiendas = grupo[[c for c in columnas_tienda if c in grupo.columns]]
                st.table(df_tiendas)
                st.divider()
    else:
        st.warning(f"No encontramos nada para '{query}'. Intenta con términos más generales.")
