import os
import glob
import json
import html
import re

import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
import pyogrio

from shapely.ops import unary_union
from branca.element import MacroElement, Element
from jinja2 import Template
from streamlit_folium import st_folium


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Living Lab",
    page_icon="🌍",
    layout="wide"
)


# ============================================================
# 2. PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
LIB_DIR = os.path.join(BASE_DIR, "lib_gpkg")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATABI_DIR = os.path.join(BASE_DIR, "databi")


# ============================================================
# 3. PERFORMANCE AND DISPLAY SETTINGS
# ============================================================

MAP_SIMPLIFY_TOLERANCE = 0.00005

LABEL_OVERFLOW = 0.30

LABEL_WIDTH = 160
MIN_REGION_WIDTH = 80
MIN_LABEL_ZOOM = 10
LABEL_SPACING = 4

LABEL_SAMPLE_COUNT = 5

LABEL_REFRESH_DELAY = 120

# Popup configuration

POPUP_MAX_HEIGHT = 350
POPUP_MAX_WIDTH = 750


# ============================================================
# 4. DATA HELPERS
# ============================================================

def normalize_key(value):

    if pd.isna(value):
        return ""

    return re.sub(
        r"\s+",
        "",
        str(value)
    ).upper()


def parse_number(value):

    if value is None or pd.isna(value):
        return None

    value = str(value).strip()

    value = value.replace(" ", "").replace("\u00a0", "")

    if not value:
        return None

    if "," in value and "." in value:

        if value.rfind(",") > value.rfind("."):

            value = value.replace(".", "").replace(",", ".")

        else:

            value = value.replace(",", "")

    elif "," in value:

        value = value.replace(",", ".")

    try:

        result = float(value)

        return result if pd.notna(result) else None

    except ValueError:

        return None


def file_version(path):

    return os.path.getmtime(path)


# ============================================================
# 5. CACHED DATA LOADING
# ============================================================

@st.cache_data(show_spinner=False)
def load_gpkg(path, version, layer=None):

    if layer is None:

        gdf = gpd.read_file(path)

    else:

        gdf = gpd.read_file(
            path,
            layer=layer
        )

    if gdf.crs is not None:

        gdf = gdf.to_crs(epsg=4326)

    return gdf


@st.cache_data(show_spinner=False)
def load_csv(path, version):

    for encoding in ["utf-8-sig", "cp1252"]:

        try:

            return pd.read_csv(
                path,
                sep=None,
                engine="python",
                dtype=str,
                encoding=encoding
            )

        except UnicodeDecodeError:

            continue

    raise ValueError("Unable to decode CSV.")


@st.cache_data(show_spinner=False)
def list_gpkg_layers(path, version):

    return pyogrio.list_layers(path)[:, 0].tolist()


# ============================================================
# 6. CACHED GEOMETRY PROCESSING
# ============================================================

@st.cache_data(show_spinner=False)
def prepare_main_data(path, version):

    gdf = load_gpkg(path, version).copy()

    if gdf.empty:
        return gdf, None, []

    geometry_column = gdf.geometry.name

    attribute_columns = [
        c for c in gdf.columns
        if c != geometry_column
    ]

    if not attribute_columns:
        return gdf, None, []

    classification_column = attribute_columns[-1]

    gdf["_map_class"] = (
        gdf[classification_column]
        .fillna("No Data")
        .astype(str)
        .str.strip()
    )

    gdf = gdf.loc[
        gdf.geometry.notna()
        & ~gdf.geometry.is_empty
    ].copy()

    return gdf, classification_column, attribute_columns


@st.cache_data(show_spinner=False)
def prepare_display_geojson(path, version, tolerance):

    gdf, classification_column, attributes = prepare_main_data(
        path,
        version
    )

    if gdf.empty:
        return {}, []

    result = {}

    for class_name, group in gdf.groupby("_map_class"):

        display = group.copy()

        display["geometry"] = display.geometry.simplify(
            tolerance=tolerance,
            preserve_topology=True
        )

        display = display[
            attributes + ["geometry"]
        ].copy()

        result[str(class_name)] = json.loads(
            display.to_json()
        )

    return result, attributes


