</> Markdown

## Results and coverage

- 3,144 county records retained.
- 1,353 PeeringDB-listed facility records in the comparison scope.
- 312 counties contain listed facilities.
- 1,345 facilities have usable baseline water-stress matches.
- 310 counties have complete water coverage and screening scores.
- Eight facilities have missing or special water-stress values.
- One Puerto Rico facility is preserved separately outside the SAIPE comparison scope.
- All 51 state/DC residential electricity prices were checked against EIA Table 2.10 for 2024.

## Screening method

The preliminary score combines poverty rate, state residential
electricity price, and mean baseline water stress at listed facility
locations. Each component is converted to a percentile among the
310 eligible counties. The default score is the equal-weight mean
of those percentiles multiplied by 100.

Facility counts are displayed separately and are not a score component.

Alternative scenarios give one component 50% weight and the others
25% each. Top-ten overlap with equal weights was 9/10 for poverty
emphasis, 4/10 for electricity emphasis, and 8/10 for water emphasis.
Rankings therefore depend materially on weighting choices.

## Run the dashboard

The project was developed using Python 3.14.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

The dashboard uses the included processed CSV files. Raw downloads
are excluded from Git; see data_sources.md for source information.

## Important limitations

- PeeringDB-listed facilities are not a complete census of data centers
  or verified AI infrastructure. A record may cover multiple buildings.
- Electricity prices describe state residential customers, not facility
  operating costs or county-specific prices.
- Water stress describes the surroundings of listed facility locations,
  not facility water consumption or county-wide water stress.
- SAIPE and electricity values refer to 2024; facility locations reflect
  the downloaded snapshot; Aqueduct supplies baseline annual conditions.
- Missing values remain missing. No listed record does not prove absence
  of infrastructure.
- Scores are descriptive screening indicators, not causal estimates
  of infrastructure-related harm.

## Lessons learned

Preserving county FIPS as text prevents lost leading zeros. Spatial
matching requires consistent coordinate systems and valid geometry.
Repairing invalid Aqueduct polygons recovered 168 facility matches;
repair records were retained locally for audit. Weight sensitivity
checks showed why a single ranking should not be presented as definitive.