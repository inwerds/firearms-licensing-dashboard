import streamlit as st
import plotly.express as px
import pandas as pd
import json
from load_data import (
    get_yearly_counts, get_type_counts, get_processing_days,
    get_zip_counts, get_summary_stats, get_municipalities,
    get_raw_data, get_full_filtered_data, get_sex_counts, get_yoy_change,
    get_female_pct, get_licenses_per_capita, get_voting_data, get_licensing_vs_voting
)

# --- Page config ---
st.set_page_config(
    page_title="MA Firearms Licensing Dashboard",
    page_icon="🔒",
    layout="wide"
)

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 20px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f6;
        border-bottom: 3px solid #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_geojson():
    with open("data/ma_zip_codes.geojson") as f:
        return json.load(f)

@st.cache_data
def cached_municipalities():
    return get_municipalities()

@st.cache_data
def get_active_licenses():
    return pd.read_excel("data/raw/active_licenses_2025.xlsx")

# --- Header ---
st.title("Massachusetts Firearms Licensing Dashboard")
st.markdown("19 years of licensing data · 2006–2024 · 1.6 million applications")

# --- Sidebar filters ---
st.sidebar.header("Filters")
st.sidebar.markdown("Explore 19 years of Massachusetts firearms licensing data. Use the filters below to narrow the data — all charts update automatically.")
st.sidebar.markdown("---")

year_min, year_max = st.sidebar.slider(
    "Year range",
    min_value=2006,
    max_value=2024,
    value=(2006, 2024)
)
st.sidebar.caption("Filter all charts and data to applications submitted within this date range.")

selected_types = st.sidebar.multiselect(
    "Application type",
    options=["New", "Renewal", "Replacement"],
    default=["New", "Renewal", "Replacement"]
)
st.sidebar.caption("New: first-time applicants. Renewal: existing license holders. Replacement: lost, stolen, or damaged licenses.")

all_municipalities = cached_municipalities()
selected_municipality = st.sidebar.selectbox(
    "Municipality",
    options=["All municipalities"] + all_municipalities,
)
st.sidebar.caption("Filter to a single licensing authority (usually a local police department). Selecting a town updates all charts, the map, and raw data.")

zip_input = st.sidebar.text_input("Zip code", placeholder="e.g. 02101")
zip_code = zip_input.strip() or None
st.sidebar.caption("Filter to applicants from a specific zip code. Note: this reflects where the applicant lives, not where they applied.")

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
tab_charts, tab_map, tab_licenses, tab_data, tab_about = st.tabs(["📈 Charts", "🗺️ Map", "📊 Active Licenses", "📋 Raw Data", "ℹ️ About"])

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
    st.caption("Total firearms license applications submitted to Massachusetts police departments each year from 2006–2024. Includes all application types and license categories.")
    yearly = get_yearly_counts(year_min, year_max, selected_types, muni, zip_code)
    fig1 = px.line(yearly, x="year", y="applications", markers=True)
    st.plotly_chart(fig1, width='stretch')

    st.subheader("Applications by Type")
    st.caption("Breakdown of applications by type. New applications are first-time applicants. Renewals are existing license holders renewing before expiration. Replacements are for lost, stolen, or damaged licenses.")
    by_type = get_type_counts(year_min, year_max, selected_types, muni, zip_code)
    fig2 = px.bar(by_type, x="year", y="applications",
                  color="application_type", barmode="stack")
    st.plotly_chart(fig2, width='stretch')

    st.subheader("Median Processing Days by Year")
    st.caption("The median number of days between application submission and license issuance. Spikes may reflect surges in application volume overwhelming local police departments.")
    processing = get_processing_days(year_min, year_max, selected_types, muni, zip_code)
    fig3 = px.bar(processing, x="year", y="processing_days",
                  color="processing_days", color_continuous_scale="Reds")
    st.plotly_chart(fig3, width='stretch')

    st.subheader("Applications by Sex over Time")
    st.caption("Annual breakdown of applications by reported sex. The second chart shows female applications as a share of total, revealing a gradual long-term trend toward more diverse applicants.")
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
    st.caption("Percentage change in total applications compared to the prior year. Green bars indicate growth, red bars indicate decline. Large swings often correlate with national events or legislation.")
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

    st.subheader("Applications per 1,000 Residents — Top 30 Municipalities")
    st.caption("Total applications normalized by town population, showing which municipalities have the highest licensing rates relative to their size. More meaningful than raw counts for comparing towns of different sizes.")
    per_capita = get_licenses_per_capita(year_min, year_max, selected_types, muni)
    if len(per_capita) == 0:
        st.info("No per capita data available for current filters.")
    else:
        top30 = per_capita.head(30).sort_values("applications_per_1000", ascending=True)
        fig7 = px.bar(
            top30,
            x="applications_per_1000",
            y="licensing_authority",
            orientation="h",
            labels={
                "applications_per_1000": "Applications per 1,000 Residents",
                "licensing_authority": "Municipality",
            },
        )
        st.plotly_chart(fig7, width='stretch')

    st.subheader("Firearms Licensing Rate vs. Political Lean by Municipality")
    st.caption("Each dot represents one Massachusetts municipality. Political lean is calculated as the difference between Trump and Harris vote share in 2024. Positive values lean Republican, negative values lean Democratic. The trendline shows the correlation between political lean and licensing rate. Hover over any dot to see the town name and details.")
    lv = get_licensing_vs_voting()
    if len(lv) == 0:
        st.info("No data available for licensing vs. voting chart.")
    else:
        fig8 = px.scatter(
            lv,
            x="lean",
            y="applications_per_1000",
            hover_name="town",
            trendline="ols",
            color="lean",
            color_continuous_scale="RdBu_r",
            color_continuous_midpoint=0,
            labels={
                "lean": "Political Lean (negative = Democratic, positive = Republican)",
                "applications_per_1000": "Applications per 1,000 Residents",
            },
        )
        st.plotly_chart(fig8, width='stretch')

