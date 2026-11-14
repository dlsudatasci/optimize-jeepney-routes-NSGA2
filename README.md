# optimize-jeepney-routes-NSGA2

## Prerequisites
* Python free-threading
* GDAL
* uv package manager

## Setup
Run if u wanna update the venv:
```
uv sync
```
Run if u wanna add a package:
```
uv add <package>
```

Run if u wanna update the amenity map submodule:
```
git submodule update --remote
```

optimize-jeepney-routes-NSGA2/
├── .gitignore
├── .gitmodules
├── README.md
├── data/
│   ├── amenity_maps/
│   │   ├── Makati City/
│   │   ├── Mandaluyong City/
│   │   ├── Manila City/
│   ├── Original Jeepney Routes/
│   │   ├── Taguig/
│   │   │   ├── Taguig Jeepney Routes/
│   │   │   │   ├── Original Data/
│   │   │   │   │   ├── Existing Jeepney Routes (Taguig).csv
│   │   │   │   ├── Taguig_routes.csv
│   │   │   ├── old amenity files/
│   │   │   │   ├── Taguig_osm_amenities.geojson
│   │   │   │   ├── Taguig_point.geojson
│   │   │   │   ├── Taguig_polygon.geojson
│   │   │   │   ├── Taguig_zoning.geojson
│   │   │   │   ├── taguig_fully_tagged.zip
│   │   │   ├── taguig_amenities_points.csv.zip
│   │   │   ├── taguig_amenities_polygon.csv.zip
│   │   │   ├── taguig_fully_tagged_manual.geojson.zip
│   │   │   ├── taguig_point.geojson.zip
│   │   │   ├── taguig_polygon.geojson.zip
│   ├── eda/
│   │   ├── eda_design_inputs.csv
│   │   ├── original_network_baseline.csv
│   ├── ga_checkpoints/
│   │   ├── GA_checkpoint_Mandaluyong__cov20_int10_ext10_vul20_rob20.pikl
│   ├── initial_route_sets/
│   │   ├── Makati/
│   │   │   ├── Makati_population.pkl
│   │   │   ├── Makati_population_w300_s20_l25_n50.pkl
│   │   │   ├── Makati_stops.pkl
│   │   │   ├── Makati_stops_w300_s20_l25_n50.pkl
│   │   ├── Mandaluyong/
│   │   │   ├── Mandaluyong_checkpoint_population.pkl
│   │   │   ├── Mandaluyong_population.pkl
│   │   │   ├── Mandaluyong_population_test.pkl
│   │   │   ├── Mandaluyong_stops.pkl
│   │   │   ├── Mandaluyong_test_stops.pkl
│   │   ├── Manila/
│   │   │   ├── Manila_checkpoint_population.pkl
│   │   │   ├── Manila_population.pkl
│   │   │   ├── Manila_population_w300_s25_l150_n100.pkl
│   │   │   ├── Manila_stops.pkl
│   │   │   ├── Manila_stops_w300_s25_l150_n100.pkl
│   ├── original_jeepney_routes/
│   │   ├── .DS_Store
│   │   ├── Makati_routes.csv
│   │   ├── Mandaluyong_routes.csv
│   │   ├── Manila_routes.csv
│   │   ├── Original Data/
│   │   │   ├── .DS_Store
│   │   │   ├── CQGIS- Route Information Drive Copy - CQGIS.csv.csv
│   │   │   ├── Existing Jeepney Routes (Makati).csv
│   │   │   ├── Existing Jeepney Routes (Mandaluyong).csv
│   │   │   ├── Existing Jeepney Routes (Manila) v2.csv
│   │   │   ├── Existing Jeepney Routes (Manila).csv
│   │   │   ├── Existing Jeepney Routes- C1.csv
│   │   │   ├── Existing Jeepney Routes- C10.csv
│   │   │   ├── Existing Jeepney Routes- C2.csv
│   │   │   ├── Existing Jeepney Routes- C3.csv
│   │   │   ├── Existing Jeepney Routes- C4.csv
│   │   │   ├── Existing Jeepney Routes- C5.csv
│   │   │   ├── Existing Jeepney Routes- C6.csv
│   │   │   ├── Existing Jeepney Routes- C7.csv
│   │   │   ├── Existing Jeepney Routes- C9.csv
│   │   │   ├── Formatted-Manila-Routes.csv
│   │   ├── Saved Networks/
│   │   │   ├── Makati Route Network.pikl
│   │   │   ├── Makati_built.pkl
│   │   │   ├── Mandaluyong Route Network.pikl
│   │   │   ├── Mandaluyong_built.pkl
│   │   │   ├── Manila Route Network.pikl
│   │   │   ├── Manila_built.pkl
│   │   │   ├── Taguig_built.pkl
│   │   │   ├── stop_graph_Makati.pkl
│   │   │   ├── stop_graph_Mandaluyong.pkl
│   │   │   ├── stop_graph_Manila.pkl
│   │   │   ├── stop_list_Makati.pkl
│   │   │   ├── stop_list_Mandaluyong.pkl
│   │   │   ├── stop_list_Manila.pkl
│   ├── population_distribution/
│   │   ├── makati-population-polygon.csv
│   │   ├── mandaluyong-population-polygon.csv
│   │   ├── manila-population-polygon.csv
│   │   ├── manila_amenities.csv
│   │   ├── taguig-population-polygon.csv
│   ├── saved_networks/
│   │   ├── .DS_Store
│   │   ├── Makati/
│   │   │   ├── .DS_Store
│   │   │   ├── Makati_Combined_Amenities_Network.pkl
│   │   │   ├── Makati_GA_Route_networks_Area_W300_cov20_con60_rf10_tf10_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Area_W300_cov25_con25_rf25_tf25_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Area_W550_cov25_con25_rf25_tf25_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Default_W550_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Degree_W300_cov20_con60_rf10_tf10_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Degree_W300_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Degree_W300_cov60_con20_rf10_tf10_S42.pkl
│   │   │   ├── Makati_GA_Route_networks_Degree_W550_cov60_con20_rf10_tf10_S42.pkl
│   │   │   ├── Makati_Initial_Network.pkl
│   │   │   ├── Makati_Population_Graph.pkl
│   │   │   ├── Makati_Route_networks_Mixed.pkl
│   │   │   ├── Makati_Route_networks_Mixed_R22.pkl
│   │   │   ├── Makati_Zone_Network.pkl
│   │   │   ├── stop_graph_Makati.pkl
│   │   │   ├── stop_list_Makati.pkl
│   │   ├── Mandaluyong/
│   │   │   ├── .DS_Store
│   │   │   ├── Mandaluyong_Combined_Amenities_Network.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Area_W300_cov20_con60_rf10_tf10_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Area_W550_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Area_W550_cov60_con20_rf10_tf10_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Default_W550_cov20_con60_rf10_tf10_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Default_W800_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Degree_W300_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Degree_W300_cov60_con20_rf10_tf10_S42.pkl
│   │   │   ├── Mandaluyong_GA_Route_networks_Degree_W800_cov60_con20_rf10_tf10_S42.pkl
│   │   │   ├── Mandaluyong_Initial_Network.pkl
│   │   │   ├── Mandaluyong_Population_Graph.pkl
│   │   │   ├── Mandaluyong_Route_networks_Mixed.pkl
│   │   │   ├── Mandaluyong_Zone_Network.pkl
│   │   │   ├── stop_graph_Mandaluyong.pkl
│   │   │   ├── stop_list_Mandaluyong.pkl
│   │   ├── Manila/
│   │   │   ├── .DS_Store
│   │   │   ├── Manila_Combined_Amenities_Network.pkl
│   │   │   ├── Manila_Filtered_Network.pkl
│   │   │   ├── Manila_GA_Route_networks_Area_W300_cov25_con25_rf25_tf25_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Area_W300_cov40_con40_rf10_tf10_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Degree_300.pkl
│   │   │   ├── Manila_GA_Route_networks_Degree_W300_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Degree_W300_cov25_con25_rf25_tf25_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Degree_W550_cov40_con40_rf10_tf10_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Degree_W800_cov20_int20_ext20_vul20_rob20_S42.pkl
│   │   │   ├── Manila_GA_Route_networks_Mixed.pkl
│   │   │   ├── Manila_Initial_Network.pkl
│   │   │   ├── Manila_Population_Graph.pkl
│   │   │   ├── Manila_Route_networks_Mixed.pkl
│   │   │   ├── Manila_Zone_Network.pkl
│   │   │   ├── stop_graph_Manila.pkl
│   │   │   ├── stop_list_Manila.pkl
│   ├── street_networks/
│   │   ├── .DS_Store
│   │   ├── Makati.graphml
│   │   ├── Mandaluyong.graphml
│   │   ├── Manila.graphml
│   │   ├── Taguig.graphml
├── download_osm.sh
├── notebooks/
│   ├── City_Zone_Creation.ipynb
│   ├── EDA.ipynb
│   ├── IRSG.ipynb
│   ├── NSGA-II_Route_Network_Optimization.ipynb
│   ├── Original Jeepney Routes.ipynb
│   ├── Taguig_CZC.ipynb
│   ├── archive/
│   │   ├── Makati_RouteConnection_GA_ModifiedImprovement.ipynb
│   │   ├── Mandaluyong_RouteConnection_GA_ModifiedImprovement.ipynb
│   │   ├── Manila_RouteConnection_GA_ModifiedImprovement.ipynb
│   │   ├── Visualizations of Optimized Network Results.ipynb
│   ├── cache/
│   │   ├── 9c5101bf8b4e4519c9103e48254fedd7fd421b0f.json
│   │   ├── d9663471fe8c1afdcaf83fc5a45d2f3b99fe9abf.json
├── plots/
│   ├── Crossover Result Maps/
│   │   ├── child1.html
│   │   ├── child2.html
│   │   ├── parent1.html
│   │   ├── parent2.html
│   ├── GA Generation Graphs/
│   │   ├── Makati/
│   │   │   ├── Makati_GA_Generations_cov20_int20_ext20_vul20_rob20_S42.png
│   │   │   ├── Makati_GA_Generations_cov25_con25_rf25_tf25_S42.png
│   │   │   ├── Makati_GA_Stacked_Max_Scores_cov20_int20_ext20_vul20_rob20_S42.png
│   │   ├── Mandaluyong/
│   │   │   ├── Mandaluyong_GA_Generations_cov20_int20_ext20_vul20_rob20_S42.png
│   │   │   ├── Mandaluyong_GA_Generations_cov25_con25_rf25_tf25_S42.png
│   │   │   ├── Mandaluyong_GA_Stacked_Max_Scores_cov20_int20_ext20_vul20_rob20_S42.png
│   │   ├── Manila/
│   │   │   ├── Manila_GA_Generations_cov20_int20_ext20_vul20_rob20_S42.png
│   │   │   ├── Manila_GA_Generations_cov25_con25_rf25_tf25_S42.png
│   │   │   ├── Manila_GA_Stacked_Max_Scores_cov20_int20_ext20_vul20_rob20_S42.png
│   ├── GA Result Route Networks HTML/
│   │   ├── .DS_Store
│   │   ├── Makati/
│   │   │   ├── .DS_Store
│   │   │   ├── Makati_GA_Map_Reverse_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Makati_GA_Map_Reverse_cov20_int20_ext20_vul20_rob20_S42.html
│   │   │   ├── Makati_GA_Map_Reverse_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Makati_GA_Map_Reverse_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Makati_GA_Map_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Makati_GA_Map_cov20_int20_ext20_vul20_rob20_S42.html
│   │   │   ├── Makati_GA_Map_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Makati_GA_Map_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Makati_Stops_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Makati_Stops_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Makati_Stops_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Makati_routes_cov20_con60_rf10_tf10_S42.csv
│   │   │   ├── Makati_routes_cov25_con25_rf25_tf25_S42.csv
│   │   │   ├── Makati_routes_cov60_con20_rf10_tf10_S42.csv
│   │   ├── Mandaluyong/
│   │   │   ├── .DS_Store
│   │   │   ├── Mandaluyong_GA_Map_Reverse_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_GA_Map_Reverse_cov20_int20_ext20_vul20_rob20_S42.html
│   │   │   ├── Mandaluyong_GA_Map_Reverse_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Mandaluyong_GA_Map_Reverse_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_GA_Map_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_GA_Map_cov20_int20_ext20_vul20_rob20_S42.html
│   │   │   ├── Mandaluyong_GA_Map_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Mandaluyong_GA_Map_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_Stops_cov20_con60_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_Stops_cov20_int20_ext20_vul20_rob20_S42.html
│   │   │   ├── Mandaluyong_Stops_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Mandaluyong_Stops_cov60_con20_rf10_tf10_S42.html
│   │   │   ├── Mandaluyong_routes_cov20_con60_rf10_tf10_S42.csv
│   │   │   ├── Mandaluyong_routes_cov20_int20_ext20_vul20_rob20_S42.csv
│   │   │   ├── Mandaluyong_routes_cov25_con25_rf25_tf25_S42.csv
│   │   │   ├── Mandaluyong_routes_cov60_con20_rf10_tf10_S42.csv
│   │   ├── Manila/
│   │   │   ├── .DS_Store
│   │   │   ├── Area/
│   │   │   │   ├── .DS_Store
│   │   │   ├── Default/
│   │   │   │   ├── .DS_Store
│   │   │   ├── Degree/
│   │   │   │   ├── .DS_Store
│   │   │   ├── Manila_GA_Map_Reverse_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Manila_GA_Map_Reverse_cov40_con40_rf10_tf10_S42.html
│   │   │   ├── Manila_GA_Map_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Manila_GA_Map_cov40_con40_rf10_tf10_S42.html
│   │   │   ├── Manila_Stops_cov25_con25_rf25_tf25_S42.html
│   │   │   ├── Manila_Stops_cov40_con40_rf10_tf10_S42.html
│   │   │   ├── Manila_routes_cov25_con25_rf25_tf25_S42.csv
│   │   │   ├── Manila_routes_cov40_con40_rf10_tf10_S42.csv
│   │   │   ├── Mixed/
│   │   │   │   ├── .DS_Store
│   │   ├── Manila Subset/
│   │   │   ├── .DS_Store
│   ├── Generated Route Networks HTML/
│   │   ├── .DS_Store
│   │   ├── Makati/
│   │   │   ├── .DS_Store
│   │   ├── Mandaluyong/
│   │   │   ├── .DS_Store
│   │   ├── Manila/
│   │   │   ├── .DS_Store
│   │   │   ├── Default/
│   │   │   │   ├── .DS_Store
│   │   │   ├── Manila t Map.html
│   │   │   ├── Manila t Reverse.html
│   │   │   ├── Mixed/
│   │   │   │   ├── .DS_Store
│   │   ├── Manila Subset/
│   │   │   ├── .DS_Store
│   ├── Initial Route Set Maps/
│   │   ├── Makati/
│   │   │   ├── Makati_Combined_Routes.html
│   │   │   ├── Makati_Combined_Routes_w300_s20_l25_n50.html
│   │   ├── Mandaluyong/
│   │   │   ├── Mandaluyong_Combined_Routes.html
│   │   │   ├── Mandaluyong_test_Combined_Routes.html
│   │   ├── Manila/
│   │   │   ├── Manila_Combined_Routes.html
│   ├── Original Jeepney Maps/
│   │   ├── .DS_Store
│   │   ├── Makati Route Map.html
│   │   ├── Mandaluyong Route Map.html
│   │   ├── Manila Route Map.html
│   ├── Population Maps/
│   │   ├── population_Makati.html
│   │   ├── population_Mandaluyong.html
│   │   ├── population_Manila.html
│   ├── Result Route Networks/
│   │   ├── Mandaluyong/
│   │   │   ├── best_network.html
│   ├── Stop Maps/
│   │   ├── stop_map_makati.html
│   │   ├── stop_map_mandaluyong.html
│   │   ├── stop_map_manila.html
│   ├── Zone Creation/
│   │   ├── .DS_Store
│   │   ├── Makati/
│   │   │   ├── after_map.html
│   │   │   ├── merge_map.html
│   │   │   ├── networks_map.html
│   │   │   ├── stops_map.html
│   │   ├── Mandaluyong/
│   │   │   ├── after_map.html
│   │   │   ├── merge_map.html
│   │   │   ├── networks_map.html
│   │   │   ├── stops_map.html
│   │   ├── Manila/
│   │   │   ├── after_map.html
│   │   │   ├── merge_map.html
│   │   │   ├── networks_map.html
│   │   │   ├── residential_filter.html
│   │   │   ├── stops_map.html
│   ├── eda/
│   │   ├── capex_options.png
│   │   ├── catchment_radius.png
│   │   ├── degree_vs_catchment.png
│   │   ├── overlap_map_makati.png
│   │   ├── overlap_map_manila.png
│   │   ├── overlap_map_taguig.png
│   │   ├── overlap_profile.png
│   ├── transpo_mandaluyong.html
├── pyproject.toml
├── src/
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── baseline.py
│   │   ├── build_original.py
│   │   ├── capacity.py
│   │   ├── catchment.py
│   │   ├── descriptive.py
│   │   ├── figures.py
│   │   ├── original_network.py
│   │   ├── overlap.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config.py
│   ├── genetic_algorithm/
│   │   ├── __init__.py
│   │   ├── crossover.py
│   │   ├── fitness.py
│   │   ├── mutate.py
│   │   ├── reverse_routes.py
│   │   ├── schema.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── checkpoint_utils.py
│   │   ├── graph_utils.py
│   │   ├── make_population_csv.py
│   │   ├── route_utils.py
│   │   ├── time_utils.py
├── tests/
│   ├── conftest.py
│   ├── test_mutate.py
├── uv.lock
