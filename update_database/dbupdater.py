#!/usr/bin/env python3
"""
CLIMATE EVENT DATABASE UPDATER SCRIPT FOR CLIMATE DISASTER RELATIONAL DATABASE
========================================================================
This script provides a flexible, interactive workflow for importing disaster
event data from various sources into the Uganda Climate Disaster database.

DESIGNED FOR: Spyder 6 IDE

Key Features:
- Interactive column mapping for new data sources
- Uses existing reference tables (source, ev_type, district, region, county, village)
- Automatic duplicate detection by event_id
- Manual review of potential duplicates
- Option to update existing database or save new records only
- Comprehensive data validation and quality reporting
- Automatic source table updates

Reference Tables Used:
- source: For tracking data sources (auto-updated with new sources)
- ev_type: 6 standard event types (Flood, Landslide, Storm, Drought, Earthquake, Fire)
- district: 135 districts with hierarchical region linkage
- region: 4 regions (Central, Eastern, Northern, Western)
- county: 208 counties (subcounties)
- village: 1520 villages with geocoordinates

Author: Max Bobholz
Last Updated: January 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

REGION_MAP = {
    1: 'CENTRAL',
    2: 'EASTERN', 
    3: 'NORTHERN',
    4: 'WESTERN'
}

REQUIRED_FIELDS = ['event_date', 'ev_type_id']  # district_id is optional
IMPACT_FIELDS = ['aff_tot', 'deaths', 'injuries', 'idps', 'missing', 'home_dam', 'home_dest']

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")

def print_section(text):
    """Print a section header"""
    print(f"\n{text}")
    print("-"*70)

def get_user_input(prompt, valid_options=None, default=None):
    """
    Get validated user input - works in Spyder console
    """
    while True:
        if default:
            user_prompt = f"{prompt} [default: {default}]: "
        else:
            user_prompt = f"{prompt}: "
        
        # Use input() which works in Spyder's IPython console
        try:
            response = input(user_prompt).strip()
        except EOFError:
            print("\nEOF detected - using default or empty response")
            response = default if default else ""
        
        if not response and default:
            return default
        
        if valid_options:
            if response.upper() in [opt.upper() for opt in valid_options]:
                return response.upper()
            else:
                print(f"Invalid input. Please choose from: {', '.join(valid_options)}")
        else:
            if not response and not default:
                continue
            return response

def generate_event_id(event_date, region_id, existing_ids):
    """
    Generate event_id in format: YYYYMMDD-REGION-##
    
    Parameters:
    - event_date: datetime or string date
    - region_id: int (1-4 for Central, Eastern, Northern, Western)
    - existing_ids: set of existing event_ids
    
    Returns:
    - event_id string
    """
    if pd.isna(event_date):
        date_str = "NODATE"
    else:
        if isinstance(event_date, str):
            try:
                event_date = pd.to_datetime(event_date)
            except:
                date_str = "NODATE"
        else:
            date_str = event_date.strftime('%Y%m%d')
    
    if pd.isna(region_id) or region_id not in REGION_MAP:
        region_str = "NOTSPEC"
    else:
        region_str = REGION_MAP[region_id]
    
    # Find next available number
    base_id = f"{date_str}-{region_str}"
    counter = 1
    while f"{base_id}-{counter:02d}" in existing_ids:
        counter += 1
    
    return f"{base_id}-{counter:02d}"

# =============================================================================
# MAIN IMPORT CLASS
# =============================================================================

class DataImporter:
    """Main class for managing the import workflow"""
    
    def __init__(self, db_path):
        """Initialize the importer with database path"""
        self.db_path = db_path
        self.db = None
        self.new_data = None
        self.column_mapping = {}
        self.source_info = {}
        
        # Tables that will be modified
        self.events_new = None
        self.ev_locations_new = None
        self.impacts_new = None
        
        # Tables for uncertain events (need manual review)
        self.uncertain_events = pd.DataFrame()
        self.uncertain_locations = pd.DataFrame()
        self.uncertain_impacts = pd.DataFrame()
        
        # Reference tables
        self.district_dict = {}
        self.region_dict = {}
        self.ev_type_dict = {}
        self.source_dict = {}
        
        print_header("CLIMATE EVENT DATABASE UPDATER TOOL")
        print("Running in Spyder 6 IDE")
        
    def load_database(self):
        """Load the existing relational database and its reference tables"""
        print_section("1. Loading Existing Database")
        
        if not os.path.exists(self.db_path):
            print(f"ERROR: Database file not found: {self.db_path}")
            sys.exit(1)
        
        self.db = pd.read_excel(self.db_path, sheet_name=None)
        
        print(f"✓ Loaded database: {self.db_path}")
        print(f"\nData Tables:")
        print(f"  events: {len(self.db['events'])} records")
        print(f"  ev_locations: {len(self.db['ev_locations'])} records")
        print(f"  impacts: {len(self.db['impacts'])} records")
        
        print(f"\nReference Tables:")
        print(f"  source: {len(self.db['source'])} sources")
        print(f"  ev_type: {len(self.db['ev_type'])} event types")
        print(f"  region: {len(self.db['region'])} regions")
        print(f"  district: {len(self.db['district'])} districts")
        print(f"  county: {len(self.db['county'])} counties")
        print(f"  village: {len(self.db['village'])} villages")
        
        # Build lookup dictionaries
        self._build_lookups()
        
        # Show available event types
        print(f"\nAvailable Event Types (from ev_type table):")
        for _, row in self.db['ev_type'].iterrows():
            print(f"  {row['ev_type_id']}: {row['ev_type']}")
        
        # Show regions
        print(f"\nRegions (from region table):")
        for _, row in self.db['region'].iterrows():
            print(f"  {row['region_id']}: {row['reg_name']}")
    
    def _build_lookups(self):
        """Build lookup dictionaries from reference tables in database"""
        
        # District lookup (by name)
        # The district_id encodes the region: 1xxx=Central, 2xxx=Eastern, 3xxx=Northern, 4xxx=Western
        for _, row in self.db['district'].iterrows():
            name_clean = str(row['dist_name']).lower().strip()
            self.district_dict[name_clean] = {
                'district_id': row['district_id'],
                'region_id': row['region_id']
            }
        
        # Region lookup (from region table)
        for _, row in self.db['region'].iterrows():
            self.region_dict[row['region_id']] = row['reg_name']
        
        # Event type lookup (from ev_type table)
        for _, row in self.db['ev_type'].iterrows():
            ev_type_clean = str(row['ev_type']).lower().strip()
            self.ev_type_dict[ev_type_clean] = row['ev_type_id']
        
        # Source lookup (from source table)
        for _, row in self.db['source'].iterrows():
            source_name_clean = str(row['source_name']).lower().strip()
            self.source_dict[source_name_clean] = row['source_id']
        
        print(f"  Loaded {len(self.district_dict)} districts from district table")
        print(f"  Loaded {len(self.region_dict)} regions from region table")
        print(f"  Loaded {len(self.ev_type_dict)} event types from ev_type table")
        print(f"  Loaded {len(self.source_dict)} sources from source table")
    
    def load_new_data(self, file_path):
        """Load the new data file to import"""
        print_section("2. Loading New Data")
        
        if not os.path.exists(file_path):
            print(f"ERROR: Data file not found: {file_path}")
            sys.exit(1)
        
        # Try to load the file
        try:
            # Check if it has multiple sheets
            xl_file = pd.ExcelFile(file_path)
            
            if len(xl_file.sheet_names) > 1:
                print(f"File contains {len(xl_file.sheet_names)} sheets:")
                for i, sheet in enumerate(xl_file.sheet_names):
                    print(f"  {i+1}. {sheet}")
                
                sheet_choice = get_user_input("Which sheet contains the data to import? (enter number or name)")
                
                try:
                    sheet_idx = int(sheet_choice) - 1
                    sheet_name = xl_file.sheet_names[sheet_idx]
                except:
                    sheet_name = sheet_choice
                
                self.new_data = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                self.new_data = pd.read_excel(file_path)
        except Exception as e:
            print(f"ERROR loading file: {e}")
            sys.exit(1)
        
        print(f"✓ Loaded new data: {len(self.new_data)} rows, {len(self.new_data.columns)} columns")
        print(f"\nColumn names in new data:")
        for i, col in enumerate(self.new_data.columns):
            print(f"  {i+1:3d}. {col}")
    
    def map_columns(self):
        """Interactively map columns from new data to database schema"""
        print_section("3. Column Mapping")
        
        print("Please map the columns from your new data to the database fields.")
        print("Type the column name or number from the list above.")
        print("Press Enter to skip optional fields.\n")
        
        # Required mappings
        print("REQUIRED FIELDS:")
        print("-" * 40)
        
        # Date
        self.column_mapping['event_date'] = self._get_column_mapping(
            "Event date (required)", required=True
        )
        
        # Event type
        self.column_mapping['ev_type'] = self._get_column_mapping(
            "Event/disaster type (required)", required=True
        )
        
        # Location - at least one location field required
        print("\nLOCATION FIELDS (at least one required):")
        print("-" * 40)
        
        self.column_mapping['district'] = self._get_column_mapping(
            "District name", required=False
        )
        
        self.column_mapping['county'] = self._get_column_mapping(
            "County/subcounty name", required=False
        )
        
        self.column_mapping['village'] = self._get_column_mapping(
            "Village/parish name", required=False
        )
        
        self.column_mapping['location_general'] = self._get_column_mapping(
            "General location description (if no district/county/village)", required=False
        )
        
        # Check if at least one location field was provided
        if not any([self.column_mapping.get('district'),
                   self.column_mapping.get('county'),
                   self.column_mapping.get('village'),
                   self.column_mapping.get('location_general')]):
            print("\n⚠ WARNING: No location fields mapped!")
            print("At least one location field is highly recommended for meaningful data.")
            proceed = get_user_input("Continue without location data? (Y/N)", valid_options=['Y', 'N'])
            if proceed == 'N':
                print("Please map at least one location field.")
                return self.map_columns()  # Restart mapping
        
        # Impact fields - at least one recommended but not strictly required
        print("\nIMPACT FIELDS (at least one recommended):")
        print("-" * 40)
        
        impact_mappings = {
            'aff_tot': 'Total people affected',
            'deaths': 'Number of deaths',
            'injuries': 'Number of injuries',
            'idps': 'Number of IDPs/displaced',
            'missing': 'Number missing',
            'home_dam': 'Homes damaged',
            'home_dest': 'Homes destroyed'
        }
        
        for field, description in impact_mappings.items():
            self.column_mapping[field] = self._get_column_mapping(
                description, required=False
            )
        
        # Check if at least one impact field was provided
        impact_fields_mapped = [self.column_mapping.get(f) for f in impact_mappings.keys()]
        if not any(impact_fields_mapped):
            print("\n⚠ WARNING: No impact fields mapped!")
            print("Impact data is highly recommended for disaster records.")
            proceed = get_user_input("Continue without impact data? (Y/N)", valid_options=['Y', 'N'])
            if proceed == 'N':
                print("Returning to impact field mapping...")
                # Don't restart entirely, just let them continue
        
        # Additional optional fields
        print("\nADDITIONAL OPTIONAL FIELDS:")
        print("-" * 40)
        
        self.column_mapping['end_date'] = self._get_column_mapping(
            "End date", required=False
        )
        
        self.column_mapping['event_name'] = self._get_column_mapping(
            "Event name/description", required=False
        )
        
        self.column_mapping['notes'] = self._get_column_mapping(
            "Notes/additional information", required=False
        )
        
        # Show summary
        print("\n" + "="*70)
        print("MAPPING SUMMARY:")
        print("="*70)
        for db_field, source_col in self.column_mapping.items():
            if source_col:
                print(f"  {db_field:20s} ← {source_col}")
    
    def _get_column_mapping(self, field_description, required=False):
        """Get column mapping from user input"""
        prompt = f"{field_description}"
        if not required:
            prompt += " (optional, press Enter to skip)"
        
        while True:
            response = input(f"  {prompt}: ").strip()
            
            if not response and not required:
                return None
            
            if not response and required:
                print("    This field is required. Please provide a column name.")
                continue
            
            # Check if it's a number (column index)
            try:
                col_idx = int(response) - 1
                if 0 <= col_idx < len(self.new_data.columns):
                    col_name = self.new_data.columns[col_idx]
                    print(f"    → Mapped to: {col_name}")
                    return col_name
                else:
                    print(f"    Invalid column number. Must be 1-{len(self.new_data.columns)}")
            except ValueError:
                # It's a column name
                if response in self.new_data.columns:
                    return response
                else:
                    print(f"    Column '{response}' not found in data.")
                    print(f"    Available columns: {', '.join(self.new_data.columns[:5])}...")
    
    def get_source_info(self):
        """Get or create source information using the source reference table"""
        print_section("4. Source Information")
        
        print("Current sources in database (from source table):")
        print(f"{'ID':<5} {'Source Name':<50} {'Type':<25}")
        print("-"*80)
        
        # Show sources from the actual source table
        for _, row in self.db['source'].iterrows():
            source_id = row['source_id']
            source_name = row['source_name']
            source_type = row.get('source_type', 'N/A')
            print(f"{source_id:<5} {source_name:<50} {source_type:<25}")
        
        source_input = get_user_input(
            "\nEnter source name (or source_id number if exists above)",
            default="Unknown"
        )
        
        # Check if it's an existing source by ID
        try:
            source_id_input = int(source_input)
            matching_source = self.db['source'][self.db['source']['source_id'] == source_id_input]
            if len(matching_source) > 0:
                row = matching_source.iloc[0]
                self.source_info['source_id'] = row['source_id']
                self.source_info['source_name'] = row['source_name']
                self.source_info['name_full'] = row.get('name_full', row['source_name'])
                self.source_info['source_type'] = row.get('source_type', '')
                print(f"✓ Using existing source: {row['source_name']} (ID: {row['source_id']})")
                return
        except ValueError:
            pass
        
        # Check if it's an existing source by name
        source_input_clean = source_input.lower().strip()
        if source_input_clean in self.source_dict:
            source_id = self.source_dict[source_input_clean]
            matching_source = self.db['source'][self.db['source']['source_id'] == source_id]
            row = matching_source.iloc[0]
            self.source_info['source_id'] = row['source_id']
            self.source_info['source_name'] = row['source_name']
            self.source_info['name_full'] = row.get('name_full', row['source_name'])
            self.source_info['source_type'] = row.get('source_type', '')
            print(f"✓ Using existing source: {row['source_name']} (ID: {row['source_id']})")
            return
        
        # New source - will be added to source table
        print(f"'{source_input}' not found in source table. Creating new source entry.")
        
        # Get next source_id from source table
        max_source_id = self.db['source']['source_id'].max()
        new_source_id = max_source_id + 1
        
        source_full_name = get_user_input(
            "Enter full source name",
            default=source_input
        )
        source_type = get_user_input(
            "Enter source type (e.g., International Organization, Government Agency, Database, News)",
            default="Database"
        )
        
        self.source_info['source_id'] = new_source_id
        self.source_info['source_name'] = source_input
        self.source_info['name_full'] = source_full_name
        self.source_info['source_type'] = source_type
        self.source_info['is_new'] = True
        
        print(f"✓ New source will be added to source table: {source_input} (ID: {new_source_id})")
    
    def process_data(self):
        """Process the new data and create database records"""
        print_section("5. Processing Data")
        
        # Initialize new dataframes
        events_list = []
        ev_locations_list = []
        impacts_list = []
        
        existing_event_ids = set(self.db['events']['event_id'].tolist())
        next_ev_loc_id = self.db['ev_locations']['ev_loc_id'].max() + 1 if len(self.db['ev_locations']) > 0 else 1
        next_impact_id_num = len(self.db['impacts']) + 1
        
        print(f"Processing {len(self.new_data)} records...")
        
        # Track unmatched items for diagnostic reporting
        unmatched_event_types = {}
        unmatched_districts = {}
        
        for idx, row in self.new_data.iterrows():
            # Extract date
            event_date = self._extract_date(row, self.column_mapping['event_date'])
            
            # Extract and match district (optional)
            district_info = self._match_district(row, self.column_mapping.get('district'))
            
            if district_info:
                district_id = district_info['district_id']
                region_id = district_info['region_id']
            else:
                # No district match - use None for district_id
                # Try to infer region from other location fields or default to unspecified
                district_id = None
                region_id = None  # Will result in "NOTSPEC" in event_id
                
                # Optionally, we could try to match county/village to get district
                # but for now, we'll allow events without district
            
            # Extract and match event type
            ev_type_id = self._match_event_type(row, self.column_mapping['ev_type'])
            
            if not ev_type_id:
                # Track unmatched event type
                raw_ev_type = str(self._get_value(row, self.column_mapping['ev_type']))
                unmatched_event_types[raw_ev_type] = unmatched_event_types.get(raw_ev_type, 0) + 1
                continue
            
            # Generate event_id
            event_id = generate_event_id(event_date, region_id, existing_event_ids)
            existing_event_ids.add(event_id)
            
            # Create event record
            event_record = {
                'event_id': event_id,
                'event_date': event_date,
                'report_date': datetime.now(),
                'ev_type_id': ev_type_id,
                'source_id': self.source_info['source_id'],
                'obs_id': event_id,  # Using event_id as obs_id
                'notes': self._get_value(row, self.column_mapping.get('notes')),
                'notes2': self._get_value(row, self.column_mapping.get('event_name'))
            }
            events_list.append(event_record)
            
            # Create location record
            ev_loc_record = {
                'ev_loc_id': next_ev_loc_id,
                'event_id': event_id,
                'village_id': None,  # Will implement matching later if needed
                'county_id': None,
                'district_id': district_id,
                'primary_loc': True
            }
            ev_locations_list.append(ev_loc_record)
            
            # Create impact record
            impact_record = {
                'impact_id': f"IMP_{event_id}_{next_impact_id_num}",
                'event_id': event_id,
                'ev_loc_id': next_ev_loc_id,
                'assess_date': event_date,
                'aff_tot': self._get_numeric_value(row, self.column_mapping.get('aff_tot')),
                'aff_m': None,
                'aff_f': None,
                'aff_u18': None,
                'aff_18_64': None,
                'aff_65o': None,
                'injuries': self._get_numeric_value(row, self.column_mapping.get('injuries')),
                'deaths': self._get_numeric_value(row, self.column_mapping.get('deaths')),
                'missing': self._get_numeric_value(row, self.column_mapping.get('missing')),
                'idps': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'disp_raw': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'disp_units': 'people' if self.column_mapping.get('idps') else None,
                'disp_est': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'hh_aff': None,
                'home_dam': self._get_numeric_value(row, self.column_mapping.get('home_dam')),
                'home_dest': self._get_numeric_value(row, self.column_mapping.get('home_dest')),
                'facil_aff': None
            }
            impacts_list.append(impact_record)
            
            next_ev_loc_id += 1
            next_impact_id_num += 1
            
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(self.new_data)} records...")
        
        # Create DataFrames
        self.events_new = pd.DataFrame(events_list)
        self.ev_locations_new = pd.DataFrame(ev_locations_list)
        self.impacts_new = pd.DataFrame(impacts_list)
        
        print(f"\n✓ Processing complete:")
        print(f"  {len(self.events_new)} events created")
        print(f"  {len(self.ev_locations_new)} locations created")
        print(f"  {len(self.impacts_new)} impact records created")
        
        # Report unmatched items
        if unmatched_event_types:
            print(f"\n⚠ UNMATCHED EVENT TYPES ({sum(unmatched_event_types.values())} records skipped):")
            for ev_type, count in sorted(unmatched_event_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{ev_type}': {count} occurrences")
            print(f"\nAvailable event types in your database:")
            for ev_type, ev_id in self.ev_type_dict.items():
                print(f"  - {ev_type} (ID: {ev_id})")
        
        if unmatched_districts:
            print(f"\n⚠ UNMATCHED DISTRICTS ({sum(unmatched_districts.values())} records affected):")
            # Show only top 10 unmatched districts
            sorted_districts = sorted(unmatched_districts.items(), key=lambda x: x[1], reverse=True)
            for dist, count in sorted_districts[:10]:
                print(f"  - '{dist}': {count} occurrences")
            if len(sorted_districts) > 10:
                print(f"  ... and {len(sorted_districts) - 10} more")
    
    def _extract_date(self, row, date_col):
        """Extract and parse date from row"""
        if not date_col or pd.isna(row[date_col]):
            return None
        
        try:
            return pd.to_datetime(row[date_col])
        except:
            return None
    
    def _match_district(self, row, district_col):
        """Match district name to database using district reference table"""
        if not district_col or pd.isna(row[district_col]):
            return None
        
        district_name = str(row[district_col]).lower().strip()
        
        # Direct match
        if district_name in self.district_dict:
            return self.district_dict[district_name]
        
        # Try removing common suffixes/prefixes for better matching
        # e.g., "Kasese District" -> "Kasese", "Kasese Province" -> "Kasese"
        district_name_clean = district_name.replace(' district', '').replace(' province', '').strip()
        if district_name_clean in self.district_dict:
            return self.district_dict[district_name_clean]
        
        # Fuzzy match - check if input is substring of database district
        for db_district, info in self.district_dict.items():
            if district_name in db_district:
                return info
        
        # Fuzzy match - check if database district is substring of input
        for db_district, info in self.district_dict.items():
            if db_district in district_name:
                return info
        
        return None
    
    def _match_event_type(self, row, ev_type_col):
        """Match event type to database using ev_type reference table with comprehensive matching"""
        if not ev_type_col or pd.isna(row[ev_type_col]):
            return None
        
        ev_type_name = str(row[ev_type_col]).lower().strip()
        
        # Direct match against ev_type table
        if ev_type_name in self.ev_type_dict:
            return self.ev_type_dict[ev_type_name]
        
        # Fuzzy match - check if input contains ev_type name
        for db_ev_type, ev_type_id in self.ev_type_dict.items():
            if db_ev_type in ev_type_name:
                return ev_type_id
        
        # Comprehensive hazard type mappings to standardized ev_type
        # This helps map various disaster databases to your 6 standard types
        # Each entry is: database_type -> [variations, synonyms, subtypes]
        hazard_mappings = {
            'flood': [
                'flood', 'floods', 'flooding',
                'flash flood', 'flash floods',
                'riverine flood', 'riverine floods', 'riverine',
                'coastal flood', 'coastal floods',
                'urban flood', 'urban floods',
                'general flood', 'flood (general)',
                'pluvial', 'fluvial',
                'inundation'
            ],
            'landslide': [
                'landslide', 'landslides',
                'mass movement', 'mass movements',
                'wet mass movement', 'wet mass movements',
                'dry mass movement', 'dry mass movements',
                'mudslide', 'mudslides', 'mud slide',
                'rockfall', 'rock fall', 'rockslide',
                'avalanche', 'avalanches',
                'debris flow', 'debris flows',
                'landslip', 'land slip',
                'slope failure', 'hillside collapse',
                'landslide (wet)', 'landslide/wet mass movement'
            ],
            'storm': [
                'storm', 'storms',
                'severe storm', 'severe storms',
                'storm (general)',
                'tropical storm', 'tropical storms',
                'convective storm', 'convective storms',
                'cyclone', 'cyclones', 'tropical cyclone',
                'hurricane', 'hurricanes',
                'typhoon', 'typhoons',
                'wind', 'windstorm', 'windstorms', 'severe wind',
                'tornado', 'tornadoes',
                'hailstorm', 'hailstorms', 'hail',
                'thunderstorm', 'thunderstorms',
                'lightning', 'lightning/thunderstorms',
                'severe weather', 'extreme weather',
                'tempest', 'squall', 'gale'
            ],
            'drought': [
                'drought', 'droughts',
                'dry spell', 'dry spells',
                'water scarcity', 'water shortage',
                'arid', 'aridity',
                'desertification',
                'crop failure'
            ],
            'earthquake': [
                'earthquake', 'earthquakes', 'quake',
                'seismic', 'seismic activity',
                'tremor', 'tremors',
                'ground movement', 'ground shaking',
                'tectonic'
            ],
            'fire': [
                'fire', 'fires',
                'wildfire', 'wildfires', 'wild fire',
                'forest fire', 'forest fires',
                'bush fire', 'bush fires', 'bushfire',
                'grass fire', 'grassfire',
                'vegetation fire',
                'scrub fire'
            ]
        }
        
        # Try to match against comprehensive mappings
        for standard_type, variations in hazard_mappings.items():
            for variation in variations:
                if variation == ev_type_name or variation in ev_type_name:
                    return self.ev_type_dict.get(standard_type)
        
        # If still no match, try partial word matching (last resort)
        # This helps catch variations we might have missed
        ev_type_words = set(ev_type_name.split())
        for standard_type in hazard_mappings.keys():
            if standard_type in ev_type_words:
                return self.ev_type_dict.get(standard_type)
        
        return None
    
    def _get_value(self, row, col_name):
        """Safely get value from row"""
        if not col_name or col_name not in row.index:
            return None
        return row[col_name] if not pd.isna(row[col_name]) else None
    
    def _get_numeric_value(self, row, col_name):
        """Safely get numeric value from row"""
        value = self._get_value(row, col_name)
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    def check_duplicates(self):
        """
        Comprehensive duplicate checking with manual review.
        Allows users to: Add as new, Skip, or mark as Uncertain for later review.
        """
        print_section("6. Checking for Duplicates")
        
        if len(self.events_new) == 0:
            print("No new events to check for duplicates.")
            return
        
        existing_events = self.db['events']
        
        # Lists to track user decisions
        events_to_keep = []  # Indices of events to import as new
        events_to_skip = []  # Indices of events to skip entirely
        events_uncertain = []  # Indices of events uncertain/need review
        
        print(f"\nChecking {len(self.events_new)} new events against {len(existing_events)} existing events...")
        print("Looking for matches by: date + event type + location\n")
        
        potential_duplicates_found = 0
        
        for idx, new_event in self.events_new.iterrows():
            # Get new event details
            new_date = new_event['event_date']
            new_type = new_event['ev_type_id']
            new_event_id = new_event['event_id']
            
            # Get location for new event
            new_location = self.ev_locations_new[
                self.ev_locations_new['event_id'] == new_event_id
            ].iloc[0] if len(self.ev_locations_new[self.ev_locations_new['event_id'] == new_event_id]) > 0 else None
            new_district = new_location['district_id'] if new_location is not None else None
            
            # Find potential matches in existing database
            # Step 1: Match by date
            date_matches = existing_events[
                pd.to_datetime(existing_events['event_date']).dt.date == pd.to_datetime(new_date).date()
            ] if pd.notna(new_date) else pd.DataFrame()
            
            # Step 2: Narrow by event type
            if len(date_matches) > 0 and pd.notna(new_type):
                type_matches = date_matches[date_matches['ev_type_id'] == new_type]
            else:
                type_matches = date_matches
            
            # Step 3: Check location overlap
            location_matches = []
            if len(type_matches) > 0 and pd.notna(new_district):
                for _, existing_event in type_matches.iterrows():
                    existing_locations = self.db['ev_locations'][
                        self.db['ev_locations']['event_id'] == existing_event['event_id']
                    ]
                    # Check if any location matches
                    if any(existing_locations['district_id'] == new_district):
                        location_matches.append(existing_event)
            
            # If we found potential matches, prompt user
            if len(location_matches) > 0 or (len(type_matches) > 0 and pd.isna(new_district)):
                potential_duplicates_found += 1
                
                print("="*70)
                print(f"POTENTIAL DUPLICATE #{potential_duplicates_found}")
                print("="*70)
                
                # Show NEW event details
                self._display_event_details("NEW EVENT", new_event, self.ev_locations_new, 
                                          self.impacts_new, is_new=True)
                
                # Show EXISTING event(s) details
                existing_to_show = location_matches if location_matches else type_matches.to_dict('records')
                
                print(f"\n📋 EXISTING EVENT(S) ON SAME DATE:")
                if len(existing_to_show) == 0:
                    print("  (Showing date matches only - no type/location overlap)")
                    existing_to_show = date_matches.to_dict('records')[:3]  # Show max 3
                
                for i, existing_event in enumerate(existing_to_show[:5], 1):  # Show max 5
                    if isinstance(existing_event, pd.Series):
                        existing_event = existing_event.to_dict()
                    print(f"\n  [{i}] Existing Event:")
                    self._display_event_details(f"    ", existing_event, self.db['ev_locations'],
                                               self.db['impacts'], is_new=False, indent="    ")
                
                if len(existing_to_show) > 5:
                    print(f"\n  ... and {len(existing_to_show) - 5} more existing events on this date")
                
                # Get user decision
                print("\n" + "-"*70)
                print("OPTIONS:")
                print("  [A] Add as NEW event (they are different events)")
                print("  [S] Skip this event (it's already in database)")
                print("  [U] Uncertain - save for later review")
                print("-"*70)
                
                while True:
                    decision = get_user_input(
                        "Your decision? (A/S/U)",
                        valid_options=['A', 'S', 'U']
                    )
                    
                    if decision == 'A':
                        events_to_keep.append(idx)
                        print("  → Will import as NEW event\n")
                        break
                    elif decision == 'S':
                        events_to_skip.append(idx)
                        print("  → Will skip this event\n")
                        break
                    elif decision == 'U':
                        events_uncertain.append(idx)
                        print("  → Marked as UNCERTAIN for later review\n")
                        break
            else:
                # No matches found - automatically keep
                events_to_keep.append(idx)
        
        # Summary
        print("\n" + "="*70)
        print("DUPLICATE CHECK SUMMARY")
        print("="*70)
        print(f"Total new events checked: {len(self.events_new)}")
        print(f"Potential duplicates found: {potential_duplicates_found}")
        print(f"  → Add as NEW: {len(events_to_keep)}")
        print(f"  → Skip: {len(events_to_skip)}")
        print(f"  → Uncertain: {len(events_uncertain)}")
        
        # Store uncertain events for later
        if events_uncertain:
            self.uncertain_events = self.events_new.iloc[events_uncertain].copy()
            self.uncertain_locations = self.ev_locations_new[
                self.ev_locations_new['event_id'].isin(self.uncertain_events['event_id'])
            ].copy()
            self.uncertain_impacts = self.impacts_new[
                self.impacts_new['event_id'].isin(self.uncertain_events['event_id'])
            ].copy()
        else:
            self.uncertain_events = pd.DataFrame()
            self.uncertain_locations = pd.DataFrame()
            self.uncertain_impacts = pd.DataFrame()
        
        # Filter to only keep approved events
        if events_to_skip or events_uncertain:
            event_ids_to_remove = []
            
            if events_to_skip:
                event_ids_to_remove.extend(
                    self.events_new.iloc[events_to_skip]['event_id'].tolist()
                )
            if events_uncertain:
                event_ids_to_remove.extend(
                    self.events_new.iloc[events_uncertain]['event_id'].tolist()
                )
            
            # Remove from main dataframes
            self.events_new = self.events_new[
                ~self.events_new['event_id'].isin(event_ids_to_remove)
            ].reset_index(drop=True)
            
            self.ev_locations_new = self.ev_locations_new[
                ~self.ev_locations_new['event_id'].isin(event_ids_to_remove)
            ].reset_index(drop=True)
            
            self.impacts_new = self.impacts_new[
                ~self.impacts_new['event_id'].isin(event_ids_to_remove)
            ].reset_index(drop=True)
            
            print(f"\nRemoved {len(events_to_skip)} skipped and {len(events_uncertain)} uncertain events from import")
            print(f"Remaining events to import: {len(self.events_new)}")
    
    def _display_event_details(self, title, event, locations_df, impacts_df, is_new=True, indent=""):
        """Helper function to display event details consistently"""
        print(f"{indent}{title}")
        
        if isinstance(event, dict):
            event_id = event['event_id']
            event_date = event.get('event_date')
            ev_type_id = event.get('ev_type_id')
            source_id = event.get('source_id')
            notes = event.get('notes', '')
            notes2 = event.get('notes2', '')
        else:
            event_id = event['event_id']
            event_date = event['event_date']
            ev_type_id = event['ev_type_id']
            source_id = event['source_id']
            notes = event.get('notes', '')
            notes2 = event.get('notes2', '')
        
        # Get event type name
        ev_type_name = 'Unknown'
        if pd.notna(ev_type_id):
            ev_type_row = self.db['ev_type'][self.db['ev_type']['ev_type_id'] == ev_type_id]
            if len(ev_type_row) > 0:
                ev_type_name = ev_type_row.iloc[0]['ev_type']
        
        # Get source name
        source_name = 'Unknown'
        if pd.notna(source_id):
            if is_new and source_id == self.source_info.get('source_id'):
                source_name = self.source_info.get('source_name', 'Unknown')
            else:
                source_row = self.db['source'][self.db['source']['source_id'] == source_id]
                if len(source_row) > 0:
                    source_name = source_row.iloc[0]['source_name']
        
        print(f"{indent}  Event ID: {event_id}")
        print(f"{indent}  Date: {pd.to_datetime(event_date).strftime('%Y-%m-%d') if pd.notna(event_date) else 'Unknown'}")
        print(f"{indent}  Type: {ev_type_name}")
        print(f"{indent}  Source: {source_name}")
        
        # Get location details
        event_locations = locations_df[locations_df['event_id'] == event_id]
        if len(event_locations) > 0:
            districts = []
            for _, loc in event_locations.iterrows():
                if pd.notna(loc['district_id']):
                    dist_row = self.db['district'][self.db['district']['district_id'] == loc['district_id']]
                    if len(dist_row) > 0:
                        districts.append(dist_row.iloc[0]['dist_name'])
            
            if districts:
                print(f"{indent}  Districts: {', '.join(districts)}")
            else:
                print(f"{indent}  Districts: None specified")
        
        # Get impact details
        event_impacts = impacts_df[impacts_df['event_id'] == event_id]
        if len(event_impacts) > 0:
            total_deaths = event_impacts['deaths'].sum()
            total_injuries = event_impacts['injuries'].sum()
            total_affected = event_impacts['aff_tot'].sum()
            total_idps = event_impacts['idps'].sum()
            
            impact_str = []
            if pd.notna(total_deaths) and total_deaths > 0:
                impact_str.append(f"Deaths: {int(total_deaths)}")
            if pd.notna(total_injuries) and total_injuries > 0:
                impact_str.append(f"Injuries: {int(total_injuries)}")
            if pd.notna(total_affected) and total_affected > 0:
                impact_str.append(f"Affected: {int(total_affected)}")
            if pd.notna(total_idps) and total_idps > 0:
                impact_str.append(f"IDPs: {int(total_idps)}")
            
            if impact_str:
                print(f"{indent}  Impacts: {', '.join(impact_str)}")
        
        # Show notes if available
        if notes and str(notes) != 'nan' and str(notes).strip():
            print(f"{indent}  Notes: {str(notes)[:80]}")
        if notes2 and str(notes2) != 'nan' and str(notes2).strip():
            print(f"{indent}  Info: {str(notes2)[:80]}")
    
    def generate_quality_report(self):
        """Generate data quality report using reference tables for readable output"""
        print_section("7. Data Quality Report")
        
        if len(self.events_new) == 0:
            print("No events to report on.")
            return
        
        print(f"NEW RECORDS TO ADD:")
        print(f"  Events: {len(self.events_new)}")
        print(f"  Locations: {len(self.ev_locations_new)}")
        print(f"  Impact records: {len(self.impacts_new)}")
        
        print(f"\nDATE COVERAGE:")
        if self.events_new['event_date'].notna().sum() > 0:
            print(f"  Date range: {self.events_new['event_date'].min()} to {self.events_new['event_date'].max()}")
            print(f"  Events with valid date: {self.events_new['event_date'].notna().sum()}/{len(self.events_new)}")
        else:
            print(f"  No valid dates found")
        
        print(f"\nGEOGRAPHIC COVERAGE:")
        print(f"  Unique districts: {self.ev_locations_new['district_id'].nunique()}")
        print(f"  Events with matched district: {self.ev_locations_new['district_id'].notna().sum()}/{len(self.ev_locations_new)}")
        
        # Show which districts are represented (using district table)
        district_ids = self.ev_locations_new['district_id'].dropna().unique()
        if len(district_ids) > 0:
            if len(district_ids) <= 10:
                print(f"  Districts represented:")
                for dist_id in district_ids:
                    dist_name = self.db['district'][self.db['district']['district_id'] == dist_id]['dist_name'].values
                    if len(dist_name) > 0:
                        print(f"    - {dist_name[0]} (ID: {int(dist_id)})")
            else:
                print(f"  Too many districts to list individually ({len(district_ids)} districts)")
        
        # Show events without district
        events_no_district = len(self.ev_locations_new) - self.ev_locations_new['district_id'].notna().sum()
        if events_no_district > 0:
            print(f"  Events without district match: {events_no_district}")
        
        print(f"\nEVENT TYPES (using ev_type table):")
        ev_type_counts = self.events_new['ev_type_id'].value_counts()
        for ev_type_id, count in ev_type_counts.items():
            # Look up the name from ev_type table
            ev_type_name = self.db['ev_type'][self.db['ev_type']['ev_type_id'] == ev_type_id]['ev_type'].values
            if len(ev_type_name) > 0:
                print(f"  {ev_type_name[0]} (ID {int(ev_type_id)}): {count} events")
            else:
                print(f"  Unknown type (ID {int(ev_type_id)}): {count} events")
        
        print(f"\nIMPACT DATA COMPLETENESS:")
        for field in ['deaths', 'injuries', 'aff_tot', 'idps', 'home_dam', 'home_dest']:
            count = self.impacts_new[field].notna().sum()
            if count > 0:
                total = self.impacts_new[field].sum()
                print(f"  {field}: {count} events ({total:,.0f} total)")
        
        print(f"\nSOURCE (from source table):")
        print(f"  Source ID: {self.source_info['source_id']}")
        print(f"  Source Name: {self.source_info['source_name']}")
        if 'source_type' in self.source_info:
            print(f"  Source Type: {self.source_info['source_type']}")
    
    def save_output(self):
        """Save the new data and optionally update the database"""
        print_section("8. Saving Output")
        
        if len(self.events_new) == 0:
            print("No new events to save.")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"Import_{self.source_info['source_name']}_{timestamp}.xlsx"
        
        print(f"Saving new records to: {output_file}")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            self.events_new.to_excel(writer, sheet_name='events_NEW', index=False)
            self.ev_locations_new.to_excel(writer, sheet_name='ev_locations_NEW', index=False)
            self.impacts_new.to_excel(writer, sheet_name='impacts_NEW', index=False)
            
            # Add uncertain events if any
            if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
                self.uncertain_events.to_excel(writer, sheet_name='events_UNCERTAIN', index=False)
                self.uncertain_locations.to_excel(writer, sheet_name='ev_locations_UNCERTAIN', index=False)
                self.uncertain_impacts.to_excel(writer, sheet_name='impacts_UNCERTAIN', index=False)
            
            # Add summary sheet
            summary_data = [
                ['Import Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Source', self.source_info['source_name']],
                ['Source ID', self.source_info['source_id']],
                ['New Events to Import', len(self.events_new)],
                ['New Locations', len(self.ev_locations_new)],
                ['New Impact Records', len(self.impacts_new)],
            ]
            
            if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
                summary_data.append(['Uncertain Events (for review)', len(self.uncertain_events)])
            
            if len(self.events_new) > 0:
                summary_data.append(['Date Range', f"{self.events_new['event_date'].min()} to {self.events_new['event_date'].max()}"])
            
            pd.DataFrame(summary_data, columns=['Metric', 'Value']).to_excel(
                writer, sheet_name='IMPORT_SUMMARY', index=False
            )
        
        print(f"✓ Saved: {output_file}")
        
        # Note about uncertain events
        if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
            print(f"\n⚠ NOTE: {len(self.uncertain_events)} uncertain event(s) saved for later review")
            print(f"  These are in the '*_UNCERTAIN' sheets of {output_file}")
            print(f"  Review these later and manually add them to the database if appropriate")
        
        # Ask about updating the main database
        print("\n" + "="*70)
        update_db = get_user_input(
            "Do you want to UPDATE the main database file? (Y/N)",
            valid_options=['Y', 'N']
        )
        
        if update_db == 'Y':
            # Create backup
            backup_file = self.db_path.replace('.xlsx', f'_backup_{timestamp}.xlsx')
            print(f"\nCreating backup: {backup_file}")
            
            import shutil
            shutil.copy2(self.db_path, backup_file)
            print(f"✓ Backup created")
            
            # Update database
            print(f"\nUpdating main database: {self.db_path}")
            
            # Append new records to existing tables
            updated_events = pd.concat([self.db['events'], self.events_new], ignore_index=True)
            updated_ev_locations = pd.concat([self.db['ev_locations'], self.ev_locations_new], ignore_index=True)
            updated_impacts = pd.concat([self.db['impacts'], self.impacts_new], ignore_index=True)
            
            # Update source table if new source
            updated_source = self.db['source'].copy()
            if self.source_info.get('is_new'):
                new_source_row = {
                    'source_id': self.source_info['source_id'],
                    'source_name': self.source_info['source_name'],
                    'name_full': self.source_info.get('name_full', self.source_info['source_name']),
                    'source_type': self.source_info.get('source_type', 'Database')
                }
                updated_source = pd.concat([updated_source, pd.DataFrame([new_source_row])], ignore_index=True)
                print(f"  Added new source to source table")
            
            # Write updated database
            with pd.ExcelWriter(self.db_path, engine='openpyxl') as writer:
                updated_events.to_excel(writer, sheet_name='events', index=False)
                updated_ev_locations.to_excel(writer, sheet_name='ev_locations', index=False)
                updated_impacts.to_excel(writer, sheet_name='impacts', index=False)
                
                # Write all other tables unchanged
                for sheet_name, df in self.db.items():
                    if sheet_name == 'source':
                        updated_source.to_excel(writer, sheet_name='source', index=False)
                    elif sheet_name not in ['events', 'ev_locations', 'impacts']:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"✓ Database updated successfully")
            print(f"  Total events now: {len(updated_events)}")
            print(f"  Total locations now: {len(updated_ev_locations)}")
            print(f"  Total impacts now: {len(updated_impacts)}")
        else:
            print("\n✓ Main database NOT updated (only new records file saved)")
    
    def run(self):
        """Run the complete import workflow"""
        try:
            self.load_database()
            self.load_new_data(new_data_path)
            self.map_columns()
            self.get_source_info()
            self.process_data()
            self.check_duplicates()
            self.generate_quality_report()
            self.save_output()
            
            print_header("IMPORT COMPLETE")
            print("Thank you for using the Climate Event Database Updater Tool!")
            
        except KeyboardInterrupt:
            print("\n\nImport cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"\n\nERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print_header("CLIMATE EVENT DATABASE UPDATER TOOL")
    print("This tool helps you import disaster event data from any source")
    print("into your Uganda Climate Disaster Relational Database.")
    print("\nYou will be guided through:")
    print("  1. Loading your existing database")
    print("  2. Loading new data to import")
    print("  3. Mapping columns interactively")
    print("  4. Checking for duplicates")
    print("  5. Saving results")
    
    # Get file paths
    print("\n" + "="*70)
    
    db_path = get_user_input(
        "Enter path to your relational database (A1_RelationalDatabase.xlsx)",
        default=r"C:\Path\To\A1_RelationalDatabase.xlsx"
    )
    
    new_data_path = get_user_input(
        "Enter path to new data file to import",
        default=r"C:\Path\To\NewData.xlsx"
    )
    
    # Create importer and run
    importer = DataImporter(db_path)
    importer.run()


# =============================================================================
# CONFIGURATION
# =============================================================================

REGION_MAP = {
    1: 'CENTRAL',
    2: 'EASTERN', 
    3: 'NORTHERN',
    4: 'WESTERN'
}

REQUIRED_FIELDS = ['event_date', 'ev_type_id']  # district_id is optional
IMPACT_FIELDS = ['aff_tot', 'deaths', 'injuries', 'idps', 'missing', 'home_dam', 'home_dest']

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")

def print_section(text):
    """Print a section header"""
    print(f"\n{text}")
    print("-"*70)

def get_user_input(prompt, valid_options=None, default=None):
    """Get validated user input"""
    while True:
        if default:
            response = input(f"{prompt} [default: {default}]: ").strip()
            if not response:
                return default
        else:
            response = input(f"{prompt}: ").strip()
        
        if valid_options:
            if response.upper() in [opt.upper() for opt in valid_options]:
                return response.upper()
            else:
                print(f"Invalid input. Please choose from: {', '.join(valid_options)}")
        else:
            return response

def generate_event_id(event_date, region_id, existing_ids):
    """
    Generate event_id in format: YYYYMMDD-REGION-##
    
    Parameters:
    - event_date: datetime or string date
    - region_id: int (1-4 for Central, Eastern, Northern, Western)
    - existing_ids: set of existing event_ids
    
    Returns:
    - event_id string
    """
    if pd.isna(event_date):
        date_str = "NODATE"
    else:
        if isinstance(event_date, str):
            try:
                event_date = pd.to_datetime(event_date)
            except:
                date_str = "NODATE"
        date_str = event_date.strftime('%Y%m%d')
    
    if pd.isna(region_id) or region_id not in REGION_MAP:
        region_str = "NOTSPEC"
    else:
        region_str = REGION_MAP[region_id]
    
    # Find next available number
    base_id = f"{date_str}-{region_str}"
    counter = 1
    while f"{base_id}-{counter:02d}" in existing_ids:
        counter += 1
    
    return f"{base_id}-{counter:02d}"

# =============================================================================
# MAIN IMPORT CLASS
# =============================================================================

class DataImporter:
    """Main class for managing the import workflow"""
    
    def __init__(self, db_path):
        """Initialize the importer with database path"""
        self.db_path = db_path
        self.db = None
        self.new_data = None
        self.column_mapping = {}
        self.source_info = {}
        
        # Tables that will be modified
        self.events_new = None
        self.ev_locations_new = None
        self.impacts_new = None
        
        # Tables for uncertain events (need manual review)
        self.uncertain_events = pd.DataFrame()
        self.uncertain_locations = pd.DataFrame()
        self.uncertain_impacts = pd.DataFrame()
        
        # Reference tables
        self.district_dict = {}
        self.region_dict = {}
        self.ev_type_dict = {}
        self.source_dict = {}
        
        print_header("CLIMATE EVENT DATABASE UPDATER TOOL")
        
    def load_database(self):
        """Load the existing relational database and its reference tables"""
        print_section("1. Loading Existing Database")
        
        if not os.path.exists(self.db_path):
            print(f"ERROR: Database file not found: {self.db_path}")
            sys.exit(1)
        
        self.db = pd.read_excel(self.db_path, sheet_name=None)
        
        print(f"✓ Loaded database: {self.db_path}")
        print(f"\nData Tables:")
        print(f"  events: {len(self.db['events'])} records")
        print(f"  ev_locations: {len(self.db['ev_locations'])} records")
        print(f"  impacts: {len(self.db['impacts'])} records")
        
        print(f"\nReference Tables:")
        print(f"  source: {len(self.db['source'])} sources")
        print(f"  ev_type: {len(self.db['ev_type'])} event types")
        print(f"  region: {len(self.db['region'])} regions")
        print(f"  district: {len(self.db['district'])} districts")
        print(f"  county: {len(self.db['county'])} counties")
        print(f"  village: {len(self.db['village'])} villages")
        
        # Build lookup dictionaries
        self._build_lookups()
        
        # Show available event types
        print(f"\nAvailable Event Types (from ev_type table):")
        for _, row in self.db['ev_type'].iterrows():
            print(f"  {row['ev_type_id']}: {row['ev_type']}")
        
        # Show regions
        print(f"\nRegions (from region table):")
        for _, row in self.db['region'].iterrows():
            print(f"  {row['region_id']}: {row['reg_name']}")
        
    def _build_lookups(self):
        """Build lookup dictionaries from reference tables in database"""
        
        # District lookup (by name)
        # The district_id encodes the region: 1xxx=Central, 2xxx=Eastern, 3xxx=Northern, 4xxx=Western
        for _, row in self.db['district'].iterrows():
            name_clean = str(row['dist_name']).lower().strip()
            self.district_dict[name_clean] = {
                'district_id': row['district_id'],
                'region_id': row['region_id']
            }
        
        # Region lookup (from region table)
        for _, row in self.db['region'].iterrows():
            self.region_dict[row['region_id']] = row['reg_name']
        
        # Event type lookup (from ev_type table)
        for _, row in self.db['ev_type'].iterrows():
            ev_type_clean = str(row['ev_type']).lower().strip()
            self.ev_type_dict[ev_type_clean] = row['ev_type_id']
        
        # Source lookup (from source table)
        for _, row in self.db['source'].iterrows():
            source_name_clean = str(row['source_name']).lower().strip()
            self.source_dict[source_name_clean] = row['source_id']
        
        print(f"  Loaded {len(self.district_dict)} districts from district table")
        print(f"  Loaded {len(self.region_dict)} regions from region table")
        print(f"  Loaded {len(self.ev_type_dict)} event types from ev_type table")
        print(f"  Loaded {len(self.source_dict)} sources from source table")
    
    def load_new_data(self, file_path):
        """Load the new data file to import"""
        print_section("2. Loading New Data")
        
        if not os.path.exists(file_path):
            print(f"ERROR: Data file not found: {file_path}")
            sys.exit(1)
        
        # Try to load the file
        try:
            # Check if it has multiple sheets
            xl_file = pd.ExcelFile(file_path)
            
            if len(xl_file.sheet_names) > 1:
                print(f"File contains {len(xl_file.sheet_names)} sheets:")
                for i, sheet in enumerate(xl_file.sheet_names):
                    print(f"  {i+1}. {sheet}")
                
                sheet_choice = get_user_input("Which sheet contains the data to import? (enter number or name)")
                
                try:
                    sheet_idx = int(sheet_choice) - 1
                    sheet_name = xl_file.sheet_names[sheet_idx]
                except:
                    sheet_name = sheet_choice
                
                self.new_data = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                self.new_data = pd.read_excel(file_path)
        except Exception as e:
            print(f"ERROR loading file: {e}")
            sys.exit(1)
        
        print(f"✓ Loaded new data: {len(self.new_data)} rows, {len(self.new_data.columns)} columns")
        print(f"\nColumn names in new data:")
        for i, col in enumerate(self.new_data.columns):
            print(f"  {i+1:3d}. {col}")
    
    def map_columns(self):
        """Interactively map columns from new data to database schema"""
        print_section("3. Column Mapping")
        
        print("Please map the columns from your new data to the database fields.")
        print("Type the column name or number from the list above.")
        print("Press Enter to skip optional fields.\n")
        
        # Required mappings
        print("REQUIRED FIELDS:")
        print("-" * 40)
        
        # Date
        self.column_mapping['event_date'] = self._get_column_mapping(
            "Event date (required)", required=True
        )
        
        # Event type
        self.column_mapping['ev_type'] = self._get_column_mapping(
            "Event/disaster type (required)", required=True
        )
        
        # Location
        self.column_mapping['district'] = self._get_column_mapping(
            "District name (required)", required=True
        )
        
        # Optional but recommended
        print("\nOPTIONAL FIELDS:")
        print("-" * 40)
        
        self.column_mapping['county'] = self._get_column_mapping(
            "County/subcounty name", required=False
        )
        
        self.column_mapping['village'] = self._get_column_mapping(
            "Village/parish name", required=False
        )
        
        # Impact fields
        print("\nIMPACT FIELDS (at least one recommended):")
        print("-" * 40)
        
        impact_mappings = {
            'aff_tot': 'Total people affected',
            'deaths': 'Number of deaths',
            'injuries': 'Number of injuries',
            'idps': 'Number of IDPs/displaced',
            'missing': 'Number missing',
            'home_dam': 'Homes damaged',
            'home_dest': 'Homes destroyed'
        }
        
        for field, description in impact_mappings.items():
            self.column_mapping[field] = self._get_column_mapping(
                description, required=False
            )
        
        # Additional optional fields
        print("\nADDITIONAL OPTIONAL FIELDS:")
        print("-" * 40)
        
        self.column_mapping['end_date'] = self._get_column_mapping(
            "End date", required=False
        )
        
        self.column_mapping['event_name'] = self._get_column_mapping(
            "Event name/description", required=False
        )
        
        self.column_mapping['notes'] = self._get_column_mapping(
            "Notes/additional information", required=False
        )
        
        # Show summary
        print("\n" + "="*70)
        print("MAPPING SUMMARY:")
        print("="*70)
        for db_field, source_col in self.column_mapping.items():
            if source_col:
                print(f"  {db_field:20s} ← {source_col}")
    
    def _get_column_mapping(self, field_description, required=False):
        """Get column mapping from user input"""
        prompt = f"{field_description}"
        if not required:
            prompt += " (optional, press Enter to skip)"
        
        while True:
            response = input(f"  {prompt}: ").strip()
            
            if not response and not required:
                return None
            
            if not response and required:
                print("    This field is required. Please provide a column name.")
                continue
            
            # Check if it's a number (column index)
            try:
                col_idx = int(response) - 1
                if 0 <= col_idx < len(self.new_data.columns):
                    col_name = self.new_data.columns[col_idx]
                    print(f"    → Mapped to: {col_name}")
                    return col_name
                else:
                    print(f"    Invalid column number. Must be 1-{len(self.new_data.columns)}")
            except ValueError:
                # It's a column name
                if response in self.new_data.columns:
                    return response
                else:
                    print(f"    Column '{response}' not found in data.")
                    print(f"    Available columns: {', '.join(self.new_data.columns[:5])}...")
    
    def get_source_info(self):
        """Get or create source information using the source reference table"""
        print_section("4. Source Information")
        
        print("Current sources in database (from source table):")
        print(f"{'ID':<5} {'Source Name':<50} {'Type':<25}")
        print("-"*80)
        
        # Show sources from the actual source table
        for _, row in self.db['source'].iterrows():
            source_id = row['source_id']
            source_name = row['source_name']
            source_type = row.get('source_type', 'N/A')
            print(f"{source_id:<5} {source_name:<50} {source_type:<25}")
        
        source_input = get_user_input(
            "\nEnter source name (or source_id number if exists above)",
            default="Unknown"
        )
        
        # Check if it's an existing source by ID
        try:
            source_id_input = int(source_input)
            matching_source = self.db['source'][self.db['source']['source_id'] == source_id_input]
            if len(matching_source) > 0:
                row = matching_source.iloc[0]
                self.source_info['source_id'] = row['source_id']
                self.source_info['source_name'] = row['source_name']
                self.source_info['name_full'] = row.get('name_full', row['source_name'])
                self.source_info['source_type'] = row.get('source_type', '')
                print(f"✓ Using existing source: {row['source_name']} (ID: {row['source_id']})")
                return
        except ValueError:
            pass
        
        # Check if it's an existing source by name
        source_input_clean = source_input.lower().strip()
        if source_input_clean in self.source_dict:
            source_id = self.source_dict[source_input_clean]
            matching_source = self.db['source'][self.db['source']['source_id'] == source_id]
            row = matching_source.iloc[0]
            self.source_info['source_id'] = row['source_id']
            self.source_info['source_name'] = row['source_name']
            self.source_info['name_full'] = row.get('name_full', row['source_name'])
            self.source_info['source_type'] = row.get('source_type', '')
            print(f"✓ Using existing source: {row['source_name']} (ID: {row['source_id']})")
            return
        
        # New source - will be added to source table
        print(f"'{source_input}' not found in source table. Creating new source entry.")
        
        # Get next source_id from source table
        max_source_id = self.db['source']['source_id'].max()
        new_source_id = max_source_id + 1
        
        source_full_name = get_user_input(
            "Enter full source name",
            default=source_input
        )
        source_type = get_user_input(
            "Enter source type (e.g., International Organization, Government Agency, Database, News)",
            default="Database"
        )
        
        self.source_info['source_id'] = new_source_id
        self.source_info['source_name'] = source_input
        self.source_info['name_full'] = source_full_name
        self.source_info['source_type'] = source_type
        self.source_info['is_new'] = True
        
        print(f"✓ New source will be added to source table: {source_input} (ID: {new_source_id})")
    
    def process_data(self):
        """Process the new data and create database records"""
        print_section("5. Processing Data")
        
        # Initialize new dataframes
        events_list = []
        ev_locations_list = []
        impacts_list = []
        
        existing_event_ids = set(self.db['events']['event_id'].tolist())
        next_ev_loc_id = self.db['ev_locations']['ev_loc_id'].max() + 1 if len(self.db['ev_locations']) > 0 else 1
        next_impact_id_num = len(self.db['impacts']) + 1
        
        print(f"Processing {len(self.new_data)} records...")
        
        # Track unmatched items for diagnostic reporting
        unmatched_event_types = {}
        unmatched_districts = {}
        
        for idx, row in self.new_data.iterrows():
            # Extract date
            event_date = self._extract_date(row, self.column_mapping['event_date'])
            
            # Extract and match district (optional)
            district_info = self._match_district(row, self.column_mapping.get('district'))
            
            if district_info:
                district_id = district_info['district_id']
                region_id = district_info['region_id']
            else:
                # No district match - use None for district_id
                # Try to infer region from other location fields or default to unspecified
                district_id = None
                region_id = None  # Will result in "NOTSPEC" in event_id
                
                # Optionally, we could try to match county/village to get district
                # but for now, we'll allow events without district
            
            # Extract and match event type
            ev_type_id = self._match_event_type(row, self.column_mapping['ev_type'])
            
            if not ev_type_id:
                # Track unmatched event type
                raw_ev_type = str(self._get_value(row, self.column_mapping['ev_type']))
                unmatched_event_types[raw_ev_type] = unmatched_event_types.get(raw_ev_type, 0) + 1
                continue
            
            # Generate event_id
            event_id = generate_event_id(event_date, region_id, existing_event_ids)
            existing_event_ids.add(event_id)
            
            # Create event record
            event_record = {
                'event_id': event_id,
                'event_date': event_date,
                'report_date': datetime.now(),
                'ev_type_id': ev_type_id,
                'source_id': self.source_info['source_id'],
                'obs_id': event_id,  # Using event_id as obs_id
                'notes': self._get_value(row, self.column_mapping.get('notes')),
                'notes2': self._get_value(row, self.column_mapping.get('event_name'))
            }
            events_list.append(event_record)
            
            # Create location record
            ev_loc_record = {
                'ev_loc_id': next_ev_loc_id,
                'event_id': event_id,
                'village_id': None,  # Will implement matching later if needed
                'county_id': None,
                'district_id': district_id,
                'primary_loc': True
            }
            ev_locations_list.append(ev_loc_record)
            
            # Create impact record
            impact_record = {
                'impact_id': f"IMP_{event_id}_{next_impact_id_num}",
                'event_id': event_id,
                'ev_loc_id': next_ev_loc_id,
                'assess_date': event_date,
                'aff_tot': self._get_numeric_value(row, self.column_mapping.get('aff_tot')),
                'aff_m': None,
                'aff_f': None,
                'aff_u18': None,
                'aff_18_64': None,
                'aff_65o': None,
                'injuries': self._get_numeric_value(row, self.column_mapping.get('injuries')),
                'deaths': self._get_numeric_value(row, self.column_mapping.get('deaths')),
                'missing': self._get_numeric_value(row, self.column_mapping.get('missing')),
                'idps': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'disp_raw': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'disp_units': 'people' if self.column_mapping.get('idps') else None,
                'disp_est': self._get_numeric_value(row, self.column_mapping.get('idps')),
                'hh_aff': None,
                'home_dam': self._get_numeric_value(row, self.column_mapping.get('home_dam')),
                'home_dest': self._get_numeric_value(row, self.column_mapping.get('home_dest')),
                'facil_aff': None
            }
            impacts_list.append(impact_record)
            
            next_ev_loc_id += 1
            next_impact_id_num += 1
            
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(self.new_data)} records...")
        
        # Create DataFrames
        self.events_new = pd.DataFrame(events_list)
        self.ev_locations_new = pd.DataFrame(ev_locations_list)
        self.impacts_new = pd.DataFrame(impacts_list)
        
        print(f"\n✓ Processing complete:")
        print(f"  {len(self.events_new)} events created")
        print(f"  {len(self.ev_locations_new)} locations created")
        print(f"  {len(self.impacts_new)} impact records created")
        
        # Report unmatched items
        if unmatched_event_types:
            print(f"\n⚠ UNMATCHED EVENT TYPES ({sum(unmatched_event_types.values())} records skipped):")
            for ev_type, count in sorted(unmatched_event_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  - '{ev_type}': {count} occurrences")
            print(f"\nAvailable event types in your database:")
            for ev_type, ev_id in self.ev_type_dict.items():
                print(f"  - {ev_type} (ID: {ev_id})")
        
        if unmatched_districts:
            print(f"\n⚠ UNMATCHED DISTRICTS ({sum(unmatched_districts.values())} records affected):")
            # Show only top 10 unmatched districts
            sorted_districts = sorted(unmatched_districts.items(), key=lambda x: x[1], reverse=True)
            for dist, count in sorted_districts[:10]:
                print(f"  - '{dist}': {count} occurrences")
            if len(sorted_districts) > 10:
                print(f"  ... and {len(sorted_districts) - 10} more")
    
    def _extract_date(self, row, date_col):
        """Extract and parse date from row"""
        if not date_col or pd.isna(row[date_col]):
            return None
        
        try:
            return pd.to_datetime(row[date_col])
        except:
            return None
    
    def _match_district(self, row, district_col):
        """Match district name to database using district reference table"""
        if not district_col or pd.isna(row[district_col]):
            return None
        
        district_name = str(row[district_col]).lower().strip()
        
        # Direct match
        if district_name in self.district_dict:
            return self.district_dict[district_name]
        
        # Try removing common suffixes/prefixes for better matching
        # e.g., "Kasese District" -> "Kasese", "Kasese Province" -> "Kasese"
        district_name_clean = district_name.replace(' district', '').replace(' province', '').strip()
        if district_name_clean in self.district_dict:
            return self.district_dict[district_name_clean]
        
        # Fuzzy match - check if input is substring of database district
        for db_district, info in self.district_dict.items():
            if district_name in db_district:
                return info
        
        # Fuzzy match - check if database district is substring of input
        for db_district, info in self.district_dict.items():
            if db_district in district_name:
                return info
        
        return None
    
    def _match_event_type(self, row, ev_type_col):
        """Match event type to database using ev_type reference table with comprehensive matching"""
        if not ev_type_col or pd.isna(row[ev_type_col]):
            return None
        
        ev_type_name = str(row[ev_type_col]).lower().strip()
        
        # Direct match against ev_type table
        if ev_type_name in self.ev_type_dict:
            return self.ev_type_dict[ev_type_name]
        
        # Fuzzy match - check if input contains ev_type name
        for db_ev_type, ev_type_id in self.ev_type_dict.items():
            if db_ev_type in ev_type_name:
                return ev_type_id
        
        # Comprehensive hazard type mappings to standardized ev_type
        # This helps map various disaster databases to your 6 standard types
        # Each entry is: database_type -> [variations, synonyms, subtypes]
        hazard_mappings = {
            'flood': [
                'flood', 'floods', 'flooding',
                'flash flood', 'flash floods',
                'riverine flood', 'riverine floods', 'riverine',
                'coastal flood', 'coastal floods',
                'urban flood', 'urban floods',
                'general flood', 'flood (general)',
                'pluvial', 'fluvial',
                'inundation'
            ],
            'landslide': [
                'landslide', 'landslides',
                'mass movement', 'mass movements',
                'wet mass movement', 'wet mass movements',
                'dry mass movement', 'dry mass movements',
                'mudslide', 'mudslides', 'mud slide',
                'rockfall', 'rock fall', 'rockslide',
                'avalanche', 'avalanches',
                'debris flow', 'debris flows',
                'landslip', 'land slip',
                'slope failure', 'hillside collapse',
                'landslide (wet)', 'landslide/wet mass movement'
            ],
            'storm': [
                'storm', 'storms',
                'severe storm', 'severe storms',
                'storm (general)',
                'tropical storm', 'tropical storms',
                'convective storm', 'convective storms',
                'cyclone', 'cyclones', 'tropical cyclone',
                'hurricane', 'hurricanes',
                'typhoon', 'typhoons',
                'wind', 'windstorm', 'windstorms', 'severe wind',
                'tornado', 'tornadoes',
                'hailstorm', 'hailstorms', 'hail',
                'thunderstorm', 'thunderstorms',
                'lightning', 'lightning/thunderstorms',
                'severe weather', 'extreme weather',
                'tempest', 'squall', 'gale'
            ],
            'drought': [
                'drought', 'droughts',
                'dry spell', 'dry spells',
                'water scarcity', 'water shortage',
                'arid', 'aridity',
                'desertification',
                'crop failure'
            ],
            'earthquake': [
                'earthquake', 'earthquakes', 'quake',
                'seismic', 'seismic activity',
                'tremor', 'tremors',
                'ground movement', 'ground shaking',
                'tectonic'
            ],
            'fire': [
                'fire', 'fires',
                'wildfire', 'wildfires', 'wild fire',
                'forest fire', 'forest fires',
                'bush fire', 'bush fires', 'bushfire',
                'grass fire', 'grassfire',
                'vegetation fire',
                'scrub fire'
            ]
        }
        
        # Try to match against comprehensive mappings
        for standard_type, variations in hazard_mappings.items():
            for variation in variations:
                if variation == ev_type_name or variation in ev_type_name:
                    return self.ev_type_dict.get(standard_type)
        
        # If still no match, try partial word matching (last resort)
        # This helps catch variations we might have missed
        ev_type_words = set(ev_type_name.split())
        for standard_type in hazard_mappings.keys():
            if standard_type in ev_type_words:
                return self.ev_type_dict.get(standard_type)
        
        return None
    
    def _get_value(self, row, col_name):
        """Safely get value from row"""
        if not col_name or col_name not in row.index:
            return None
        return row[col_name] if not pd.isna(row[col_name]) else None
    
    def _get_numeric_value(self, row, col_name):
        """Safely get numeric value from row"""
        value = self._get_value(row, col_name)
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    def check_duplicates(self):
        """Check for potential duplicates and handle them"""
        print_section("6. Checking for Duplicates")
        
        existing_events = self.db['events']
        potential_duplicates = []
        
        for idx, new_event in self.events_new.iterrows():
            # Check by event_id (shouldn't happen but just in case)
            if new_event['event_id'] in existing_events['event_id'].values:
                potential_duplicates.append((idx, new_event['event_id'], 'event_id'))
                continue
            
            # Check by date + type + approximate location
            date_matches = existing_events[
                existing_events['event_date'] == new_event['event_date']
            ]
            
            if len(date_matches) > 0:
                type_matches = date_matches[
                    date_matches['ev_type_id'] == new_event['ev_type_id']
                ]
                
                if len(type_matches) > 0:
                    # Check district
                    new_district = self.ev_locations_new[
                        self.ev_locations_new['event_id'] == new_event['event_id']
                    ]['district_id'].values[0]
                    
                    for _, existing_event in type_matches.iterrows():
                        existing_district = self.db['ev_locations'][
                            self.db['ev_locations']['event_id'] == existing_event['event_id']
                        ]['district_id'].values
                        
                        if len(existing_district) > 0 and existing_district[0] == new_district:
                            potential_duplicates.append((
                                idx, 
                                new_event['event_id'],
                                'date_type_location',
                                existing_event['event_id']
                            ))
        
        if len(potential_duplicates) == 0:
            print("✓ No potential duplicates found")
            return
        
        print(f"Found {len(potential_duplicates)} potential duplicate(s)")
        print("\nReviewing each potential duplicate...\n")
        
        rows_to_remove = []
        
        for dup_info in potential_duplicates:
            idx = dup_info[0]
            new_id = dup_info[1]
            match_type = dup_info[2]
            existing_id = dup_info[3] if len(dup_info) > 3 else None
            
            print("="*70)
            print(f"POTENTIAL DUPLICATE: {new_id}")
            if match_type == 'date_type_location':
                print(f"Matches existing event: {existing_id}")
            print("-"*70)
            
            # Show new event details
            new_event = self.events_new.iloc[idx]
            new_impact = self.impacts_new[self.impacts_new['event_id'] == new_id].iloc[0]
            
            print("\nNEW EVENT:")
            print(f"  Event ID: {new_event['event_id']}")
            print(f"  Date: {new_event['event_date']}")
            print(f"  Type: {new_event['ev_type_id']}")
            print(f"  Deaths: {new_impact['deaths']}")
            print(f"  Affected: {new_impact['aff_tot']}")
            print(f"  IDPs: {new_impact['idps']}")
            
            if existing_id:
                # Show existing event details
                existing_event = self.db['events'][
                    self.db['events']['event_id'] == existing_id
                ].iloc[0]
                existing_impact = self.db['impacts'][
                    self.db['impacts']['event_id'] == existing_id
                ].iloc[0]
                
                print("\nEXISTING EVENT:")
                print(f"  Event ID: {existing_event['event_id']}")
                print(f"  Date: {existing_event['event_date']}")
                print(f"  Type: {existing_event['ev_type_id']}")
                print(f"  Source: {existing_event['source_id']}")
                print(f"  Deaths: {existing_impact['deaths']}")
                print(f"  Affected: {existing_impact['aff_tot']}")
                print(f"  IDPs: {existing_impact['idps']}")
            
            print("-"*70)
            decision = get_user_input(
                "Is this a TRUE duplicate? (Y=skip new event, N=keep both)",
                valid_options=['Y', 'N']
            )
            
            if decision == 'Y':
                rows_to_remove.append(idx)
                print("  → Marked for removal")
            else:
                print("  → Will keep both events")
            print()
        
        # Remove marked duplicates
        if rows_to_remove:
            print(f"\nRemoving {len(rows_to_remove)} duplicate records...")
            
            # Get event_ids to remove
            event_ids_to_remove = self.events_new.iloc[rows_to_remove]['event_id'].tolist()
            
            # Remove from all dataframes
            self.events_new = self.events_new.drop(index=rows_to_remove).reset_index(drop=True)
            self.ev_locations_new = self.ev_locations_new[
                ~self.ev_locations_new['event_id'].isin(event_ids_to_remove)
            ].reset_index(drop=True)
            self.impacts_new = self.impacts_new[
                ~self.impacts_new['event_id'].isin(event_ids_to_remove)
            ].reset_index(drop=True)
            
            print(f"✓ Removed {len(rows_to_remove)} duplicate(s)")
            print(f"  Remaining: {len(self.events_new)} events")
    
    def generate_quality_report(self):
        """Generate data quality report using reference tables for readable output"""
        print_section("7. Data Quality Report")
        
        if len(self.events_new) == 0:
            print("No events to report on.")
            return
        
        print(f"NEW RECORDS TO ADD:")
        print(f"  Events: {len(self.events_new)}")
        print(f"  Locations: {len(self.ev_locations_new)}")
        print(f"  Impact records: {len(self.impacts_new)}")
        
        print(f"\nDATE COVERAGE:")
        if self.events_new['event_date'].notna().sum() > 0:
            print(f"  Date range: {self.events_new['event_date'].min()} to {self.events_new['event_date'].max()}")
            print(f"  Events with valid date: {self.events_new['event_date'].notna().sum()}/{len(self.events_new)}")
        else:
            print(f"  No valid dates found")
        
        print(f"\nGEOGRAPHIC COVERAGE:")
        print(f"  Unique districts: {self.ev_locations_new['district_id'].nunique()}")
        print(f"  Events with matched district: {self.ev_locations_new['district_id'].notna().sum()}/{len(self.ev_locations_new)}")
        
        # Show which districts are represented (using district table)
        district_ids = self.ev_locations_new['district_id'].dropna().unique()
        if len(district_ids) > 0:
            if len(district_ids) <= 10:
                print(f"  Districts represented:")
                for dist_id in district_ids:
                    dist_name = self.db['district'][self.db['district']['district_id'] == dist_id]['dist_name'].values
                    if len(dist_name) > 0:
                        print(f"    - {dist_name[0]} (ID: {int(dist_id)})")
            else:
                print(f"  Too many districts to list individually ({len(district_ids)} districts)")
        
        # Show events without district
        events_no_district = len(self.ev_locations_new) - self.ev_locations_new['district_id'].notna().sum()
        if events_no_district > 0:
            print(f"  Events without district match: {events_no_district}")
        
        print(f"\nEVENT TYPES (using ev_type table):")
        ev_type_counts = self.events_new['ev_type_id'].value_counts()
        for ev_type_id, count in ev_type_counts.items():
            # Look up the name from ev_type table
            ev_type_name = self.db['ev_type'][self.db['ev_type']['ev_type_id'] == ev_type_id]['ev_type'].values
            if len(ev_type_name) > 0:
                print(f"  {ev_type_name[0]} (ID {int(ev_type_id)}): {count} events")
            else:
                print(f"  Unknown type (ID {int(ev_type_id)}): {count} events")
        
        print(f"\nIMPACT DATA COMPLETENESS:")
        for field in ['deaths', 'injuries', 'aff_tot', 'idps', 'home_dam', 'home_dest']:
            count = self.impacts_new[field].notna().sum()
            if count > 0:
                total = self.impacts_new[field].sum()
                print(f"  {field}: {count} events ({total:,.0f} total)")
        
        print(f"\nSOURCE (from source table):")
        print(f"  Source ID: {self.source_info['source_id']}")
        print(f"  Source Name: {self.source_info['source_name']}")
        if 'source_type' in self.source_info:
            print(f"  Source Type: {self.source_info['source_type']}")
    
    def save_output(self):
        """Save the new data and optionally update the database"""
        print_section("8. Saving Output")
        
        if len(self.events_new) == 0:
            print("No new events to save.")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"Import_{self.source_info['source_name']}_{timestamp}.xlsx"
        
        print(f"Saving new records to: {output_file}")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            self.events_new.to_excel(writer, sheet_name='events_NEW', index=False)
            self.ev_locations_new.to_excel(writer, sheet_name='ev_locations_NEW', index=False)
            self.impacts_new.to_excel(writer, sheet_name='impacts_NEW', index=False)
            
            # Add uncertain events if any
            if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
                self.uncertain_events.to_excel(writer, sheet_name='events_UNCERTAIN', index=False)
                self.uncertain_locations.to_excel(writer, sheet_name='ev_locations_UNCERTAIN', index=False)
                self.uncertain_impacts.to_excel(writer, sheet_name='impacts_UNCERTAIN', index=False)
            
            # Add summary sheet
            summary_data = [
                ['Import Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Source', self.source_info['source_name']],
                ['Source ID', self.source_info['source_id']],
                ['New Events to Import', len(self.events_new)],
                ['New Locations', len(self.ev_locations_new)],
                ['New Impact Records', len(self.impacts_new)],
            ]
            
            if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
                summary_data.append(['Uncertain Events (for review)', len(self.uncertain_events)])
            
            if len(self.events_new) > 0:
                summary_data.append(['Date Range', f"{self.events_new['event_date'].min()} to {self.events_new['event_date'].max()}"])
            
            pd.DataFrame(summary_data, columns=['Metric', 'Value']).to_excel(
                writer, sheet_name='IMPORT_SUMMARY', index=False
            )
        
        print(f"✓ Saved: {output_file}")
        
        # Note about uncertain events
        if hasattr(self, 'uncertain_events') and len(self.uncertain_events) > 0:
            print(f"\n⚠ NOTE: {len(self.uncertain_events)} uncertain event(s) saved for later review")
            print(f"  These are in the '*_UNCERTAIN' sheets of {output_file}")
            print(f"  Review these later and manually add them to the database if appropriate")
        
        # Ask about updating the main database
        print("\n" + "="*70)
        update_db = get_user_input(
            "Do you want to UPDATE the main database file? (Y/N)",
            valid_options=['Y', 'N']
        )
        
        if update_db == 'Y':
            # Create backup
            backup_file = self.db_path.replace('.xlsx', f'_backup_{timestamp}.xlsx')
            print(f"\nCreating backup: {backup_file}")
            
            import shutil
            shutil.copy2(self.db_path, backup_file)
            print(f"✓ Backup created")
            
            # Update database
            print(f"\nUpdating main database: {self.db_path}")
            
            # Append new records to existing tables
            updated_events = pd.concat([self.db['events'], self.events_new], ignore_index=True)
            updated_ev_locations = pd.concat([self.db['ev_locations'], self.ev_locations_new], ignore_index=True)
            updated_impacts = pd.concat([self.db['impacts'], self.impacts_new], ignore_index=True)
            
            # Update source table if new source
            updated_source = self.db['source'].copy()
            if self.source_info.get('is_new'):
                new_source_row = {
                    'source_id': self.source_info['source_id'],
                    'source_name': self.source_info['source_name'],
                    'name_full': self.source_info.get('name_full', self.source_info['source_name']),
                    'source_type': self.source_info.get('source_type', 'Database')
                }
                updated_source = pd.concat([updated_source, pd.DataFrame([new_source_row])], ignore_index=True)
                print(f"  Added new source to source table")
            
            # Write updated database
            with pd.ExcelWriter(self.db_path, engine='openpyxl') as writer:
                updated_events.to_excel(writer, sheet_name='events', index=False)
                updated_ev_locations.to_excel(writer, sheet_name='ev_locations', index=False)
                updated_impacts.to_excel(writer, sheet_name='impacts', index=False)
                
                # Write all other tables unchanged
                for sheet_name, df in self.db.items():
                    if sheet_name == 'source':
                        updated_source.to_excel(writer, sheet_name='source', index=False)
                    elif sheet_name not in ['events', 'ev_locations', 'impacts']:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"✓ Database updated successfully")
            print(f"  Total events now: {len(updated_events)}")
            print(f"  Total locations now: {len(updated_ev_locations)}")
            print(f"  Total impacts now: {len(updated_impacts)}")
        else:
            print("\n✓ Main database NOT updated (only new records file saved)")
    
    def run(self):
        """Run the complete import workflow"""
        try:
            self.load_database()
            self.load_new_data(new_data_path)
            self.map_columns()
            self.get_source_info()
            self.process_data()
            self.check_duplicates()
            self.generate_quality_report()
            self.save_output()
            
            print_header("IMPORT COMPLETE")
            print("Thank you for using the Climate Event Database Updater Tool!")
            
        except KeyboardInterrupt:
            print("\n\nImport cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"\n\nERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print_header("CLIMATE EVENT DATABASE UPDATER TOOL")
    print("This tool helps you import disaster event data from any source")
    print("into your Uganda Climate Disaster Relational Database.")
    print("\nYou will be guided through:")
    print("  1. Loading your existing database")
    print("  2. Loading new data to import")
    print("  3. Mapping columns interactively")
    print("  4. Checking for duplicates")
    print("  5. Saving results")
    
    # Get file paths
    print("\n" + "="*70)
    
    db_path = get_user_input(
        "Enter path to your relational database (A1_RelationalDatabase.xlsx)",
        default="/Users/maxbobholz/Library/CloudStorage/OneDrive-SharedLibraries-mcw.edu/SSA Climate Health - General/1 - Document Analysis/Database Building/A1_RelationalDatabase.xlsx"
    )
    
    new_data_path = get_user_input(
        "Enter path to new data file to import",
        default="/Users/maxbobholz/Library/CloudStorage/OneDrive-SharedLibraries-mcw.edu/SSA Climate Health - General/1 - Document Analysis/Records/datasets/idmc/IDMC_GIDD_Disasters_Internal_Displacement_Data.xlsx"
    )
    
    # Create importer and run
    importer = DataImporter(db_path)
    importer.run()