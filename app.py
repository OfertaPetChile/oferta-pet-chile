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
        for i, row in df_resumen.iterrows():
            tienda = row['Tienda']
            opciones = row['Opciones']
            tiene_opciones = len(opciones) > 1
            
            c_check, c_card = st.columns([0.1, 0.9])
            
            with c_card:
                # 1. DEFINICIÓN DE ALTURAS SEGÚN ESQUEMA [Ref: image_039324.png]
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

                # 4. DESPLEGABLE (Ubicado en la franja inferior de 52px)
                if tiene_opciones:
                    # m_top_select negativo para "succionar" el widget hacia el centro de la mitad inferior
                    m_top_select = "-12px"
                    st.markdown(f'<div style="margin-top:{m_top_select};"></div>', unsafe_allow_html=True)
                    
                    fmt = lambda x: f"Variedad: $ {x['Precio']:,.0f} - {x['Disponibilidad']}"
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

    if query:
        q = query.strip().upper()
        res = supabase.table("SKUs_unicos").select("*").or_(f"nombre_oficial.ilike.%{q}%,mi_sku.ilike.%{q}%").execute()

        if res.data:
            df_maestro = pd.DataFrame(res.data)
            cols = st.columns(5)
            for idx, row in df_maestro.iterrows():
                with cols[idx % 5]:
                    nombre_card = row.get('nombre_oficial', 'Producto')
                    img_url = row.get('imagen_url_maestra', '')
                    st.markdown(f'''
                        <div class="product-card">
                            <img src="{img_url}" style="width:100%; height:160px; object-fit:contain;">
                            <div>
                                <div class="product-title">{nombre_card}</div>
                                <div class="ver-detalle-text">Ver comparativa</div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
                    if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                        st.query_params.sku = row['mi_sku']
                        st.rerun()
        else:
            st.info("No hay resultados.")