# ============================================================
# 7. CACHED POSTCODE GROUPS
# ============================================================

@st.cache_data(show_spinner=False)
def prepare_postcode_groups(path, version):

    gdf, _, _ = prepare_main_data(path, version)

    required = [
        "meest_voorkomende_postcode",
        "buurtnaam",
        "_map_class"
    ]

    if any(c not in gdf.columns for c in required):
        return {}

    data = gdf[
        required + ["geometry"]
    ].copy()

    data["_postcode"] = (
        data["meest_voorkomende_postcode"]
        .map(normalize_key)
    )

    data = data.loc[
        data["_postcode"] != ""
    ].copy()

    results = {}

    for postcode, group in data.groupby("_postcode"):

        geometries = [
            geom
            for geom in group.geometry
            if geom is not None and not geom.is_empty
        ]

        if not geometries:
            continue

        try:

            combined = unary_union(geometries)

        except Exception:

            continue

        if combined.is_empty:
            continue

        if combined.geom_type not in [
            "Polygon",
            "MultiPolygon"
        ]:
            continue

        anchor = combined.representative_point()

        names = (
            group["buurtnaam"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        names = [
            name
            for name in dict.fromkeys(names)
            if name
        ]

        classes = (
            group["_map_class"]
            .astype(str)
            .unique()
            .tolist()
        )

        simplified = combined.simplify(
            0.00003,
            preserve_topology=True
        )

        results[postcode] = {

            "name": " + ".join(names) or "Unnamed area",

            "classes": classes,

            "anchor": [
                anchor.x,
                anchor.y
            ],

            "geometry": simplified.__geo_interface__

        }

    return results


# ============================================================
# 8. SCROLLABLE GIS POPUPS
#
# Applies to:
# - Classification Data
# - Additional GIS Layers
#
# Popup height is limited.
# A vertical scrollbar appears when needed.
# ============================================================

def add_scrollable_popup(geojson_layer, fields):

    if not fields:
        return

    popup = folium.GeoJsonPopup(
        fields=fields,
        aliases=[
            f"{field}:"
            for field in fields
        ],
        labels=True,
        localize=True,
        min_width=600,
        max_width=POPUP_MAX_WIDTH,
        style=(
            "font-size:12px;"
            "line-height:1.4;"
            "white-space:normal;"
            "word-break:break-word;"
        )
    )

    popup.add_to(geojson_layer)


def add_popup_css(folium_map):

    popup_css = f"""
    <style>

    /* ================================================
       POPUP CONTENT
       ================================================ */

    .leaflet-popup-content {{

        max-height: {POPUP_MAX_HEIGHT}px !important;

        max-width: {POPUP_MAX_WIDTH - 30}px !important;

        overflow-y: auto !important;

        overflow-x: auto !important;

        margin: 12px 14px !important;

        padding-right: 6px;

        box-sizing: border-box;

        scrollbar-width: thin;

        scrollbar-color: #aab7c4 #f1f3f5;

    }}


    /* ================================================
       POPUP WRAPPER
       ================================================ */

    .leaflet-popup-content-wrapper {{

        max-width: {POPUP_MAX_WIDTH}px !important;

        border-radius: 8px;

        box-shadow: 0 3px 12px rgba(0,0,0,0.18);

    }}


    /* ================================================
       POPUP TABLE
       ================================================ */

    .leaflet-popup-content table {{

        width: 100%;

        border-collapse: collapse;

        font-size: 12px;

        line-height: 1.4;

    }}


    .leaflet-popup-content th,
    .leaflet-popup-content td {{

        padding: 6px 8px;

        border-bottom: 1px solid #e5e7eb;

        vertical-align: top;

        text-align: left;

        white-space: normal;

        overflow-wrap: anywhere;

        word-break: break-word;

    }}


    .leaflet-popup-content th {{

        font-weight: 600;

        background-color: #f8fafc;

    }}


    .leaflet-popup-content tr:nth-child(even) {{

        background-color: #fafbfc;

    }}


    /* ================================================
       WEBKIT SCROLLBAR
       ================================================ */

    .leaflet-popup-content::-webkit-scrollbar {{

        width: 7px;

        height: 7px;

    }}


    .leaflet-popup-content::-webkit-scrollbar-track {{

        background: #f1f3f5;

        border-radius: 4px;

    }}


    .leaflet-popup-content::-webkit-scrollbar-thumb {{

        background: #aab7c4;

        border-radius: 4px;

    }}


    .leaflet-popup-content::-webkit-scrollbar-thumb:hover {{

        background: #7d8b99;

    }}

    </style>
    """

    folium_map.get_root().header.add_child(
        Element(popup_css)
    )


# ============================================================
# 9. RESPONSIVE SHIPMENT CHARTS
# ============================================================

class ResponsiveShipmentCharts(MacroElement):

    def __init__(
        self,
        features,
        selected_columns,
        column_names,
        maxima,
        class_refs
    ):

        super().__init__()

        self._name = "ResponsiveShipmentCharts"

        self.features_json = json.dumps(
            features,
            ensure_ascii=False
        ).replace("</", "<\\/")

        self.selected_json = json.dumps(selected_columns)

        self.names_json = json.dumps(
            column_names,
            ensure_ascii=False
        ).replace("</", "<\\/")

        self.maxima_json = json.dumps(maxima)

        self.class_refs = class_refs

        self.overflow = LABEL_OVERFLOW
        self.width = LABEL_WIDTH
        self.min_width = MIN_REGION_WIDTH
        self.min_zoom = MIN_LABEL_ZOOM
        self.spacing = LABEL_SPACING
        self.samples = LABEL_SAMPLE_COUNT
        self.delay = LABEL_REFRESH_DELAY

        self._template = Template(r"""

{% macro script(this, kwargs) %}

(function() {

    const map = {{ this._parent.get_name() }};

    const features = {{ this.features_json | safe }};
    const selected = {{ this.selected_json | safe }};
    const names = {{ this.names_json | safe }};
    const maxima = {{ this.maxima_json | safe }};

    const classLayers = {
        {{ this.class_refs | safe }}
    };

    const overflow = {{ this.overflow }};
    const labelWidth = {{ this.width }};
    const minWidth = {{ this.min_width }};
    const minZoom = {{ this.min_zoom }};
    const spacing = {{ this.spacing }};
    const samples = {{ this.samples }};
    const delay = {{ this.delay }};

    const root = map.getContainer();

    root.style.position = "relative";

    const holder = document.createElement("div");

    holder.style.cssText =
        "position:absolute;" +
        "inset:0;" +
        "z-index:450;" +
        "pointer-events:none;" +
        "overflow:hidden;";

    root.appendChild(holder);


    // ========================================================
    // HELPERS
    // ========================================================

    function escapeHTML(value) {

        return String(value ?? "").replace(
            /[&<>"']/g,
            c => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[c])
        );

    }


    function formatNumber(value) {

        if (
            value === null ||
            value === undefined ||
            !Number.isFinite(Number(value))
        ) {
            return "—";
        }

        return Number(value).toLocaleString(
            undefined,
            {maximumFractionDigits: 2}
        );

    }


    function project(coordinate) {

        return map.latLngToContainerPoint([
            coordinate[1],
            coordinate[0]
        ]);

    }


    function polygonsOf(geometry) {

        if (!geometry) return [];

        if (geometry.type === "Polygon") {
            return [geometry.coordinates];
        }

        if (geometry.type === "MultiPolygon") {
            return geometry.coordinates;
        }

        return [];

    }


    // ========================================================
    // POINT IN POLYGON
    // ========================================================

    function pointInRing(point, ring) {

        let inside = false;

        for (
            let i = 0, j = ring.length - 1;
            i < ring.length;
            j = i++
        ) {

            const a = ring[i];
            const b = ring[j];

            if (
                ((a.y > point.y) !== (b.y > point.y)) &&
                (
                    point.x <
                    (b.x - a.x) *
                    (point.y - a.y) /
                    (b.y - a.y) + a.x
                )
            ) {
                inside = !inside;
            }

        }

        return inside;

    }


    function pointInPolygon(point, rings) {

        if (!rings.length) return false;

        if (!pointInRing(point, rings[0])) {
            return false;
        }

        for (let i = 1; i < rings.length; i++) {

            if (pointInRing(point, rings[i])) {
                return false;
            }

        }

        return true;

    }


    function pointInGeometry(point, projectedPolygons) {

        for (const polygon of projectedPolygons) {

            if (pointInPolygon(point, polygon)) {
                return true;
            }

        }

        return false;

    }


    // ========================================================
    // PROJECT GEOMETRY ONCE PER UPDATE
    // ========================================================

    function projectGeometry(geometry) {

        return polygonsOf(geometry).map(
            polygon => polygon.map(
                ring => ring.map(project)
            )
        );

    }


    // ========================================================
    // REGION BOUNDS
    // ========================================================

    function geometryBounds(projectedPolygons) {

        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        for (const polygon of projectedPolygons) {

            for (const ring of polygon) {

                for (const p of ring) {

                    minX = Math.min(minX, p.x);
                    minY = Math.min(minY, p.y);

                    maxX = Math.max(maxX, p.x);
                    maxY = Math.max(maxY, p.y);

                }

            }

        }

        return {
            minX,
            minY,
            maxX,
            maxY,
            width: maxX - minX,
            height: maxY - minY
        };

    }


    // ========================================================
    // LABEL FIT CHECK
    // ========================================================

    function fits(rect, projectedPolygons) {

        let inside = 0;
        let total = 0;

        for (let i = 0; i < samples; i++) {

            for (let j = 0; j < samples; j++) {

                const point = {

                    x:
                        rect.left +
                        rect.width *
                        (i + 0.5) / samples,

                    y:
                        rect.top +
                        rect.height *
                        (j + 0.5) / samples

                };

                total++;

                if (
                    pointInGeometry(
                        point,
                        projectedPolygons
                    )
                ) {
                    inside++;
                }

            }

        }

        return inside / total >= 1 - overflow;

    }


    // ========================================================
    // OVERLAP CHECK
    // ========================================================

    function overlaps(a, b) {

        return !(
            a.left + a.width + spacing <= b.left ||
            b.left + b.width + spacing <= a.left ||
            a.top + a.height + spacing <= b.top ||
            b.top + b.height + spacing <= a.top
        );

    }


    // ========================================================
    // CLASSIFICATION VISIBILITY
    // ========================================================

    function isVisible(classes) {

        return classes.some(
            className => {

                const layer = classLayers[String(className)];

                return layer && map.hasLayer(layer);

            }
        );

    }


    // ========================================================
    // CREATE CHART HTML
    // ========================================================

    function chartHTML(feature) {

        const colors = [
            "#2684ff",
            "#00a884",
            "#f08b32"
        ];

        let content =
            '<div style="' +
            'font-weight:700;' +
            'font-size:11px;' +
            'overflow-wrap:anywhere;' +
            'margin-bottom:5px;">' +
            escapeHTML(feature.name) +
            '</div>';

        for (const index of selected) {

            const value = feature.values[index];

            let ratio = 0;

            if (
                value !== null &&
                Number.isFinite(Number(value))
            ) {

                ratio = Math.max(
                    0,
                    Math.min(
                        100,
                        100 * Number(value) /
                        (maxima[index] || 1)
                    )
                );

            }

            content +=
                '<div style="margin-top:4px;">' +

                '<div style="' +
                'font-size:10px;' +
                'overflow-wrap:anywhere;">' +

                escapeHTML(names[index]) +

                ': <b>' +

                formatNumber(value) +

                '</b></div>' +

                '<div style="' +
                'height:6px;' +
                'background:#e6eaf0;' +
                'border-radius:3px;' +
                'overflow:hidden;' +
                'margin-top:2px;">' +

                '<div style="' +
                'height:100%;' +
                'width:' + ratio + '%;' +
                'background:' + colors[index] + ';">' +

                '</div></div></div>';

        }

        return content;

    }


    // ========================================================
    // CANDIDATE POSITIONS
    // ========================================================

    function candidatePositions(feature, bounds) {

        const anchor = project(feature.anchor);

        const positions = [anchor];

        const fractions = [0.3, 0.5, 0.7];

        for (const fy of fractions) {

            for (const fx of fractions) {

                positions.push({

                    x:
                        bounds.minX +
                        bounds.width * fx,

                    y:
                        bounds.minY +
                        bounds.height * fy

                });

            }

        }

        return positions;

    }


    // ========================================================
    // DRAW CHARTS
    // ========================================================

    function draw() {

        holder.replaceChildren();

        if (!selected.length) return;

        if (map.getZoom() < minZoom) return;

        const size = map.getSize();

        const occupied = [];

        const visibleFeatures = [];


        // ====================================================
        // PRE-FILTER VISIBLE REGIONS
        // ====================================================

        for (const feature of features) {

            if (!isVisible(feature.classes)) {
                continue;
            }

            const projected = projectGeometry(
                feature.geometry
            );

            const bounds = geometryBounds(projected);

            if (bounds.width < minWidth) {
                continue;
            }

            if (
                bounds.maxX < 0 ||
                bounds.minX > size.x ||
                bounds.maxY < 0 ||
                bounds.minY > size.y
            ) {
                continue;
            }

            visibleFeatures.push({
                feature,
                projected,
                bounds,
                area: bounds.width * bounds.height
            });

        }


        visibleFeatures.sort(
            (a, b) => b.area - a.area
        );


        // ====================================================
        // PLACE CHARTS
        // ====================================================

        for (const item of visibleFeatures) {

            const feature = item.feature;

            const label = document.createElement("div");

            label.style.cssText =
                "position:absolute;" +
                "box-sizing:border-box;" +
                "width:" + labelWidth + "px;" +
                "padding:5px 7px;" +
                "border:1px solid #b7c5d3;" +
                "border-radius:5px;" +
                "background:rgba(255,255,255,.94);" +
                "color:#172b4d;" +
                "font:10px/1.3 Arial,sans-serif;" +
                "box-shadow:0 1px 3px rgba(0,0,0,.14);";

            label.innerHTML = chartHTML(feature);

            label.style.left = "-9999px";
            label.style.top = "-9999px";

            holder.appendChild(label);

            const width = label.offsetWidth;
            const height = label.offsetHeight;

            const positions = candidatePositions(
                feature,
                item.bounds
            );

            let placed = false;

            for (const position of positions) {

                const rect = {

                    left: position.x - width / 2,
                    top: position.y - height / 2,
                    width,
                    height

                };

                if (
                    rect.left < 0 ||
                    rect.top < 0 ||
                    rect.left + width > size.x ||
                    rect.top + height > size.y
                ) {
                    continue;
                }

                if (
                    !fits(
                        rect,
                        item.projected
                    )
                ) {
                    continue;
                }

                if (
                    occupied.some(
                        existing => overlaps(rect, existing)
                    )
                ) {
                    continue;
                }

                label.style.left = rect.left + "px";
                label.style.top = rect.top + "px";

                occupied.push(rect);

                placed = true;

                break;

            }

            if (!placed) {
                label.remove();
            }

        }

    }


    // ========================================================
    // UPDATE ON ZOOM / PAN / LAYER CHANGES
    // ========================================================

    let timer = null;

    function refresh() {

        clearTimeout(timer);

        timer = setTimeout(draw, delay);

    }

    map.on(
        "zoomend moveend resize overlayadd overlayremove",
        refresh
    );

    map.whenReady(refresh);

})();

{% endmacro %}

""")


# ============================================================
# 10. MAIN APPLICATION
# ============================================================

st.title("Living Lab")

st.caption("Rotterdam University of Applied Sciences")

tab_intro, tab_powerbi, tab_map = st.tabs([
    "1. Introduction",
    "2. Power BI",
    "3. Interactive Map"
])


# ============================================================
# TAB 1 — INTRODUCTION
# ============================================================

with tab_intro:

    st.header("Living Lab")

    image_path = os.path.join(
        ASSETS_DIR,
        "rotterdam_university.jpg"
    )

    if os.path.exists(image_path):

        st.image(
            image_path,
            use_container_width=True
        )

    st.subheader("About the Living Lab")

    st.write(
        """
        The Living Lab provides an interactive environment
        for exploring, analysing and visualising urban
        logistics data.

        The platform integrates geospatial information,
        interactive maps and business intelligence dashboards
        to support data-driven analysis and decision-making.

        This application is developed in the context of
        Rotterdam University of Applied Sciences.
        """
    )

    st.subheader("Application Structure")

    st.markdown(
        """
        **Introduction:** General information about the Living Lab.

        **Power BI:** Interactive dashboards and analytical results.

        **Interactive Map:** Spatial visualisation of
        GeoPackage and shipment data.
        """
    )


# ============================================================
# TAB 2 — POWER BI
# ============================================================

with tab_powerbi:

    st.header("Power BI Dashboard")

    POWERBI_URL = ""

    if POWERBI_URL:

        st.components.v1.iframe(
            POWERBI_URL,
            height=800,
            scrolling=True
        )

    else:

        st.info(
            "Power BI dashboard has not been configured yet."
        )


# ============================================================
# TAB 3 — INTERACTIVE MAP
# ============================================================

with tab_map:

    st.header("Interactive Urban Logistics Map")


    # ========================================================
    # MAIN GPKG
    # ========================================================

    st.subheader("Classification Data")

    gpkg_files = sorted(
        glob.glob(
            os.path.join(DATA_DIR, "*.gpkg")
        )
    )

    if not gpkg_files:

        st.warning("No GPKG file found in /data.")

        st.stop()

    main_path = st.selectbox(
        "Select classification dataset",
        gpkg_files,
        format_func=os.path.basename
    )

    main_version = file_version(main_path)


    # ========================================================
    # LOAD PREPARED DATA
    # ========================================================

    with st.spinner("Loading classification data..."):

        gdf, class_column, popup_columns = prepare_main_data(
            main_path,
            main_version
        )

    if gdf.empty or class_column is None:

        st.error("Classification dataset is empty or invalid.")

        st.stop()

    class_values = sorted(
        gdf["_map_class"].unique().tolist()
    )


    # ========================================================
    # CONTROLS
    # ========================================================

    col1, col2 = st.columns([2, 1])

    with col1:

        selected_classes = st.multiselect(
            f"Select classification layers ({class_column})",
            class_values,
            default=class_values
        )

    with col2:

        basemap = st.selectbox(
            "Basemap",
            [
                "Esri Street",
                "Esri Satellite"
            ]
        )

    show_transport = st.checkbox(
        "Show transportation network",
        value=False
    )


    # ========================================================
    # SHIPMENT DATA
    #
    # Automatically loads the first CSV in /data.
    #
    # All three indicators are enabled by default.
    # ========================================================

    st.divider()

    st.subheader("Shipment Data")

    csv_files = sorted(
        glob.glob(
            os.path.join(DATA_DIR, "*.csv")
        )
    )

    csv_df = None
    csv_fields = []
    csv_lookup = {}
    selected_indicators = []

    if not csv_files:

        st.info("No CSV file found in /data.")

    else:

        csv_path = csv_files[0]

        try:

            csv_df = load_csv(
                csv_path,
                file_version(csv_path)
            ).copy()

            if csv_df.shape[1] < 4:

                st.warning(
                    "Shipment CSV must contain at least four columns."
                )

                csv_df = None

            elif (
                "meest_voorkomende_postcode" not in gdf.columns
                or "buurtnaam" not in gdf.columns
            ):

                st.warning(
                    "Main GPKG must contain "
                    "'meest_voorkomende_postcode' and 'buurtnaam'."
                )

                csv_df = None

            else:

                csv_fields = list(csv_df.columns[:4])

                indicator_cols = st.columns(3)

                for i, name in enumerate(csv_fields[1:4]):

                    with indicator_cols[i]:

                        # All indicators enabled by default.

                        if st.checkbox(
                            str(name),
                            value=True,
                            key=f"shipment_indicator_{i}"
                        ):

                            selected_indicators.append(i)

                csv_df["_postcode"] = (
                    csv_df.iloc[:, 0]
                    .map(normalize_key)
                )

                csv_df = csv_df.loc[
                    csv_df["_postcode"] != ""
                ]

                csv_df = csv_df.drop_duplicates(
                    "_postcode",
                    keep="first"
                )

                for _, row in csv_df.iterrows():

                    csv_lookup[row["_postcode"]] = [
                        parse_number(row[csv_fields[1]]),
                        parse_number(row[csv_fields[2]]),
                        parse_number(row[csv_fields[3]])
                    ]

        except Exception as exc:

            st.warning(f"Unable to read shipment CSV: {exc}")

            csv_df = None


    # ========================================================
    # ADDITIONAL GIS LAYERS
    # ========================================================

    st.divider()

    st.subheader("Additional GIS Layers")

    lib_files = sorted(
        glob.glob(
            os.path.join(LIB_DIR, "*.gpkg")
        )
    )

    lib_path = lib_files[0] if lib_files else None

    selected_lib_layers = []

    if lib_path:

        try:

            lib_names = list_gpkg_layers(
                lib_path,
                file_version(lib_path)
            )

            selected_lib_layers = st.multiselect(
                "Select additional GIS layers",
                lib_names,
                default=[]
            )

        except Exception as exc:

            st.warning(f"GIS library error: {exc}")

    else:

        st.info("No additional GPKG found in /lib_gpkg.")


    # ========================================================
    # CREATE FOLIUM MAP
    # ========================================================

    m = folium.Map(
        location=[51.9244, 4.4777],
        zoom_start=11,
        tiles=None,
        control_scale=True,
        prefer_canvas=True
    )


    # ========================================================
    # ADD SCROLLABLE POPUP CSS
    # ========================================================

    add_popup_css(m)


    # ========================================================
    # ESRI BASEMAPS
    # ========================================================

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
        show=basemap == "Esri Street"
    ).add_to(m)

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
        show=basemap == "Esri Satellite"
    ).add_to(m)

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
        show=show_transport,
        opacity=0.9
    ).add_to(m)


    # ========================================================
    # CLASSIFICATION COLORS
    # ========================================================

    colors = [
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

    color_map = {
        value: colors[i % len(colors)]
        for i, value in enumerate(class_values)
    }


    # ========================================================
    # LOAD CACHED GEOJSON
    # ========================================================

    with st.spinner("Preparing map layers..."):

        class_geojson, popup_fields = prepare_display_geojson(
            main_path,
            main_version,
            MAP_SIMPLIFY_TOLERANCE
        )


    # ========================================================
    # DRAW CLASSIFICATION
    # ========================================================

    class_refs = {}

    for value in selected_classes:

        if value not in class_geojson:
            continue

        color = color_map[value]

        swatch = (
            f'<span style="display:inline-block;'
            f'width:12px;height:12px;'
            f'background:{color};'
            f'border:1px solid #777;'
            f'margin-right:6px;"></span>'
        )

        group = folium.FeatureGroup(
            name=swatch + html.escape(str(value)),
            show=True
        )

        geojson = folium.GeoJson(
            class_geojson[value],
            style_function=(
                lambda feature, c=color: {
                    "color": c,
                    "fillColor": c,
                    "weight": 1.5,
                    "opacity": 0.9,
                    "fillOpacity": 0.5
                }
            ),
            highlight_function=(
                lambda feature: {
                    "weight": 3,
                    "fillOpacity": 0.7
                }
            )
        )


        # ====================================================
        # SCROLLABLE CLASSIFICATION POPUP
        # ====================================================

        if popup_fields:

            add_scrollable_popup(
                geojson,
                popup_fields
            )

        geojson.add_to(group)

        group.add_to(m)

        class_refs[str(value)] = group.get_name()


    # ========================================================
    # ADDITIONAL GIS LAYERS
    # ========================================================

    lib_colors = [
        "#00BCD4",
        "#FF5722",
        "#8BC34A",
        "#FFC107",
        "#9C27B0",
        "#03A9F4",
        "#795548",
        "#E91E63"
    ]

    for i, layer_name in enumerate(selected_lib_layers):

        try:

            lib = load_gpkg(
                lib_path,
                file_version(lib_path),
                layer_name
            ).copy()

            lib = lib.loc[
                lib.geometry.notna()
                & ~lib.geometry.is_empty
            ].copy()

            if lib.empty:
                continue

            lib["geometry"] = lib.geometry.simplify(
                MAP_SIMPLIFY_TOLERANCE,
                preserve_topology=True
            )

            color = lib_colors[i % len(lib_colors)]

            swatch = (
                f'<span style="display:inline-block;'
                f'width:12px;height:12px;'
                f'background:{color};'
                f'border:1px solid #777;'
                f'margin-right:6px;"></span>'
            )

            group = folium.FeatureGroup(
                name=swatch + html.escape(layer_name),
                show=True
            )

            geojson = folium.GeoJson(
                lib.to_json(),
                style_function=(
                    lambda feature, c=color: {
                        "color": c,
                        "fillColor": c,
                        "weight": 2,
                        "opacity": 0.95,
                        "fillOpacity": 0.3
                    }
                )
            )

            fields = [
                c for c in lib.columns
                if c != lib.geometry.name
            ]


            # ================================================
            # SCROLLABLE ADDITIONAL GIS POPUP
            # ================================================

            if fields:

                add_scrollable_popup(
                    geojson,
                    fields
                )

            geojson.add_to(group)

            group.add_to(m)

        except Exception as exc:

            st.warning(
                f"Could not load layer '{layer_name}': {exc}"
            )


    # ========================================================
    # SHIPMENT CHARTS
    # ========================================================

    if csv_df is not None and selected_indicators:

        postcode_groups = prepare_postcode_groups(
            main_path,
            main_version
        )

        features = []

        maxima = [1.0, 1.0, 1.0]

        for values in csv_lookup.values():

            for i, value in enumerate(values):

                if value is not None:

                    maxima[i] = max(
                        maxima[i],
                        value
                    )

        selected_class_set = set(selected_classes)

        for postcode, region in postcode_groups.items():

            if postcode not in csv_lookup:
                continue

            if not (
                selected_class_set
                & set(region["classes"])
            ):
                continue

            features.append({

                "name": region["name"],

                "classes": region["classes"],

                "anchor": region["anchor"],

                "geometry": region["geometry"],

                "values": csv_lookup[postcode]

            })

        js_refs = ", ".join(
            f"{json.dumps(key)}: {value}"
            for key, value in class_refs.items()
        )

        if features:

            ResponsiveShipmentCharts(
                features=features,
                selected_columns=selected_indicators,
                column_names=csv_fields[1:4],
                maxima=maxima,
                class_refs=js_refs
            ).add_to(m)

        st.caption(
            f"Shipment data matched with "
            f"{len(features):,} postcode groups."
        )


    # ========================================================
    # INITIAL MAP BOUNDS
    # ========================================================

    filtered = gdf.loc[
        gdf["_map_class"].isin(selected_classes)
    ]

    if not filtered.empty:

        minx, miny, maxx, maxy = filtered.total_bounds

        if (
            -180 <= minx <= 180
            and -180 <= maxx <= 180
            and -90 <= miny <= 90
            and -90 <= maxy <= 90
        ):

            m.fit_bounds([
                [miny, minx],
                [maxy, maxx]
            ])


    # ========================================================
    # LAYER CONTROL
    # ========================================================

    folium.LayerControl(
        collapsed=False,
        position="topright"
    ).add_to(m)


    # ========================================================
    # DISPLAY MAP
    # ========================================================

    st_folium(
        m,
        height=750,
        use_container_width=True,
        key="living_lab_map",
        returned_objects=[]
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Classification features",
            f"{len(filtered):,}"
        )

    with col2:

        st.metric(
            "Additional GIS layers",
            len(selected_lib_layers)
        )