with tab_map:
    st.subheader("Applications by Zip Code")
    st.markdown("Colored by total applications · filtered by sidebar selections")
    st.caption("Note: the map shows zip codes where applicants live, not where they applied. When filtering by municipality, applicants may live in neighboring towns outside that municipality's boundaries.")
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

with tab_licenses:
    st.subheader("Active Licenses — 2025 Snapshot")

    active = get_active_licenses()

    st.metric("Total Active Licenses Statewide", f"{active['Count'].sum():,}")

    by_muni = (
        active.groupby("Licensing Authority", as_index=False)["Count"]
        .sum()
        .sort_values("Count", ascending=False)
    )
    top20 = by_muni.head(20).sort_values("Count", ascending=True)

    st.subheader("Top 20 Municipalities by Active License Count")
    fig_lic1 = px.bar(
        top20,
        x="Count",
        y="Licensing Authority",
        orientation="h",
        labels={"Count": "Active Licenses", "Licensing Authority": "Municipality"},
    )
    st.plotly_chart(fig_lic1, width='stretch')

    st.subheader("License Type Breakdown — Top 20 Municipalities")
    top20_names = by_muni.head(20)["Licensing Authority"].tolist()
    top20_detail = (
        active[active["Licensing Authority"].isin(top20_names)]
        .copy()
    )
    muni_order = by_muni.head(20).sort_values("Count", ascending=True)["Licensing Authority"].tolist()
    top20_detail["Licensing Authority"] = pd.Categorical(
        top20_detail["Licensing Authority"], categories=muni_order, ordered=True
    )
    top20_detail = top20_detail.sort_values("Licensing Authority")

    fig_lic2 = px.bar(
        top20_detail,
        x="Count",
        y="Licensing Authority",
        color="License Type",
        orientation="h",
        barmode="stack",
        labels={"Count": "Active Licenses", "Licensing Authority": "Municipality"},
    )
    st.plotly_chart(fig_lic2, width='stretch')

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
        "comprising approximately **1.6 million applications** across all Massachusetts municipalities. "
        "Municipal population figures used for per capita calculations are drawn from **U.S. Census data via Wikipedia**."
    )

    st.subheader("Methodology")
    st.markdown(
        "The raw data was delivered as **5 CSV files** spanning different time periods. "
        "These were combined, deduplicated, and cleaned — including normalizing applicant zip codes to 5-digit format. "
        "The cleaned dataset is stored as a **Parquet file** and queried on demand using **DuckDB** in-memory, "
        "keeping memory usage low even at 1.6 million rows. "
        "A partial **2025 snapshot** of active licenses was separately obtained from EOPSS and is displayed in the Active Licenses tab."
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

    st.subheader("🔫 About Me")
    st.markdown(
        "I like guns and solving problems. Not a developer. Used Claude."
    )

    st.subheader("Contact")
    st.markdown("Reddit: [u/whiskeygraven0g](https://www.reddit.com/user/whiskeygraven0g)")