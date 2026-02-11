# %% DISASTER DATA SUMMARY - NATIONAL AND DISTRICT LEVEL
# ============================================================================

import pandas as pd
import numpy as np
from datetime import datetime

print("="*70)
print("DISASTER DATA SUMMARY - NATIONAL AND DISTRICT ANALYSIS")
print("="*70)

# %% STEP 1: Load relational database
# ============================================================================

print("\n1. Loading relational database...")

db_file = '/Users/maxbobholz/Library/CloudStorage/OneDrive-SharedLibraries-mcw.edu/SSA Climate Health - General/1 - Document Analysis/Analysis/Event Database/A1_RelationalDatabase.xlsx'
db = pd.read_excel(db_file, sheet_name=None)

events = db['events']
ev_locations = db['ev_locations']
impacts = db['impacts']
district = db['district']
region = db['region']
ev_type = db['ev_type']

print(f"✓ Loaded database")
print(f"  Events: {len(events)}")
print(f"  Event locations: {len(ev_locations)}")
print(f"  Impact records: {len(impacts)}")

# %% STEP 2: Create comprehensive merged dataset
# ============================================================================

print("\n2. Creating comprehensive event-impact-location dataset...")

# Start with impacts
data = impacts.copy()

# Merge with event locations
data = data.merge(
    ev_locations[['ev_loc_id', 'event_id', 'district_id', 'primary_loc']], 
    on='ev_loc_id', 
    how='left',
    suffixes=('', '_evloc')
)

# Handle duplicate event_id column if it exists
if 'event_id_evloc' in data.columns:
    data['event_id'] = data['event_id_evloc']
    data = data.drop(columns=['event_id_evloc'])

# Merge with events to get date and type
data = data.merge(
    events[['event_id', 'event_date', 'ev_type_id']], 
    on='event_id', 
    how='left'
)

# Merge with event type
data = data.merge(
    ev_type[['ev_type_id', 'ev_type']], 
    on='ev_type_id', 
    how='left'
)

# Merge with district
data = data.merge(
    district[['district_id', 'dist_name', 'region_id']], 
    on='district_id', 
    how='left'
)

# Merge with region
data = data.merge(
    region[['region_id', 'reg_name']], 
    on='region_id', 
    how='left'
)

# Convert impact columns to numeric
impact_columns = ['aff_tot', 'injuries', 'deaths', 'disp_est', 
                  'home_dam', 'home_dest']

for col in impact_columns:
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int)

# Create homes_affected column (damaged + destroyed)
data['homes_affected'] = data['home_dam'] + data['home_dest']

# Extract year from event_date
data['event_year'] = pd.to_datetime(data['event_date'], errors='coerce').dt.year

# Filter to 2000-2025
data = data[(data['event_year'] >= 2000) & (data['event_year'] <= 2025)].copy()

print(f"✓ Created merged dataset: {len(data)} impact records")
print(f"  Date range: {data['event_year'].min():.0f} - {data['event_year'].max():.0f}")

# Filter to records with district locations
data_with_district = data[data['district_id'].notna()].copy()
print(f"  Records with district location: {len(data_with_district)}")

# %% STEP 3: NATIONAL LEVEL SUMMARY
# ============================================================================

print("\n3. Calculating NATIONAL level statistics...")

timestamp = datetime.now().strftime("%Y%m%d")

# National totals (all time 2000-2025)
national_totals = {
    'total_affected': data['aff_tot'].sum(),
    'total_displaced': data['disp_est'].sum(),
    'total_deaths': data['deaths'].sum(),
    'total_injuries': data['injuries'].sum(),
    'total_homes_affected': data['homes_affected'].sum(),
    'total_events': data['event_id'].nunique()
}

# Event counts by type (national)
event_type_counts = data.groupby('ev_type')['event_id'].nunique().to_dict()
national_event_counts = {
    'flood_events': event_type_counts.get('Flood', 0),
    'landslide_events': event_type_counts.get('Landslide', 0),
    'storm_events': event_type_counts.get('Storm', 0),
    'drought_events': event_type_counts.get('Drought', 0),
    'earthquake_events': event_type_counts.get('Earthquake', 0),
    'fire_events': event_type_counts.get('Fire', 0)
}

# Annual totals by year (national)
annual_national = data.groupby('event_year').agg({
    'aff_tot': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'homes_affected': 'sum',
    'event_id': 'nunique'
}).reset_index()

