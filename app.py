import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc

# 1. Configuración de página
st.set_page_config(
   page_title="Oferta Pet Chile",
   page_icon="🐾",
   layout="wide"
)

# 2. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE APOYO PARA GALERÍA ---
def obtener_badge_ahorro(mi_sku):
    """Calcula ahorro y retorna el estilo del badge si aplica."""
    try:
        # 1. Buscar imagen y IDs en tabla Productos
        res_p = supabase.table("Productos").select("url_imagen, id_producto").eq("mi_sku", mi_sku).execute()
        if not res_p.data: return None, None, None
        
        url_img = next((p['url_imagen'].strip() for p in res_p.data if p.get('url_imagen')), "")
        
        # 2. Calcular ahorro con Historial
        ids = [p['id_producto'] for p in res_p.data]
        res_h = supabase.table("Historial_precios").select("precio, fecha").in_("id_producto", ids).execute()
        df = pd.DataFrame(res_h.data)
        if df.empty: return url_img, None, None
        
        precio_act = df.sort_values("fecha").iloc[-1]['precio']
        suelo_30d = df.groupby("fecha")['precio'].min().tail(30).mean()
        ahorro = int(((suelo_30d - precio_act) / suelo_30d) * 100) if suelo_30d > 0 else 0
        
        # 3. Definir Metal
        if ahorro >= 10:
            return url_img, "background: linear-gradient(135deg, #FFD700, #FDB931); color: #4B3B00;", f"{ahorro}% ORO"
        elif ahorro >= 5:
            return url_img, "background: linear-gradient(135deg, #E0E0E0, #BDBDBD); color: #333;", f"{ahorro}% PLATA"
        elif ahorro >= 1:
            return url_img, "background: linear-gradient(135deg, #CD7F32, #A0522D); color: #fff;", f"{ahorro}% BRONCE"
        
        return url_img, None, None
    except:
        return "", None, None

