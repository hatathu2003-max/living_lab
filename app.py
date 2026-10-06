import os
import glob

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium


# ============================================================
# LIVING LAB - STREAMLIT APPLICATION
# Rotterdam University of Applied Sciences
#
# TAB 1: Introduction / Living Lab
# TAB 2: Power BI Dashboard
# TAB 3: Interactive GIS Map
# ============================================================


# ============================================================
# GENERAL PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Living Lab",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# PROJECT PATH
# Tự động xác định thư mục chứa app.py
# Hoạt động trên cả GitHub Codespaces và Streamlit Cloud
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
DATABI_DIR = os.path.join(BASE_DIR, "databi")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


# ============================================================
# MAIN HEADER
# ============================================================

st.title("Living Lab")
st.caption("Rotterdam University of Applied Sciences")


# ============================================================
# CREATE 3 MAIN TABS
# ============================================================

tab_intro, tab_powerbi, tab_map = st.tabs(
    [
        "1. Introduction",
        "2. Power BI",
        "3. Interactive Map",
    ]
)


# ============================================================
# TAB 1 — INTRODUCTION
# Purpose:
# Introduce the Living Lab project and Rotterdam University
# of Applied Sciences.
# ============================================================

with tab_intro:

    st.header("Living Lab")

    # --------------------------------------------------------
    # University image
    # Put your university image in:
    #
    # /workspaces/living_lab/assets/rotterdam_university.jpg
    #
    # --------------------------------------------------------

    university_image = os.path.join(
        ASSETS_DIR,
        "rotterdam_university.jpg"
    )

    if os.path.exists(university_image):
        st.image(
            university_image,
            caption="Rotterdam University of Applied Sciences",
            use_container_width=True,
        )
    else:
        st.info(
            "Add an image of Rotterdam University of Applied Sciences "
            "to `assets/rotterdam_university.jpg`."
        )

    st.subheader("About the Living Lab")

    st.write(
        """
        The Living Lab provides an interactive environment for exploring,
        analysing and visualising urban and logistics-related data.

        The platform integrates geospatial data, interactive maps and
        business intelligence dashboards to support data-driven analysis
        and decision-making.

        This application is developed in the context of Rotterdam
        University of Applied Sciences.
        """
    )

    st.subheader("Application Structure")

    st.markdown(
        """
        **Introduction**  
        General information about the Living Lab and the project.

        **Power BI**  
        Interactive dashboards and analytical results.

        **Interactive Map**  
        Spatial visualisation of GeoPackage (GPKG) datasets using
        OpenStreetMap and Esri basemaps.
        """
    )


# ============================================================
# TAB 2 — POWER BI
# Purpose:
# Display Power BI content stored/configured in the databi
# section of the project.
#
# NOTE:
# A .pbix file itself cannot normally be rendered directly
# inside Streamlit. For an interactive Power BI dashboard,
# use a Power BI embed/publish URL.
# ============================================================

with tab_powerbi:

    st.header("Power BI Dashboard")

    st.write(
        """
        This section presents the Business Intelligence component
        of the Living Lab.
        """
    )

    # --------------------------------------------------------
    # OPTION 1:
    # Put your Power BI public/embed URL below.
    # --------------------------------------------------------

    POWERBI_URL = ""

    if POWERBI_URL:

        st.components.v1.iframe(
            POWERBI_URL,
            height=800,
            scrolling=True,
        )

    else:

        st.info(
            "Power BI dashboard has not been configured yet. "
            "Add the Power BI embed URL to `POWERBI_URL` in app.py."
        )

        # Show files available in databi
        if os.path.exists(DATABI_DIR):

            databi_files = os.listdir(DATABI_DIR)

            if databi_files:

                st.subheader("Files in databi")

                for file_name in databi_files:
                    st.write(f"• {file_name}")

            else:
                st.warning("The databi folder is currently empty.")

        else:
            st.warning(
                f"Folder not found: {DATABI_DIR}"
            )

# ============================================================
# TAB 3 — INTERACTIVE MAP
# Living Lab - Rotterdam University of Applied Sciences
#
# OPTIMISED VERSION
#
# - Last attribute column = classification field
# - Select classes to display
# - NO hover tooltip
# - Click feature -> scrollable popup with attribute data
# - Geometry simplification for faster rendering
# - Esri Street / Satellite
# - Transportation overlay
# ============================================================