# Create dictionary of annual values for wide format
annual_dict = {}
for year in range(2000, 2026):
    year_data = annual_national[annual_national['event_year'] == year]
    if len(year_data) > 0:
        annual_dict[f'affected_{year}'] = year_data['aff_tot'].iloc[0]
        annual_dict[f'displaced_{year}'] = year_data['disp_est'].iloc[0]
        annual_dict[f'deaths_{year}'] = year_data['deaths'].iloc[0]
        annual_dict[f'homes_aff_{year}'] = year_data['homes_affected'].iloc[0]
        annual_dict[f'events_{year}'] = year_data['event_id'].iloc[0]
    else:
        annual_dict[f'affected_{year}'] = 0
        annual_dict[f'displaced_{year}'] = 0
        annual_dict[f'deaths_{year}'] = 0
        annual_dict[f'homes_aff_{year}'] = 0
        annual_dict[f'events_{year}'] = 0

# Pre-2020 vs Since 2020 comparison (national)
data_pre2020 = data[data['event_year'] < 2020]
data_since2020 = data[data['event_year'] >= 2020]

years_pre2020 = data_pre2020['event_year'].nunique()
years_since2020 = data_since2020['event_year'].nunique()

pre2020_stats = {
    'pre2020_affected': data_pre2020['aff_tot'].sum(),
    'pre2020_displaced': data_pre2020['disp_est'].sum(),
    'pre2020_deaths': data_pre2020['deaths'].sum(),
    'pre2020_homes_affected': data_pre2020['homes_affected'].sum(),
    'pre2020_events': data_pre2020['event_id'].nunique(),
    'pre2020_years': years_pre2020,
    'pre2020_avg_affected_per_year': data_pre2020['aff_tot'].sum() / years_pre2020 if years_pre2020 > 0 else 0,
    'pre2020_avg_displaced_per_year': data_pre2020['disp_est'].sum() / years_pre2020 if years_pre2020 > 0 else 0,
    'pre2020_avg_deaths_per_year': data_pre2020['deaths'].sum() / years_pre2020 if years_pre2020 > 0 else 0,
    'pre2020_avg_homes_per_year': data_pre2020['homes_affected'].sum() / years_pre2020 if years_pre2020 > 0 else 0,
    'pre2020_avg_events_per_year': data_pre2020['event_id'].nunique() / years_pre2020 if years_pre2020 > 0 else 0
}

since2020_stats = {
    'since2020_affected': data_since2020['aff_tot'].sum(),
    'since2020_displaced': data_since2020['disp_est'].sum(),
    'since2020_deaths': data_since2020['deaths'].sum(),
    'since2020_homes_affected': data_since2020['homes_affected'].sum(),
    'since2020_events': data_since2020['event_id'].nunique(),
    'since2020_years': years_since2020,
    'since2020_avg_affected_per_year': data_since2020['aff_tot'].sum() / years_since2020 if years_since2020 > 0 else 0,
    'since2020_avg_displaced_per_year': data_since2020['disp_est'].sum() / years_since2020 if years_since2020 > 0 else 0,
    'since2020_avg_deaths_per_year': data_since2020['deaths'].sum() / years_since2020 if years_since2020 > 0 else 0,
    'since2020_avg_homes_per_year': data_since2020['homes_affected'].sum() / years_since2020 if years_since2020 > 0 else 0,
    'since2020_avg_events_per_year': data_since2020['event_id'].nunique() / years_since2020 if years_since2020 > 0 else 0
}

# Combine all national data
national_summary = {
    'level': 'National',
    **national_totals,
    **national_event_counts,
    **pre2020_stats,
    **since2020_stats,
    **annual_dict
}

national_df = pd.DataFrame([national_summary])

# Save national summary
national_file = f'National_Summary_{timestamp}.csv'
national_df.to_csv(national_file, index=False)
print(f"✓ National summary saved: {national_file}")
print(f"  Total affected: {national_totals['total_affected']:,}")
print(f"  Total displaced: {national_totals['total_displaced']:,}")
print(f"  Total deaths: {national_totals['total_deaths']:,}")
print(f"  Total events: {national_totals['total_events']:,}")

# %% STEP 4: DISTRICT LEVEL SUMMARY
# ============================================================================

print("\n4. Calculating DISTRICT level statistics...")

