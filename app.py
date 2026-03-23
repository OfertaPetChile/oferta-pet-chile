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
    
    # 1. Buscamos el producto en la tabla maestra
    res_prod = supabase.table("productos_web").select("*").or_(f"nombre_producto.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

    if res_prod.data:
        # Extraemos los SKUs encontrados y limpiamos posibles espacios
        skus_encontrados = [str(p["mi_sku"]).strip() for p in res_prod.data]
        
        # 2. Buscamos los precios para esos SKUs específicos
        res_precios = supabase.table("historial_precios").select("mi_sku, precio").in_("mi_sku", skus_encontrados).execute()
        
        # Creamos el mapa de precios (limpiando también los SKUs de la tabla de precios)
        mapa_precios = {str(p["mi_sku"]).strip(): p["precio"] for p in res_precios.data}

        # 3. Construimos la lista final uniendo los datos en Python
        resultados = []
        for p in res_prod.data:
            sku_limpio = str(p["mi_sku"]).strip()
            precio = mapa_precios.get(sku_limpio, "Próximamente") # Si no hay precio, sale este aviso
            
            resultados.append({
                "Producto": p["nombre_producto"],
                "SKU": sku_limpio,
                "Precio": precio,
                "Tienda": p.get("nombre_tienda", "Ver Tienda"),
                "Link": p["enlace_tienda"],
                "Imagen": p["imagen_url"]
            })
        
        df = pd.DataFrame(resultados)
        
        # 4. Tabla profesional con imágenes
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
