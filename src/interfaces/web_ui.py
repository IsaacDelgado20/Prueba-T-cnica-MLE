"""
Interfaz Web con Streamlit - Adaptador de entrada (Inbound Adapter).
Proporciona una UI conversacional minimalista y dashboard de analíticas.
"""

import os
import uuid
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")
_API_TIMEOUT_SHORT = 10   # Consultas ligeras
_API_TIMEOUT_LONG = 120   # Chat
_API_TIMEOUT_SCRAPE = 600 # Scraping


# ---------- Helpers HTTP ----------

def _api_get(path: str, timeout: int = _API_TIMEOUT_SHORT) -> Optional[Dict]:
    """Realiza un GET al API y retorna el JSON o None si falla."""
    try:
        resp = requests.get(f"{API_URL}{path}", timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            "No se puede conectar con la API. "
            "Verifica que el servicio esté corriendo."
        )
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de la API ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
    return None


def _api_post(path: str, json: Dict, timeout: int = _API_TIMEOUT_LONG) -> Optional[Dict]:
    """Realiza un POST al API y retorna el JSON o None si falla."""
    try:
        resp = requests.post(f"{API_URL}{path}", json=json, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            "No se puede conectar con la API. "
            "Asegúrate de que el servicio esté corriendo."
        )
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de la API ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        st.error(f"Error: {e}")
    return None


# ---------- Main ----------

def main():
    st.set_page_config(
        page_title="BBVA RAG Assistant",
        page_icon="🏦",
        layout="wide",
    )

    st.title("🏦 BBVA Colombia - Asistente RAG")

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Gestión de sesión
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = str(uuid.uuid4())

        st.text_input(
            "ID de Conversación",
            value=st.session_state.conversation_id,
            key="conv_id_input",
            on_change=lambda: setattr(
                st.session_state, "conversation_id", st.session_state.conv_id_input
            ),
        )

        if st.button("🔄 Nueva Conversación"):
            st.session_state.conversation_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # Controles de Scraping
        st.header("🌐 Web Scraping")
        scrape_url = st.text_input("URL objetivo", value="https://www.bbva.com.co/")
        max_pages = st.slider("Máx. páginas", min_value=5, max_value=50, value=30)

        if st.button("🚀 Iniciar Scraping", type="primary"):
            with st.spinner("Scraping en progreso... Esto puede tomar varios minutos."):
                data = _api_post(
                    "/scrape",
                    json={"url": scrape_url, "max_pages": max_pages},
                    timeout=_API_TIMEOUT_SCRAPE,
                )
                if data:
                    st.success(f"✅ {data.get('message', 'Scraping completado')}")

        # Info del índice
        index_data = _api_get("/index/count", timeout=5)
        count = index_data.get("count", 0) if index_data else "N/A"
        st.metric("📊 Chunks indexados", count)

        st.divider()

        # Cargar conversación existente
        st.header("📂 Conversaciones")
        if st.button("Cargar conversaciones"):
            convs = _api_get("/conversations")
            if convs is not None:
                if convs:
                    st.session_state.available_convs = convs
                else:
                    st.info("No hay conversaciones guardadas.")

        if "available_convs" in st.session_state:
            conv_options = {
                c["id"][:8] + "...": c["id"]
                for c in st.session_state.available_convs
            }
            if conv_options:
                selected = st.selectbox(
                    "Seleccionar conversación",
                    options=list(conv_options.keys()),
                )
                if st.button("Cargar"):
                    full_id = conv_options[selected]
                    st.session_state.conversation_id = full_id
                    conv_data = _api_get(f"/conversations/{full_id}")
                    if conv_data:
                        st.session_state.messages = [
                            {
                                "role": m["role"],
                                "content": m["content"],
                                "sources": m.get("metadata", {}).get("sources", []),
                            }
                            for m in conv_data["messages"]
                        ]
                        st.rerun()

    # --- Área principal con tabs ---
    tab_chat, tab_analytics = st.tabs(["💬 Chat", "📊 Analíticas"])

    with tab_chat:
        _render_chat()

    with tab_analytics:
        _render_analytics()


def _render_chat():
    """Renderiza la interfaz de chat."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostrar mensajes existentes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📎 Fuentes"):
                    for src in msg["sources"]:
                        st.markdown(f"- {src}")

    # Input de chat
    if prompt := st.chat_input("Haz una pregunta sobre BBVA Colombia..."):
        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Obtener respuesta
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                data = _api_post(
                    "/chat",
                    json={
                        "conversation_id": st.session_state.conversation_id,
                        "question": prompt,
                    },
                )

                if data:
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    response_time = data.get("response_time_s", 0)

                    st.markdown(answer)

                    if sources:
                        with st.expander("📎 Fuentes"):
                            for src in sources:
                                st.markdown(f"- {src}")

                    st.caption(f"⏱️ {response_time}s")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    })

                    # Actualizar conversation_id
                    st.session_state.conversation_id = data["conversation_id"]


def _render_analytics():
    """Renderiza el dashboard de analíticas."""
    if st.button("🔄 Actualizar analíticas"):
        st.rerun()

    metrics = _api_get("/analytics")
    if not metrics:
        st.warning("No se pudieron obtener las analíticas.")
        return

    # KPIs principales
    st.subheader("📈 Métricas Generales")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Conversaciones", metrics["total_conversations"])
    with col2:
        st.metric("Total Mensajes", metrics["total_messages"])
    with col3:
        st.metric("Prom. msgs/conv", metrics["avg_messages_per_conversation"])
    with col4:
        st.metric("Tiempo resp. prom.", f"{metrics['avg_response_time_s']}s")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Preguntas", metrics["total_user_messages"])
    with col6:
        st.metric("Respuestas", metrics["total_assistant_messages"])
    with col7:
        st.metric("Long. prom. pregunta", f"{metrics['avg_user_message_length']} chars")
    with col8:
        st.metric("Long. prom. respuesta", f"{metrics['avg_assistant_message_length']} chars")

    # Top Keywords
    st.subheader("🔑 Top Keywords en Preguntas")
    if metrics["top_keywords"]:
        kw_df = pd.DataFrame(
            metrics["top_keywords"], columns=["Keyword", "Frecuencia"]
        )
        st.bar_chart(kw_df.set_index("Keyword"))
    else:
        st.info("No hay suficientes datos para mostrar keywords.")

    # Conversaciones por fecha
    st.subheader("📅 Conversaciones por Fecha")
    if metrics["conversations_by_date"]:
        date_df = pd.DataFrame(
            list(metrics["conversations_by_date"].items()),
            columns=["Fecha", "Conversaciones"],
        )
        st.line_chart(date_df.set_index("Fecha"))

    # Detalle de conversaciones
    st.subheader("📋 Detalle de Conversaciones")
    details = _api_get("/analytics/conversations")
    if details:
        df = pd.DataFrame(details)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay conversaciones registradas.")


if __name__ == "__main__":
    main()