# Get districts with at least one event
districts_with_events = data_with_district.groupby('district_id')['event_id'].nunique()
districts_with_events = districts_with_events[districts_with_events > 0].index.tolist()

print(f"  Districts with at least 1 event: {len(districts_with_events)}")

district_summaries = []

for dist_id in districts_with_events:
    dist_data = data_with_district[data_with_district['district_id'] == dist_id]
    
    # Get district name
    dist_name = dist_data['dist_name'].iloc[0] if len(dist_data) > 0 else f"District_{dist_id}"
    
    # District totals (all time)
    dist_totals = {
        'district_id': dist_id,
        'district_name': dist_name,
        'total_affected': dist_data['aff_tot'].sum(),
        'total_displaced': dist_data['disp_est'].sum(),
        'total_deaths': dist_data['deaths'].sum(),
        'total_injuries': dist_data['injuries'].sum(),
        'total_homes_affected': dist_data['homes_affected'].sum(),
        'total_events': dist_data['event_id'].nunique()
    }
    
    # Event counts by type for this district
    dist_event_counts = dist_data.groupby('ev_type')['event_id'].nunique().to_dict()
    dist_events = {
        'flood_events': dist_event_counts.get('Flood', 0),
        'landslide_events': dist_event_counts.get('Landslide', 0),
        'storm_events': dist_event_counts.get('Storm', 0),
        'drought_events': dist_event_counts.get('Drought', 0),
        'earthquake_events': dist_event_counts.get('Earthquake', 0),
        'fire_events': dist_event_counts.get('Fire', 0)
    }
    
    # Annual totals by year for this district
    annual_dist = dist_data.groupby('event_year').agg({
        'aff_tot': 'sum',
        'disp_est': 'sum',
        'deaths': 'sum',
        'homes_affected': 'sum',
        'event_id': 'nunique'
    }).reset_index()
    
    # Create dictionary of annual values
    dist_annual_dict = {}
    for year in range(2000, 2026):
        year_data = annual_dist[annual_dist['event_year'] == year]
        if len(year_data) > 0:
            dist_annual_dict[f'affected_{year}'] = year_data['aff_tot'].iloc[0]
            dist_annual_dict[f'displaced_{year}'] = year_data['disp_est'].iloc[0]
            dist_annual_dict[f'deaths_{year}'] = year_data['deaths'].iloc[0]
            dist_annual_dict[f'homes_aff_{year}'] = year_data['homes_affected'].iloc[0]
            dist_annual_dict[f'events_{year}'] = year_data['event_id'].iloc[0]
        else:
            dist_annual_dict[f'affected_{year}'] = 0
            dist_annual_dict[f'displaced_{year}'] = 0
            dist_annual_dict[f'deaths_{year}'] = 0
            dist_annual_dict[f'homes_aff_{year}'] = 0
            dist_annual_dict[f'events_{year}'] = 0
    
    # Pre-2020 vs Since 2020 for this district
    dist_pre2020 = dist_data[dist_data['event_year'] < 2020]
    dist_since2020 = dist_data[dist_data['event_year'] >= 2020]
    
    dist_years_pre2020 = dist_pre2020['event_year'].nunique()
    dist_years_since2020 = dist_since2020['event_year'].nunique()
    
    # Handle division by zero
    if dist_years_pre2020 == 0:
        dist_years_pre2020 = 1  # Avoid division by zero, will show 0 averages
    if dist_years_since2020 == 0:
        dist_years_since2020 = 1
    
    dist_pre2020_stats = {
        'pre2020_affected': dist_pre2020['aff_tot'].sum(),
        'pre2020_displaced': dist_pre2020['disp_est'].sum(),
        'pre2020_deaths': dist_pre2020['deaths'].sum(),
        'pre2020_homes_affected': dist_pre2020['homes_affected'].sum(),
        'pre2020_events': dist_pre2020['event_id'].nunique(),
        'pre2020_years': dist_pre2020['event_year'].nunique(),
        'pre2020_avg_affected_per_year': dist_pre2020['aff_tot'].sum() / dist_years_pre2020,
        'pre2020_avg_displaced_per_year': dist_pre2020['disp_est'].sum() / dist_years_pre2020,
        'pre2020_avg_deaths_per_year': dist_pre2020['deaths'].sum() / dist_years_pre2020,
        'pre2020_avg_homes_per_year': dist_pre2020['homes_affected'].sum() / dist_years_pre2020,
        'pre2020_avg_events_per_year': dist_pre2020['event_id'].nunique() / dist_years_pre2020
    }
    
    dist_since2020_stats = {
        'since2020_affected': dist_since2020['aff_tot'].sum(),
        'since2020_displaced': dist_since2020['disp_est'].sum(),
        'since2020_deaths': dist_since2020['deaths'].sum(),
        'since2020_homes_affected': dist_since2020['homes_affected'].sum(),
        'since2020_events': dist_since2020['event_id'].nunique(),
        'since2020_years': dist_since2020['event_year'].nunique(),
        'since2020_avg_affected_per_year': dist_since2020['aff_tot'].sum() / dist_years_since2020,
        'since2020_avg_displaced_per_year': dist_since2020['disp_est'].sum() / dist_years_since2020,
        'since2020_avg_deaths_per_year': dist_since2020['deaths'].sum() / dist_years_since2020,
        'since2020_avg_homes_per_year': dist_since2020['homes_affected'].sum() / dist_years_since2020,
        'since2020_avg_events_per_year': dist_since2020['event_id'].nunique() / dist_years_since2020
    }
    
    # Combine all district data
    district_summary = {
        **dist_totals,
        **dist_events,
        **dist_pre2020_stats,
        **dist_since2020_stats,
        **dist_annual_dict
    }
    
    district_summaries.append(district_summary)

