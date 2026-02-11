#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  9 11:01:06 2026

@author: maxbobholz
"""

# %% COMPREHENSIVE DATABASE PULL - Events and Impacts by District
# ============================================================================

import pandas as pd
import geopandas as gpd
import numpy as np
from datetime import datetime

print("="*70)
print("COMPREHENSIVE DISASTER DATA PULL - EVENTS & IMPACTS")
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
print(f"  Districts: {len(district)}")

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

# If there are duplicate event_id columns, keep the one from ev_locations
if 'event_id_evloc' in data.columns:
    data['event_id'] = data['event_id_evloc']
    data = data.drop(columns=['event_id_evloc'])

# Merge with events to get date and type
data = data.merge(
    events[['event_id', 'event_date', 'ev_type_id']], 
    on='event_id', 
    how='left',
    suffixes=('', '_event')
)

# Merge with event type
data = data.merge(
    ev_type[['ev_type_id', 'ev_type']], 
    on='ev_type_id', 
    how='left',
    suffixes=('', '_type')
)

# Merge with district
data = data.merge(
    district[['district_id', 'dist_name', 'region_id']], 
    on='district_id', 
    how='left',
    suffixes=('', '_dist')
)

# Merge with region
data = data.merge(
    region[['region_id', 'reg_name']], 
    on='region_id', 
    how='left',
    suffixes=('', '_reg')
)

# Convert impact columns to numeric
impact_columns = ['aff_tot', 'aff_m', 'aff_f', 'aff_u18', 'aff_18_64', 'aff_65o',
                  'injuries', 'deaths', 'missing', 'idps', 'disp_raw', 'disp_est',
                  'hh_aff', 'home_dam', 'home_dest', 'facil_aff']

for col in impact_columns:
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int)

# Extract year from event_date
data['event_year'] = pd.to_datetime(data['event_date'], errors='coerce').dt.year

# Get date range
min_year = data['event_year'].min()
max_year = data['event_year'].max()

print(f"✓ Created merged dataset: {len(data)} impact records")
print(f"  Date range: {min_year:.0f} - {max_year:.0f}")
print(f"  Records with district location: {data['district_id'].notna().sum()}")

# Filter to records with district locations
data_with_district = data[data['district_id'].notna()].copy()

print(f"  Working with {len(data_with_district)} records with district locations")

# %% STEP 3: Count unique events by district and type (from previous script)
# ============================================================================

print("\n3. Counting events by district and type...")

# Count UNIQUE events per district (total)
total_events_by_district = data_with_district.groupby('district_id')['event_id'].nunique().reset_index()
total_events_by_district.columns = ['district_id', 'total_events']

# Count UNIQUE events per district BY TYPE
events_by_district_type = data_with_district.groupby(['district_id', 'ev_type'])['event_id'].nunique().reset_index()
events_by_district_type.columns = ['district_id', 'ev_type', 'event_count']

# Pivot to get one column per event type
events_pivot = events_by_district_type.pivot(
    index='district_id', 
    columns='ev_type', 
    values='event_count'
).reset_index()

events_pivot = events_pivot.fillna(0)

# Rename columns
column_mapping = {
    'Flood': 'flood_events',
    'Landslide': 'landslide_events',
    'Storm': 'storm_events',
    'Drought': 'drought_events',
    'Earthquake': 'earthquake_events',
    'Fire': 'fire_events'
}

events_pivot = events_pivot.rename(columns=column_mapping)

# Add total events
district_events = events_pivot.merge(total_events_by_district, on='district_id', how='outer').fillna(0)

print(f"✓ Event counts calculated for {len(district_events)} districts")

# %% STEP 4: Calculate impact metrics by district - ALL TIME
# ============================================================================

print("\n4. Calculating impact metrics - ALL TIME...")

impacts_by_district_all = data_with_district.groupby('district_id').agg({
    'idps': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'injuries': 'sum',
    'aff_tot': 'sum',
    'home_dest': 'sum',
    'home_dam': 'sum',
    'facil_aff': 'sum',
    'hh_aff': 'sum',
    'event_id': 'nunique'
}).reset_index()

impacts_by_district_all.columns = [
    'district_id', 'total_idps', 'total_displaced', 'total_deaths', 
    'total_injuries', 'total_affected', 'total_homes_destroyed', 
    'total_homes_damaged', 'total_facilities_affected', 'total_households_affected',
    'total_events_check'
]

print(f"✓ All-time impacts calculated")
print(f"  Total displaced: {impacts_by_district_all['total_displaced'].sum():,.0f}")
print(f"  Total deaths: {impacts_by_district_all['total_deaths'].sum():,.0f}")
print(f"  Total affected: {impacts_by_district_all['total_affected'].sum():,.0f}")

# %% STEP 5: Calculate impact metrics by district - PRE-2020
# ============================================================================

print("\n5. Calculating impact metrics - PRE-2020...")

data_pre2020 = data_with_district[data_with_district['event_year'] < 2020].copy()

impacts_by_district_pre2020 = data_pre2020.groupby('district_id').agg({
    'idps': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'injuries': 'sum',
    'aff_tot': 'sum',
    'home_dest': 'sum',
    'home_dam': 'sum',
    'facil_aff': 'sum',
    'hh_aff': 'sum',
    'event_id': 'nunique'
}).reset_index()

impacts_by_district_pre2020.columns = [
    'district_id', 'pre2020_idps', 'pre2020_displaced', 'pre2020_deaths', 
    'pre2020_injuries', 'pre2020_affected', 'pre2020_homes_destroyed', 
    'pre2020_homes_damaged', 'pre2020_facilities_affected', 'pre2020_households_affected',
    'pre2020_events'
]

print(f"✓ Pre-2020 impacts calculated")
print(f"  Period: {data_pre2020['event_year'].min():.0f} - 2019")
print(f"  Total displaced: {impacts_by_district_pre2020['pre2020_displaced'].sum():,.0f}")
print(f"  Total deaths: {impacts_by_district_pre2020['pre2020_deaths'].sum():,.0f}")
print(f"  Total events: {impacts_by_district_pre2020['pre2020_events'].sum():.0f}")

# %% STEP 6: Calculate impact metrics by district - SINCE 2020
# ============================================================================

print("\n6. Calculating impact metrics - SINCE 2020...")

data_since2020 = data_with_district[data_with_district['event_year'] >= 2020].copy()

impacts_by_district_since2020 = data_since2020.groupby('district_id').agg({
    'idps': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'injuries': 'sum',
    'aff_tot': 'sum',
    'home_dest': 'sum',
    'home_dam': 'sum',
    'facil_aff': 'sum',
    'hh_aff': 'sum',
    'event_id': 'nunique'
}).reset_index()

impacts_by_district_since2020.columns = [
    'district_id', 'since2020_idps', 'since2020_displaced', 'since2020_deaths', 
    'since2020_injuries', 'since2020_affected', 'since2020_homes_destroyed', 
    'since2020_homes_damaged', 'since2020_facilities_affected', 'since2020_households_affected',
    'since2020_events'
]

print(f"✓ Since 2020 impacts calculated")
print(f"  Period: 2020 - {data_since2020['event_year'].max():.0f}")
print(f"  Total displaced: {impacts_by_district_since2020['since2020_displaced'].sum():,.0f}")
print(f"  Total deaths: {impacts_by_district_since2020['since2020_deaths'].sum():,.0f}")
print(f"  Total events: {impacts_by_district_since2020['since2020_events'].sum():.0f}")

# %% STEP 7: Calculate impact metrics by district and YEAR
# ============================================================================

print("\n7. Calculating annual impact metrics by district...")

impacts_by_district_year = data_with_district.groupby(['district_id', 'event_year']).agg({
    'idps': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'injuries': 'sum',
    'aff_tot': 'sum',
    'home_dest': 'sum',
    'home_dam': 'sum',
    'facil_aff': 'sum',
    'hh_aff': 'sum',
    'event_id': 'nunique'
}).reset_index()

impacts_by_district_year.columns = [
    'district_id', 'year', 'idps', 'displaced', 'deaths', 
    'injuries', 'affected', 'homes_destroyed', 'homes_damaged', 
    'facilities_affected', 'households_affected', 'num_events'
]

print(f"✓ Annual impacts calculated: {len(impacts_by_district_year)} district-year records")
print(f"  Years covered: {impacts_by_district_year['year'].min():.0f} - {impacts_by_district_year['year'].max():.0f}")

# %% STEP 8: Calculate annual averages - ALL TIME
# ============================================================================

print("\n8. Calculating annual averages - ALL TIME...")

# Calculate number of years in dataset
years_in_data = data_with_district['event_year'].nunique()
min_year_data = data_with_district['event_year'].min()
max_year_data = data_with_district['event_year'].max()

print(f"  Time period: {min_year_data:.0f} - {max_year_data:.0f} ({years_in_data} years)")

annual_avg_all = impacts_by_district_all.copy()
annual_avg_all['avg_displaced_per_year'] = (annual_avg_all['total_displaced'] / years_in_data).round(1)
annual_avg_all['avg_deaths_per_year'] = (annual_avg_all['total_deaths'] / years_in_data).round(1)
annual_avg_all['avg_injuries_per_year'] = (annual_avg_all['total_injuries'] / years_in_data).round(1)
annual_avg_all['avg_affected_per_year'] = (annual_avg_all['total_affected'] / years_in_data).round(1)
annual_avg_all['avg_homes_destroyed_per_year'] = (annual_avg_all['total_homes_destroyed'] / years_in_data).round(1)
annual_avg_all['avg_homes_damaged_per_year'] = (annual_avg_all['total_homes_damaged'] / years_in_data).round(1)
annual_avg_all['avg_facilities_per_year'] = (annual_avg_all['total_facilities_affected'] / years_in_data).round(1)
annual_avg_all['avg_events_per_year'] = (annual_avg_all['total_events_check'] / years_in_data).round(1)

print(f"✓ All-time annual averages calculated")

# %% STEP 9: Calculate annual averages - PRE-2020
# ============================================================================

print("\n9. Calculating annual averages - PRE-2020...")

years_pre2020 = data_pre2020['event_year'].nunique()
print(f"  Years in pre-2020 period: {years_pre2020}")

annual_avg_pre2020 = impacts_by_district_pre2020.copy()
annual_avg_pre2020['avg_displaced_per_year_pre2020'] = (annual_avg_pre2020['pre2020_displaced'] / years_pre2020).round(1)
annual_avg_pre2020['avg_deaths_per_year_pre2020'] = (annual_avg_pre2020['pre2020_deaths'] / years_pre2020).round(1)
annual_avg_pre2020['avg_injuries_per_year_pre2020'] = (annual_avg_pre2020['pre2020_injuries'] / years_pre2020).round(1)
annual_avg_pre2020['avg_affected_per_year_pre2020'] = (annual_avg_pre2020['pre2020_affected'] / years_pre2020).round(1)
annual_avg_pre2020['avg_homes_destroyed_per_year_pre2020'] = (annual_avg_pre2020['pre2020_homes_destroyed'] / years_pre2020).round(1)
annual_avg_pre2020['avg_events_per_year_pre2020'] = (annual_avg_pre2020['pre2020_events'] / years_pre2020).round(1)

print(f"✓ Pre-2020 annual averages calculated")

# %% STEP 10: Calculate annual averages - SINCE 2020
# ============================================================================

print("\n10. Calculating annual averages - SINCE 2020...")

years_since2020 = data_since2020['event_year'].nunique()
print(f"  Years in since-2020 period: {years_since2020}")

annual_avg_since2020 = impacts_by_district_since2020.copy()
annual_avg_since2020['avg_displaced_per_year_since2020'] = (annual_avg_since2020['since2020_displaced'] / years_since2020).round(1)
annual_avg_since2020['avg_deaths_per_year_since2020'] = (annual_avg_since2020['since2020_deaths'] / years_since2020).round(1)
annual_avg_since2020['avg_injuries_per_year_since2020'] = (annual_avg_since2020['since2020_injuries'] / years_since2020).round(1)
annual_avg_since2020['avg_affected_per_year_since2020'] = (annual_avg_since2020['since2020_affected'] / years_since2020).round(1)
annual_avg_since2020['avg_homes_destroyed_per_year_since2020'] = (annual_avg_since2020['since2020_homes_destroyed'] / years_since2020).round(1)
annual_avg_since2020['avg_events_per_year_since2020'] = (annual_avg_since2020['since2020_events'] / years_since2020).round(1)

print(f"✓ Since 2020 annual averages calculated")

# %% STEP 11: Merge all datasets together
# ============================================================================

print("\n11. Merging all datasets...")

# Start with district info
master_dataset = district[['district_id', 'dist_name', 'region_id', 'dist_pop2023', 'dist_area']].copy()

# Add region
master_dataset = master_dataset.merge(
    region[['region_id', 'reg_name']], 
    on='region_id', 
    how='left'
)

# Add event counts
master_dataset = master_dataset.merge(district_events, on='district_id', how='left')

# Add all-time impacts
master_dataset = master_dataset.merge(impacts_by_district_all, on='district_id', how='left')

# Add pre-2020 impacts
master_dataset = master_dataset.merge(impacts_by_district_pre2020, on='district_id', how='left')

# Add since 2020 impacts
master_dataset = master_dataset.merge(impacts_by_district_since2020, on='district_id', how='left')

# Add all-time averages (select only avg columns)
avg_cols_all = ['district_id'] + [col for col in annual_avg_all.columns if col.startswith('avg_')]
master_dataset = master_dataset.merge(annual_avg_all[avg_cols_all], on='district_id', how='left')

# Add pre-2020 averages
avg_cols_pre = ['district_id'] + [col for col in annual_avg_pre2020.columns if col.startswith('avg_')]
master_dataset = master_dataset.merge(annual_avg_pre2020[avg_cols_pre], on='district_id', how='left')

# Add since 2020 averages
avg_cols_since = ['district_id'] + [col for col in annual_avg_since2020.columns if col.startswith('avg_')]
master_dataset = master_dataset.merge(annual_avg_since2020[avg_cols_since], on='district_id', how='left')

# Fill NaN with 0
master_dataset = master_dataset.fillna(0)

print(f"✓ Master dataset created: {len(master_dataset)} districts, {len(master_dataset.columns)} columns")

# %% STEP 12: Add district info to annual data
# ============================================================================

print("\n12. Adding district info to annual dataset...")

impacts_by_district_year = impacts_by_district_year.merge(
    district[['district_id', 'dist_name', 'region_id']], 
    on='district_id', 
    how='left'
)

impacts_by_district_year = impacts_by_district_year.merge(
    region[['region_id', 'reg_name']], 
    on='region_id', 
    how='left'
)

print(f"✓ Annual dataset enhanced")

# %% STEP 13: Export CSV files
# ============================================================================

print("\n13. Exporting CSV files...")

timestamp = datetime.now().strftime("%Y%m%d")

# Master dataset with all metrics
master_csv = f'Districts_AllMetrics_{timestamp}.csv'
master_dataset.to_csv(master_csv, index=False)
print(f"  ✓ {master_csv}")

# Annual data
annual_csv = f'Districts_AnnualMetrics_{timestamp}.csv'
impacts_by_district_year.to_csv(annual_csv, index=False)
print(f"  ✓ {annual_csv}")

# All-time impacts only
alltime_csv = f'Districts_AllTime_Impacts_{timestamp}.csv'
alltime_export = master_dataset[
    ['district_id', 'dist_name', 'reg_name', 'total_events'] + 
    [col for col in master_dataset.columns if col.startswith('total_')]
].copy()
alltime_export.to_csv(alltime_csv, index=False)
print(f"  ✓ {alltime_csv}")

# Pre-2020 impacts only
pre2020_csv = f'Districts_Pre2020_Impacts_{timestamp}.csv'
pre2020_export = master_dataset[
    ['district_id', 'dist_name', 'reg_name'] + 
    [col for col in master_dataset.columns if 'pre2020' in col]
].copy()
pre2020_export.to_csv(pre2020_csv, index=False)
print(f"  ✓ {pre2020_csv}")

# Since 2020 impacts only
since2020_csv = f'Districts_Since2020_Impacts_{timestamp}.csv'
since2020_export = master_dataset[
    ['district_id', 'dist_name', 'reg_name'] + 
    [col for col in master_dataset.columns if 'since2020' in col]
].copy()
since2020_export.to_csv(since2020_csv, index=False)
print(f"  ✓ {since2020_csv}")

# Annual averages only
annual_avg_csv = f'Districts_AnnualAverages_{timestamp}.csv'
annual_avg_export = master_dataset[
    ['district_id', 'dist_name', 'reg_name', 'total_events'] + 
    [col for col in master_dataset.columns if col.startswith('avg_')]
].copy()
annual_avg_export.to_csv(annual_avg_csv, index=False)
print(f"  ✓ {annual_avg_csv}")

# %% STEP 14: Create shapefiles with meaningful short names
# ============================================================================

print("\n14. Creating shapefiles with meaningful field names...")

shapefile_path = '/Users/maxbobholz/Library/CloudStorage/OneDrive-SharedLibraries-mcw.edu/SSA Climate Health - General/1 - Document Analysis/Analysis/Event Mapping/shapes/Uganda_Districts_3D_Data.shp'

try:
    gdf = gpd.read_file(shapefile_path)
    print(f"  ✓ Loaded base shapefile: {len(gdf)} districts")
    
    # The column is 'district_i' (truncated from district_id by shapefile format)
    if 'district_i' in gdf.columns:
        gdf['district_id'] = gdf['district_i']
    elif 'district_id' not in gdf.columns:
        if 'dist_id' in gdf.columns:
            gdf['district_id'] = gdf['dist_id']
    
    # Ensure district_id is integer in both datasets
    gdf['district_id'] = pd.to_numeric(gdf['district_id'], errors='coerce').astype('Int64')
    master_dataset['district_id'] = pd.to_numeric(master_dataset['district_id'], errors='coerce').astype('Int64')
    
    print(f"  Sample district IDs from shapefile: {gdf['district_id'].dropna().head().tolist()}")
    print(f"  Sample district IDs from database: {master_dataset['district_id'].dropna().head().tolist()}")
    
    # Create field name mapping for shapefiles (10 char limit)
    # Format: short_name: (long_name, description)
    field_mapping = {
        # Identifiers and basic info
        'dist_id': ('district_id', 'District ID number'),
        'dist_name': ('dist_name', 'District name'),
        'region': ('reg_name', 'Region name'),
        'pop2023': ('dis_pop2023', 'Population (2023)'),
        'area_km2': ('dist_area', 'Area in square kilometers'),
        
        # Event counts by type
        'ev_flood': ('flood_events', 'Number of flood events'),
        'ev_slide': ('landslide_events', 'Number of landslide events'),
        'ev_storm': ('storm_events', 'Number of storm events'),
        'ev_drought': ('drought_events', 'Number of drought events'),
        'ev_quake': ('earthquake_events', 'Number of earthquake events'),
        'ev_fire': ('fire_events', 'Number of fire events'),
        'ev_total': ('total_events', 'Total number of events'),
        
        # All-time cumulative impacts
        'tot_idps': ('total_idps', 'Total IDPs (all time)'),
        'tot_displ': ('total_displaced', 'Total displaced (all time)'),
        'tot_deaths': ('total_deaths', 'Total deaths (all time)'),
        'tot_injur': ('total_injuries', 'Total injuries (all time)'),
        'tot_affect': ('total_affected', 'Total affected (all time)'),
        'homes_dest': ('total_homes_destroyed', 'Homes destroyed (all time)'),
        'homes_dam': ('total_homes_damaged', 'Homes damaged (all time)'),
        'facil_aff': ('total_facilities_affected', 'Facilities affected (all time)'),
        'hh_affect': ('total_households_affected', 'Households affected (all time)'),
        
        # Pre-2020 impacts
        'pre_idps': ('pre2020_idps', 'IDPs before 2020'),
        'pre_displ': ('pre2020_displaced', 'Displaced before 2020'),
        'pre_deaths': ('pre2020_deaths', 'Deaths before 2020'),
        'pre_injur': ('pre2020_injuries', 'Injuries before 2020'),
        'pre_affect': ('pre2020_affected', 'Affected before 2020'),
        'pre_h_dest': ('pre2020_homes_destroyed', 'Homes destroyed before 2020'),
        'pre_h_dam': ('pre2020_homes_damaged', 'Homes damaged before 2020'),
        'pre_facil': ('pre2020_facilities_affected', 'Facilities affected before 2020'),
        'pre_hh': ('pre2020_households_affected', 'Households affected before 2020'),
        'pre_events': ('pre2020_events', 'Events before 2020'),
        
        # Since 2020 impacts
        'sin_idps': ('since2020_idps', 'IDPs since 2020'),
        'sin_displ': ('since2020_displaced', 'Displaced since 2020'),
        'sin_deaths': ('since2020_deaths', 'Deaths since 2020'),
        'sin_injur': ('since2020_injuries', 'Injuries since 2020'),
        'sin_affect': ('since2020_affected', 'Affected since 2020'),
        'sin_h_dest': ('since2020_homes_destroyed', 'Homes destroyed since 2020'),
        'sin_h_dam': ('since2020_homes_damaged', 'Homes damaged since 2020'),
        'sin_facil': ('since2020_facilities_affected', 'Facilities affected since 2020'),
        'sin_hh': ('since2020_households_affected', 'Households affected since 2020'),
        'sin_events': ('since2020_events', 'Events since 2020'),
        
        # Annual averages - all time
        'avg_displ': ('avg_displaced_per_year', 'Avg displaced per year (all time)'),
        'avg_deaths': ('avg_deaths_per_year', 'Avg deaths per year (all time)'),
        'avg_injur': ('avg_injuries_per_year', 'Avg injuries per year (all time)'),
        'avg_affect': ('avg_affected_per_year', 'Avg affected per year (all time)'),
        'avg_h_dest': ('avg_homes_destroyed_per_year', 'Avg homes destroyed per year (all time)'),
        'avg_h_dam': ('avg_homes_damaged_per_year', 'Avg homes damaged per year (all time)'),
        'avg_facil': ('avg_facilities_per_year', 'Avg facilities per year (all time)'),
        'avg_events': ('avg_events_per_year', 'Avg events per year (all time)'),
        
        # Annual averages - pre-2020
        'avg_pre_dp': ('avg_displaced_per_year_pre2020', 'Avg displaced per year (pre-2020)'),
        'avg_pre_dt': ('avg_deaths_per_year_pre2020', 'Avg deaths per year (pre-2020)'),
        'avg_pre_in': ('avg_injuries_per_year_pre2020', 'Avg injuries per year (pre-2020)'),
        'avg_pre_af': ('avg_affected_per_year_pre2020', 'Avg affected per year (pre-2020)'),
        'avg_pre_hd': ('avg_homes_destroyed_per_year_pre2020', 'Avg homes destroyed per year (pre-2020)'),
        'avg_pre_ev': ('avg_events_per_year_pre2020', 'Avg events per year (pre-2020)'),
        
        # Annual averages - since 2020
        'avg_sin_dp': ('avg_displaced_per_year_since2020', 'Avg displaced per year (since 2020)'),
        'avg_sin_dt': ('avg_deaths_per_year_since2020', 'Avg deaths per year (since 2020)'),
        'avg_sin_in': ('avg_injuries_per_year_since2020', 'Avg injuries per year (since 2020)'),
        'avg_sin_af': ('avg_affected_per_year_since2020', 'Avg affected per year (since 2020)'),
        'avg_sin_hd': ('avg_homes_destroyed_per_year_since2020', 'Avg homes destroyed per year (since 2020)'),
        'avg_sin_ev': ('avg_events_per_year_since2020', 'Avg events per year (since 2020)')
    }
    
    # Create reverse mapping (long name -> short name)
    long_to_short = {v[0]: k for k, v in field_mapping.items()}
    
    # Function to rename columns in dataset
    def rename_for_shapefile(df, field_mapping_dict):
        """Rename columns to shapefile-friendly names"""
        rename_dict = {}
        for col in df.columns:
            if col in field_mapping_dict:
                rename_dict[col] = field_mapping_dict[col]
        return df.rename(columns=rename_dict)
    
    print(f"\n  Applying field name mapping...")
    
    # Create minimal GeoDataFrame
    gdf_minimal = gdf[['district_id', 'geometry']].copy()
    
    # Merge and rename for comprehensive shapefile
    gdf_master = gdf_minimal.merge(master_dataset, on='district_id', how='left')
    gdf_master = gdf_master.loc[:, ~gdf_master.columns.duplicated()]
    gdf_master = gdf_master.fillna(0).infer_objects(copy=False)
    gdf_master_renamed = rename_for_shapefile(gdf_master, long_to_short)
    
    districts_with_data = (gdf_master_renamed['ev_total'] > 0).sum()
    print(f"  ✓ Merged shapefile: {len(gdf_master_renamed)} districts, {len(gdf_master_renamed.columns)} columns")
    print(f"  ✓ Districts with event data: {districts_with_data}")
    
    if districts_with_data == 0:
        print(f"  ⚠ WARNING: No districts matched! Check district_id alignment")
    
    # Save master shapefile
    print(f"\n  Saving shapefiles...")
    master_shp = f'Uganda_Districts_Comprehensive_{timestamp}.shp'
    gdf_master_renamed.to_file(master_shp)
    print(f"  ✓ {master_shp}")
    
    # Save as GeoPackage with original long names
    master_gpkg = f'Uganda_Districts_Comprehensive_{timestamp}.gpkg'
    gdf_master.to_file(master_gpkg, driver='GPKG')
    print(f"  ✓ {master_gpkg} (with full field names)")
    
    # Ensure export dataframes have correct types
    for df in [alltime_export, pre2020_export, since2020_export, annual_avg_export]:
        df['district_id'] = pd.to_numeric(df['district_id'], errors='coerce').astype('Int64')
    
    # Create and rename other shapefiles
    # All-time impacts
    alltime_shp = f'Uganda_Districts_AllTime_{timestamp}.shp'
    gdf_alltime = gdf_minimal.merge(alltime_export, on='district_id', how='left')
    gdf_alltime = gdf_alltime.loc[:, ~gdf_alltime.columns.duplicated()]
    gdf_alltime = gdf_alltime.fillna(0).infer_objects(copy=False)
    gdf_alltime_renamed = rename_for_shapefile(gdf_alltime, long_to_short)
    gdf_alltime_renamed.to_file(alltime_shp)
    print(f"  ✓ {alltime_shp}")
    
    # Pre-2020
    pre2020_shp = f'Uganda_Districts_Pre2020_{timestamp}.shp'
    gdf_pre2020 = gdf_minimal.merge(pre2020_export, on='district_id', how='left')
    gdf_pre2020 = gdf_pre2020.loc[:, ~gdf_pre2020.columns.duplicated()]
    gdf_pre2020 = gdf_pre2020.fillna(0).infer_objects(copy=False)
    gdf_pre2020_renamed = rename_for_shapefile(gdf_pre2020, long_to_short)
    gdf_pre2020_renamed.to_file(pre2020_shp)
    print(f"  ✓ {pre2020_shp}")
    
    # Since 2020
    since2020_shp = f'Uganda_Districts_Since2020_{timestamp}.shp'
    gdf_since2020 = gdf_minimal.merge(since2020_export, on='district_id', how='left')
    gdf_since2020 = gdf_since2020.loc[:, ~gdf_since2020.columns.duplicated()]
    gdf_since2020 = gdf_since2020.fillna(0).infer_objects(copy=False)
    gdf_since2020_renamed = rename_for_shapefile(gdf_since2020, long_to_short)
    gdf_since2020_renamed.to_file(since2020_shp)
    print(f"  ✓ {since2020_shp}")
    
    # Annual averages
    annual_avg_shp = f'Uganda_Districts_AnnualAvg_{timestamp}.shp'
    gdf_annual_avg = gdf_minimal.merge(annual_avg_export, on='district_id', how='left')
    gdf_annual_avg = gdf_annual_avg.loc[:, ~gdf_annual_avg.columns.duplicated()]
    gdf_annual_avg = gdf_annual_avg.fillna(0).infer_objects(copy=False)
    gdf_annual_avg_renamed = rename_for_shapefile(gdf_annual_avg, long_to_short)
    gdf_annual_avg_renamed.to_file(annual_avg_shp)
    print(f"  ✓ {annual_avg_shp}")
    
    # Create data dictionary for shapefiles
    print(f"\n  Creating shapefile data dictionary...")
    
    shapefile_dict_data = {
        'Shapefile_Field': [],
        'Full_Name': [],
        'Description': [],
        'Data_Type': [],
        'Notes': []
    }
    
    # Add fields from comprehensive shapefile
    for short_name, (long_name, description) in field_mapping.items():
        if short_name in gdf_master_renamed.columns:
            shapefile_dict_data['Shapefile_Field'].append(short_name)
            shapefile_dict_data['Full_Name'].append(long_name)
            shapefile_dict_data['Description'].append(description)
            
            # Determine data type
            if short_name in ['dist_id', 'pop2023'] or 'ev_' in short_name or any(x in short_name for x in ['tot_', 'pre_', 'sin_']):
                dtype = 'Integer'
            elif 'avg_' in short_name or short_name == 'area_km2':
                dtype = 'Float'
            else:
                dtype = 'Text'
            
            shapefile_dict_data['Data_Type'].append(dtype)
            
            # Add notes based on field type
            if 'avg_' in short_name:
                shapefile_dict_data['Notes'].append('Annual average value')
            elif 'pre_' in short_name:
                shapefile_dict_data['Notes'].append('Before 2020')
            elif 'sin_' in short_name:
                shapefile_dict_data['Notes'].append('Since 2020 (inclusive)')
            elif 'tot_' in short_name:
                shapefile_dict_data['Notes'].append('Cumulative all-time total')
            elif 'ev_' in short_name:
                shapefile_dict_data['Notes'].append('Count of unique events')
            else:
                shapefile_dict_data['Notes'].append('')
    
    shapefile_dict_df = pd.DataFrame(shapefile_dict_data)
    
    # Save shapefile data dictionary
    shapefile_dict_file = f'Shapefile_Data_Dictionary_{timestamp}.csv'
    shapefile_dict_df.to_csv(shapefile_dict_file, index=False)
    print(f"  ✓ {shapefile_dict_file}")
    
    # Also create a text version
    shapefile_dict_txt = f'Shapefile_Data_Dictionary_{timestamp}.txt'
    with open(shapefile_dict_txt, 'w') as f:
        f.write("="*80 + "\n")
        f.write("UGANDA DISASTER SHAPEFILES - DATA DICTIONARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*80 + "\n\n")
        
        f.write("FIELD NAME GUIDE\n")
        f.write("-"*80 + "\n")
        f.write("Prefixes:\n")
        f.write("  ev_     = Event counts by type\n")
        f.write("  tot_    = Total cumulative impacts (all time)\n")
        f.write("  pre_    = Impacts before 2020\n")
        f.write("  sin_    = Impacts since 2020\n")
        f.write("  avg_    = Annual averages\n")
        f.write("\nSuffixes:\n")
        f.write("  _displ  = Displaced persons\n")
        f.write("  _deaths = Deaths\n")
        f.write("  _injur  = Injuries\n")
        f.write("  _affect = Affected persons\n")
        f.write("  _h_dest = Homes destroyed\n")
        f.write("  _h_dam  = Homes damaged\n")
        f.write("  _facil  = Facilities affected\n")
        f.write("  _hh     = Households\n")
        f.write("  _events = Number of events\n")
        f.write("\n" + "="*80 + "\n\n")
        
        f.write("COMPLETE FIELD LIST\n")
        f.write("-"*80 + "\n\n")
        
        for idx, row in shapefile_dict_df.iterrows():
            f.write(f"{row['Shapefile_Field']:12s} ({row['Data_Type']:7s}) - {row['Description']}\n")
            if row['Notes']:
                f.write(f"{'':15s}Note: {row['Notes']}\n")
            f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("\nFILE DESCRIPTIONS\n")
        f.write("-"*80 + "\n")
        f.write(f"{master_shp}\n")
        f.write("  Comprehensive dataset with all metrics and time periods\n\n")
        f.write(f"{alltime_shp}\n")
        f.write("  All-time cumulative impacts only\n\n")
        f.write(f"{pre2020_shp}\n")
        f.write("  Impacts before 2020 only\n\n")
        f.write(f"{since2020_shp}\n")
        f.write("  Impacts since 2020 only\n\n")
        f.write(f"{annual_avg_shp}\n")
        f.write("  Annual average metrics for comparison\n\n")
        f.write(f"{master_gpkg}\n")
        f.write("  GeoPackage with full field names (no 10-character limit)\n")
        f.write("="*80 + "\n")
    
    print(f"  ✓ {shapefile_dict_txt}")
    
    # Print sample of field mapping
    print(f"\n  📋 Sample field name mappings:")
    print(f"     Shapefile    → Full Name")
    print(f"     {'-'*40}")
    for i, (short, (long, desc)) in enumerate(list(field_mapping.items())[:10]):
        print(f"     {short:12s} → {long}")
    print(f"     ... ({len(field_mapping)} total fields)")
    
    shapefiles_created = True
    print(f"\n  ✅ All shapefiles created with meaningful field names!")
    print(f"  📖 Data dictionary created for field reference")
    
except FileNotFoundError:
    print(f"  ✗ Shapefile not found at: {shapefile_path}")
    print(f"    Skipping shapefile creation...")
    shapefiles_created = False
except Exception as e:
    print(f"  ✗ Error creating shapefiles: {e}")
    import traceback
    traceback.print_exc()
    shapefiles_created = False

# %% STEP 15: Create comprehensive report
# ============================================================================

print("\n15. Creating comprehensive report...")

report = []
report.append("="*70)
report.append("UGANDA DISASTER DATABASE - COMPREHENSIVE IMPACTS REPORT")
report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append("="*70)
report.append("")
report.append(f"DATA COVERAGE: {min_year_data:.0f} - {max_year_data:.0f} ({years_in_data} years)")
report.append(f"  Pre-2020 period: {data_pre2020['event_year'].min():.0f} - 2019 ({years_pre2020} years)")
report.append(f"  Since 2020 period: 2020 - {data_since2020['event_year'].max():.0f} ({years_since2020} years)")
report.append("")
report.append("="*70)
report.append("OVERALL STATISTICS - ALL TIME")
report.append("="*70)
report.append(f"Total events: {master_dataset['total_events'].sum():.0f}")
report.append(f"Districts with events: {(master_dataset['total_events'] > 0).sum()}")
report.append("")
report.append("IMPACTS:")
report.append(f"  Total displaced: {master_dataset['total_displaced'].sum():,.0f}")
report.append(f"  Total deaths: {master_dataset['total_deaths'].sum():,.0f}")
report.append(f"  Total injuries: {master_dataset['total_injuries'].sum():,.0f}")
report.append(f"  Total affected: {master_dataset['total_affected'].sum():,.0f}")
report.append(f"  Total homes destroyed: {master_dataset['total_homes_destroyed'].sum():,.0f}")
report.append(f"  Total homes damaged: {master_dataset['total_homes_damaged'].sum():,.0f}")
report.append(f"  Total facilities affected: {master_dataset['total_facilities_affected'].sum():,.0f}")
report.append("")
report.append("ANNUAL AVERAGES (All Time):")
report.append(f"  Displaced per year: {master_dataset['avg_displaced_per_year'].sum():,.1f}")
report.append(f"  Deaths per year: {master_dataset['avg_deaths_per_year'].sum():,.1f}")
report.append(f"  Affected per year: {master_dataset['avg_affected_per_year'].sum():,.1f}")
report.append(f"  Events per year: {master_dataset['avg_events_per_year'].sum():,.1f}")
report.append("")
report.append("="*70)
report.append("PRE-2020 PERIOD")
report.append("="*70)
report.append(f"Total events: {master_dataset['pre2020_events'].sum():.0f}")
report.append(f"Total displaced: {master_dataset['pre2020_displaced'].sum():,.0f}")
report.append(f"Total deaths: {master_dataset['pre2020_deaths'].sum():,.0f}")
report.append(f"Total affected: {master_dataset['pre2020_affected'].sum():,.0f}")
report.append("")
report.append("Annual averages (pre-2020):")
report.append(f"  Displaced per year: {master_dataset['avg_displaced_per_year_pre2020'].sum():,.1f}")
report.append(f"  Deaths per year: {master_dataset['avg_deaths_per_year_pre2020'].sum():,.1f}")
report.append(f"  Events per year: {master_dataset['avg_events_per_year_pre2020'].sum():,.1f}")
report.append("")
report.append("="*70)
report.append("SINCE 2020 PERIOD")
report.append("="*70)
report.append(f"Total events: {master_dataset['since2020_events'].sum():.0f}")
report.append(f"Total displaced: {master_dataset['since2020_displaced'].sum():,.0f}")
report.append(f"Total deaths: {master_dataset['since2020_deaths'].sum():,.0f}")
report.append(f"Total affected: {master_dataset['since2020_affected'].sum():,.0f}")
report.append("")
report.append("Annual averages (since 2020):")
report.append(f"  Displaced per year: {master_dataset['avg_displaced_per_year_since2020'].sum():,.1f}")
report.append(f"  Deaths per year: {master_dataset['avg_deaths_per_year_since2020'].sum():,.1f}")
report.append(f"  Events per year: {master_dataset['avg_events_per_year_since2020'].sum():,.1f}")
report.append("")
report.append("="*70)
report.append("COMPARISON: PRE-2020 vs SINCE 2020")
report.append("="*70)

# Calculate percentage changes
pre_displaced_avg = master_dataset['avg_displaced_per_year_pre2020'].sum()
since_displaced_avg = master_dataset['avg_displaced_per_year_since2020'].sum()
displaced_change = ((since_displaced_avg - pre_displaced_avg) / pre_displaced_avg * 100) if pre_displaced_avg > 0 else 0

pre_deaths_avg = master_dataset['avg_deaths_per_year_pre2020'].sum()
since_deaths_avg = master_dataset['avg_deaths_per_year_since2020'].sum()
deaths_change = ((since_deaths_avg - pre_deaths_avg) / pre_deaths_avg * 100) if pre_deaths_avg > 0 else 0

pre_events_avg = master_dataset['avg_events_per_year_pre2020'].sum()
since_events_avg = master_dataset['avg_events_per_year_since2020'].sum()
events_change = ((since_events_avg - pre_events_avg) / pre_events_avg * 100) if pre_events_avg > 0 else 0

report.append(f"Annual displaced: {pre_displaced_avg:,.1f} → {since_displaced_avg:,.1f} ({displaced_change:+.1f}%)")
report.append(f"Annual deaths: {pre_deaths_avg:,.1f} → {since_deaths_avg:,.1f} ({deaths_change:+.1f}%)")
report.append(f"Annual events: {pre_events_avg:,.1f} → {since_events_avg:,.1f} ({events_change:+.1f}%)")
report.append("")
report.append("="*70)
report.append("TOP 10 MOST AFFECTED DISTRICTS (All Time - by displaced)")
report.append("="*70)

top_10_displaced = master_dataset.nlargest(10, 'total_displaced')
for idx, row in top_10_displaced.iterrows():
    report.append(f"{row['dist_name']:20s} ({row['reg_name']:8s}): {row['total_displaced']:7,.0f} displaced, {row['total_deaths']:5,.0f} deaths")

report.append("")
report.append("="*70)
report.append("IMPACTS BY REGION")
report.append("="*70)

regional_impacts = master_dataset.groupby('reg_name').agg({
    'total_events': 'sum',
    'total_displaced': 'sum',
    'total_deaths': 'sum',
    'total_affected': 'sum'
}).sort_values('total_displaced', ascending=False)

for region, row in regional_impacts.iterrows():
    report.append(f"{region:12s}: {row['total_events']:4.0f} events, {row['total_displaced']:7,.0f} displaced, {row['total_deaths']:5,.0f} deaths")

report.append("")
report.append("="*70)

report_text = "\n".join(report)
print("\n" + report_text)

# Save report
report_file = f'Comprehensive_Impacts_Report_{timestamp}.txt'
with open(report_file, 'w') as f:
    f.write(report_text)

print(f"\n✓ Saved report to: {report_file}")

# %% STEP 16: Create annual summary table
# ============================================================================

print("\n16. Creating annual summary table...")

annual_summary = data_with_district.groupby('event_year').agg({
    'event_id': 'nunique',
    'idps': 'sum',
    'disp_est': 'sum',
    'deaths': 'sum',
    'injuries': 'sum',
    'aff_tot': 'sum',
    'home_dest': 'sum',
    'home_dam': 'sum',
    'facil_aff': 'sum'
}).reset_index()

annual_summary.columns = [
    'year', 'events', 'idps', 'displaced', 'deaths', 
    'injuries', 'affected', 'homes_destroyed', 'homes_damaged', 'facilities'
]

# Save annual summary
annual_summary_csv = f'Annual_Summary_{timestamp}.csv'
annual_summary.to_csv(annual_summary_csv, index=False)
print(f"  ✓ {annual_summary_csv}")

print("\n  Annual summary (recent 10 years):")
print(annual_summary.tail(10).to_string(index=False))

# %% STEP 17: FINAL SUMMARY
# ============================================================================

print("\n" + "="*70)
print("COMPREHENSIVE DATABASE PULL COMPLETE")
print("="*70)

print(f"\n📁 CSV FILES CREATED ({timestamp}):")
print(f"  1. {master_csv}")
print(f"     → Complete dataset with all metrics")
print(f"  2. {annual_csv}")
print(f"     → Annual data by district and year (for time series)")
print(f"  3. {alltime_csv}")
print(f"     → All-time cumulative impacts")
print(f"  4. {pre2020_csv}")
print(f"     → Pre-2020 cumulative impacts")
print(f"  5. {since2020_csv}")
print(f"     → Since 2020 cumulative impacts")
print(f"  6. {annual_avg_csv}")
print(f"     → Annual averages for all periods")
print(f"  7. {annual_summary_csv}")
print(f"     → Year-by-year summary (all districts combined)")
print(f"  8. {report_file}")
print(f"     → Comprehensive text report")

if shapefiles_created:
    print(f"\n🗺️ SHAPEFILES CREATED ({timestamp}):")
    print(f"  1. {master_shp}")
    print(f"     → Comprehensive (all metrics) - BEST FOR GENERAL USE")
    print(f"  2. {alltime_shp}")
    print(f"     → All-time impacts - FOR CUMULATIVE ANALYSIS")
    print(f"  3. {pre2020_shp}")
    print(f"     → Pre-2020 impacts - FOR TEMPORAL COMPARISON")
    print(f"  4. {since2020_shp}")
    print(f"     → Since 2020 impacts - FOR RECENT TRENDS")
    print(f"  5. {annual_avg_shp}")
    print(f"     → Annual averages - FOR NORMALIZED COMPARISON")
    print(f"  6. {master_gpkg}")
    print(f"     → GeoPackage format (better than shapefile)")
else:
    print(f"\n⚠️ Shapefiles not created - base shapefile not found")

print(f"\n📊 KEY METRICS:")
print(f"  Total events: {master_dataset['total_events'].sum():.0f}")
print(f"  Total displaced: {master_dataset['total_displaced'].sum():,.0f}")
print(f"  Total deaths: {master_dataset['total_deaths'].sum():,.0f}")
print(f"  Total affected: {master_dataset['total_affected'].sum():,.0f}")
print(f"  Date range: {min_year_data:.0f} - {max_year_data:.0f} ({years_in_data} years)")

print(f"\n📈 TEMPORAL COMPARISON:")
print(f"  Pre-2020 avg displaced/year: {pre_displaced_avg:,.1f}")
print(f"  Since 2020 avg displaced/year: {since_displaced_avg:,.1f}")
print(f"  Change: {displaced_change:+.1f}%")
print(f"")
print(f"  Pre-2020 avg deaths/year: {pre_deaths_avg:,.1f}")
print(f"  Since 2020 avg deaths/year: {since_deaths_avg:,.1f}")
print(f"  Change: {deaths_change:+.1f}%")
print(f"")
print(f"  Pre-2020 avg events/year: {pre_events_avg:.1f}")
print(f"  Since 2020 avg events/year: {since_events_avg:.1f}")
print(f"  Change: {events_change:+.1f}%")

print(f"\n🎨 FOR ARCGIS VISUALIZATION:")
print(f"\n  TIME SERIES ANIMATIONS:")
print(f"    Use: {annual_csv}")
print(f"    Shows year-by-year changes for each district")
print(f"\n  TEMPORAL COMPARISON MAPS:")
print(f"    Use: {pre2020_shp} and {since2020_shp}")
print(f"    Compare side-by-side or create difference maps")
print(f"\n  3D EXTRUSION MAPS:")
print(f"    Use: {master_shp} or period-specific shapefiles")
print(f"    Extrude by: total_displaced, total_deaths, total_affected")
print(f"\n  NORMALIZED COMPARISON:")
print(f"    Use: {annual_avg_shp}")
print(f"    Shows average annual impacts (controls for time period length)")
print(f"\n  CHOROPLETH MAPS:")
print(f"    Use any shapefile")
print(f"    Classify by: impact metrics or event counts")

print(f"\n💡 RECOMMENDED ANALYSES:")
print(f"  1. Time series animation showing annual displacement")
print(f"  2. 3D extrusion comparing pre-2020 vs since 2020")
print(f"  3. Hotspot analysis using total_displaced")
print(f"  4. Multi-variable map showing multiple impact types")
print(f"  5. Regional comparisons using aggregated data")

print("\n" + "="*70)
print("✅ ALL DATASETS READY FOR MAPPING AND ANALYSIS!")
print("="*70)

# %% OPTIONAL: Create data dictionary
# ============================================================================

print("\n17. Creating data dictionary...")

data_dictionary = {
    'Field Name': [],
    'Description': [],
    'Data Type': [],
    'Time Period': []
}

field_descriptions = {
    # Event counts
    'total_events': ('Total number of unique disaster events', 'Integer', 'All time'),
    'flood_events': ('Number of flood events', 'Integer', 'All time'),
    'landslide_events': ('Number of landslide events', 'Integer', 'All time'),
    'storm_events': ('Number of storm events', 'Integer', 'All time'),
    'drought_events': ('Number of drought events', 'Integer', 'All time'),
    'earthquake_events': ('Number of earthquake events', 'Integer', 'All time'),
    'fire_events': ('Number of fire events', 'Integer', 'All time'),
    
    # All-time totals
    'total_idps': ('Total internally displaced persons', 'Integer', 'All time'),
    'total_displaced': ('Total displaced persons (estimated)', 'Integer', 'All time'),
    'total_deaths': ('Total deaths from disasters', 'Integer', 'All time'),
    'total_injuries': ('Total injuries from disasters', 'Integer', 'All time'),
    'total_affected': ('Total persons affected by disasters', 'Integer', 'All time'),
    'total_homes_destroyed': ('Total homes completely destroyed', 'Integer', 'All time'),
    'total_homes_damaged': ('Total homes damaged', 'Integer', 'All time'),
    'total_facilities_affected': ('Total facilities affected (schools, hospitals, etc.)', 'Integer', 'All time'),
    'total_households_affected': ('Total households affected', 'Integer', 'All time'),
    
    # Pre-2020
    'pre2020_displaced': ('Displaced persons before 2020', 'Integer', 'Pre-2020'),
    'pre2020_deaths': ('Deaths before 2020', 'Integer', 'Pre-2020'),
    'pre2020_injuries': ('Injuries before 2020', 'Integer', 'Pre-2020'),
    'pre2020_affected': ('Persons affected before 2020', 'Integer', 'Pre-2020'),
    'pre2020_homes_destroyed': ('Homes destroyed before 2020', 'Integer', 'Pre-2020'),
    'pre2020_events': ('Number of events before 2020', 'Integer', 'Pre-2020'),
    
    # Since 2020
    'since2020_displaced': ('Displaced persons since 2020', 'Integer', 'Since 2020'),
    'since2020_deaths': ('Deaths since 2020', 'Integer', 'Since 2020'),
    'since2020_injuries': ('Injuries since 2020', 'Integer', 'Since 2020'),
    'since2020_affected': ('Persons affected since 2020', 'Integer', 'Since 2020'),
    'since2020_homes_destroyed': ('Homes destroyed since 2020', 'Integer', 'Since 2020'),
    'since2020_events': ('Number of events since 2020', 'Integer', 'Since 2020'),
    
    # Annual averages - all time
    'avg_displaced_per_year': ('Average displaced persons per year', 'Float', 'All time average'),
    'avg_deaths_per_year': ('Average deaths per year', 'Float', 'All time average'),
    'avg_injuries_per_year': ('Average injuries per year', 'Float', 'All time average'),
    'avg_affected_per_year': ('Average affected persons per year', 'Float', 'All time average'),
    'avg_homes_destroyed_per_year': ('Average homes destroyed per year', 'Float', 'All time average'),
    'avg_events_per_year': ('Average events per year', 'Float', 'All time average'),
    
    # Annual averages - pre-2020
    'avg_displaced_per_year_pre2020': ('Average displaced persons per year', 'Float', 'Pre-2020 average'),
    'avg_deaths_per_year_pre2020': ('Average deaths per year', 'Float', 'Pre-2020 average'),
    'avg_events_per_year_pre2020': ('Average events per year', 'Float', 'Pre-2020 average'),
    
    # Annual averages - since 2020
    'avg_displaced_per_year_since2020': ('Average displaced persons per year', 'Float', 'Since 2020 average'),
    'avg_deaths_per_year_since2020': ('Average deaths per year', 'Float', 'Since 2020 average'),
    'avg_events_per_year_since2020': ('Average events per year', 'Float', 'Since 2020 average'),
    
    # District info
    'district_id': ('Unique district identifier', 'Integer', 'N/A'),
    'dist_name': ('District name', 'Text', 'N/A'),
    'reg_name': ('Region name', 'Text', 'N/A'),
    'dist_pop2023': ('District population (2023)', 'Integer', 'N/A'),
    'dist_area': ('District area in km²', 'Float', 'N/A'),
}

for field, (desc, dtype, period) in field_descriptions.items():
    data_dictionary['Field Name'].append(field)
    data_dictionary['Description'].append(desc)
    data_dictionary['Data Type'].append(dtype)
    data_dictionary['Time Period'].append(period)

dict_df = pd.DataFrame(data_dictionary)
dict_file = f'Data_Dictionary_{timestamp}.csv'
dict_df.to_csv(dict_file, index=False)

print(f"  ✓ {dict_file}")
print(f"     Contains descriptions of all {len(dict_df)} fields")

print("\n" + "="*70)
print("🎉 COMPLETE! All files ready for analysis and mapping!")
print("="*70)