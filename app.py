import streamlit as st
import plotly.express as px
import json
from load_data import (
    get_yearly_counts, get_type_counts, get_processing_days,
    get_zip_counts, get_summary_stats, get_municipalities,
    get_raw_data, get_full_filtered_data, get_sex_counts, get_yoy_change,
    get_female_pct
)

# --- Page config ---
st.set_page_config(
    page_title="MA Firearms Licensing Dashboard",
    page_icon="🔒",
    layout="wide"
)

@st.cache_data
def load_geojson():
    with open("data/ma_zip_codes.geojson") as f:
        return json.load(f)

@st.cache_data
def cached_municipalities():
    return get_municipalities()

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

all_municipalities = cached_municipalities()
selected_municipality = st.sidebar.selectbox(
    "Municipality",
    options=["All municipalities"] + all_municipalities,
)

zip_input = st.sidebar.text_input("Zip code", placeholder="e.g. 02101")
zip_code = zip_input.strip() or None

# --- Guard: no application types selected ---
if not selected_types:
    st.warning("Please select at least one application type.")
    st.stop()

muni = selected_municipality if selected_municipality != "All municipalities" else None

# --- Summary metrics ---
stats = get_summary_stats(year_min, year_max, selected_types, muni, zip_code)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Applications", f"{stats['total']:,}")
col2.metric("Years Covered", f"{year_min}–{year_max}")
col3.metric("Municipalities", f"{stats['municipalities']:,}")
col4.metric("Median Processing Days", f"{stats['median_days']:.0f}")

st.divider()

# --- Tabs ---
tab_charts, tab_map, tab_data, tab_about = st.tabs(["📈 Charts", "🗺️ Map", "📋 Raw Data", "ℹ️ About"])

with tab_charts:

    female_pct = get_female_pct(year_min, year_max, selected_types, muni, zip_code)
    muni_label = muni if muni else "all Massachusetts municipalities"
    if zip_code:
        muni_label = f"zip code {zip_code}"
    types_label = ", ".join(selected_types)
    year_span = year_max - year_min + 1
    summary_parts = [
        f"From {year_min} to {year_max} ({year_span} {'year' if year_span == 1 else 'years'}), "
        f"there were **{stats['total']:,}** {types_label.lower()} applications "
        f"across {muni_label}.",
        f"The median processing time over this period was **{stats['median_days']:.0f} days**.",
    ]
    if female_pct is not None:
        summary_parts.append(
            f"Female applicants accounted for **{female_pct:.1f}%** of applications "
            f"where sex was recorded."
        )
    st.markdown(" ".join(summary_parts))

    st.subheader("Applications by Year")
    yearly = get_yearly_counts(year_min, year_max, selected_types, muni, zip_code)
    fig1 = px.line(yearly, x="year", y="applications", markers=True)
    st.plotly_chart(fig1, width='stretch')

    st.subheader("Applications by Type")
    by_type = get_type_counts(year_min, year_max, selected_types, muni, zip_code)
    fig2 = px.bar(by_type, x="year", y="applications",
                  color="application_type", barmode="stack")
    st.plotly_chart(fig2, width='stretch')

    st.subheader("Median Processing Days by Year")
    processing = get_processing_days(year_min, year_max, selected_types, muni, zip_code)
    fig3 = px.bar(processing, x="year", y="processing_days",
                  color="processing_days", color_continuous_scale="Reds")
    st.plotly_chart(fig3, width='stretch')

    st.subheader("Applications by Sex over Time")
    sex_counts = get_sex_counts(year_min, year_max, selected_types, muni, zip_code)

    # Add a female percentage column for the annotation
    sex_pivot = sex_counts.pivot(index="year", columns="sex", values="applications").fillna(0)
    sex_pivot["pct_female"] = (sex_pivot["FEMALE"] / (sex_pivot["FEMALE"] + sex_pivot["MALE"]) * 100).round(1)
    sex_pivot = sex_pivot.reset_index()

    fig4 = px.bar(
        sex_counts,
        x="year",
        y="applications",
        color="sex",
        barmode="stack",
        color_discrete_map={"MALE": "#4C72B0", "FEMALE": "#DD8452"},
        title="Applications by Sex per Year",
        labels={"applications": "Number of Applications", "sex": "Sex"}
    )
    st.plotly_chart(fig4, width='stretch')

    # Female share line chart
    fig5 = px.line(
        sex_pivot,
        x="year",
        y="pct_female",
        markers=True,
        title="Female Applications as % of Total by Year",
        labels={"pct_female": "Female %", "year": "Year"}
    )
    fig5.update_layout(yaxis_ticksuffix="%")
    st.plotly_chart(fig5, width='stretch')

    st.subheader("Year-over-Year % Change in Applications")
    yoy = get_yoy_change(year_min, year_max, selected_types, muni, zip_code)
    if len(yoy) < 2:
        st.info("Need at least two years of data to compute year-over-year change.")
    else:
        max_abs = yoy["yoy_pct"].abs().max()
        fig6 = px.bar(
            yoy,
            x="year",
            y="yoy_pct",
            color="yoy_pct",
            color_continuous_scale=[(0, "red"), (0.5, "lightgrey"), (1, "green")],
            color_continuous_midpoint=0,
            range_color=[-max_abs, max_abs],
            labels={"yoy_pct": "YoY Change", "year": "Year"},
        )
        fig6.update_layout(
            yaxis_ticksuffix="%",
            coloraxis_showscale=False,
        )
        fig6.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
        st.plotly_chart(fig6, width='stretch')