district_df = pd.DataFrame(district_summaries)

# Sort by total displaced (descending)
district_df = district_df.sort_values('total_displaced', ascending=False)

# Save district summary
district_file = f'District_Summary_{timestamp}.csv'
district_df.to_csv(district_file, index=False)
print(f"✓ District summary saved: {district_file}")
print(f"  Districts included: {len(district_df)}")

# %% STEP 5: CREATE TEXT SUMMARY REPORT
# ============================================================================

print("\n5. Creating summary report...")

report = []
report.append("="*80)
report.append("UGANDA DISASTER DATA SUMMARY REPORT")
report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append(f"Time Period: 2000 - 2025")
report.append("="*80)
report.append("")

# National Summary
report.append("NATIONAL LEVEL SUMMARY")
report.append("-"*80)
report.append(f"Total Events: {national_totals['total_events']:,}")
report.append("")
report.append("Event Types:")
report.append(f"  Floods: {national_event_counts['flood_events']:,}")
report.append(f"  Landslides: {national_event_counts['landslide_events']:,}")
report.append(f"  Storms: {national_event_counts['storm_events']:,}")
report.append(f"  Droughts: {national_event_counts['drought_events']:,}")
report.append(f"  Earthquakes: {national_event_counts['earthquake_events']:,}")
report.append(f"  Fires: {national_event_counts['fire_events']:,}")
report.append("")
report.append("Total Impacts (2000-2025):")
report.append(f"  People Affected: {national_totals['total_affected']:,}")
report.append(f"  People Displaced: {national_totals['total_displaced']:,}")
report.append(f"  Deaths: {national_totals['total_deaths']:,}")
report.append(f"  Injuries: {national_totals['total_injuries']:,}")
report.append(f"  Homes Affected: {national_totals['total_homes_affected']:,}")
report.append("")
report.append("="*80)
report.append("TEMPORAL COMPARISON: PRE-2020 vs SINCE 2020")
report.append("="*80)
report.append("")
report.append(f"PRE-2020 ({int(pre2020_stats['pre2020_years'])} years: 2000-2019)")
report.append("-"*80)
report.append(f"Total affected: {pre2020_stats['pre2020_affected']:,}")
report.append(f"Total displaced: {pre2020_stats['pre2020_displaced']:,}")
report.append(f"Total deaths: {pre2020_stats['pre2020_deaths']:,}")
report.append(f"Total homes affected: {pre2020_stats['pre2020_homes_affected']:,}")
report.append(f"Total events: {pre2020_stats['pre2020_events']:,}")
report.append("")
report.append("Annual Averages (Pre-2020):")
report.append(f"  Affected per year: {pre2020_stats['pre2020_avg_affected_per_year']:,.1f}")
report.append(f"  Displaced per year: {pre2020_stats['pre2020_avg_displaced_per_year']:,.1f}")
report.append(f"  Deaths per year: {pre2020_stats['pre2020_avg_deaths_per_year']:,.1f}")
report.append(f"  Homes affected per year: {pre2020_stats['pre2020_avg_homes_per_year']:,.1f}")
report.append(f"  Events per year: {pre2020_stats['pre2020_avg_events_per_year']:,.1f}")
report.append("")
report.append(f"SINCE 2020 ({int(since2020_stats['since2020_years'])} years: 2020-2025)")
report.append("-"*80)
report.append(f"Total affected: {since2020_stats['since2020_affected']:,}")
report.append(f"Total displaced: {since2020_stats['since2020_displaced']:,}")
report.append(f"Total deaths: {since2020_stats['since2020_deaths']:,}")
report.append(f"Total homes affected: {since2020_stats['since2020_homes_affected']:,}")
report.append(f"Total events: {since2020_stats['since2020_events']:,}")
report.append("")
report.append("Annual Averages (Since 2020):")
report.append(f"  Affected per year: {since2020_stats['since2020_avg_affected_per_year']:,.1f}")
report.append(f"  Displaced per year: {since2020_stats['since2020_avg_displaced_per_year']:,.1f}")
report.append(f"  Deaths per year: {since2020_stats['since2020_avg_deaths_per_year']:,.1f}")
report.append(f"  Homes affected per year: {since2020_stats['since2020_avg_homes_per_year']:,.1f}")
report.append(f"  Events per year: {since2020_stats['since2020_avg_events_per_year']:,.1f}")
report.append("")

