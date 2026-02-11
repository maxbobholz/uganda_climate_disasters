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


### Contact information
With questions, please feel free to reach out to the following individual:

Max Bobholz
Medical College of Wisconsin
[mbobholz@mcw.edu](mailto:mbobholz@mcw.edu)
+1 920 634 6731
