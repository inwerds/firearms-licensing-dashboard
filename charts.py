import plotly.express as px
from load_data import load_data

df = load_data()

# Aggregate: count rows per year
yearly = df.groupby("year").size().reset_index(name="applications")

# Build the chart
fig = px.line(
    yearly,
    x="year",
    y="applications",
    title="Massachusetts Firearms License Applications by Year (2006–2024)",
    labels={"year": "Year", "applications": "Number of Applications"},
    markers=True,
)


fig.show()

# Aggregate: count rows per year AND application type
by_type = (
    df.groupby(["year", "application_type"])
    .size()
    .reset_index(name="applications")
)

fig2 = px.bar(
    by_type,
    x="year",
    y="applications",
    color="application_type",
    title="Applications by Type per Year",
    labels={
        "year": "Year",
        "applications": "Number of Applications",
        "application_type": "Application Type"
    },
    barmode="stack",
)

fig2.show()

# Aggregate: median processing days per year
processing = (
    df[df["processing_days"] > 0]  # exclude negatives/zeros (data errors)
    .groupby("year")["processing_days"]
    .median()
    .reset_index()
)

fig3 = px.bar(
    processing,
    x="year",
    y="processing_days",
    title="Median Days to Process a License Application by Year",
    labels={
        "year": "Year",
        "processing_days": "Median Processing Days"
    },
    color="processing_days",
    color_continuous_scale="Reds",
)

fig3.show()

# Aggregate by zip
zip_counts = (
    df[df["applicant_zip"].notna()]
    .groupby("applicant_zip")
    .size()
    .reset_index(name="applications")
)

fig4 = px.choropleth(
    zip_counts,
    geojson="https://raw.githubusercontent.com/OpenDataDE/State-zip-code-GeoJSON/master/ma_massachusetts_zip_codes_geo.min.json",
    locations="applicant_zip",
    featureidkey="properties.ZCTA5CE10",
    color="applications",
    color_continuous_scale="Blues",
    title="Firearms License Applications by Zip Code",
    labels={"applications": "Total Applications"}
)

fig4.update_geos(
    fitbounds="locations",  # zoom to MA automatically
    visible=False           # hide the rest of the world
)

fig4.show()