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
    # 1. Limpieza de la búsqueda
    q = query.strip().upper() 
    
    # 2. Consulta simplificada: Buscamos coincidencia en nombre O en sku
    # Nota: Usamos .or_ con una sintaxis que Supabase entiende siempre
    try:
        res = supabase.table("productos_web") \
            .select("*") \
            .or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%") \
            .execute()

        if res.data and len(res.data) > 0:
            df = pd.DataFrame(res.data)
            st.success(f"Se encontraron {len(df)} resultados")
            
            # Mostramos la tabla básica para confirmar que hay datos
            columnas_existentes = [c for c in ["nombre_producto", "mi_sku", "precio", "imagen_url"] if c in df.columns]
            st.dataframe(df[columnas_existentes], use_container_width=True)
        else:
            # Si no hay resultados, probamos una búsqueda aún más simple (solo por una palabra)
            primera_palabra = q.split()[0]
            st.info(f"Buscando términos similares a '{primera_palabra}'...")
            
            res_retry = supabase.table("productos_web") \
                .select("*") \
                .ilike("nombre_producto", f"%{primera_palabra}%") \
                .execute()
                
            if res_retry.data:
                st.write("Quizás quisiste decir:")
                st.dataframe(pd.DataFrame(res_retry.data)[["nombre_producto", "mi_sku"]], use_container_width=True)
            else:
                st.error("No se encontró nada. Verifica que la tabla 'productos_web' tenga datos en Supabase.")
                
    except Exception as e:
        st.error(f"Error de conexión: {e}")
