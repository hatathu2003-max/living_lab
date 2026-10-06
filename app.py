import os
import glob

import streamlit as st
import geopandas as gpd
import folium
import pyogrio
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
LIB_GPKG_DIR = os.path.join(BASE_DIR, "lib_gpkg")


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
# TAB 3 — INTERACTIVE URBAN LOGISTICS MAP
# Living Lab - Rotterdam University of Applied Sciences
#
# DATA SOURCES:
#
# A. /data
#    Main GeoPackage
#    -> Last attribute column = classification field
#    -> Unique values = selectable classification layers
#
# B. /lib_gpkg
#    One additional GeoPackage
#    -> May contain multiple internal GIS layers
#    -> User selects which GIS layers to display
#
# MAP:
#    -> Esri Street
#    -> Esri Satellite
#    -> Transportation overlay
#
# INTERACTION:
#    -> No data on hover
#    -> Click feature to open popup
#    -> Popup does not move/pan the map
# ============================================================

with tab_map:

    st.header("Interactive Urban Logistics Map")

    st.write(
        """
        Explore spatial patterns and supporting GIS datasets used in
        the Living Lab. Select classification results from the main
        dataset and combine them with additional spatial layers.
        """
    )

    # ========================================================
    # 1. CACHE FUNCTIONS
    # ========================================================

    @st.cache_data(show_spinner=False)
    def load_main_gpkg(path):
        """
        Load the main GeoPackage and convert it to WGS84.
        """

        data = gpd.read_file(path)

        if data.crs is not None:
            data = data.to_crs(epsg=4326)

        return data


    @st.cache_data(show_spinner=False)
    def get_gpkg_layers(path):
        """
        Return all internal layer names from a GeoPackage.
        """

        layer_info = pyogrio.list_layers(path)

        return layer_info[:, 0].tolist()


    @st.cache_data(show_spinner=False)
    def load_library_layer(path, layer_name):
        """
        Load one selected layer from the library GeoPackage.
        """

        data = gpd.read_file(
            path,
            layer=layer_name
        )

        if data.crs is not None:
            data = data.to_crs(epsg=4326)

        return data


    # ========================================================
    # 2. MAIN GPKG — FIND FILES IN /data
    # ========================================================

    st.subheader("Classification Data")

    main_gpkg_files = glob.glob(
        os.path.join(DATA_DIR, "*.gpkg")
    )

    if not main_gpkg_files:

        st.warning(
            f"No GeoPackage was found in:\n\n{DATA_DIR}"
        )

    else:

        # ====================================================
        # 3. SELECT MAIN GPKG
        # ====================================================

        selected_main_gpkg = st.selectbox(
            "Select classification dataset",
            options=main_gpkg_files,
            format_func=lambda x: os.path.basename(x)
        )

        try:

            # =================================================
            # 4. LOAD MAIN GPKG
            # =================================================

            with st.spinner(
                "Loading classification data..."
            ):

                gdf = load_main_gpkg(
                    selected_main_gpkg
                )


            if gdf.empty:

                st.warning(
                    "The selected GeoPackage contains no data."
                )

            elif gdf.crs is None:

                st.error(
                    "The main GeoPackage does not contain "
                    "CRS information."
                )

            else:

                # =============================================
                # 5. IDENTIFY LAST ATTRIBUTE COLUMN
                # =============================================

                geometry_column = gdf.geometry.name

                attribute_columns = [
                    col
                    for col in gdf.columns
                    if col != geometry_column
                ]

                if not attribute_columns:

                    st.error(
                        "No attribute columns were found "
                        "in the main GeoPackage."
                    )

                else:

                    # =========================================
                    # Last non-geometry column
                    # =========================================

                    classification_column = (
                        attribute_columns[-1]
                    )

                    # =========================================
                    # Create cleaned map classification
                    # =========================================

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

                    # =========================================
                    # 6. MAIN MAP CONTROLS
                    # =========================================

                    control_col1, control_col2 = st.columns(
                        [2, 1]
                    )

                    with control_col1:

                        selected_classes = st.multiselect(
                            (
                                "Select classification layers "
                                f"({classification_column})"
                            ),
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

                    # =========================================
                    # Transportation overlay
                    # =========================================

                    show_transportation = st.checkbox(
                        "Show transportation network",
                        value=False
                    )

                    # =================================================
                    # 7. ADDITIONAL GIS LAYERS
                    # =================================================

                    st.divider()

                    st.subheader(
                        "Additional GIS Layers"
                    )

                    st.caption(
                        "Select additional spatial layers from "
                        "the Living Lab GIS library."
                    )

                    # =========================================
                    # Find library GPKG
                    # =========================================

                    library_files = glob.glob(
                        os.path.join(
                            LIB_GPKG_DIR,
                            "*.gpkg"
                        )
                    )

                    library_gpkg = None

                    selected_library_layers = []

                    if not library_files:

                        st.info(
                            "No library GeoPackage was found "
                            "in the lib_gpkg folder."
                        )

                    else:

                        # -------------------------------------
                        # Only ONE library GPKG is expected
                        # -------------------------------------

                        library_gpkg = library_files[0]

                        try:

                            library_layer_names = (
                                get_gpkg_layers(
                                    library_gpkg
                                )
                            )

                            selected_library_layers = (
                                st.multiselect(
                                    "Select additional GIS layers",
                                    options=library_layer_names,
                                    default=[]
                                )
                            )

                            st.caption(
                                "Source: "
                                f"{os.path.basename(library_gpkg)}"
                            )

                        except Exception as e:

                            st.error(
                                "Unable to read GIS library: "
                                f"{e}"
                            )

                    # =================================================
                    # 8. FILTER MAIN DATA
                    # =================================================

                    filtered_gdf = gdf[
                        gdf["_map_class"].isin(
                            selected_classes
                        )
                    ].copy()

                    # Remove NULL geometries

                    filtered_gdf = filtered_gdf[
                        filtered_gdf.geometry.notnull()
                    ]

                    # Remove empty geometries

                    filtered_gdf = filtered_gdf[
                        ~filtered_gdf.geometry.is_empty
                    ]

                    # =================================================
                    # 9. SIMPLIFY MAIN GEOMETRY
                    #
                    # Improves browser performance.
                    # =================================================

                    if not filtered_gdf.empty:

                        filtered_gdf["geometry"] = (
                            filtered_gdf.geometry.simplify(
                                tolerance=0.00002,
                                preserve_topology=True
                            )
                        )

                    # =================================================
                    # 10. CREATE MAP
                    # =================================================

                    m = folium.Map(
                        location=[
                            51.9244,
                            4.4777
                        ],
                        zoom_start=11,
                        tiles=None,
                        control_scale=True,
                        prefer_canvas=True
                    )

                    # =================================================
                    # 11. ESRI STREET
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

                        control=True,

                        show=(
                            basemap == "Esri Street"
                        )

                    ).add_to(m)

                    # =================================================
                    # 12. ESRI SATELLITE
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

                        control=True,

                        show=(
                            basemap == "Esri Satellite"
                        )

                    ).add_to(m)

                    # =================================================
                    # 13. TRANSPORTATION OVERLAY
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

                        control=True,

                        show=show_transportation,

                        opacity=0.9

                    ).add_to(m)

                    # =================================================
                    # 14. COLORS FOR MAIN CLASSIFICATION
                    # =================================================

                    classification_colors = [
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
                        "#d62728",
                        "#9467bd"
                    ]

                    # =================================================
                    # 15. DRAW MAIN CLASSIFICATION LAYERS
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

                        class_color = (
                            classification_colors[
                                class_index
                                % len(
                                    classification_colors
                                )
                            ]
                        )

                        # ---------------------------------------------
                        # Feature Group
                        # ---------------------------------------------

                        classification_group = (
                            folium.FeatureGroup(
                                name=(
                                    f"{classification_column}: "
                                    f"{class_value}"
                                ),
                                show=True
                            )
                        )

                        # ---------------------------------------------
                        # Popup fields
                        # ---------------------------------------------

                        popup_fields = [
                            col
                            for col in attribute_columns
                            if col in class_gdf.columns
                        ]

                        popup_aliases = [
                            f"{col}:"
                            for col in popup_fields
                        ]

                        # ---------------------------------------------
                        # GeoJSON
                        #
                        # No tooltip.
                        # Nothing appears when hovering.
                        # ---------------------------------------------

                        classification_geojson = (
                            folium.GeoJson(

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
                        )

                        # ---------------------------------------------
                        # Click popup
                        # ---------------------------------------------

                        if popup_fields:

                            classification_popup = (
                                folium.GeoJsonPopup(

                                    fields=popup_fields,

                                    aliases=popup_aliases,

                                    localize=True,

                                    labels=True,

                                    sticky=False,

                                    max_width=450,

                                    style=(
                                        "background-color:white;"
                                        "font-size:12px;"
                                        "padding:5px;"
                                        "max-height:300px;"
                                        "overflow-y:auto;"
                                    ),

                                    popup_options={
                                        "autoPan": False,
                                        "keepInView": False
                                    }
                                )
                            )

                            classification_popup.add_to(
                                classification_geojson
                            )

                        classification_geojson.add_to(
                            classification_group
                        )

                        classification_group.add_to(m)

                    # =================================================
                    # 16. ADDITIONAL GIS LAYER COLORS
                    # =================================================

                    library_colors = [
                        "#00BCD4",
                        "#FF5722",
                        "#8BC34A",
                        "#FFC107",
                        "#9C27B0",
                        "#03A9F4",
                        "#795548",
                        "#E91E63",
                        "#607D8B",
                        "#CDDC39",
                        "#009688",
                        "#673AB7"
                    ]

                    # =================================================
                    # 17. LOAD + DRAW SELECTED LIBRARY LAYERS
                    # =================================================

                    if (
                        library_gpkg is not None
                        and selected_library_layers
                    ):

                        for (
                            library_index,
                            layer_name
                        ) in enumerate(
                            selected_library_layers
                        ):

                            try:

                                # =====================================
                                # Load selected internal GPKG layer
                                # =====================================

                                lib_gdf = (
                                    load_library_layer(
                                        library_gpkg,
                                        layer_name
                                    )
                                ).copy()

                                if lib_gdf.empty:
                                    continue

                                # =====================================
                                # Remove invalid geometries
                                # =====================================

                                lib_gdf = lib_gdf[
                                    lib_gdf.geometry.notnull()
                                ]

                                lib_gdf = lib_gdf[
                                    ~lib_gdf.geometry.is_empty
                                ]

                                if lib_gdf.empty:
                                    continue

                                # =====================================
                                # Simplify geometry
                                # =====================================

                                lib_gdf["geometry"] = (
                                    lib_gdf.geometry.simplify(
                                        tolerance=0.00002,
                                        preserve_topology=True
                                    )
                                )

                                # =====================================
                                # Layer color
                                # =====================================

                                library_color = (
                                    library_colors[
                                        library_index
                                        % len(library_colors)
                                    ]
                                )

                                # =====================================
                                # Feature group
                                # =====================================

                                library_group = (
                                    folium.FeatureGroup(
                                        name=(
                                            f"GIS: {layer_name}"
                                        ),
                                        show=True
                                    )
                                )

                                # =====================================
                                # Popup fields
                                # =====================================

                                lib_geometry_column = (
                                    lib_gdf.geometry.name
                                )

                                lib_popup_fields = [
                                    col
                                    for col in lib_gdf.columns
                                    if col
                                    != lib_geometry_column
                                ]

                                lib_popup_aliases = [
                                    f"{col}:"
                                    for col
                                    in lib_popup_fields
                                ]

                                # =====================================
                                # GeoJSON
                                # =====================================

                                library_geojson = (
                                    folium.GeoJson(

                                        data=lib_gdf.to_json(),

                                        name=layer_name,

                                        style_function=(
                                            lambda feature,
                                            color=library_color: {

                                                "color": color,

                                                "fillColor": color,

                                                "weight": 2,

                                                "opacity": 0.95,

                                                "fillOpacity": 0.30
                                            }
                                        ),

                                        highlight_function=(
                                            lambda feature: {

                                                "weight": 4,

                                                "fillOpacity": 0.55
                                            }
                                        )
                                    )
                                )

                                # =====================================
                                # CLICK POPUP
                                # =====================================

                                if lib_popup_fields:

                                    library_popup = (
                                        folium.GeoJsonPopup(

                                            fields=(
                                                lib_popup_fields
                                            ),

                                            aliases=(
                                                lib_popup_aliases
                                            ),

                                            localize=True,

                                            labels=True,

                                            sticky=False,

                                            max_width=450,

                                            style=(
                                                "background-color:"
                                                "white;"
                                                "font-size:12px;"
                                                "padding:5px;"
                                                "max-height:300px;"
                                                "overflow-y:auto;"
                                            ),

                                            popup_options={
                                                "autoPan": False,
                                                "keepInView": False
                                            }
                                        )
                                    )

                                    library_popup.add_to(
                                        library_geojson
                                    )

                                # =====================================
                                # Add layer to map
                                # =====================================

                                library_geojson.add_to(
                                    library_group
                                )

                                library_group.add_to(m)

                            except Exception as e:

                                st.warning(
                                    f"Could not load GIS layer "
                                    f"'{layer_name}': {e}"
                                )

                    # =================================================
                    # 18. AUTO ZOOM
                    #
                    # Zoom is based on MAIN classification dataset.
                    # This prevents an additional GIS layer with a
                    # large extent from unexpectedly zooming the map.
                    # =================================================

                    if not filtered_gdf.empty:

                        try:

                            (
                                minx,
                                miny,
                                maxx,
                                maxy

                            ) = filtered_gdf.total_bounds

                            if (
                                -180 <= minx <= 180
                                and
                                -180 <= maxx <= 180
                                and
                                -90 <= miny <= 90
                                and
                                -90 <= maxy <= 90
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
                    # 19. LAYER CONTROL
                    # =================================================

                    folium.LayerControl(
                        collapsed=True,
                        position="topright"
                    ).add_to(m)

                    # =================================================
                    # 20. DISPLAY MAP
                    #
                    # returned_objects=[] reduces unnecessary
                    # Streamlit map events/reruns.
                    # =================================================

                    st_folium(
                        m,
                        height=750,
                        use_container_width=True,
                        key="living_lab_interactive_map",
                        returned_objects=[]
                    )

                    # =================================================
                    # 21. MAP SUMMARY
                    # =================================================

                    summary_col1, summary_col2 = (
                        st.columns(2)
                    )

                    with summary_col1:

                        st.metric(
                            "Classification features",
                            f"{len(filtered_gdf):,}"
                        )

                    with summary_col2:

                        st.metric(
                            "Additional GIS layers",
                            len(
                                selected_library_layers
                            )
                        )

                    st.caption(
                        "Click a spatial object to view its "
                        "attribute information."
                    )

        except Exception as e:

            st.error(
                f"Error loading map data: {e}"
            )