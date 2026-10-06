from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

st.set_page_config(
    page_title="AI Infrastructure Burden Index",
    layout="wide",
)


@st.cache_data
def load_data():
    counties = pd.read_csv(
        DATA / "county_screening_scores.csv",
        dtype={"county_fips": str},
    )
    sensitivity = pd.read_csv(
        DATA / "county_score_sensitivity.csv",
        dtype={"county_fips": str},
    )
    facilities = pd.read_csv(
        DATA / "facilities_with_counties.csv",
        dtype={"county_fips": str, "facility_id": str},
    )

    facilities = facilities[
        facilities["county_fips"].isin(counties["county_fips"])
    ].copy()

    scenario_columns = [
        "county_fips",
        "equal_score",
        "equal_rank",
        "poverty_focus_score",
        "poverty_focus_rank",
        "electricity_focus_score",
        "electricity_focus_rank",
        "water_focus_score",
        "water_focus_rank",
        "rank_range",
    ]

    counties = counties.merge(
        sensitivity[scenario_columns],
        on="county_fips",
        how="left",
        validate="one_to_one",
    )
    return counties, facilities


try:
    counties, facilities = load_data()
except (OSError, KeyError, ValueError) as error:
    st.error(f"Unable to load project data: {error}")
    st.stop()

st.title("AI Infrastructure Burden Index")
st.caption(
    "Exploratory county screening using PeeringDB-listed facilities"
)
st.warning(
    "DRAFT — electricity source verification is outstanding. "
    "Scores describe selected vulnerability indicators; "
    "they do not establish harm caused by facilities."
)

scenarios = {
    "Equal weights": "equal",
    "Poverty emphasis": "poverty_focus",
    "Electricity-price emphasis": "electricity_focus",
    "Water-stress emphasis": "water_focus",
}

st.sidebar.header("Explore")

selection = st.sidebar.selectbox(
    "Weighting scenario", list(scenarios)
)
scenario = scenarios[selection]

states = st.sidebar.multiselect(
    "States",
    sorted(counties["state"].dropna().unique()),
)

listed_only = st.sidebar.checkbox(
    "Only counties with listed facilities",
    value=True,
)

view = counties.copy()

if states:
    view = view[view["state"].isin(states)]

if listed_only:
    view = view[view["listed_facility_count"].gt(0)]

score_column = f"{scenario}_score"
rank_column = f"{scenario}_rank"

mapped = facilities[
    facilities["county_fips"].isin(view["county_fips"])
].copy()

a, b, c = st.columns(3)
a.metric("Counties shown", len(view))
b.metric("Listed facility records", len(mapped))
c.metric(
    "Scored counties shown",
    int(view[score_column].notna().sum()),
)

st.caption(
    "Scores and ranks use the full eligible county reference group. "
    "Filters change the display, not the reference group."
)

map_tab, ranking_tab, county_tab, method_tab = st.tabs(
    [
        "Facility map",
        "Rankings",
        "County details",
        "Method and coverage",
    ]
)

with map_tab:
    st.subheader("PeeringDB-listed facility locations")

    coordinates = mapped[["latitude", "longitude"]].apply(
        pd.to_numeric, errors="coerce"
    ).dropna()

    if coordinates.empty:
        st.info("No facility locations for these filters.")
    else:
        st.map(coordinates)

    st.caption(
        "A listed record may represent multiple buildings. "
        "Listing does not confirm AI workloads or capacity."
    )

with ranking_tab:
    st.subheader(selection)

    ranked = view[view[score_column].notna()].sort_values(
        [score_column, "county_fips"],
        ascending=[False, True],
    )

    columns = [
        "county_name",
        "state",
        "listed_facility_count",
        score_column,
        rank_column,
        "poverty_rate",
        "residential_price_cents_kwh",
        "mean_facility_water_stress_score",
        "rank_range",
    ]

    if ranked.empty:
        st.info("No scored counties match these filters.")
    else:
        st.dataframe(
            ranked[columns].round(2),
            hide_index=True,
        )

    st.caption(
        "Rank range is the difference between a county's best "
        "and worst rank across the four weighting scenarios."
    )

with county_tab:
    if view.empty:
        st.info("No counties match these filters.")
    else:
        options = view.sort_values(
            ["state", "county_name"]
        )["county_fips"].tolist()

        labels = {
            row["county_fips"]:
                f"{row['county_name']}, {row['state']}"
            for _, row in view.iterrows()
        }

        chosen = st.selectbox(
            "Choose a county",
            options,
            format_func=lambda code: labels[code],
        )

        row = view.set_index("county_fips").loc[chosen]

        details = {
            "County FIPS": chosen,
            "Listed facility records":
                row["listed_facility_count"],
            "Poverty rate (%)":
                row["poverty_rate"],
            "Median household income ($)":
                row["median_household_income"],
            "State residential price (cents/kWh)":
                row["residential_price_cents_kwh"],
            "Mean facility-location water-stress score (0–5)":
                row["mean_facility_water_stress_score"],
            "Water coverage (%)":
                row["water_stress_coverage_pct"],
            "Water coverage status":
                row["water_stress_summary_status"],
            "Selected screening score":
                row[score_column],
        }

        detail_rows = []
        for label, value in details.items():
            if pd.isna(value):
                display = "Not available"
            elif isinstance(value, float):
                display = f"{value:,.2f}"
            else:
                display = str(value)

            detail_rows.append({
                "Indicator": label,
                "Value": display,
            })

        st.dataframe(
            pd.DataFrame(detail_rows),
            hide_index=True,
        )

with method_tab:
    st.subheader("How the score works")
    st.write(
        "Each component is converted to a percentile among "
        "eligible counties. The weighted mean is multiplied "
        "by 100. Higher scores indicate higher combined values "
        "of the selected indicators."
    )
    st.write(
        "Eligibility requires listed facilities, complete water "
        "coverage, and nonmissing poverty and electricity values. "
        "Unscored counties remain in the dataset."
    )

    st.table(pd.DataFrame({
        "Scenario": list(scenarios),
        "Poverty weight": ["33⅓%", "50%", "25%", "25%"],
        "Electricity weight": ["33⅓%", "25%", "50%", "25%"],
        "Water weight": ["33⅓%", "25%", "25%", "50%"],
    }))

    st.subheader("Sources and limitations")
    st.write(
        "SAIPE estimates and electricity prices refer to 2024. "
        "Facility locations reflect the downloaded inventory "
        "snapshot. Aqueduct 4.0 supplies baseline annual water "
        "stress, not a 2024 measurement."
    )
    st.write(
        "Electricity prices are state-level residential prices. "
        "Water summaries describe listed facility locations, "
        "not county-wide conditions or facility water consumption."
    )
    st.write(
        "Missing water stress remains missing. No listed facilities "
        "does not prove absence of infrastructure. Invalid Aqueduct "
        "geometry was repaired, with an audit file retained."
    )
    st.write(
        "Rankings are sensitive to weighting choices: the "
        "electricity-emphasis scenario shared only four of the "
        "equal-weight scenario's top ten counties."
    )

    st.subheader("Coverage across all counties")
    coverage = (
        counties["water_stress_summary_status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Counties")
    )
    st.dataframe(coverage, hide_index=True)

st.download_button(
    "Download displayed county data",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="county_dashboard_selection.csv",
    mime="text/csv",
)