# Calculate percent changes
if pre2020_stats['pre2020_avg_displaced_per_year'] > 0:
    disp_change = ((since2020_stats['since2020_avg_displaced_per_year'] - pre2020_stats['pre2020_avg_displaced_per_year']) 
                   / pre2020_stats['pre2020_avg_displaced_per_year'] * 100)
else:
    disp_change = 0

if pre2020_stats['pre2020_avg_affected_per_year'] > 0:
    aff_change = ((since2020_stats['since2020_avg_affected_per_year'] - pre2020_stats['pre2020_avg_affected_per_year']) 
                  / pre2020_stats['pre2020_avg_affected_per_year'] * 100)
else:
    aff_change = 0

if pre2020_stats['pre2020_avg_events_per_year'] > 0:
    ev_change = ((since2020_stats['since2020_avg_events_per_year'] - pre2020_stats['pre2020_avg_events_per_year']) 
                 / pre2020_stats['pre2020_avg_events_per_year'] * 100)
else:
    ev_change = 0

report.append("CHANGE IN ANNUAL AVERAGES")
report.append("-"*80)
report.append(f"Displaced per year: {disp_change:+.1f}%")
report.append(f"Affected per year: {aff_change:+.1f}%")
report.append(f"Events per year: {ev_change:+.1f}%")
report.append("")
report.append("="*80)
report.append("TOP 10 MOST AFFECTED DISTRICTS (by total displaced)")
report.append("="*80)
report.append("")

top_10 = district_df.head(10)
for idx, row in top_10.iterrows():
    report.append(f"{row['district_name']:25s}")
    report.append(f"  Displaced: {row['total_displaced']:,}")
    report.append(f"  Affected: {row['total_affected']:,}")
    report.append(f"  Deaths: {row['total_deaths']:,}")
    report.append(f"  Events: {row['total_events']:,}")
    report.append("")

report.append("="*80)
report.append("FILES CREATED")
report.append("="*80)
report.append(f"{national_file}")
report.append(f"  National-level statistics with annual data (2000-2025)")
report.append("")
report.append(f"{district_file}")
report.append(f"  District-level statistics for {len(district_df)} districts with events")
report.append("")
report.append("="*80)

report_text = "\n".join(report)
print("\n" + report_text)

# Save report
report_file = f'Summary_Report_{timestamp}.txt'
with open(report_file, 'w') as f:
    f.write(report_text)

print(f"\n✓ Summary report saved: {report_file}")

# %% FINAL SUMMARY
# ============================================================================

print("\n" + "="*70)
print("SUMMARY COMPLETE")
print("="*70)
print(f"\n📁 FILES CREATED:")
print(f"  1. {national_file}")
print(f"     → National statistics with annual data")
print(f"  2. {district_file}")
print(f"     → {len(district_df)} districts with events")
print(f"  3. {report_file}")
print(f"     → Human-readable summary report")
print(f"\n✅ All summary data generated successfully!")
print("="*70)