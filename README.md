# Comprehensive database of climate disaster events (and their impacts) in Uganda

This repository centers around a relational database -- created by means of document analysis -- that contains a variety of valuable metadata for climate disaster events in Uganda since 2008. The **Events Database** (and other relevant files for understanding its structure) can be found in the `database` directory.

### `database` directory
This repository contains three files that are all related to the **Events Database**:
- `A1_RelationalDatabase_DDMonYY.xlsx` - This Excel file contains the structure and data included within the Events Database (and the date of latest update).
- `A1_Codebook_RelationalDatabase.docx` - This Word document contains descriptions of all variables within the Events Database.
- `A1_RDBSchema_v#.png` - This image file includes the visual schematic that outlines the relationships between tables within the Events Database.

### `update_database` directory
This directory contains relevant files for updating the **Events Database** with data from a variety of sources.
- `dbupdater.py` - This Python script can be used to update the **Events Database** with new events stored in a CSV format. Within this script, the user will be prompted in various ways in order to match variable names, handle duplicate events, and more.

### `database_pulls` directory
This directory contains a script used to gather summary information from the relational database (as well as the resulting CSV and TXT files).
- `District_Summary_YYYYMMDD.csv` - This file contains summary details for climate disaster events at the district level in Uganda.
- `National_Summary_YYYYMMDD.csv` - This file contains summary details for climate disaster events at the national level in Uganda.
- `Summary_Report_YYYYMMDD.txt` - A narrative summary of climate disasters (and their impacts) in Uganda based on the existing database.
- `events_summary.py` - This is the script used to generate the above files. This script can be edited or adjusted for your specific desired database pulls.

### `spatial_data` directory
This directory contains relevant spatial data files either created from the existing **Events Database** or gathered & adjusted from other sources.
- `admin_boundaries` - This directory contains administrative boundary shapefiles for Uganda at the administrative levels (0=Nation, 1=Region, 2=District, 3=County, 4=Village/Parish).
- `natural_features` - This directory contains shapefiles related to the notable natural features of Uganda contributing to the climate displacement crisis.
- `database_shapes` - This directory contains a variety of shapefiles (and the script used to generate them) created from the **Events Database**.


### Contact information
With questions, please feel free to reach out to the following individual: \\

**Max Bobholz** \\
*Medical College of Wisconsin* \\
[mbobholz@mcw.edu](mailto:mbobholz@mcw.edu) \\
+1 920 634 6731 \\
