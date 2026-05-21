import streamlit as st
import pandas as pd
import plotly.express as px
import json
from load_data import load_data

# --- Page config ---
st.set_page_config(
    page_title="MA Firearms Licensing Dashboard",
    page_icon="🔒",
    layout="wide"
)

# --- Load data (cached so it only runs once) ---
@st.cache_data
def get_data():
    return load_data()

@st.cache_data
def load_geojson():
    with open("data/ma_zip_codes.geojson") as f:
        return json.load(f)

df = get_data()

# --- Header ---
st.title("Massachusetts Firearms Licensing Dashboard")
st.markdown("19 years of licensing data · 2006–2024 · 1.6 million applications")

# --- Sidebar filters ---
st.sidebar.header("Filters")

year_min, year_max = st.sidebar.slider(
    "Year range",
    min_value=2006,
    max_value=2024,
    value=(2006, 2024)
)

selected_types = st.sidebar.multiselect(
    "Application type",
    options=["New", "Renewal", "Replacement"],
    default=["New", "Renewal", "Replacement"]
)

all_municipalities = sorted(df["licensing_authority"].dropna().unique())
selected_municipality = st.sidebar.selectbox(
    "Municipality",
    options=["All municipalities"] + all_municipalities,
)

mem_mb = df.memory_usage(deep=True).sum() / 1e6
st.sidebar.caption(f"Data in memory: {mem_mb:.0f} MB")

# --- Apply filters ---
filtered = df[
    (df["year"] >= year_min) &
    (df["year"] <= year_max) &
    (df["application_type"].isin(selected_types))
]

if selected_municipality != "All municipalities":
    filtered = filtered[filtered["licensing_authority"] == selected_municipality]

# --- Guard: empty dataframe ---
if filtered.empty:
    st.warning("No data matches your current filters. Try adjusting the sidebar.")
    st.stop()

# --- Summary metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Applications", f"{len(filtered):,}")
col2.metric("Years Covered", f"{year_min}–{year_max}")
col3.metric("Municipalities", f"{filtered['licensing_authority'].nunique():,}")
median_days = filtered[filtered["processing_days"] > 0]["processing_days"].median()
col4.metric("Median Processing Days", f"{median_days:.0f}")

st.divider()

# --- Tabs ---
tab_charts, tab_map, tab_data = st.tabs(["📈 Charts", "🗺️ Map", "📋 Raw Data"])

with tab_charts:

    st.subheader("Applications by Year")
    yearly = filtered.groupby("year").size().reset_index(name="applications")
    fig1 = px.line(yearly, x="year", y="applications", markers=True)
    st.plotly_chart(fig1, width='stretch')

    st.subheader("Applications by Type")
    by_type = (
        filtered.groupby(["year", "application_type"])
        .size()
        .reset_index(name="applications")
    )
    fig2 = px.bar(by_type, x="year", y="applications",
                  color="application_type", barmode="stack")
    st.plotly_chart(fig2, width='stretch')

    st.subheader("Median Processing Days by Year")
    processing = (
        filtered[filtered["processing_days"] > 0]
        .groupby("year")["processing_days"]
        .median()
        .reset_index()
    )
    fig3 = px.bar(processing, x="year", y="processing_days",
                  color="processing_days", color_continuous_scale="Reds")
    if selected_municipality == "All municipalities":
        fig3.add_annotation(
            x=2013, y=89,
            text="Sandy Hook surge",
            showarrow=True, arrowhead=2, yshift=10
        )
    st.plotly_chart(fig3, width='stretch')

with tab_map:
    st.subheader("Applications by Zip Code")
    st.markdown("Colored by total applications · filtered by sidebar selections")
    st.info("Click the button to generate the map after setting your filters.")

    if st.button("Generate Map"):
        zip_counts = (
            filtered[filtered["applicant_zip"].notna()]
            .groupby("applicant_zip")
            .size()
            .reset_index(name="applications")
        )

        if len(zip_counts) == 0:
            st.warning("No zip code data for current filters.")
        else:
            ma_geojson = load_geojson()

            fig_map = px.choropleth(
                zip_counts,
                geojson=ma_geojson,
                locations="applicant_zip",
                featureidkey="properties.ZCTA5CE10",
                color="applications",
                color_continuous_scale="Blues",
                title="Firearms License Applications by Zip Code",
                labels={"applications": "Total Applications"}
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(
                margin={"r": 0, "t": 30, "l": 0, "b": 0},
                height=600
            )
            st.plotly_chart(fig_map, width='stretch')

            st.subheader("Top 20 Zip Codes by Volume")
            top_zips = (
                zip_counts
                .sort_values("applications", ascending=False)
                .head(20)
                .reset_index(drop=True)
            )
            top_zips.index += 1
            st.dataframe(top_zips, width='stretch')

with tab_data:

    st.subheader("Raw Data")

    DISPLAY_LIMIT = 10_000
    display_df = filtered.reset_index(drop=True)
    truncated = len(display_df) > DISPLAY_LIMIT

    st.markdown(
        f"Showing **{min(DISPLAY_LIMIT, len(display_df)):,}** of "
        f"**{len(display_df):,}** rows · "
        f"{'_Apply filters or select a municipality to narrow results_' if truncated else 'All rows shown'}"
    )

    all_cols = filtered.columns.tolist()
    selected_cols = st.multiselect(
        "Columns to display",
        options=all_cols,
        default=["application_date", "licensing_authority", "applicant_city",
                 "license_type", "application_type", "sex", "status", "processing_days"]
    )

    st.dataframe(
        display_df[selected_cols].head(DISPLAY_LIMIT),
        width='stretch',
        height=500
    )

    if truncated:
        st.info(
            f"⚠️ Display limited to {DISPLAY_LIMIT:,} rows. "
            "Use the sidebar filters or select a municipality to see a smaller subset. "
            "The download below includes all filtered rows."
        )

    @st.cache_data
    def to_csv(dataframe):
        return dataframe.to_csv(index=False).encode("utf-8")

    st.download_button(
        label=f"⬇️ Download all {len(display_df):,} rows as CSV",
        data=to_csv(filtered[selected_cols]),
        file_name="ma_firearms_filtered.csv",
        mime="text/csv"
    )