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


## ============================================================
# TAB 3 — INTERACTIVE MAP
# Living Lab - Rotterdam University of Applied Sciences
#
# Chức năng:
# 1. Tìm các file .gpkg trong thư mục /data
# 2. Cho người dùng chọn file GPKG
# 3. Tự động lấy CỘT ATTRIBUTE CUỐI CÙNG làm cột phân loại
# 4. Mỗi giá trị unique của cột cuối = một lớp dữ liệu
# 5. Cho phép chọn lớp muốn hiển thị
# 6. Mỗi lớp được hiển thị bằng màu khác nhau
# 7. Có Esri Street và Esri Satellite làm basemap
# 8. Có Esri Transportation làm overlay
# 9. Cho phép bật/tắt từng lớp trực tiếp trên bản đồ
# ============================================================

with tab_map:

    st.header("Interactive Urban Logistics Map")

    st.write(
        """
        Explore the spatial data used in the Living Lab.
        Select a GeoPackage dataset and choose the classification
        layers that you want to display.
        """
    )

    # ========================================================
    # 1. TÌM TẤT CẢ FILE GPKG TRONG /data
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
        # 2. CHỌN FILE GPKG
        # ====================================================

        selected_gpkg = st.selectbox(
            "Select GeoPackage dataset",
            options=gpkg_files,
            format_func=lambda x: os.path.basename(x)
        )

        try:

            # =================================================
            # 3. ĐỌC FILE GPKG
            # =================================================

            gdf = gpd.read_file(selected_gpkg)

            if gdf.empty:

                st.warning(
                    "The selected GeoPackage contains no data."
                )

            else:

                # =============================================
                # 4. KIỂM TRA CRS
                # =============================================

                if gdf.crs is None:

                    st.error(
                        "The selected GeoPackage does not contain "
                        "coordinate reference system (CRS) information."
                    )

                else:

                    # Folium sử dụng WGS84 / EPSG:4326

                    gdf = gdf.to_crs(epsg=4326)

                    # =========================================
                    # 5. XÁC ĐỊNH CỘT ATTRIBUTE CUỐI CÙNG
                    #
                    # Geometry KHÔNG được tính là data column.
                    #
                    # Ví dụ:
                    #
                    # name | population | cluster | geometry
                    #
                    # => classification column = cluster
                    # =========================================

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

                        # =====================================
                        # CỘT CUỐI = CỘT PHÂN LOẠI
                        # =====================================

                        classification_column = (
                            attribute_columns[-1]
                        )

                        st.info(
                            "Classification field: "
                            f"**{classification_column}**"
                        )

                        # =====================================
                        # 6. CLEAN CỘT PHÂN LOẠI
                        # =====================================

                        gdf["_map_class"] = (
                            gdf[classification_column]
                            .fillna("No Data")
                            .astype(str)
                            .str.strip()
                        )

                        # =====================================
                        # 7. LẤY TẤT CẢ CLASS
                        # =====================================

                        class_values = sorted(
                            gdf["_map_class"]
                            .unique()
                            .tolist()
                        )

                        # =====================================
                        # 8. LAYOUT CONTROL
                        # =====================================

                        control_col1, control_col2 = st.columns(
                            [2, 1]
                        )

                        # -------------------------------------
                        # Chọn classification layers
                        # -------------------------------------

                        with control_col1:

                            selected_classes = st.multiselect(
                                "Select layers to display",
                                options=class_values,
                                default=class_values,
                                help=(
                                    "Layers are automatically "
                                    "generated from the unique "
                                    "values of the last attribute "
                                    "column."
                                )
                            )

                        # -------------------------------------
                        # Chọn basemap
                        # -------------------------------------

                        with control_col2:

                            basemap = st.selectbox(
                                "Basemap",
                                [
                                    "Esri Street",
                                    "Esri Satellite"
                                ]
                            )

                        # =====================================
                        # 9. TRANSPORTATION OVERLAY
                        # =====================================

                        show_transportation = st.checkbox(
                            "Show transportation network",
                            value=False
                        )

                        # =====================================
                        # 10. HIỂN THỊ THỐNG KÊ LỚP
                        # =====================================

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

                            # Đếm feature của từng class

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

                        # =====================================
                        # 11. TẠO FOLIUM MAP
                        # =====================================

                        m = folium.Map(
                            location=[51.92, 4.48],
                            zoom_start=11,
                            tiles=None,
                            control_scale=True
                        )

                        # =====================================
                        # 12. ESRI STREET BASEMAP
                        # =====================================

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

                        # =====================================
                        # 13. ESRI SATELLITE BASEMAP
                        # =====================================

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

                        # =====================================
                        # 14. ESRI TRANSPORTATION OVERLAY
                        #
                        # Đây không phải basemap.
                        # Nó được đặt phía trên Street/Satellite.
                        # =====================================

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

                        # =====================================
                        # 15. MÀU CHO CLASSIFICATION LAYERS
                        # =====================================

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

                        # =====================================
                        # 16. LỌC THEO CLASS ĐƯỢC CHỌN
                        # =====================================

                        filtered_gdf = gdf[
                            gdf["_map_class"].isin(
                                selected_classes
                            )
                        ].copy()

                        # Bỏ geometry NULL

                        filtered_gdf = filtered_gdf[
                            filtered_gdf.geometry.notnull()
                        ]

                        # Bỏ geometry rỗng

                        filtered_gdf = filtered_gdf[
                            ~filtered_gdf.geometry.is_empty
                        ]

                        # =====================================
                        # 17. VẼ TỪNG CLASS
                        #
                        # Mỗi unique value của cột cuối
                        # là một FeatureGroup riêng biệt.
                        # =====================================

                        for class_index, class_value in enumerate(
                            selected_classes
                        ):

                            # ---------------------------------
                            # Lọc đúng class
                            # ---------------------------------

                            class_gdf = filtered_gdf[
                                filtered_gdf["_map_class"]
                                == class_value
                            ].copy()

                            if class_gdf.empty:
                                continue

                            # ---------------------------------
                            # Màu của class
                            # ---------------------------------

                            class_color = layer_colors[
                                class_index
                                % len(layer_colors)
                            ]

                            # ---------------------------------
                            # Tạo layer riêng
                            # ---------------------------------

                            feature_group = (
                                folium.FeatureGroup(
                                    name=(
                                        f"{classification_column}"
                                        f": {class_value}"
                                    ),
                                    show=True
                                )
                            )

                            # ---------------------------------
                            # Tooltip fields
                            #
                            # Không đưa temporary column
                            # _map_class vào tooltip.
                            # ---------------------------------

                            tooltip_fields = [
                                column
                                for column
                                in attribute_columns
                                if column in class_gdf.columns
                            ]

                            # ---------------------------------
                            # Convert GeoDataFrame -> GeoJSON
                            # ---------------------------------

                            geojson_data = (
                                class_gdf.to_json()
                            )

                            # ---------------------------------
                            # VẼ DATA
                            # ---------------------------------

                            folium.GeoJson(

                                data=geojson_data,

                                name=str(class_value),

                                style_function=(
                                    lambda feature,
                                    color=class_color: {

                                        "color": color,

                                        "fillColor": color,

                                        "weight": 2,

                                        "opacity": 0.9,

                                        "fillOpacity": 0.55
                                    }
                                ),

                                highlight_function=(
                                    lambda feature: {

                                        "weight": 4,

                                        "fillOpacity": 0.8
                                    }
                                ),

                                tooltip=(
                                    folium.GeoJsonTooltip(

                                        fields=tooltip_fields,

                                        aliases=[
                                            f"{field}:"
                                            for field
                                            in tooltip_fields
                                        ],

                                        sticky=False,

                                        localize=True
                                    )
                                )

                            ).add_to(feature_group)

                            # ---------------------------------
                            # Add class vào map
                            # ---------------------------------

                            feature_group.add_to(m)

                        # =====================================
                        # 18. AUTO ZOOM THEO DATA ĐƯỢC CHỌN
                        # =====================================

                        if not filtered_gdf.empty:

                            try:

                                (
                                    minx,
                                    miny,
                                    maxx,
                                    maxy

                                ) = filtered_gdf.total_bounds

                                # Kiểm tra bounds hợp lệ

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

                        # =====================================
                        # 19. LAYER CONTROL
                        #
                        # Góc phải map sẽ có:
                        #
                        # BASE LAYERS
                        # ○ Esri Street
                        # ○ Esri Satellite
                        #
                        # OVERLAYS
                        # ☐ Transportation
                        # ☑ Class 1
                        # ☑ Class 2
                        # ...
                        # =====================================

                        folium.LayerControl(
                            collapsed=False,
                            position="topright"
                        ).add_to(m)

                        # =====================================
                        # 20. HIỂN THỊ MAP
                        # =====================================

                        st_folium(
                            m,
                            height=750,
                            use_container_width=True,
                            key="living_lab_interactive_map"
                        )

                        # =====================================
                        # 21. MAP SUMMARY
                        # =====================================

                        if selected_classes:

                            st.caption(
                                f"Displaying "
                                f"{len(filtered_gdf):,} features "
                                f"across "
                                f"{len(selected_classes)} "
                                f"selected layer(s)."
                            )

                        else:

                            st.warning(
                                "No classification layer selected. "
                                "Select at least one layer above "
                                "to display spatial data."
                            )

        except Exception as e:

            st.error(
                f"Error loading GeoPackage: {e}"
            )