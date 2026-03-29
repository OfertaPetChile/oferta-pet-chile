import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go

# 1. Configuración de página
st.set_page_config(page_title="Oferta Pet Chile", page_icon="🐾", layout="wide")

# 2. Conexión a Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE NAVEGACIÓN ---
params = st.query_params
selected_sku = params.get("sku")

# 3. ESTILOS CSS (Ajustados para Card Unificada)
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
    /* Estilo para que el botón de Streamlit parezca parte de la card */
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

# --- VISTA 2: HOJA DE DETALLE (Diseño Ancho Completo + Selector) ---
if selected_sku:
    if st.button("⬅️ Volver a la galería"):
        st.query_params.clear()
        st.rerun()

    # 1. Traer datos básicos del SKU
    res_maestro = supabase.table("SKUs_unicos").select("nombre_oficial").eq("mi_sku", selected_sku).single().execute()
    nombre_oficial = res_maestro.data["nombre_oficial"] if res_maestro.data else "Producto"

    st.title(f"📊 {nombre_oficial}")
    st.caption(f"ID Producto: {selected_sku}")
    st.divider()

    # --- 2. Preparación de Datos (Productos + Historial) ---
    res_prod = supabase.table("Productos").select("id_producto, nombre_tienda, url_tienda").eq("mi_sku", selected_sku).execute()
    
    if not res_prod.data:
        st.warning("No hay ofertas registradas para este producto.")
        st.stop()

    datos_tabla = []
    historiales_completos = {}
    promedios_historicos = {}

    for p in res_prod.data:
        res_hist = supabase.table("Historial_precios")\
            .select("fecha, precio")\
            .eq("id_producto", p['id_producto'])\
            .order("fecha", desc=True).execute()
        
        df_h = pd.DataFrame(res_hist.data)
        
        if not df_h.empty:
            tienda = p['nombre_tienda']
            
            # Datos para la tabla de ofertas actuales (último precio)
            datos_tabla.append({
                "Tienda": tienda,
                "Precio Actual": df_h.iloc[0]['precio'],
                "URL": p['url_tienda']
            })
            
            # Datos para la gráfica y promedios (reordenamos cronológicamente)
            df_hist_ord = df_h.sort_values(by="fecha")
            historiales_completos[tienda] = df_hist_ord
            
            # Calculamos promedio histórico para pre-selección
            promedios_historicos[tienda] = df_hist_ord['precio'].mean()

    # --- 3. SECCIÓN 1: GRÁFICA DE HISTORIAL (Ancho Completo) ---
    st.subheader("📈 Historial de Evolución de Precios")
    
    # 3a. Determinar tiendas pre-seleccionadas (Top 5 promedios más bajos)
    tiendas_disponibles = sorted(list(historiales_completos.keys()))
    
    # Ordenamos las tiendas por promedio más bajo
    tiendas_por_promedio = sorted(promedios_historicos, key=promedios_historicos.get)
    # Tomamos las top 5 (o menos si hay pocas tiendas)
    pre_seleccion = tiendas_por_promedio[:min(5, len(tiendas_por_promedio))]

    # 3b. Selector Interactivo de Tiendas (Añadido entre gráfica y tabla en tu boceto, lo pondré justo antes para filtrar)
    tiendas_a_graficar = st.multiselect(
        "Filtrar tiendas en la gráfica:",
        options=tiendas_disponibles,
        default=pre_seleccion,
        placeholder="Selecciona tiendas..."
    )

    # 3c. Creación de la Gráfica Dinámica
    if tiendas_a_graficar:
        fig = go.Figure()
        for tienda in tiendas_a_graficar:
            if tienda in historiales_completos:
                df = historiales_completos[tienda]
                fig.add_trace(go.Scatter(
                    x=df['fecha'], 
                    y=df['precio'], 
                    name=tienda, 
                    mode='lines+markers',
                    hovertemplate=f"<b>{tienda}</b><br>Fecha: %{{x}}<br>Precio: $%{{y:,.0f}}<extra></extra>".replace(",", ".")
                ))
        
        fig.update_layout(
            template="plotly_white", 
            margin=dict(l=10, r=10, t=10, b=10), 
            height=500, # Gráfica más alta al tener más ancho
            xaxis_title="Fecha",
            yaxis_title="Precio ($)",
            legend=dict(orientation="h", y=-0.2),
            separators=",."
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecciona al menos una tienda en el selector de arriba para visualizar la gráfica.")

    st.divider()

    # --- 4. SECCIÓN 2: MEJORES OFERTAS ACTUALES (Abajo, Ancho Completo) ---
    st.subheader("💰 Mejores Ofertas Disponibles Hoy")
    
    if datos_tabla:
        # Ordenamos la tabla de ofertas por precio más bajo
        df_precios_actuales = pd.DataFrame(datos_tabla).sort_values(by="Precio Actual", ascending=True)

        # Usamos st.columns para renderizar las cards de precios de forma lineal (Tienda - Precio - Botón)
        # pero en el ancho completo. Para que no queden muy anchas, podemos hacer un bucle
        # y usar st.markdown, similar al diseño lineal que ya funcionaba, pero a ancho completo.
        
        for i, row in df_precios_actuales.iterrows():
            precio_cl = f"$ {row['Precio Actual']:,.0f}".replace(",", ".")
            
            # Estilo sutil para el más barato
            es_primero = (i == df_precios_actuales.index[0])
            bg_color = "#f0fff4" if es_primero else "white"
            border_color = "#2ecc71" if es_primero else "#eee"

            # Renderizado HTML Lineal y Compacto (Adaptado para ancho completo)
            st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background-color: {bg_color};
                    padding: 8px 15px;
                    border-radius: 8px;
                    border: 1px solid {border_color};
                    margin-bottom: 5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                ">
                    <div style="flex: 1; min-width: 0; margin-right: 15px;">
                        <p style="margin:0; font-size:13px; color:#7f8c8d; font-weight:bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            {row['Tienda']}
                        </p>
                    </div>
                    
                    <div style="margin-right: 20px;">
                        <span style="font-size: 16px; font-weight: 800; color: #2c3e50;">{precio_cl}</span>
                    </div>
                    
                    <div>
                        <a href="{row['URL']}" target="_blank" style="
                            display: inline-block;
                            background-color: #1abc9c;
                            color: white;
                            padding: 5px 12px;
                            border-radius: 5px;
                            text-decoration: none;
                            font-weight: bold;
                            font-size: 12px;
                            white-space: nowrap;
                        ">
                            🛒 Ver en tienda
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    # --- COLUMNA IZQUIERDA: TABLA ORDENADA (Versión Compacta) ---
    with col_izq:
        st.subheader("💰 Mejores Ofertas")
        
        # ORDENAR DE MENOR A MAYOR
        df_precios = pd.DataFrame(datos_tabla).sort_values(by="Precio", ascending=True)

        for i, row in df_precios.iterrows():
            precio_cl = f"$ {row['Precio']:,.0f}".replace(",", ".")
            
            # Estilo especial para el más barato (Borde verde sutil)
            es_primero = (i == df_precios.index[0])
            bg_color = "#f0fff4" if es_primero else "#ffffff"
            border_color = "#2ecc71" if es_primero else "#e0e0e0"
            
            # Diseño Lineal: Tienda | Precio | Botón
            st.markdown(f"""
                <div style="
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    background-color: {bg_color}; 
                    padding: 6px 10px; 
                    border-radius: 8px; 
                    border: 1px solid {border_color}; 
                    margin-bottom: 6px; 
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                ">
                    <div style="flex: 1; min-width: 0; margin-right: 10px;">
                        <p style="margin:0; font-size:11px; color:#7f8c8d; font-weight:bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            {row['Tienda']}
                        </p>
                    </div>
                    <div style="margin-right: 15px;">
                        <span style="font-size: 14px; font-weight: 800; color: #2c3e50;">{precio_cl}</span>
                    </div>
                    <div>
                        <a href="{row['URL']}" target="_blank" style="
                            display: inline-block; 
                            background-color: #1abc9c; 
                            color: white; 
                            padding: 4px 10px; 
                            border-radius: 4px; 
                            text-decoration: none; 
                            font-weight: bold; 
                            font-size: 11px;
                            white-space: nowrap;
                        ">
                            🛒 Ver
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    # --- COLUMNA DERECHA: GRÁFICA ---
    with col_der:
        st.subheader("📈 Historial")
        fig = go.Figure()
        for tienda, df in historiales_grafica.items():
            fig.add_trace(go.Scatter(x=df['fecha'], y=df['precio'], name=tienda, mode='lines+markers'))
        
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), height=450, separators=",.")
        st.plotly_chart(fig, use_container_width=True)

# --- VISTA 1: GALERÍA PRINCIPAL (Corregida con nuevos nombres de columna) ---
else:
    st.title("🐾 Oferta Pet Chile")
    query = st.text_input("Busca tu producto...", placeholder="Ej: Leonardo, Cat it...")

    if query:
        q = query.strip().upper()
        
        # CAMBIO CLAVE: Cambiamos 'nombre_maestro' por 'nombre_oficial'
        res = supabase.table("SKUs_unicos")\
            .select("*")\
            .or_(f"nombre_oficial.ilike.%{q}%,mi_sku.ilike.%{q}%")\
            .execute()

        if res.data:
            df_maestro = pd.DataFrame(res.data)
            
            # Configuramos 5 columnas para la galería
            cols = st.columns(5)
            
            for idx, row in df_maestro.iterrows():
                with cols[idx % 5]:
                    # Usamos 'nombre_oficial' también para el texto de la card
                    nombre_card = row.get('nombre_oficial', 'Producto sin nombre')
                    img_url = row.get('imagen_url_maestra', '') # Verifica si este es el nombre en SKUs_unicos
                    
                    # Render de la Card HTML
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_url}" style="width:100%; height:160px; object-fit:contain;">
                        <div>
                            <div class="product-title">{nombre_card}</div>
                            <div class="ver-detalle-text">Ver comparativa</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón de acción
                    if st.button("Ver detalle", key=f"btn_{row['mi_sku']}", use_container_width=True):
                        st.query_params.sku = row['mi_sku']
                        st.rerun()
        else:
            st.info("No encontramos coincidencias con 'nombre_oficial' en el catálogo.")
