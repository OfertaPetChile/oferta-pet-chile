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

# --- VISTA 2: HOJA DE DETALLE ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.divider()

    # 1. Carga de Datos (Asegúrate de incluir disponibilidad)
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
        # Ordenamos opciones por precio (la más barata primero por defecto)
        opciones_ord = sorted(opciones, key=lambda x: x['Precio'])
        principal = opciones_ord[0]
        resumen_tiendas.append({
            "Tienda": tienda,
            "Precio_Min": principal['Precio'],
            "Disponibilidad": principal['Disponibilidad'],
            "Opciones": opciones_ord
        })

    df_resumen = pd.DataFrame(resumen_tiendas)
    
    # 3. GENERAR MAPA DE COLORES ANTES DE ORDENAR
    colores_fijos = {
        "Punto Mascotas": "#a6a6a6",   
        "LH Petshop": "#326475",       
        "Distribuidora Lira": "#cd0201", 
        "Pet Kingdom": "#6b1e46",      
        "Laika": "#5e17eb",            
        "PetBJ": "#0c15f5",            
        "Amigales": "#00b0f0",         
        "Superzoo": "#d504b9",         
        "JardinZoo": "#31ab5c",        
        "Tus Mascotas": "#c1ff72",     
        "Laika Member": "#9662fe",     
        "Petvet Repet": "#e2c78a",    
        "BestForPets": "#C4FF1A",      
        "Braloy": "#8aeef2",           
        "Razaspet": "#ffcc11",        
        "Petvet": "#907740",           
        "CPyG": "#fb8bd0",            
    } 

    mapa_colores = {t: colores_fijos.get(t, pc.qualitative.Alphabet[i % 26]) 
                    for i, t in enumerate(df_resumen['Tienda'].unique())}
    
    # 4. ORDENAMIENTO POR STOCK Y PRECIO MÍNIMO
    df_resumen['Dispo_limpia'] = df_resumen['Disponibilidad'].astype(str).str.strip().str.capitalize()
    df_resumen['prioridad_stock'] = df_resumen['Dispo_limpia'].apply(lambda x: 0 if "Disponible" in x or "Stock" in x else 1)
    df_resumen = df_resumen.sort_values(by=['prioridad_stock', 'Precio_Min'], ascending=[True, True]).reset_index(drop=True)

    # 5. RENDERIZADO
    col_precios, col_grafica = st.columns([1.4, 2.6], gap="large")
    seleccion_tiendas = {}
    contador_grafica = 0

    with col_precios:
        st.markdown("#### 💰 Ofertas Actuales")
        st.markdown("""
            <style>
                /* 1. POSICIÓN DE LA CARD (Contenedor del selectbox) */
                [data-testid="stVerticalBlock"] > div:has(div[data-testid="stSelectbox"]) {
                    margin-top: 0px !important; 
                    margin-bottom: -4px !important;
                    display: flex;
                    justify-content: center;
                    min-height: 45px !important; 
                }

                div[data-testid="stSelectbox"] {
                    width: 90% !important; 
                    margin-top: 1px !important; 
                    margin-bottom: 3px !important;
                    z-index: 10;
                }

                /* 2. EL TEXTO SELECCIONADO  */
                div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
                    border-radius: 20px !important; 
                    height: 35px !important; 
                    min-height: 35px !important; 
                    border: 1px solid #ddd !important;
                    background-color: #fcfcfc !important;
                    display: flex !important;
                    align-items: center !important;
                }

                /* Tamaño de letra del valor seleccionado */
                div[data-testid="stSelectbox"] [data-baseweb="select"] * {
                    font-size: 12px !important; 
                }
                
                /* 3. LA LISTA DESPLEGABLE (EL POPUP QUE SE ABRE) */                
                div[role="listbox"] li, 
                div[role="listbox"] div,
                div[role="listbox"] span,
                [data-baseweb="popover"] * {
                    font-size: 12px !important; 
                }

                /* Altura de las filas en la lista para que coincida con la letra chica */
                div[role="option"] {
                    min-height: 24px !important;
                    padding-top: 2px !important;
                    padding-bottom: 2px !important;
                }

            </style>
        """, unsafe_allow_html=True)
       
        for i, row in df_resumen.iterrows():
            tienda = row['Tienda']
            opciones = row['Opciones']
            tiene_opciones = len(opciones) > 1
            
            c_check, c_card = st.columns([0.1, 0.9])
            
            with c_card:
                # 1. DEFINICIÓN DE ALTURAS
                if tiene_opciones:
                    h_total = "105px"
                    # En tarjeta doble, usamos un margen negativo sutil para subir el bloque superior
                    m_top_contenido = "-8px" 
                else:
                    h_total = "52px"
                    # En tarjeta simple, subimos más para compensar el espacio del contenedor
                    m_top_contenido = "-8px"

                # 2. FONDO DE LA TARJETA (Z-INDEX 0)
                color_t = mapa_colores.get(tienda, "#eee")
                esta_agotado_init = "Agotado" in str(opciones[0]['Disponibilidad']).capitalize()
                es_top = (i == 0 and not esta_agotado_init)
                bg_c = '#f0fff4' if es_top else ('#fafafa' if esta_agotado_init else 'white')
                brd_c = '#2ecc71' if es_top else '#eee'

                st.markdown(
                    f'<div style="background-color:{bg_c}; border:1px solid {brd_c}; '
                    f'border-radius:8px; height:{h_total}; width:100%; position:absolute; '
                    f'z-index:0; box-shadow:0 2px 4px rgba(0,0,0,0.02);"></div>', 
                    unsafe_allow_html=True
                )

                # 3. BLOQUE DE INFORMACIÓN (Centrado en la franja superior de 52px)
                op_id = f"sel_{tienda}_{selected_sku}"
                opcion_actual = st.session_state.get(op_id, opciones[0]) if tiene_opciones else opciones[0]
                
                precio_cl = f"$ {opcion_actual['Precio']:,.0f}".replace(",", ".")
                opac = "0.5" if "Agotado" in str(opcion_actual['Disponibilidad']).capitalize() else "1.0"
                btn_bg = "#ccc" if opac == "0.5" else "#1abc9c"

                # m_top_contenido es la clave para el centrado
                info_html = (
                    f'<div style="display:flex; justify-content:space-between; align-items:center; '
                    f'padding:0 12px; height:52px; position:relative; z-index:2; margin-top:{m_top_contenido};">'
                    f'<div style="display:flex; align-items:center; width:150px;">'
                    f'<div style="width:12px; height:12px; border-radius:50%; background-color:{color_t}; margin-right:10px;"></div>'
                    f'<div style="opacity:{opac}; font-size:13px; font-weight:800; color:#333; line-height:1.2;">{tienda}</div>'
                    f'</div>'
                    f'<div style="flex-grow:1; text-align:right; margin-right:12px; opacity:{opac};">'
                    f'<span style="font-size:15px; font-weight:800; color:#2c3e50;">{precio_cl}</span>'
                    f'</div>'
                    f'<div><a href="{opcion_actual["URL"]}" target="_blank" style="background-color:{btn_bg}; '
                    f'color:white; padding:6px 14px; border-radius:6px; text-decoration:none; font-weight:bold; '
                    f'font-size:11px; pointer-events:{"none" if opac=="0.5" else "auto"}; opacity:{opac};">'
                    f'{"Agotado" if opac=="0.5" else "Ir al sitio"}</a></div>'
                    f'</div>'
                )
                st.markdown(info_html, unsafe_allow_html=True)

                # 4. DESPLEGABLE
                if tiene_opciones:
                    fmt = lambda x: f"Variedad: $ {x['Precio']:,.0f} - {x['Disponibilidad']}".replace(",",".")
                    opcion_elegida = st.selectbox(
                        f"Variedad en {tienda}", opciones, format_func=fmt, 
                        key=op_id, label_visibility="collapsed"
                    )
                else:
                    opcion_elegida = opciones[0]                       
                   
            with c_check:
                # Alineación del checkbox para que coincida con el centro de los primeros 52px
                st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
                check_val = (not esta_agotado_init and contador_grafica < 5)
                if check_val: contador_grafica += 1
                seleccion_tiendas[tienda] = {
                    "active": st.checkbox("", value=check_val, key=f"ch_{tienda}_{selected_sku}"),
                    "id_producto": opcion_elegida['id_producto']
                }    
               
    with col_grafica:
        st.markdown("#### 📈 Evolución Histórica")
        tiendas_a_graficar = [t for t, v in seleccion_tiendas.items() if v["active"]]
        
        if tiendas_a_graficar:
            fig = go.Figure()
            for t in tiendas_a_graficar:
                id_p = seleccion_tiendas[t]["id_producto"]
                if id_p in historiales_por_id:
                    df_h = historiales_por_id[id_p]
                    fig.add_trace(go.Scatter(
                        x=df_h['fecha'], y=df_h['precio'], 
                        name=t, mode='lines',
                        line=dict(color=mapa_colores[t], width=3)
                    ))
            fig.update_layout(template="plotly_white", height=500, margin=dict(l=0,r=0,t=10,b=0), 
                              showlegend=False, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

# --- VISTA 1: GALERÍA PRINCIPAL ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    # 1. Lógica de búsqueda unificada
    if query:
       q = query.strip().upper()
       
       # A. Buscamos en Productos (Traemos todo de una: nombre, sku e imagen)
       # Esto evita hacer un select por cada fila después.
       res_prod = supabase.table("Productos")\
           .select("mi_sku, url_imagen, nombre_producto, id_producto")\
           .ilike("nombre_producto", f"%{q}%")\
           .limit(40).execute()
       
       # B. Buscamos en SKUs_unicos (Solo si es necesario)
       res_sku = supabase.table("SKUs_unicos")\
           .select("mi_sku, nombre_oficial")\
           .ilike("nombre_oficial", f"%{q}%")\
           .limit(20).execute()
   
       vistos = set()
       productos_lista = []
   
       # Mapeo rápido de nombres oficiales para acceso instantáneo
       nombres_maestros = {s['mi_sku']: s['nombre_oficial'] for s in res_sku.data}
   
       # Procesamos todo en un solo paso
       for p in res_prod.data:
           id_ref = p['mi_sku'] if p['mi_sku'] else f"ID_{p['id_producto']}"
           if id_ref not in vistos:
               productos_lista.append({
                   "id": id_ref,
                   # Si tenemos el nombre oficial en nuestro mapa, lo usamos; si no, el de la tienda
                   "nombre_final": nombres_maestros.get(p['mi_sku']) or p['nombre_producto'],
                   "img": p['url_imagen'],
                   "es_grupo": bool(p['mi_sku'])
               })
               vistos.add(id_ref)
    else:
       res_default = supabase.table("Productos")\
           .select("mi_sku, url_imagen, nombre_producto")\
           .not_.is_("mi_sku", "null")\
           .order("created_at", desc=True)\
           .limit(20).execute()
           
       productos_lista = []
       vistos = set()
       for p in res_default.data:
           if p['mi_sku'] not in vistos:
               # Aquí podrías cruzar con SKUs_unicos si quieres el nombre oficial
               productos_lista.append({
                   "id": p['mi_sku'],
                   "nombre_final": p['nombre_producto'], # O busca el oficial si prefieres
                   "img": p['url_imagen'],
                   "es_grupo": True
               })
               vistos.add(p['mi_sku'])
   
    else:
        res_default = supabase.table("SKUs_unicos").select("*").limit(20).execute()
        productos_lista = []
        for s in res_default.data:
            img_res = supabase.table("Productos").select("url_imagen").eq("mi_sku", s['mi_sku']).limit(1).execute()
            img = img_res.data[0]['url_imagen'] if img_res.data else ""
            productos_lista.append({"id": s['mi_sku'], "nombre": s['nombre_oficial'], "img": img})

    # 2. Renderizado
    if productos_lista:
        cols = st.columns(5)
        for idx, p in enumerate(productos_lista):
            with cols[idx % 5]:
                # Limpiamos nombre para el f-string
                nombre_a_mostrar = p.get('nombre_oficial') or p.get('nombre') or "Producto"
                n_display = nombre_a_mostrar.replace('"', '').replace("'", "")

                st.markdown(
                   f'<div class="product-card">'
                   f'<img src="{p["img"]}" style="width:100%; height:150px; object-fit:contain;" referrerpolicy="no-referrer">'
                   f'<div>'
                   f'<div class="product-title" style="height:45px; overflow:hidden; font-size:13px; line-height:1.2; font-weight:700; color:#333;">{n_display}</div>'
                   f'<div class="ver-detalle-text" style="color:#e67e22; font-weight:bold; font-size:11px; margin-top:5px;">Ver comparativa</div>'
                   f'</div>'
                   f'</div>',
                   unsafe_allow_html=True
                )
               
                # Botón invisible sobre la card o botón inferior (según tu preferencia)
                if st.button("Ver detalle", key=f"btn_{p['id']}_{idx}", use_container_width=True):
                   st.query_params.sku = p['id']
                   st.rerun()
    else:
        st.info("No se encontraron productos. Intenta con otra palabra.")