with tab_map:

    st.header("Interactive Urban Logistics Map")

    st.write(
        """
        Explore the spatial data used in the Living Lab.
        Select the classification layers to display and click
        an object on the map to view its information.
        """
    )

    # ========================================================
    # 1. FIND GPKG FILES
    # ========================================================

    gpkg_files = glob.glob(
        os.path.join(DATA_DIR, "*.gpkg")
    )

    if not gpkg_files:

        st.warning(
            f"No GeoPackage (.gpkg) files found in:\n\n"
            f"{DATA_DIR}"
        )

    else:

        # ====================================================
        # 2. SELECT GPKG
        # ====================================================

        selected_gpkg = st.selectbox(
            "Select GeoPackage dataset",
            options=gpkg_files,
            format_func=lambda x: os.path.basename(x)
        )

        try:

            # =================================================
            # 3. LOAD DATA
            # =================================================

            @st.cache_data(show_spinner=False)
            def load_gpkg(path):

                data = gpd.read_file(path)

                if data.crs is not None:
                    data = data.to_crs(epsg=4326)

                return data


            with st.spinner("Loading spatial data..."):

                gdf = load_gpkg(selected_gpkg)


            if gdf.empty:

                st.warning(
                    "The selected GeoPackage contains no data."
                )

            elif gdf.crs is None:

                st.error(
                    "The GeoPackage does not contain CRS information."
                )

            else:

                # =================================================
                # 4. DETERMINE LAST ATTRIBUTE COLUMN
                # =================================================

                geometry_column = gdf.geometry.name

                attribute_columns = [
                    col
                    for col in gdf.columns
                    if col != geometry_column
                ]

                if not attribute_columns:

                    st.error(
                        "No attribute columns found in the GeoPackage."
                    )

                else:

                    classification_column = attribute_columns[-1]

                    # =================================================
                    # 5. CLEAN CLASSIFICATION VALUES
                    # =================================================

                    gdf["_map_class"] = (
                        gdf[classification_column]
                        .fillna("No Data")
                        .astype(str)
                        .str.strip()
                    )

                    class_values = sorted(
                        gdf["_map_class"]
                        .unique()
                        .tolist()
                    )

                    # =================================================
                    # 6. MAP CONTROLS
                    # =================================================

                    control_col1, control_col2 = st.columns(
                        [2, 1]
                    )

                    with control_col1:

                        selected_classes = st.multiselect(
                            f"Select {classification_column} layers",
                            options=class_values,
                            default=class_values
                        )

                    with control_col2:

                        basemap = st.selectbox(
                            "Basemap",
                            [
                                "Esri Street",
                                "Esri Satellite"
                            ]
                        )

                    show_transportation = st.checkbox(
                        "Show transportation network",
                        value=False
                    )

                    # =================================================
                    # 7. FILTER DATA FIRST
                    #
                    # IMPORTANT FOR PERFORMANCE:
                    # only selected features are sent to browser.
                    # =================================================

                    filtered_gdf = gdf[
                        gdf["_map_class"].isin(
                            selected_classes
                        )
                    ].copy()

                    filtered_gdf = filtered_gdf[
                        filtered_gdf.geometry.notnull()
                    ]

                    filtered_gdf = filtered_gdf[
                        ~filtered_gdf.geometry.is_empty
                    ]

                    # =================================================
                    # 8. SIMPLIFY GEOMETRY
                    #
                    # Reduces number of polygon vertices.
                    # This makes Folium considerably faster.
                    #
                    # EPSG:4326 is degrees.
                    # 0.00002 is a small simplification suitable
                    # for neighbourhood/urban visualisation.
                    # =================================================

                    if not filtered_gdf.empty:

                        filtered_gdf["geometry"] = (
                            filtered_gdf.geometry.simplify(
                                tolerance=0.00002,
                                preserve_topology=True
                            )
                        )

                    # =================================================
                    # 9. CREATE MAP
                    # =================================================

                    m = folium.Map(
                        location=[51.92, 4.48],
                        zoom_start=11,
                        tiles=None,
                        control_scale=True,
                        prefer_canvas=True
                    )

                    # =================================================
                    # 10. ESRI STREET
                    # =================================================

                    folium.TileLayer(

                        tiles=(
                            "https://server.arcgisonline.com/"
                            "ArcGIS/rest/services/"
                            "World_Street_Map/"
                            "MapServer/tile/{z}/{y}/{x}"
                        ),

                        attr="Esri",

                        name="Esri Street",

                        overlay=False,

                        show=(
                            basemap == "Esri Street"
                        )

                    ).add_to(m)

                    # =================================================
                    # 11. ESRI SATELLITE
                    # =================================================

                    folium.TileLayer(

                        tiles=(
                            "https://server.arcgisonline.com/"
                            "ArcGIS/rest/services/"
                            "World_Imagery/"
                            "MapServer/tile/{z}/{y}/{x}"
                        ),

                        attr="Esri",

                        name="Esri Satellite",

                        overlay=False,

                        show=(
                            basemap == "Esri Satellite"
                        )

                    ).add_to(m)

                    # =================================================
                    # 12. TRANSPORTATION OVERLAY
                    # =================================================

                    folium.TileLayer(

                        tiles=(
                            "https://server.arcgisonline.com/"
                            "ArcGIS/rest/services/"
                            "Reference/"
                            "World_Transportation/"
                            "MapServer/tile/{z}/{y}/{x}"
                        ),

                        attr="Esri",

                        name="Transportation Network",

                        overlay=True,

                        show=show_transportation,

                        opacity=0.9

                    ).add_to(m)

                    # =================================================
                    # 13. CLASS COLORS
                    # =================================================

                    layer_colors = [
                        "#e41a1c",
                        "#377eb8",
                        "#4daf4a",
                        "#984ea3",
                        "#ff7f00",
                        "#a65628",
                        "#f781bf",
                        "#17becf",
                        "#bcbd22",
                        "#1f77b4",
                        "#d62728"
                    ]

                    # =================================================
                    # 14. DRAW EACH CLASS
                    # =================================================

                    for class_index, class_value in enumerate(
                        selected_classes
                    ):

                        class_gdf = filtered_gdf[
                            filtered_gdf["_map_class"]
                            == class_value
                        ].copy()

                        if class_gdf.empty:
                            continue

                        class_color = layer_colors[
                            class_index % len(layer_colors)
                        ]

                        # =============================================
                        # Feature group
                        # =============================================

                        feature_group = folium.FeatureGroup(
                            name=(
                                f"{classification_column}: "
                                f"{class_value}"
                            ),
                            show=True
                        )

                        # =============================================
                        # Columns displayed in popup
                        # =============================================

                        popup_fields = [
                            col
                            for col in attribute_columns
                            if col in class_gdf.columns
                        ]

                        popup_aliases = [
                            f"{col}:"
                            for col in popup_fields
                        ]

                        # =============================================
                        # GeoJSON
                        #
                        # NO TOOLTIP
                        # -> nothing appears on hover.
                        # =============================================

                        geojson_layer = folium.GeoJson(

                            data=class_gdf.to_json(),

                            name=str(class_value),

                            style_function=(
                                lambda feature,
                                color=class_color: {

                                    "color": color,

                                    "fillColor": color,

                                    "weight": 1.5,

                                    "opacity": 0.9,

                                    "fillOpacity": 0.50
                                }
                            ),

                            highlight_function=(
                                lambda feature: {

                                    "weight": 3,

                                    "fillOpacity": 0.70
                                }
                            )
                        )

                        # =============================================
                        # CLICK POPUP
                        #
                        # All attribute information appears only
                        # when the feature is clicked.
                        #
                        # max_height -> popup becomes scrollable
                        # when there are many attributes.
                        # =============================================

                        popup = folium.GeoJsonPopup(
							fields=popup_fields,
							aliases=popup_aliases,
							localize=True,
							labels=True,
							sticky=False,

							style=(
								"background-color: white;"
								"font-size: 12px;"
								"padding: 5px;"
								"max-height: 300px;"
								"overflow-y: auto;"
							),

							max_width=450,

							# QUAN TRỌNG:
							# Không cho Leaflet tự di chuyển map khi mở popup
							popup_options={
								"autoPan": False,
								"keepInView": False,
								"closeButton": True,
								"autoClose": True,
								"closeOnClick": True
							}
						)

                        popup.add_to(geojson_layer)

                        geojson_layer.add_to(feature_group)

                        feature_group.add_to(m)

                    # =================================================
                    # 15. AUTO ZOOM
                    # =================================================

                    if not filtered_gdf.empty:

                        try:

                            minx, miny, maxx, maxy = (
                                filtered_gdf.total_bounds
                            )

                            if (
                                -180 <= minx <= 180
                                and -180 <= maxx <= 180
                                and -90 <= miny <= 90
                                and -90 <= maxy <= 90
                            ):

                                m.fit_bounds(
                                    [
                                        [miny, minx],
                                        [maxy, maxx]
                                    ]
                                )

                        except Exception:
                            pass

                    # =================================================
                    # 16. LAYER CONTROL
                    # =================================================

                    folium.LayerControl(
                        collapsed=True,
                        position="topright"
                    ).add_to(m)

                    # =================================================
                    # 17. DISPLAY MAP
                    # =================================================

                    st_folium(
                        m,
                        height=750,
                        use_container_width=True,
                        key="living_lab_interactive_map",
                        returned_objects=[]
                    )

                    # =================================================
                    # 18. SUMMARY
                    # =================================================

                    if selected_classes:

                        st.caption(
                            f"{len(filtered_gdf):,} features displayed "
                            f"across {len(selected_classes)} layer(s). "
                            f"Click a map object to view its data."
                        )

                    else:

                        st.warning(
                            "Select at least one layer to display data."
                        )

        except Exception as e:

            st.error(
                f"Error loading GeoPackage: {e}"
            )