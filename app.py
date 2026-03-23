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
    
    # 1. Buscamos coincidencias en la tabla maestra de productos
    res_prod = supabase.table("productos_web").select("*").or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

    if res_prod.data:
        # Extraemos solo los SKUs que sí encontramos para no pedir de más
        skus_encontrados = [p["mi_sku"] for p in res_prod.data]
        
        # 2. Buscamos los precios asociados a esos SKUs encontrados
        res_precios = supabase.table("historial_precios").select("mi_sku, precio").in_("mi_sku", skus_encontrados).execute()
        
        # Creamos un diccionario para cruzar datos rápido: { 'SKU123': 25000 }
        mapa_precios = {p["mi_sku"]: p["precio"] for p in res_precios.data}

        # 3. Construimos la lista final para mostrar
        resultados = []
        for p in res_prod.data:
            sku_actual = p["mi_sku"]
            resultados.append({
                "Producto": p["nombre_producto"],
                "SKU": sku_actual,
                "Precio": mapa_precios.get(sku_actual, "Sin stock/Próximamente"),
                "Tienda": p.get("nombre_tienda", "Ver tienda"),
                "Link": p["enlace_tienda"],
                "Imagen": p["imagen_url"]
            })
        
        df = pd.DataFrame(resultados)
        
        # 4. Renderizado de la tabla
        st.dataframe(
            df,
            column_config={
                "Imagen": st.column_config.ImageColumn("Foto"),
                "Precio": st.column_config.NumberColumn("Precio ($)", format="$ %d"),
                "Link": st.column_config.LinkColumn("Ir a la oferta")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(f"No hay resultados para '{query}'. Prueba con otra palabra clave.")
