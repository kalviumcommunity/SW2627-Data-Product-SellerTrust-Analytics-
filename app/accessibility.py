from __future__ import annotations

import pandas as pd
import streamlit as st
from plotly.graph_objects import Figure


def render_accessible_chart(
    figure: Figure,
    *,
    description: str,
    data: pd.DataFrame,
    table_label: str = "View chart data as a table",
) -> None:
    """Render a chart with a visible description and a tabular alternative."""
    st.plotly_chart(figure, use_container_width=True)
    st.caption(f"Chart description: {description}")
    with st.expander(table_label):
        st.dataframe(data, hide_index=True, use_container_width=True)
