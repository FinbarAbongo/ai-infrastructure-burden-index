# Data-source checklist

Track potential datasets here. 
Mark a source as verified only after opening it and checking its documentation or downloaded data.

## 1. Data-center locations
- Status: Not verified
- Dataset/provider:
- Source URL:
- Variables needed: Facility name, location, operating status,
  opening date, capacity and evidence of AI use where available
- Geographic level:
- Years covered:
- Download method:
- Access conditions/license:
- Join keys: Coordinates or county FIPS, if available
- Limitations:
- Date checked:

## 2. Residential electricity prices
### Residential electricity prices
- Year: 2024.
- Geographic level: State, including Washington, DC.
- Unit: Cents per kilowatt-hour (cents/kWh).
- Join method: State abbreviation; each county receives its state's price.
- Limitation: These prices do not measure county-level variation,
  data-center electricity costs, or effects caused by facilities.
- Original source URL: [add the exact EIA download/page URL].
- Processed file: data/processed/electricity_states_2024.csv
- Combined file: data/processed/county_indicators_with_electricity.csv

### Electricity source verification
- Reference: EIA Electric Power Annual, Table 2.10.
- URL: https://www.eia.gov/electricity/annual/table.php?t=epa_02_10.html
- Column: Residential, Year 2024.
- Units: Cents per kilowatt-hour.
- Verified: October 6, 2026.
- Result: All 51 state/DC prices in the supplied CSV match the reference.
- Limitation: State residential prices are assigned to counties;
  they do not measure facility electricity costs or causal impacts.

## 3. Water stress
- Status: Not verified
- Dataset/provider:
- Source URL:
- Variables needed: Water-stress measure, location, reference period
- Geographic level:
- Years covered:
- Download method:
- Access conditions/license:
- Join keys:
- Limitations:
- Date checked:

## 4. Income and community demographics
- Status: Downloaded, inspected and cleaned
- Dataset/provider:
- Source URL:
- Variables needed: Median household income, poverty rate,
  population and demographic composition
- Geographic level:
- Years covered:
- Download method:
- Access conditions/license:
- Join keys: County FIPS, if available
- Limitations:
- Date checked:
- Validation: 3,144 county records; unique county FIPS codes.
- Missing estimates: Kalawao County, Hawaii (15005), has no
  poverty count, poverty rate or median household income estimate.
- Handling: Preserve missing values. Exclude this record only
  from analyses requiring those estimates; never replace with zero.
## 5. Grid constraints
- Status: Not verified
- Dataset/provider:
- Source URL:
- Variables needed: A documented measure of grid constraints
- Geographic level:
- Years covered:
- Download method:
- Access conditions/license:
- Join keys:
- Limitations:
- Date checked:


# Added notes
- Analysis coverage: 50 US states and Washington, DC.
- One facility record in Bayamón, Puerto Rico (72021), was
  retained separately because it is outside the SAIPE table.