with tab_map:
    st.subheader("Applications by Zip Code")
    st.markdown("Colored by total applications · filtered by sidebar selections")
    st.info("Click the button to generate the map after setting your filters.")

    if st.button("Generate Map"):
        zip_counts = get_zip_counts(year_min, year_max, selected_types, muni, zip_code)

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
            top_zips = zip_counts.head(20).reset_index(drop=True)
            top_zips.index += 1
            st.dataframe(top_zips, width='stretch')

with tab_data:
    st.subheader("Raw Data")

    DISPLAY_LIMIT = 10_000
    raw = get_raw_data(year_min, year_max, selected_types, muni, zip_code, limit=DISPLAY_LIMIT)
    total_count = stats["total"]
    truncated = total_count > DISPLAY_LIMIT

    st.markdown(
        f"Showing **{len(raw):,}** of **{total_count:,}** rows · "
        f"{'_Apply filters or select a municipality to narrow results_' if truncated else 'All rows shown'}"
    )

    st.dataframe(raw, width='stretch', height=500)

    if truncated:
        st.info(
            f"⚠️ Display limited to {DISPLAY_LIMIT:,} rows. "
            "The download below includes all filtered rows."
        )

    if st.button("Prepare Download"):
        full_data = get_full_filtered_data(year_min, year_max, selected_types, muni, zip_code)
        csv = full_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"⬇️ Download all {len(full_data):,} rows as CSV",
            data=csv,
            file_name="ma_firearms_filtered.csv",
            mime="text/csv"
        )

with tab_about:
    st.subheader("Data Source")
    st.markdown(
        "The underlying data comes from the **Massachusetts Executive Office of Public Safety and Security (EOPSS)**, "
        "downloaded directly from the [EOPSS firearms licensing data page](https://www.mass.gov/info-details/data-about-firearms-licensing-and-transactions). "
        "It covers firearms license applications filed between **2006 and 2024**, "
        "comprising approximately **1.6 million applications** across all Massachusetts municipalities."
    )

    st.subheader("Methodology")
    st.markdown(
        "The raw data was delivered as **5 CSV files** spanning different time periods. "
        "These were combined, deduplicated, and cleaned — including normalizing applicant zip codes to 5-digit format. "
        "The cleaned dataset is stored in a **DuckDB** database and queried on demand, keeping memory usage low "
        "even at 1.6 million rows."
    )

    st.subheader("Tech Stack")
    st.markdown(
        "- **Python** — core language\n"
        "- **DuckDB** — embedded analytical database\n"
        "- **Pandas** — data wrangling\n"
        "- **Plotly** — interactive charts\n"
        "- **Streamlit** — dashboard framework\n"
        "- **Streamlit Community Cloud** — hosting"
    )

    st.subheader("About This Project")
    st.markdown(
        "This dashboard was built by a non-developer using AI-assisted development with "
        "[Claude](https://claude.ai) (Anthropic). No prior software engineering background — "
        "just curiosity about public data and how firearms licensing works in Massachusetts."
    )

    st.subheader("Contact")
    st.markdown("Reddit: [u/whiskeygraven0g](https://www.reddit.com/user/whiskeygraven0g)")