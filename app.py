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
    q = query.strip().upper()
    
    # 1. Buscamos en productos_web y pedimos que traiga los datos de historial_precios
    # Usamos mi_sku como puente entre ambas tablas
    res = supabase.table("productos_web") \
        .select("nombre_producto, mi_sku, imagen_url, enlace_tienda, historial_precios(precio, fecha)") \
        .or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%") \
        .execute()

    if res.data:
        # 2. Aplanamos los datos para que Streamlit los entienda
        datos_planos = []
        for item in res.data:
            # Sacamos el precio más reciente de la lista de historial
            precios = item.get("historial_precios", [])
            ultimo_precio = precios[0]["precio"] if precios else "N/A"
            
            datos_planos.append({
                "Producto": item["nombre_producto"],
                "SKU": item["mi_sku"],
                "Precio": ultimo_precio,
                "Imagen": item["imagen_url"],
                "Link": item["enlace_tienda"]
            })
        
        df = pd.DataFrame(datos_planos)
        st.success(f"Encontramos {len(df)} coincidencias:")
        
        # 3. Mostramos la tabla profesional
        st.dataframe(
            df,
            column_config={
                "Imagen": st.column_config.ImageColumn("Vista"),
                "Precio": st.column_config.NumberColumn("Precio", format="$ %d"),
                "Link": st.column_config.LinkColumn("Ir a la tienda")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning(f"No hay resultados para '{query}'. Prueba con 'CAT IT' o 'VOYAGEUR'.")
