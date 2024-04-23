#Emma Castiblanco
#03/05/2024
#Updated 4/23/2024

# Uniformity for Street Lines and Bus Routes
# Combining Street Centerline shapefile with Centerlines for bus routes
# Assigning street centerlines as either bus routes or non-bus route roads
# Assistance from ChatGPT


# User will be prompted with Insert folder name: the names of all the folders are cities located in city_data csv

import arcpy
import os
import sys
import csv

def load_city_data_from_csv(csv_file):
    city_data = {}
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            city_name = row['folder']
            city_data[city_name] = {
                "folder": row['folder'],
                "utm_zone": int(row['utm_zone']),
                "street_centers": row['street_centers'],
                "bus_routes": row['bus_routes'],
                "city_limits": row['city_limits']
            }
    return city_data

def main(city_name, city_data):
    print("***Emma's Code is Starting***")

    city_info = city_data.get(city_name)
    if not city_info:
        print("City not found in the database.")
        return

    # Set the working directory based on the city name
    working_directory = os.path.join(r"N:\Classes\workspace\CastiblancoE\Final Project2\Final Project", city_info["folder"])
    if not os.path.exists(working_directory):
        print(f"Folder for city '{city_name}' does not exist.")
        sys.exit(1)

    arcpy.env.workspace = working_directory

    # Paths to shapefiles
    street_centerlines = os.path.join(working_directory, city_info["street_centers"],  city_info["street_centers"] + ".shp")
    bus_routes = os.path.join(working_directory, city_info["bus_routes"], city_info["bus_routes"] + ".shp")
    city_limit = os.path.join(working_directory, city_info["city_limits"], city_info["city_limits"] + ".shp")

    # Define output projected shapefile paths
    projected_street_centerlines = os.path.join(working_directory, "projected_street_centerlines.shp")
    projected_bus_routes = os.path.join(working_directory, "projected_bus_routes.shp")
    projected_city_limit = os.path.join(working_directory, "projected_city_limit.shp")

    # Get the UTM zone for the current city
    utm_zone = city_info["utm_zone"]

    # Define the coordinate system using the UTM zone
    output_crs = arcpy.SpatialReference(utm_zone)

    try:
        # Delete existing output files if they exist
        if arcpy.Exists(projected_street_centerlines):
            arcpy.Delete_management(projected_street_centerlines)
        if arcpy.Exists(projected_bus_routes):
            arcpy.Delete_management(projected_bus_routes)
        if arcpy.Exists(projected_city_limit):
            arcpy.Delete_management(projected_city_limit)

        # Project the shapefiles
        arcpy.management.Project(street_centerlines, projected_street_centerlines, output_crs)
        arcpy.management.Project(bus_routes, projected_bus_routes, output_crs)
        arcpy.management.Project(city_limit, projected_city_limit, output_crs)


    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))

    # Define output clipped shapefile paths
    clipped_street_centerlines = "clipped_street_centerlines.shp"
    clipped_bus_routes = "clipped_bus_routes.shp"

    # Delete existing output files if they exist
    if arcpy.Exists(clipped_bus_routes):
        arcpy.Delete_management(clipped_bus_routes)
    if arcpy.Exists(clipped_street_centerlines):
        arcpy.Delete_management(clipped_street_centerlines)

        # Check if all shapefiles have been projected to the desired CRS
    projected_shapefiles = [projected_street_centerlines, projected_bus_routes, projected_city_limit]
    for shapefile in projected_shapefiles:
        if arcpy.Exists(shapefile):
            desc = arcpy.Describe(shapefile)
            if desc.spatialReference.factoryCode != output_crs.factoryCode:
                print(f"Warning: {shapefile} is not projected to the desired CRS.")
        else:
            print(f"Error: {shapefile} does not exist.")

    # Clip the projected bus routes and street centerlines to the projected city limit
    arcpy.analysis.Clip(bus_routes, city_limit, clipped_bus_routes)
    arcpy.analysis.Clip(street_centerlines, city_limit, clipped_street_centerlines)

    # Define output shapefile paths for buffered features
    buffered_bus_routes = "buffered_bus_routes.shp"

    # Delete existing output files if they exist
    if arcpy.Exists(buffered_bus_routes):
        arcpy.Delete_management(buffered_bus_routes)

    # Buffer the clipped street centerlines and bus routes
    arcpy.Buffer_analysis(clipped_bus_routes, buffered_bus_routes, "10 Meters", "FULL", "ROUND", "ALL", " ","PLANAR")

    print("Buffers created successfully!")

    # Define output path for the intersected feature class (Bus_Route_Roads)
    bus_route_roads_fc = "Bus_Route_Roads.shp"

    # Delete existing output files if they exist
    if arcpy.Exists(bus_route_roads_fc):
        arcpy.Delete_management(bus_route_roads_fc)

    # Compute the intersect between clipped street centerlines and buffered bus routes
    arcpy.analysis.Intersect([clipped_street_centerlines, buffered_bus_routes], bus_route_roads_fc, "ALL", "", "INPUT")

    # Add the "RoadType" field to the "Bus_Route_Roads" feature class
    arcpy.AddField_management(bus_route_roads_fc, "RoadType", "TEXT")

    # Calculate "Bus" for all rows in the "RoadType" field of Bus_Route_Roads
    arcpy.CalculateField_management(bus_route_roads_fc, "RoadType", "'Bus'", "PYTHON3")

    print("Intersected feature class (Bus_Route_Roads) created successfully!")

    # Define output path for the symmetric difference feature class (Non_Bus_Route_Roads)
    non_bus_route_roads_fc = "Non_Bus_Route_Roads.shp"

    # Delete existing output files if they exist
    if arcpy.Exists(non_bus_route_roads_fc):
        arcpy.Delete_management(non_bus_route_roads_fc)

    # Compute the symmetric difference between clipped street centerlines and bus routes
    arcpy.analysis.SymDiff(clipped_street_centerlines, bus_route_roads_fc, non_bus_route_roads_fc)

    # Add the "RoadType" field to the "Non_Bus_Route_Roads" feature class
    arcpy.AddField_management(non_bus_route_roads_fc, "RoadType", "TEXT")

    # Calculate "Non-Bus" for all rows in the "RoadType" field of Non_Bus_Route_Roads
    arcpy.CalculateField_management(non_bus_route_roads_fc, "RoadType", "'Non-Bus'", "PYTHON3")

    print("Feature class (Non_Bus_Route_Roads) created successfully!")

    # Define output path for the merged feature class (City_Streets)
    city_streets_fc = f"{city_name}_Streets.shp"

    # Delete existing output files if they exist
    if arcpy.Exists(city_streets_fc):
        arcpy.Delete_management(city_streets_fc)

    # Merge the Non_Bus_Route_Roads and Bus_Route_Roads feature classes
    arcpy.management.Merge([non_bus_route_roads_fc, bus_route_roads_fc], city_streets_fc)

    print("Merged feature class (City_Streets) created successfully!")

    print("City Streets defined as Non-Bus and Bus Roads")

  # Delete all shapefiles except city_streets_fc
    for file in os.listdir(arcpy.env.workspace):
        if file.endswith(".shp") and file != city_streets_fc:
            arcpy.Delete_management(os.path.join(arcpy.env.workspace, file))

    print("All shp.'s besides the new streets with route info have been deleted!")
# Insert Specific city (use city_data table to find cities: format should be City_StateInitials, ex. Denver_CO)
if __name__ == "__main__":
    csv_file = "city_data.csv"  # Update this with the path to your CSV file
    city_data = load_city_data_from_csv(csv_file)
    city_name = input("Insert folder name: ").strip()  # Using folder name as input
    main(city_name, city_data)




print("***The Code is Done***")