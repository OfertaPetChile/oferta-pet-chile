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
    # 1. Buscamos en 'nombre_producto' ignorando mayúsculas/minúsculas
    res = supabase.table("productos_web").select("*").ilike("nombre_producto", f"%{query}%").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # 2. Configuramos las columnas para que se vean bien
        # Usamos nombres que existan en tu tabla según tu imagen anterior
        columnas = ["nombre_producto", "mi_sku", "imagen_url"]
        df_final = df[[c for c in columnas if c in df.columns]]
        
        # 3. Mostramos los resultados en una tabla bonita
        st.write(f"Resultados para: **{query}**")
        st.dataframe(
            df_final, 
            column_config={
                "imagen_url": st.column_config.ImageColumn("Vista Previa"),
                "nombre_producto": "Producto",
                "mi_sku": "SKU"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning(f"No hay resultados exactos para '{query}'. Prueba con otra palabra (ej: 'Cat it' o 'Voyageur').")
