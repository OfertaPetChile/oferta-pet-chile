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
    # Consulta simple a tu tabla de productos
    res = supabase.table("productos_web").select("*").ilike("nombre", f"%{query}%").limit(24).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df)
    else:
        st.warning("No encontramos ofertas para ese producto por ahora.")
