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
            
            # 1. Columnas principales: Checkbox | Contenedor de Tarjeta
            c_check, c_card = st.columns([0.1, 0.9])
            
            with c_card:
                # --- AQUÍ ESTÁ EL TRUCO ---
                # Ponemos el desplegable al inicio de la columna de la tarjeta
                if len(opciones) > 1:
                    fmt = lambda x: f"$ {x['Precio']:,.0f} - {x['Disponibilidad']}"
                    opcion_elegida = st.selectbox(
                        f"Variedades en {tienda}", # Etiqueta pequeña
                        opciones, 
                        format_func=fmt, 
                        key=f"sel_{tienda}_{selected_sku}",
                        label_visibility="collapsed" # Escondemos el texto para que parezca parte de la tarjeta
                    )
                else:
                    opcion_elegida = opciones[0]

                # 2. Extraer datos de la opción (puede cambiar según el selectbox)
                precio_val = opcion_elegida['Precio']
                url_tienda = opcion_elegida['URL']
                dispo_status = str(opcion_elegida['Disponibilidad']).strip().capitalize()
                esta_agotado = "Agotado" in dispo_status
                precio_cl = f"$ {precio_val:,.0f}".replace(",", ".")
                color_tienda = mapa_colores.get(tienda, "#eee")
                
                # 3. Estilos dinámicos
                es_top = (i == 0 and not esta_agotado)
                opacidad_info = "0.5" if esta_agotado else "1.0"
                bg_card = '#f0fff4' if es_top else ('#fafafa' if esta_agotado else 'white')
                border_card = '#2ecc71' if es_top else '#eee'
                btn_bg = "#ccc" if esta_agotado else "#1abc9c"
                btn_txt = "Sin Stock" if esta_agotado else "Ir al sitio"
                p_events = "none" if esta_agotado else "auto"

                # 4. Renderizado del HTML (Debajo del selectbox)
                badge = f'<span style="background-color:#e74c3c;color:white;padding:1px 5px;border-radius:4px;font-size:9px;font-weight:bold;margin-top:3px;display:inline-block;">AGOTADO</span>' if esta_agotado else ''
                
                html_final = (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'background-color:{bg_card};padding:6px 12px;border-radius:8px;'
                    f'border:1px solid {border_card};margin-top:2px;margin-bottom:8px;height:52px;width:100%;">'
                    f'<div style="display:flex;align-items:center;width:150px;flex-shrink:0;">'
                    f'<div style="width:13px;height:13px;border-radius:50%;background-color:{color_tienda};'
                    f'margin-right:10px;flex-shrink:0;"></div>'
                    f'<div style="display:flex;flex-direction:column;opacity:{opacidad_info};">'
                    f'<div style="font-size:13px;font-weight:800;color:#333;line-height:1.1;">{tienda}</div>'
                    f'{badge}'
                    f'</div></div>'
                    f'<div style="flex-grow:1;text-align:right;margin-right:12px;opacity:{opacidad_info};">'
                    f'<span style="font-size:14px;font-weight:800;color:#2c3e50;">{precio_cl}</span>'
                    f'</div>'
                    f'<a href="{url_tienda}" target="_blank" style="background-color:{btn_bg};color:white;'
                    f'padding:5px 12px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:11px;'
                    f'white-space:nowrap;pointer-events:{p_events};opacity:{opacidad_info};">{btn_txt}</a>'
                    f'</div>'
                )
                st.markdown(html_final, unsafe_allow_html=True)

            with c_check:
                # El checkbox se define al final para poder usar la 'opcion_elegida' del selectbox de arriba
                check_inicial = False
                if not esta_agotado and contador_grafica < 5:
                    check_inicial = True
                    contador_grafica += 1
                
                seleccion_tiendas[tienda] = {
                    "active": st.checkbox("", value=check_inicial, key=f"ch_{tienda}_{selected_sku}"),
                    "id_producto": opcion_elegida['id_producto']
                }

            with c_card:
                badge = f'<span style="background-color:#e74c3c;color:white;padding:1px 5px;border-radius:4px;font-size:9px;font-weight:bold;margin-top:3px;display:inline-block;">AGOTADO</span>' if esta_agotado else ''
                
                html_final = (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'background-color:{bg_card};padding:6px 12px;border-radius:8px;'
                    f'border:1px solid {border_card};margin-bottom:6px;height:52px;width:100%;">'
                    f'<div style="display:flex;align-items:center;width:150px;flex-shrink:0;">'
                    f'<div style="width:13px;height:13px;border-radius:50%;background-color:{color_tienda};'
                    f'margin-right:10px;flex-shrink:0;box-shadow:0 0 2px rgba(0,0,0,0.2);"></div>'
                    f'<div style="display:flex;flex-direction:column;opacity:{opacidad_info};">'
                    f'<div style="font-size:13px;font-weight:800;color:#333;line-height:1.1;">{tienda}</div>'
                    f'{badge}'
                    f'</div></div>'
                    f'<div style="flex-grow:1;text-align:right;margin-right:12px;opacity:{opacidad_info};">'
                    f'<span style="font-size:14px;font-weight:800;color:#2c3e50;">{precio_cl}</span>'
                    f'</div>'
                    f'<a href="{url_tienda}" target="_blank" style="background-color:{btn_bg};color:white;'
                    f'padding:5px 12px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:11px;'
                    f'white-space:nowrap;pointer-events:{p_events};opacity:{opacidad_info};">{btn_txt}</a>'
                    f'</div>'
                )
                st.markdown(html_final, unsafe_allow_html=True)
                
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