# --- LÓGICA DE NAVEGACIÓN ---
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS
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
        position: relative;
    }
    .badge-ahorro {
        position: absolute;
        top: 10px;
        left: 10px;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: bold;
        z-index: 10;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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

# --- VISTA 2: HOJA DE DETALLE (TU CÓDIGO INTACTO) ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.divider()

    # 1. Carga de Datos
    res_prod = supabase.table("Productos").select("id_producto, nombre_tienda, url_tienda, disponibilidad").eq("mi_sku", selected_sku).execute()
    
    if not res_prod.data:
        st.warning("Sin ofertas disponibles.")
        st.stop()

    datos_tabla = []
    historiales_por_id = {}
    
    for p in res_prod.data:
        res_hist = supabase.table("Historial_precios").select("fecha, precio").eq("id_producto", p['id_producto']).order("fecha", desc=True).execute()
        df_h = pd.DataFrame(res_hist.data)
        if not df_h.empty:
            tienda = p['nombre_tienda']
            id_p = p['id_producto']
            datos_tabla.append({
                "id_producto": id_p,
                "Tienda": tienda, 
                "Precio": df_h.iloc[0]['precio'], 
                "URL": p['url_tienda'],
                "Disponibilidad": p.get('disponibilidad')
            })
            historiales_por_id[id_p] = df_h.sort_values(by="fecha")

    # 2. AGRUPAR POR TIENDA
    tiendas_agrupadas = {}
    for item in datos_tabla:
        t = item['Tienda']
        if t not in tiendas_agrupadas:
            tiendas_agrupadas[t] = []
        tiendas_agrupadas[t].append(item)

    resumen_tiendas =[]
    for tienda, opciones in tiendas_agrupadas.items():
        opciones_ord = sorted(opciones, key=lambda x: x['Precio'])
        principal = opciones_ord[0]
        resumen_tiendas.append({
            "Tienda": tienda,
            "Precio_Min": principal['Precio'],
            "Disponibilidad": principal['Disponibilidad'],
            "Opciones": opciones_ord
        })

    df_resumen = pd.DataFrame(resumen_tiendas)
    
    # 3. MAPA DE COLORES
    colores_fijos = {
        "Punto Mascotas": "#a6a6a6", "LH Petshop": "#326475", "Distribuidora Lira": "#cd0201",
        "Pet Kingdom": "#6b1e46", "Laika": "#5e17eb", "PetBJ": "#0c15f5", "Amigales": "#00b0f0",
        "Superzoo": "#d504b9", "JardinZoo": "#31ab5c", "Tus Mascotas": "#c1ff72",
        "Laika Member": "#9662fe", "Petvet Repet": "#e2c78a", "BestForPets": "#C4FF1A",
        "Braloy": "#8aeef2", "Razaspet": "#ffcc11", "Petvet": "#907740", "CPyG": "#fb8bd0",
    } 

    mapa_colores = {t: colores_fijos.get(t, pc.qualitative.Alphabet[i % 26]) 
                    for i, t in enumerate(df_resumen['Tienda'].unique())}
    
    # 4. ORDENAMIENTO
    df_resumen['Dispo_limpia'] = df_resumen['Disponibilidad'].astype(str).str.strip().str.capitalize()
    df_resumen['prioridad_stock'] = df_resumen['Dispo_limpia'].apply(lambda x: 0 if "Disponible" in x or "Stock" in x else 1)
    df_resumen = df_resumen.sort_values(by=['prioridad_stock', 'Precio_Min'], ascending=[True, True]).reset_index(drop=True)

    # 5. RENDERIZADO DETALLE
    col_precios, col_grafica = st.columns([1.4, 2.6], gap="large")
    seleccion_tiendas = {}
    contador_grafica = 0

    with col_precios:
        st.markdown("#### 💰 Ofertas Actuales")
        # [Se mantiene todo tu bloque de CSS del selectbox e iteración de tarjetas del detalle...]
        # (Omitido aquí para brevedad, pero en tu script debe seguir tal cual)
        for i, row in df_resumen.iterrows():
            # ... tu lógica de tarjetas de detalle ...
            pass # Aquí va tu código original de la vista de detalle

# --- VISTA 1: GALERÍA PRINCIPAL (CORRECCIÓN DE RENDERIZADO) ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    # Consulta a SKUs_unicos
    stmt = supabase.table("SKUs_unicos").select("*")
    if query:
        q = query.strip().upper()
        stmt = stmt.or_(f"nombre_oficial.ilike.%{q}%,mi_sku.ilike.%{q}%")
    
    res = stmt.limit(20).execute()

    if res.data:
        cols = st.columns(5)
        for idx, row in enumerate(res.data):
            with cols[idx % 5]:
                sku = row['mi_sku']
                # Obtenemos imagen y medalla
                img_url, estilo_badge, texto_badge = obtener_badge_ahorro(sku)
                
                # FALLBACK: Si no hay imagen, usamos un placeholder para evitar que se rompa el diseño
                if not img_url:
                    img_url = "https://via.placeholder.com/160?text=Sin+Imagen"

                # UN SOLO BLOQUE HTML: Esto evita que Streamlit muestre el código como texto
                # Usamos estilos inline simples para asegurar compatibilidad
                badge_html = f'<div style="{estilo_badge} position:absolute; top:10px; left:10px; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:10px; z-index:10;">{texto_badge}</div>' if estilo_badge else ""
                
                card_content = f'''
                    <div style="background-color: white; border-radius: 12px; padding: 15px; border: 1px solid #eee; height: 320px; text-align: center; position: relative; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                        {badge_html}
                        <img src="{img_url}" style="width: 100%; height: 160px; object-fit: contain;" referrerpolicy="no-referrer">
                        <div style="font-size: 14px; font-weight: 600; color: #2c3e50; margin-top: 15px; height: 40px; overflow: hidden; line-height: 1.2;">
                            {row['nombre_oficial']}
                        </div>
                        <div style="color: #1abc9c; font-weight: bold; font-size: 13px; margin-top: 10px;">Ver comparativa</div>
                    </div>
                '''
                
                # Renderizamos el contenido visual
                st.markdown(card_content, unsafe_allow_html=True)
                
                # El botón de Streamlit va FUERA del markdown para que sea interactivo
                if st.button("Ver detalle", key=f"btn_{sku}", use_container_width=True):
                    st.query_params.sku = sku
                    st.rerun()
    else:
        st.info("No hay resultados.")
