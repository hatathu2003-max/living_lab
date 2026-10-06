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
# FAST VERSION
#
# - Không hiển thị data khi hover
# - Click feature -> popup có scroll
# - Cache GPKG
# - Giảm dữ liệu đưa vào GeoJSON
# - Layer riêng cho từng class
# ============================================================

with tab_map:

    st.header("Interactive Urban Logistics Map")

    # ========================================================
    # 1. FIND GPKG FILES
    # ========================================================

    gpkg_files = glob.glob(
        os.path.join(DATA_DIR, "*.gpkg")
    )

    if not gpkg_files:

        st.warning(
            f"No GeoPackage (.gpkg) files were found in:\n\n"
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

        # ====================================================
        # 3. CACHE GPKG LOADING
        # ====================================================

        @st.cache_data(show_spinner="Loading GeoPackage...")
        def load_gpkg(path):

            gdf = gpd.read_file(path)

            return gdf

        try:

            gdf = load_gpkg(selected_gpkg)

            if gdf.empty:

                st.warning(
                    "The selected GeoPackage contains no data."
                )

            else:

                # =================================================
                # 4. CRS
                # =================================================

                if gdf.crs is None:

                    st.error(
                        "The selected GeoPackage does not contain "
                        "coordinate reference system (CRS) information."
                    )

                else:

                    # Folium = WGS84

                    if gdf.crs.to_epsg() != 4326:
                        gdf = gdf.to_crs(epsg=4326)

                    # =================================================
                    # 5. ATTRIBUTE COLUMNS
                    # =================================================

                    geometry_column = gdf.geometry.name

                    attribute_columns = [
                        column
                        for column in gdf.columns
                        if column != geometry_column
                    ]

                    if not attribute_columns:

                        st.error(
                            "No attribute columns were found "
                            "in the GeoPackage."
                        )

                    else:

                        # =================================================
                        # 6. LAST ATTRIBUTE COLUMN = CLASSIFICATION
                        # =================================================

                        classification_column = attribute_columns[-1]

                        st.info(
                            f"Classification field: "
                            f"**{classification_column}**"
                        )

                        # =================================================
                        # 7. CLEAN CLASS
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
                        # 8. CONTROLS
                        # =================================================

                        control_col1, control_col2 = st.columns(
                            [2, 1]
                        )

                        with control_col1:

                            selected_classes = st.multiselect(
                                "Select layers to display",
                                options=class_values,
                                default=class_values,
                                help=(
                                    "Each unique value of the last "
                                    "attribute column becomes a layer."
                                )
                            )

                        with control_col2:

                            basemap = st.selectbox(
                                "Basemap",
                                [
                                    "Esri Street",
                                    "Esri Satellite"
                                ]
                            )

                        # =================================================
                        # 9. TRANSPORTATION
                        # =================================================

                        show_transportation = st.checkbox(
                            "Show transportation network",
                            value=False
                        )

                        # =================================================
                        # 10. DATA INFORMATION
                        # =================================================

                        with st.expander(
                            "Dataset and layer information"
                        ):

                            st.write(
                                f"**Dataset:** "
                                f"{os.path.basename(selected_gpkg)}"
                            )

                            st.write(
                                f"**Classification field:** "
                                f"{classification_column}"
                            )

                            st.write(
                                f"**Total features:** "
                                f"{len(gdf):,}"
                            )

                            st.write(
                                f"**Number of classes:** "
                                f"{len(class_values)}"
                            )

                            layer_statistics = (
                                gdf["_map_class"]
                                .value_counts()
                                .rename_axis(
                                    classification_column
                                )
                                .reset_index(
                                    name="Number of features"
                                )
                            )

                            st.dataframe(
                                layer_statistics,
                                use_container_width=True,
                                hide_index=True
                            )

                        # =================================================
                        # 11. FILTER DATA BEFORE CREATING MAP
                        # =================================================

                        filtered_gdf = gdf[
                            gdf["_map_class"].isin(
                                selected_classes
                            )
                        ].copy()

                        # Remove null geometry

                        filtered_gdf = filtered_gdf[
                            filtered_gdf.geometry.notnull()
                        ]

                        # Remove empty geometry

                        filtered_gdf = filtered_gdf[
                            ~filtered_gdf.geometry.is_empty
                        ]

                        # =================================================
                        # 12. CREATE MAP
                        # =================================================

                        m = folium.Map(
                            location=[51.92, 4.48],
                            zoom_start=11,
                            tiles=None,
                            control_scale=True,
                            prefer_canvas=True
                        )

                        # =================================================
                        # 13. ESRI STREET
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
                        # 14. ESRI SATELLITE
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
                        # 15. TRANSPORTATION
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
                        # 16. COLORS
                        # =================================================

                        layer_colors = [
                            "#e41a1c",
                            "#377eb8",
                            "#4daf4a",
                            "#984ea3",
                            "#ff7f00",
                            "#ffff33",
                            "#a65628",
                            "#f781bf",
                            "#17becf",
                            "#bcbd22",
                            "#1f77b4",
                            "#d62728"
                        ]

                        # =================================================
                        # 17. CREATE CLASS LAYERS
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

                            # ---------------------------------------------
                            # COLOR
                            # ---------------------------------------------

                            class_color = layer_colors[
                                class_index
                                % len(layer_colors)
                            ]

                            # ---------------------------------------------
                            # FEATURE GROUP
                            # ---------------------------------------------

                            feature_group = folium.FeatureGroup(

                                name=(
                                    f"{classification_column}: "
                                    f"{class_value}"
                                ),

                                show=True
                            )

                            # =================================================
                            # 18. PREPARE POPUP DATA
                            #
                            # Không đưa geometry vào popup.
                            # Không dùng tooltip.
                            # =================================================

                            popup_fields = [
                                column
                                for column in attribute_columns
                                if column in class_gdf.columns
                            ]

                            # Chỉ giữ attribute columns + geometry

                            popup_gdf = class_gdf[
                                popup_fields + [geometry_column]
                            ].copy()

                            # =================================================
                            # 19. GEOJSON
                            # =================================================

                            geojson = folium.GeoJson(

                                popup_gdf,

                                name=str(class_value),

                                style_function=(
                                    lambda feature,
                                    color=class_color: {

                                        "color": color,

                                        "fillColor": color,

                                        "weight": 1.5,

                                        "opacity": 0.9,

                                        "fillOpacity": 0.55
                                    }
                                ),

                                highlight_function=(
                                    lambda feature: {

                                        "weight": 3,

                                        "fillOpacity": 0.75
                                    }
                                )

                            )

                            # =================================================
                            # 20. CLICK POPUP
                            #
                            # Hover = KHÔNG HIỆN DATA
                            #
                            # Click = Popup
                            # =================================================

                            popup = folium.GeoJsonPopup(

                                fields=popup_fields,

                                aliases=[
                                    f"{field}"
                                    for field in popup_fields
                                ],

                                localize=True,

                                labels=True,

                                sticky=False,

                                max_width=450,

                                max_height=350,

                                style=(
                                    """
                                    background-color: white;
                                    border-radius: 8px;
                                    padding: 10px;
                                    font-size: 13px;
                                    """
                                )
                            )

                            popup.add_to(geojson)

                            # Add GeoJSON to layer

                            geojson.add_to(feature_group)

                            # Add layer to map

                            feature_group.add_to(m)

                        # =================================================
                        # 21. AUTO ZOOM
                        # =================================================

                        if not filtered_gdf.empty:

                            try:

                                minx, miny, maxx, maxy = (
                                    filtered_gdf.total_bounds
                                )

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
                        # 22. LAYER CONTROL
                        # =================================================

                        folium.LayerControl(
                            collapsed=False,
                            position="topright"
                        ).add_to(m)

                        # =================================================
                        # 23. DISPLAY MAP
                        # =================================================

                        st_folium(

                            m,

                            height=750,

                            use_container_width=True,

                            key=(
                                "living_lab_interactive_map"
                            )

                        )

                        # =================================================
                        # 24. SUMMARY
                        # =================================================

                        if selected_classes:

                            st.caption(
                                f"Displaying "
                                f"{len(filtered_gdf):,} features "
                                f"across "
                                f"{len(selected_classes)} "
                                f"selected layer(s). "
                                f"Click a feature to view its data."
                            )

                        else:

                            st.warning(
                                "No classification layer selected. "
                                "Select at least one layer above."
                            )

        except Exception as e:

            st.error(
                f"Error loading GeoPackage: {e}"
            )