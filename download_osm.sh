#!/bin/bash

DATA_DIR="data/osm_ph"
mkdir -p "$DATA_DIR"

# Geofabrik URL for the Philippines
# For Shapefiles: https://download.geofabrik.de/asia/philippines-latest-free.shp.zip
# For GeoPackage: https://download.geofabrik.de/asia/philippines-latest-free.gpkg.zip
URL="https://download.geofabrik.de/asia/philippines-latest-free.shp.zip"
FILE_NAME="philippines-latest-free.shp"

echo "Checking for updates to $FILE_NAME..."

# Download the file to the specified directory.
# -N checks timestamps. -qO- suppresses output except errors. -c resumes broken downloads.
wget -N -c -P "$DATA_DIR" "$URL"

if [ $? -eq 0 ]; then
    echo "Success: $FILE_NAME is up to date in $DATA_DIR"
else
    echo "Error: Failed to download the OSM data."
    exit 1
fi
