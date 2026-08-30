import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import re
import base64
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Dynamic Fare Optimiser | Capstone",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and base64-encode background image if available
bg_image_path = os.path.join(os.path.dirname(__file__), "airside_background.png")
if os.path.exists(bg_image_path):
    try:
        with open(bg_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.45)), url("data:image/png;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        }
        </style>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    }
    </style>
    """, unsafe_allow_html=True)

# Custom premium CSS for light theme and glassmorphism styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Main font style */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* App Background - Default text color */
.stApp {
    color: #0f172a;
}

/* Card layout - Soft white card with dark text */
.glass-card {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.05);
    color: #1e293b;
}

/* Ensure headings inside cards use dark color */
.glass-card h1, .glass-card h2, .glass-card h3, .glass-card h4 {
    color: #0f172a !important;
}

/* Deep blue/teal title gradient for light background */
.title-gradient {
    background: linear-gradient(90deg, #1e3a8a 0%, #0d9488 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.8rem;
    margin-bottom: 5px;
}

/* Subtitle styling */
.subtitle-text {
    color: #475569;
    font-size: 1.1rem;
    margin-bottom: 30px;
}

/* Prediction card - Bright Royal Blue */
.price-card {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    border-radius: 16px;
    padding: 30px 20px;
    text-align: center;
    box-shadow: 0 12px 30px rgba(29, 78, 216, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.15);
    margin-top: 10px;
    margin-bottom: 30px;
    color: #ffffff;
}

.price-label {
    font-size: 1.4rem;
    color: #ffffff;
    font-weight: 600;
}

.price-val {
    font-size: 3.5rem;
    font-weight: 700;
    color: #ffffff;
    margin: 15px 0;
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.currency-symbol {
    font-size: 2rem;
    vertical-align: super;
    margin-right: 5px;
    color: #60a5fa;
}

.price-sub {
    font-size: 0.9rem;
    color: #93c5fd;
}

/* KPI metric cards inside prediction card */
.kpi-container {
    display: flex;
    justify-content: space-between;
    gap: 15px;
    margin-top: 20px;
}

.kpi-box {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 12px;
    flex: 1;
    text-align: center;
}

.kpi-title {
    font-size: 0.75rem;
    color: #bfdbfe;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.kpi-val {
    font-size: 1.1rem;
    font-weight: 600;
    color: #ffffff;
    margin-top: 5px;
}

/* Sidebar styling overrides for light theme compatibility */
[data-testid="stSidebar"] {
    background-color: #f1f5f9;
    border-right: 1px solid rgba(0, 0, 0, 0.08);
}

/* High-contrast highlight badges */
.badge-highlight {
    background-color: rgba(16, 185, 129, 0.12);
    color: #047857;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    border: 1px solid rgba(16, 185, 129, 0.2);
    display: inline-block;
}

.badge-info {
    background-color: rgba(59, 130, 246, 0.12);
    color: #1d4ed8;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    border: 1px solid rgba(59, 130, 246, 0.2);
    display: inline-block;
}

.badge-warning {
    background-color: rgba(245, 158, 11, 0.12);
    color: #b45309;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 600;
    border: 1px solid rgba(245, 158, 11, 0.2);
    display: inline-block;
}

/* Style Streamlit container borders to look like glass cards with 30% transparency */
div.st-key-param_container,
div.st-key-param_container [data-testid="stVerticalBlock"],
div.st-key-find_param_container,
div.st-key-find_param_container [data-testid="stVerticalBlock"],
div.st-key-chart_container,
div.st-key-chart_container [data-testid="stVerticalBlock"],
div.st-key-tips_container,
div.st-key-tips_container [data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: rgba(255, 255, 255, 0.7) !important;
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    border-radius: 16px !important;
    padding: 24px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05) !important;
}

/* Header container: Rounded top, flat bottom, no margin bottom */
div.st-key-header_container,
div.st-key-header_container [data-testid="stVerticalBlock"] {
    background-color: rgba(255, 255, 255, 0.7) !important;
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    border-bottom: none !important;
    border-top-left-radius: 16px !important;
    border-top-right-radius: 16px !important;
    border-bottom-left-radius: 0px !important;
    border-bottom-right-radius: 0px !important;
    padding: 24px 24px 12px 24px !important;
    margin-bottom: 0px !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
}

/* Tab bar container: Flat top, rounded bottom, pull up to merge with header card */
div[role="tablist"] {
    background-color: rgba(255, 255, 255, 0.7) !important;
    background: rgba(255, 255, 255, 0.7) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    border-top: none !important;
    border-top-left-radius: 0px !important;
    border-top-right-radius: 0px !important;
    border-bottom-left-radius: 16px !important;
    border-bottom-right-radius: 16px !important;
    padding: 0px 24px 12px 24px !important;
    margin-top: -16px !important; /* Pull up to touch the header card exactly */
    margin-bottom: 25px !important;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05) !important;
}

/* Reset nested block borders only in the second (right) column to prevent double-boxing on insights */
[data-testid="column"]:nth-of-type(2) div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* Bold all native Streamlit widget labels */
div[data-testid="stWidgetLabel"] p {
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# Load the model and its paired feature schema together. The schema is the exact list of
# columns (and order) the model was trained on - saved by pipeline/ml.py's export_model().
# Deriving EXPECTED_FEATURES from it here, instead of hardcoding a separate copy of the
# same list, means the app automatically stays in sync whenever a training run changes the
# supported booking-window/route categories, rather than silently drifting out of sync with
# whatever model is actually loaded.
@st.cache_resource
def load_prediction_model():
    model_path = os.path.join(os.path.dirname(__file__), "flight_predictor_rf.joblib")
    schema_path = os.path.join(os.path.dirname(__file__), "model_feature_schema.joblib")
    try:
        model = joblib.load(model_path)
        schema = joblib.load(schema_path)
        return model, schema
    except Exception as e:
        st.error(f"Error loading model/schema from '{model_path}' / '{schema_path}': {e}")
        return None, None

# Load the model resource
model, EXPECTED_FEATURES = load_prediction_model()

# Auto-holiday calculation logic using python holidays package
import holidays

# Day offsets (relative to the holiday itself, 0) to mark as holiday-adjacent for elevated
# travel demand, keyed by the holiday's weekday (Mon=0 ... Sun=6). Mirrors
# pipeline/process_flight_data.py's HOLIDAY_DAY_OFFSETS exactly - this is what the model was
# actually trained on, so this UI auto-detection has to match it or the checkboxes here would
# pre-fill differently than the labels the model learned from. Keep both in sync.
HOLIDAY_DAY_OFFSETS = {
    0: [-3, -2, -1, 0],   # Monday
    1: [-3, -2, -1, 0],   # Tuesday
    2: [0],               # Wednesday
    3: [0, 1, 2, 3],       # Thursday
    4: [0, 1, 2, 3],       # Friday
    5: [0],               # Saturday
    6: [0],               # Sunday
}

@st.cache_data
def get_holiday_lookup_sets(year):
    airport_to_country = {
        'LHR': 'GB',
        'NRT': 'JP',
        'BKK': 'TH',
        'MEL': 'AU',
        'SIN': 'SG'
    }

    holiday_sets = {}
    for code, country_iso in airport_to_country.items():
        try:
            # We fetch holidays for the year before, current year, and year after to cover boundaries
            country_hols = holidays.country_holidays(country_iso, years=[year - 1, year, year + 1])
        except Exception:
            country_hols = {}

        expanded_set = set()
        for h_date in country_hols.keys():
            for offset in HOLIDAY_DAY_OFFSETS[h_date.weekday()]:
                expanded_set.add(h_date + timedelta(days=offset))

        holiday_sets[code] = expanded_set
    return holiday_sets

def is_sch_holiday_calc(flight_date):
    current_year = flight_date.year
    month = flight_date.month

    # Check if departure date is in Jun or Dec
    if month in [6, 12]:
        return True

    # For 1 Jun
    jun1 = datetime(current_year, 6, 1).date()
    jun1_weekday = jun1.weekday()  # 5 = Sat; 6 = Sun
    if jun1_weekday == 5 and flight_date == (jun1 - timedelta(days=1)):
        return True
    if jun1_weekday == 6 and flight_date == (jun1 - timedelta(days=2)):
        return True

    # For 1 Dec 
    dec1 = datetime(current_year, 12, 1).date()
    dec1_weekday = dec1.weekday()  # 5 = Sat; 6 = Sun
    if dec1_weekday == 5 and flight_date == (dec1 - timedelta(days=1)):
        return True
    if dec1_weekday == 6 and flight_date == (dec1 - timedelta(days=2)):
        return True

    return False
def get_destination_climate_html(dest_code, month):
    # Mapping of destination codes to human-readable names and emoji
    dest_names = {
        'SIN': ('Singapore', '🇸🇬'),
        'BKK': ('Bangkok', '🇹🇭'),
        'LHR': ('London', '🇬🇧'),
        'MEL': ('Melbourne', '🇦🇺'),
        'NRT': ('Tokyo', '🇯🇵')
    }
    dest_name, flag_emoji = dest_names.get(dest_code, (dest_code, '📍'))
    
    # Climate and season lookup
    if dest_code == 'SIN':
        temp = "26°C - 31°C (79°F - 88°F)"
        if month in [12, 1, 2, 3]:
            season = "Northeast Monsoon (Wet Phase)" if month in [12, 1] else "Northeast Monsoon (Dry Phase)"
            desc = "Generally wet and windy from Dec to Jan, transitioning to drier, sunnier weather in Feb and March."
            icon = "🌧️" if month in [12, 1] else "⛅"
        elif month in [6, 7, 8, 9]:
            season = "Southwest Monsoon"
            desc = "Warm and humid with occasional morning showers and afternoon thunderstorms."
            icon = "⛈️"
        else:
            season = "Inter-Monsoonal Period"
            desc = "Hot, humid conditions with light winds and frequent afternoon thunderstorms."
            icon = "☀️"
        pack = "Light, breathable summer clothing and a compact umbrella."
        
    elif dest_code == 'BKK':
        if month in [11, 12, 1, 2]:
            season = "Cool and Dry Season"
            temp = "22°C - 32°C (72°F - 90°F)"
            desc = "The most comfortable time to visit. Sunny skies, cool evening breezes, and minimal rainfall."
            icon = "☀️"
            pack = "Light summer wear, but carry a light jacket for cooler evenings."
        elif month in [3, 4, 5]:
            season = "Hot Season"
            temp = "26°C - 36°C (79°F - 97°F)"
            desc = "Intensely hot and humid. April is usually the hottest month. High UV levels."
            icon = "🥵"
            pack = "Sun protection (hat, sunglasses, sunscreen) and very light breathable clothes."
        else:
            season = "Rainy (Monsoon) Season"
            temp = "25°C - 33°C (77°F - 91°F)"
            desc = "Humid with heavy rain showers and thunderstorms, often peaking in September and October."
            icon = "⛈️"
            pack = "Waterproof gear, rain jacket/umbrella, and quick-drying shoes."
            
    elif dest_code == 'LHR':
        if month in [3, 4, 5]:
            season = "Spring"
            temp = "6°C - 14°C (43°F - 57°F)"
            desc = "Mild but unpredictable. Blossoms are blooming, with alternating sunny periods and light showers."
            icon = "🌸"
            pack = "Layered clothing, a warm sweater, and a light waterproof coat."
        elif month in [6, 7, 8]:
            season = "Summer"
            temp = "13°C - 23°C (55°F - 73°F)"
            desc = "Warmest and pleasant time of the year. Long daylight hours, though rain is still possible."
            icon = "☀️"
            pack = "T-shirts, shorts, light trousers, and sunglasses. Carry a light sweater."
        elif month in [9, 10, 11]:
            season = "Autumn"
            temp = "8°C - 16°C (46°F - 61°F)"
            desc = "Cooling down rapidly. Beautiful autumn foliage, shorter days, and increasing dampness."
            icon = "🍂"
            pack = "Medium-weight coat, scarf, boots, and an umbrella."
        else:
            season = "Winter"
            temp = "2°C - 8°C (36°F - 46°F)"
            desc = "Cold, damp, and often grey. Occasional frost or light snow. Short daylight hours."
            icon = "❄️"
            pack = "Heavy winter coat, gloves, thermal layers, and a warm hat."
            
    elif dest_code == 'MEL':
        if month in [12, 1, 2]:
            season = "Summer"
            temp = "14°C - 26°C (57°F - 79°F)"
            desc = "Warm and sunny, with occasional extreme hot days peaking above 35°C due to northern winds."
            icon = "☀️"
            pack = "Summer wear, sunscreen, sunglasses, and a light jacket for evening cool downs."
        elif month in [3, 4, 5]:
            season = "Autumn"
            temp = "11°C - 20°C (52°F - 68°F)"
            desc = "Mild and cooling down. Known for beautiful autumn colors in the parks. Generally pleasant."
            icon = "🍂"
            pack = "Layered clothing, sweater, and light jacket."
        elif month in [6, 7, 8]:
            season = "Winter"
            temp = "7°C - 14°C (45°F - 57°F)"
            desc = "Cold and crisp, often cloudy with brisk winds and occasional light drizzle."
            icon = "❄️"
            pack = "Warm coat, scarf, thermal layers, and windproof jacket."
        else:
            season = "Spring"
            temp = "10°C - 20°C (50°F - 68°F)"
            desc = "Highly changeable weather ('four seasons in one day'). Gradual warming with moderate rainfall."
            icon = "🌸"
            pack = "Layered clothing, umbrella, and a medium jacket."

    elif dest_code == 'NRT':
        if month in [3, 4, 5]:
            season = "Spring (Sakura Season)"
            temp = "8°C - 19°C (46°F - 66°F)"
            desc = "Mild and pleasant. Cherry blossom season peaks in late March / early April. Very popular time."
            icon = "🌸"
            pack = "Light layers, sweater, and a comfortable jacket."
        elif month in [6, 7, 8]:
            season = "Summer"
            temp = "21°C - 28°C (70°F - 82°F)"
            desc = "Hot, humid, and rainy. Rainy season (Tsuyu) lasts through mid-July, followed by high heat."
            icon = "🥵"
            pack = "Very light summer clothing, umbrella, and sunglasses."
        elif month in [9, 10, 11]:
            season = "Autumn"
            temp = "12°C - 21°C (54°F - 70°F)"
            desc = "Cool and highly pleasant. Beautiful autumn foliage (Momiji) peaks in November."
            icon = "🍁"
            pack = "Comfortable light layers, cardigan, or light coat."
        else:
            season = "Winter"
            temp = "2°C - 10°C (36°F - 50°F)"
            desc = "Cold, dry, and sunny. Rare snowfall in Tokyo itself, but crisp blue skies are common."
            icon = "❄️"
            pack = "Heavy coat, gloves, scarf, and thermal wear."
    else:
        season = "Varies"
        temp = "Check local forecasts"
        desc = "No local historical data available."
        icon = "🌍"
        pack = "All-weather gear."

    html_card = f'<div class="glass-card">' \
                f'<h3 style="margin-top: 0; color: #0f172a; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">' \
                f'<span>⛅ Destination Climate Insights</span>' \
                f'</h3>' \
                f'<div style="display: flex; flex-direction: column; gap: 15px;">' \
                f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 10px;">' \
                f'<span style="font-weight: 600; color: #475569; font-size: 0.95rem;">Destination:</span>' \
                f'<span style="font-weight: 700; color: #1e3a8a; font-size: 1rem;">{flag_emoji} {dest_name}</span>' \
                f'</div>' \
                f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 10px;">' \
                f'<span style="font-weight: 600; color: #475569; font-size: 0.95rem;">Season at Travel ({datetime(2026, month, 1).strftime("%B")}):</span>' \
                f'<span style="font-weight: 700; color: #0d9488; font-size: 1rem;">{icon} {season}</span>' \
                f'</div>' \
                f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.05); padding-bottom: 10px;">' \
                f'<span style="font-weight: 600; color: #475569; font-size: 0.95rem;">Historical Temperature:</span>' \
                f'<span style="font-weight: 700; color: #0f172a; font-size: 1rem;">🌡️ {temp}</span>' \
                f'</div>' \
                f'<div>' \
                f'<span style="font-weight: 600; color: #475569; font-size: 0.95rem; display: block; margin-bottom: 5px;">Weather Description:</span>' \
                f'<p style="margin: 0; font-size: 0.9rem; color: #334155; line-height: 1.5; font-weight: 400;">{desc}</p>' \
                f'</div>' \
                f'<div style="background: rgba(13, 148, 136, 0.08); padding: 12px; border-radius: 8px; border-left: 4px solid #0d9488;">' \
                f'<span style="font-weight: 700; color: #0f766e; font-size: 0.85rem; display: block; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">🎒 Recommended Packing</span>' \
                f'<p style="margin: 0; font-size: 0.9rem; color: #115e59; line-height: 1.4; font-weight: 500;">{pack}</p>' \
                f'</div>' \
                f'</div>' \
                f'</div>'
    return html_card


# NOTE: EXPECTED_FEATURES itself now comes from model_feature_schema.joblib (see
# load_prediction_model() above) rather than being hardcoded here.

def get_known_booking_windows(expected_features):
    """Derive the sorted list of (lower_days, upper_days, label) booking-window buckets the
    loaded model actually supports, straight from its feature schema. "1-14 days" is always
    included as the implicit baseline category: pd.get_dummies(..., drop_first=True) drops
    it during training (it sorts first alphabetically among "N-M days" labels), so it never
    appears as its own column - the model represents it as "every booking_window_* column
    is 0" instead."""
    windows = [(1, 14, "1-14 days")]
    for col in expected_features or []:
        match = re.fullmatch(r"booking_window_(\d+)-(\d+) days", col)
        if match:
            lower, upper = int(match.group(1)), int(match.group(2))
            windows.append((lower, upper, f"{lower}-{upper} days"))
    windows.sort(key=lambda w: w[0])
    return windows

KNOWN_BOOKING_WINDOWS = get_known_booking_windows(EXPECTED_FEATURES)
MAX_KNOWN_DAYS = KNOWN_BOOKING_WINDOWS[-1][1] if KNOWN_BOOKING_WINDOWS else 84

def map_days_to_window_bucket(days):
    """Map a days-to-departure count to whichever known booking-window bucket it falls into.
    The extraction schedule samples booking windows somewhat randomly across a wide range
    (see extract_flight_data.py), so coverage can be patchy - not every 14-day bucket is
    guaranteed to exist yet. If `days` falls in a gap between known buckets, or beyond the
    furthest one the model has seen, this clamps to the nearest known bucket at or below it
    as the closest available approximation."""
    for lower, upper, label in KNOWN_BOOKING_WINDOWS:
        if lower <= days <= upper:
            return label
    candidates = [w for w in KNOWN_BOOKING_WINDOWS if w[0] <= days]
    return candidates[-1][2] if candidates else KNOWN_BOOKING_WINDOWS[0][2]

with st.container(key="header_container", border=True):
    st.markdown('<div class="title-gradient">✈️ Dynamic Fare Optimiser</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle-text" style="margin-bottom: 0px;">Taking the turbulence out of ticket pricing.</div>', unsafe_allow_html=True)

if model is None or not EXPECTED_FEATURES:
    st.error("Could not load the flight predictor model and its feature schema. Please make sure 'flight_predictor_rf.joblib' and 'model_feature_schema.joblib' are both in the application directory.")
else:
    # Create Tabs
    tab_predict, tab_finder = st.tabs(["🔮 Price Predictor", "📅 Booking Window Finder"])
    
    with tab_predict:
        # Set up layout columns
        col_input, col_pred = st.columns([0.9, 1.1], gap="medium")
        
        with col_input:
            with st.container(key="param_container", border=True):
                st.subheader("🔍 Search Flight Parameters")
                
                # 1. Flight Details
                st.markdown('<h3 style="margin-top: 0; margin-bottom: 12px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Flight Details</h3>', unsafe_allow_html=True)
                col_org, col_dst = st.columns(2)
                with col_org:
                    origins = ["Singapore (SIN)", "Bangkok (BKK)", "London (LHR)", "Melbourne (MEL)", "Tokyo (NRT)"]
                    origin = st.selectbox("Origin Airport", origins, index=0)
                
                with col_dst:
                    # Dynamic filtering of destinations to only allow valid routes from training set
                    # Supported routes: SIN-BKK, BKK-SIN, SIN-LHR, LHR-SIN, SIN-MEL, MEL-SIN, SIN-NRT, NRT-SIN
                    valid_destinations = []
                    if "SIN" in origin:
                        valid_destinations = ["Bangkok (BKK)", "London (LHR)", "Melbourne (MEL)", "Tokyo (NRT)"]
                    else:
                        valid_destinations = ["Singapore (SIN)"]
                        
                    destination = st.selectbox("Destination Airport", valid_destinations, index=0)
                
                # Extract clean route string (e.g. SIN-BKK)
                origin_code = origin.split("(")[1].replace(")", "")
                dest_code = destination.split("(")[1].replace(")", "")
                selected_route = f"{origin_code}-{dest_code}"
                
                # Use session state to prevent widget validation crashes (e.g. if Booking Date is shifted after Departure Date)
                today_date = datetime.today().date()
                if "booking_date" not in st.session_state:
                    st.session_state.booking_date = today_date
                if "departure_date" not in st.session_state:
                    st.session_state.departure_date = today_date + timedelta(days=30)
                if "calculate_clicked" not in st.session_state:
                    st.session_state.calculate_clicked = False
                if "finder_results" not in st.session_state:
                    st.session_state.finder_results = None
                    
                col_book, col_dep = st.columns(2)
                
                with col_book:
                    booking_date = st.date_input(
                        "Booking Date",
                        value=st.session_state.booking_date,
                        min_value=today_date - timedelta(days=365),
                        max_value=today_date + timedelta(days=365),
                        key="booking_date_widget"
                    )
                    
                    # Today button stacked directly underneath the Booking Date input
                    if st.button("Today", key="reset_booking_today", use_container_width=True):
                        st.session_state.booking_date = today_date
                        # If today_date is after departure_date, adjust departure_date
                        if today_date > st.session_state.departure_date:
                            st.session_state.departure_date = today_date + timedelta(days=30)
                        st.rerun()
                            
                # If the user sets booking_date ahead of the departure_date, adjust departure_date in session state to stay valid
                if booking_date > st.session_state.departure_date:
                    st.session_state.departure_date = booking_date + timedelta(days=30)
                    
                with col_dep:
                    departure_date = st.date_input(
                        "Departure Date",
                        value=st.session_state.departure_date,
                        min_value=booking_date,
                        key="departure_date_widget"
                    )
                    
                # Sync variables back to session state for the next run
                st.session_state.booking_date = booking_date
                st.session_state.departure_date = departure_date
                    
                # Calculate days to departure
                days_to_departure = (departure_date - booking_date).days
                
                # Clamp to bounds and generate warning if needed
                clamped_days = days_to_departure
                if days_to_departure <= 0:
                    clamped_days = 1
                    st.warning("⚠️ Departure date must be after booking date. Calculated window set to 1 day.")
                elif days_to_departure > MAX_KNOWN_DAYS:
                    st.warning(f"⚠️ Model was trained on booking windows up to {MAX_KNOWN_DAYS} days. Predicting for {days_to_departure} days ahead might have higher variance.")

                # Map to booking window categories (dynamically, from whichever buckets the
                # loaded model's schema actually supports - see map_days_to_window_bucket()).
                booking_window_cat = map_days_to_window_bucket(clamped_days)
                    
                # Display the derived timing details
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                weekday_idx = departure_date.weekday()
                dep_day_name = day_names[weekday_idx]
                is_weekend_val = (weekday_idx >= 5) # Sat/Sun
                dep_month = departure_date.month
                
                st.info(f"📅 **Travel Stats:** {clamped_days} days to departure • **Departure Day:** {dep_day_name} " + 
                        ("🟩" if not is_weekend_val else "🟥 (Weekend)"))
                
                # 3. Holidays
                st.markdown('<h3 style="margin-top: 15px; margin-bottom: 12px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Holiday Calendars</h3>', unsafe_allow_html=True)
                st.caption("These fields are auto-populated based on the selected departure date and route, but you can manually override them.")
                
                # Calculate holidays automatically using the holidays package
                try:
                    holiday_lookup = get_holiday_lookup_sets(departure_date.year)
                    auto_holiday_sin = departure_date in holiday_lookup.get('SIN', set())
                    
                    other_airport = dest_code if origin_code == 'SIN' else origin_code
                    auto_holiday_other = departure_date in holiday_lookup.get(other_airport, set())
                except Exception:
                    auto_holiday_sin = False
                    auto_holiday_other = False
                    
                # School holiday calculation
                try:
                    auto_sch_holiday = is_sch_holiday_calc(departure_date)
                except Exception:
                    auto_sch_holiday = False
                    
                col_h1, col_h2, col_h3 = st.columns(3)
                with col_h1:
                    is_holiday_sin_val = 1 if st.checkbox("Singapore Public Holiday", value=auto_holiday_sin) else 0
                with col_h2:
                    is_holiday_other_val = 1 if st.checkbox("Destination Public Holiday", value=auto_holiday_other) else 0
                with col_h3:
                    is_sch_holiday_val = 1 if st.checkbox("Singapore School Holiday", value=auto_sch_holiday) else 0
                    
                st.markdown("---")
                
                # 4. Carrier Type
                st.markdown('<h3 style="margin-top: 15px; margin-bottom: 12px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Carrier Preferences</h3>', unsafe_allow_html=True)
                
                is_lhr_route = (origin_code == 'LHR' or dest_code == 'LHR')
                if is_lhr_route:
                    st.caption("Fares are based on Economy class tickets only. *(Low Cost Carriers are unavailable for LHR routes)*")
                    carrier_options = ["Full Service Carrier (e.g. Singapore Airlines, Qantas, British Airways)"]
                else:
                    st.caption("Fares are based on Economy class tickets only.")
                    carrier_options = [
                        "Full Service Carrier (e.g. Singapore Airlines, Qantas, British Airways)", 
                        "Low Cost Carrier (e.g. AirAsia, Scoot, Jetstar)"
                    ]
                
                carrier_choice = st.radio(
                    "Carrier Service Class",
                    carrier_options,
                    index=0,
                    label_visibility="collapsed"
                )
                is_lcc_val = 1 if "Low Cost" in carrier_choice else 0
            
        with col_pred:
            # Preprocessing inputs into DataFrame
            input_dict = {col: False for col in EXPECTED_FEATURES}
            
            # Set exact numerical values
            input_dict['day_of_week'] = int(weekday_idx)
            input_dict['is_weekend'] = bool(is_weekend_val)
            input_dict['is_lcc'] = int(is_lcc_val)
            input_dict['is_holiday_sin'] = int(is_holiday_sin_val)
            input_dict['is_holiday_other'] = int(is_holiday_other_val)
            input_dict['is_sch_holiday'] = int(is_sch_holiday_val)
            input_dict['departure_month'] = float(dep_month)
            
            # Set route one-hot
            route_col = f"route_{selected_route}"
            if route_col in input_dict:
                input_dict[route_col] = True
                
            # Set booking window one-hot
            window_col = f"booking_window_{booking_window_cat}"
            if window_col in input_dict:
                input_dict[window_col] = True
                
            # Convert to dataframe matching column schema
            df_input = pd.DataFrame([input_dict])
            
            # Ensure order matches exactly
            df_input = df_input[EXPECTED_FEATURES]
            
            # Predict price
            try:
                predicted_price = model.predict(df_input)[0]
                
                # Prediction Card UI (Single line strings to prevent markdown indentation code blocks)
                price_card_html = f'<div class="price-card">' \
                                  f'<div class="price-label">Estimated Airfare</div>' \
                                  f'<div class="price-val"><span class="currency-symbol">S$</span>{predicted_price:,.2f}</div>' \
                                  f'<div class="kpi-container">' \
                                  f'<div class="kpi-box"><div class="kpi-title">Route</div><div class="kpi-val">{selected_route}</div></div>' \
                                  f'<div class="kpi-box"><div class="kpi-title">Booking Window</div><div class="kpi-val">{booking_window_cat}</div></div>' \
                                  f'<div class="kpi-box"><div class="kpi-title">Carrier Type</div><div class="kpi-val">{"Low Cost" if is_lcc_val == 1 else "Full Service"}</div></div>' \
                                  f'</div>' \
                                  f'</div>'
                st.markdown(price_card_html, unsafe_allow_html=True)
                
                # Dynamic Insights card based on features
                insights = []
                
                # 1. Booking Window Insights
                if booking_window_cat == "1-14 days":
                    insights.append((
                        "badge-warning", 
                        "Urgent Booking Window", 
                        "You are booking within the 1-14 days threshold. Fares are historically higher due to close-in demand. Booking at least 15-28 days earlier can help reduce costs by up to 20-30%."
                    ))
                elif booking_window_cat in ["15-28 days", "29-42 days"]:
                    insights.append((
                        "badge-info", 
                        "Moderate Booking Window", 
                        "Booking 15-42 days in advance generally offers average pricing. If travel dates are flexible, extending your booking window beyond 43 days usually unlocks the lowest rates."
                    ))
                else:
                    insights.append((
                        "badge-highlight",
                        "Optimal Booking Window",
                        "Booking 43 or more days in advance is generally the optimal window. Fares are statistically lowest and most stable in this timeframe."
                    ))
                    
                # 2. Day of Week / Weekend Insights
                if is_weekend_val:
                    insights.append((
                        "badge-warning",
                        "Weekend Departure Surcharge",
                        f"Fares departing on {dep_day_name} are typically priced higher due to weekend travel surges. Shifting departure to a Tuesday or Wednesday could save you money."
                    ))
                else:
                    insights.append((
                        "badge-highlight",
                        "Midweek Departure Savings",
                        f"Departing on {dep_day_name} avoids the standard weekend travel premium. Midweek flights are generally less crowded and more affordable."
                    ))
                    
                # 3. Carrier Type Insights
                if is_lcc_val == 1:
                    insights.append((
                        "badge-info",
                        "Low Cost Carrier Selected",
                        "Budget airfare selected. Keep in mind that base fares exclude baggage, meals, and seat selection fees. Factor these add-ons into your total comparison."
                    ))
                else:
                    insights.append((
                        "badge-highlight",
                        "Full Service Carrier Selected",
                        "Premium airline selected. This fare typically includes checked baggage, in-flight dining, and seat selections."
                    ))
                    
                # 4. Holiday Premium Insights
                if is_holiday_sin_val == 1 or is_holiday_other_val == 1 or is_sch_holiday_val == 1:
                    insights.append((
                        "badge-warning",
                        "Holiday Season Premium",
                        "Your travel coincides with a holiday period. Airfares generally experience high demand surcharges during these peak periods."
                    ))
                    
                # Render Insights side-by-side in columns under the Estimated Airfare card
                col_ins_left, col_ins_right = st.columns(2)
                
                with col_ins_left:
                    # Render Insights (Single flat string to prevent markdown code block detection)
                    insights_html = '<div class="glass-card"><h3 style="margin-top: 0; color: #0f172a; margin-bottom: 20px; font-size: 1.25rem; font-weight: 600; white-space: nowrap; display: flex; align-items: center; gap: 8px; line-height: 1.2;">💡 Smart Travel Insights</h3>'
                    for badge_class, title, desc in insights:
                        insights_html += f'<div style="margin-bottom: 20px;">' \
                                         f'<span class="{badge_class}">{title}</span>' \
                                         f'<p style="margin-top: 8px; font-size: 0.95rem; color: #334155; line-height: 1.5; font-weight: 400; margin-bottom: 0;">{desc}</p>' \
                                         f'</div>'
                    insights_html += '</div>'
                    st.markdown(insights_html, unsafe_allow_html=True)
                
                with col_ins_right:
                    # Destination Climate & Season Insights
                    climate_html = get_destination_climate_html(dest_code, dep_month)
                    st.markdown(climate_html, unsafe_allow_html=True)
                
            except Exception as pred_err:
                st.error(f"Error predicting price: {pred_err}")

    with tab_finder:
        col_find_input, col_find_pred = st.columns([1.0, 1.0], gap="medium")
        
        with col_find_input:
            with st.container(key="find_param_container", border=True):
                st.subheader("🔍 Find Optimal Booking Window")
                
                # 1. Flight Details
                st.markdown('<h3 style="margin-top: 0; margin-bottom: 8px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Flight Details</h3>', unsafe_allow_html=True)
                col_org_f, col_dst_f = st.columns(2)
                with col_org_f:
                    origins_f = ["Singapore (SIN)", "Bangkok (BKK)", "London (LHR)", "Melbourne (MEL)", "Tokyo (NRT)"]
                    origin_f = st.selectbox("Origin Airport", origins_f, index=0, key="origin_find_widget")
                
                with col_dst_f:
                    valid_destinations_f = []
                    if "SIN" in origin_f:
                        valid_destinations_f = ["Bangkok (BKK)", "London (LHR)", "Melbourne (MEL)", "Tokyo (NRT)"]
                    else:
                        valid_destinations_f = ["Singapore (SIN)"]
                    destination_f = st.selectbox("Destination Airport", valid_destinations_f, index=0, key="destination_find_widget")
                
                origin_code_f = origin_f.split("(")[1].replace(")", "")
                dest_code_f = destination_f.split("(")[1].replace(")", "")
                selected_route_f = f"{origin_code_f}-{dest_code_f}"
                
                # 2. Travel Date & Target Budget Side-by-Side (More compact!)
                today_date = datetime.today().date()
                col_date_f, col_budget_f = st.columns(2)
                with col_date_f:
                    departure_date_f = st.date_input(
                        "Departure Date",
                        value=today_date + timedelta(days=30),
                        min_value=today_date,
                        key="departure_date_find_widget"
                    )
                with col_budget_f:
                    target_price_f = st.number_input(
                        "Target Budget (S$)",
                        min_value=10.0,
                        value=500.0,
                        step=10.0,
                        key="target_price_find_widget"
                    )
                
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                weekday_idx_f = departure_date_f.weekday()
                dep_day_name_f = day_names[weekday_idx_f]
                is_weekend_val_f = (weekday_idx_f >= 5)
                dep_month_f = departure_date_f.month
                
                st.info(f"📅 **Departure:** {dep_day_name_f} " + 
                        ("🟩" if not is_weekend_val_f else "🟥 (Weekend)"))
                
                # 3. Carrier Preferences
                st.markdown('<h3 style="margin-top: 15px; margin-bottom: 12px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Carrier Preferences</h3>', unsafe_allow_html=True)
                
                is_lhr_route_f = (origin_code_f == 'LHR' or dest_code_f == 'LHR')
                if is_lhr_route_f:
                    st.caption("Fares are based on Economy class tickets only. *(Low Cost Carriers are unavailable for LHR routes)*")
                    carrier_options_f = ["Full Service Carrier (e.g. Singapore Airlines, Qantas, British Airways)"]
                else:
                    st.caption("Fares are based on Economy class tickets only.")
                    carrier_options_f = [
                        "Full Service Carrier (e.g. Singapore Airlines, Qantas, British Airways)", 
                        "Low Cost Carrier (e.g. AirAsia, Scoot, Jetstar)"
                    ]
                
                carrier_choice_f = st.radio(
                    "Carrier Service Class",
                    carrier_options_f,
                    index=0,
                    key="carrier_choice_find_widget",
                    label_visibility="collapsed"
                )
                is_lcc_val_f = 1 if "Low Cost" in carrier_choice_f else 0
                
                # 4. Holiday Calendars (Side-by-Side checkboxes, compact)
                st.markdown('<h3 style="margin-top: 15px; margin-bottom: 12px; color: #0f172a; font-size: 1.25rem; font-weight: 600; white-space: nowrap; line-height: 1.2;">Holiday Calendars</h3>', unsafe_allow_html=True)
                st.caption("These fields are auto-populated based on the selected departure date and route, but you can manually override them.")
                
                try:
                    holiday_lookup_f = get_holiday_lookup_sets(departure_date_f.year)
                    auto_holiday_sin_f = departure_date_f in holiday_lookup_f.get('SIN', set())
                    
                    other_airport_f = dest_code_f if origin_code_f == 'SIN' else origin_code_f
                    auto_holiday_other_f = departure_date_f in holiday_lookup_f.get(other_airport_f, set())
                except Exception:
                    auto_holiday_sin_f = False
                    auto_holiday_other_f = False
                    
                try:
                    auto_sch_holiday_f = is_sch_holiday_calc(departure_date_f)
                except Exception:
                    auto_sch_holiday_f = False
                    
                col_h1_f, col_h2_f, col_h3_f = st.columns(3)
                with col_h1_f:
                    is_holiday_sin_val_f = 1 if st.checkbox("Singapore Public Holiday", value=auto_holiday_sin_f, key="holiday_sin_find") else 0
                with col_h2_f:
                    is_holiday_other_val_f = 1 if st.checkbox("Destination Public Holiday", value=auto_holiday_other_f, key="holiday_other_find") else 0
                with col_h3_f:
                    is_sch_holiday_val_f = 1 if st.checkbox("Singapore School Holiday", value=auto_sch_holiday_f, key="sch_holiday_find") else 0
            
            # Calculate Button at the bottom
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            if st.button("Calculate", key="calculate_find_btn", use_container_width=True, type="primary"):
                try:
                    # Booking windows sorted in chronological order (earliest booking first,
                    # i.e. longest lead time first) - derived from the model's own schema so
                    # this automatically covers whatever buckets it actually supports.
                    windows = [w[2] for w in sorted(KNOWN_BOOKING_WINDOWS, key=lambda w: -w[0])]
                    predictions_by_cat = {}
                    predictions_f = {}
                    cat_to_range = {}
                    
                    for w_cat in windows:
                        # Preprocessing inputs into DataFrame
                        input_dict_f = {col: False for col in EXPECTED_FEATURES}
                        
                        # Set exact numerical values
                        input_dict_f['day_of_week'] = int(weekday_idx_f)
                        input_dict_f['is_weekend'] = bool(is_weekend_val_f)
                        input_dict_f['is_lcc'] = int(is_lcc_val_f)
                        input_dict_f['is_holiday_sin'] = int(is_holiday_sin_val_f)
                        input_dict_f['is_holiday_other'] = int(is_holiday_other_val_f)
                        input_dict_f['is_sch_holiday'] = int(is_sch_holiday_val_f)
                        input_dict_f['departure_month'] = float(dep_month_f)
                        
                        # Set route one-hot
                        route_col = f"route_{selected_route_f}"
                        if route_col in input_dict_f:
                            input_dict_f[route_col] = True
                            
                        # Set booking window one-hot
                        if w_cat != "1-14 days":
                            window_col = f"booking_window_{w_cat}"
                            if window_col in input_dict_f:
                                input_dict_f[window_col] = True
                                
                        # Convert to dataframe matching column schema
                        df_input_f = pd.DataFrame([input_dict_f])
                        df_input_f = df_input_f[EXPECTED_FEATURES]
                        
                        # Predict price
                        pred_price_f = model.predict(df_input_f)[0]
                        predictions_by_cat[w_cat] = pred_price_f
                        
                        # Calculate actual booking date range
                        start_days = int(w_cat.split("-")[0])
                        end_days = int(w_cat.split("-")[1].split(" ")[0])
                        date_start = departure_date_f - timedelta(days=end_days)
                        date_end = departure_date_f - timedelta(days=start_days)
                        range_str = f"{date_start.strftime('%d %b')} - {date_end.strftime('%d %b')}"
                        
                        predictions_f[range_str] = pred_price_f
                        cat_to_range[w_cat] = range_str
                    
                    min_cat_f = min(predictions_by_cat, key=predictions_by_cat.get)
                    min_window_range = cat_to_range[min_cat_f]
                    min_price_f = predictions_by_cat[min_cat_f]
                    
                    # Check if target is achievable
                    is_achievable = (target_price_f >= min_price_f)
                    
                    # Custom Status Card UI
                    if is_achievable:
                        status_title = "Target Achievable! 🎉"
                        status_desc = f"Book between <strong>{min_window_range}</strong> to get the lowest predicted fare of <strong>S$ {min_price_f:,.2f}</strong>, which meets your budget of S$ {target_price_f:,.2f}."
                        bg_color = "linear-gradient(135deg, #10b981 0%, #059669 100%)" # Emerald Green
                        shadow_color = "rgba(16, 185, 129, 0.2)"
                    else:
                        status_title = "Target Unachievable ⚠️"
                        status_desc = f"The lowest predicted fare is <strong>S$ {min_price_f:,.2f}</strong> when booking between <strong>{min_window_range}</strong>. This exceeds your budget of S$ {target_price_f:,.2f}."
                        bg_color = "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)" # Red/Crimson
                        shadow_color = "rgba(239, 68, 68, 0.2)"
                    
                    advice = []
                    # Find general trends
                    best_w_cat = min_cat_f
                    worst_w_cat = max(predictions_by_cat, key=predictions_by_cat.get)
                    best_w_range = cat_to_range[best_w_cat]
                    worst_w_range = cat_to_range[worst_w_cat]
                    saving_potential = predictions_by_cat[worst_w_cat] - predictions_by_cat[best_w_cat]
                    
                    if saving_potential > 20:
                        advice.append(f"⏱️ <strong>Saving Potential</strong>: Booking during the optimal period (<strong>{best_w_range}</strong>) instead of the peak period (<strong>{worst_w_range}</strong>) could save you up to <strong>S$ {saving_potential:,.2f}</strong>.")
                        
                    # Compare the bucket's lower bound directly (rather than a fixed list of
                    # labels) so this still reasons correctly about buckets beyond 71-84 days.
                    best_w_lower_days = int(best_w_cat.split("-")[0])
                    if best_w_lower_days >= 43:
                        advice.append(f"📅 <strong>Book in Advance</strong>: Cheaper fares occur earlier (between <strong>{best_w_range}</strong>). Make sure to lock in your tickets early to avoid high close-in demand pricing.")
                    else:
                        advice.append(f"🔥 <strong>Last Minute Options</strong>: Statistically, the best prices are found closer to departure (between <strong>{best_w_range}</strong>).")
                        
                    if is_weekend_val_f:
                        advice.append("📆 <strong>Day of Week Surcharge</strong>: Since your departure is on a weekend, prices are slightly higher across all windows. Consider shifting departure to a weekday if you want to lower the prices further.")
                    
                    # Store results in session state
                    st.session_state.finder_results = {
                        'predictions_f': predictions_f,
                        'predictions_by_cat': predictions_by_cat,
                        'cat_to_range': cat_to_range,
                        'target_price_f': target_price_f,
                        'min_price_f': min_price_f,
                        'min_window_range': min_window_range,
                        'is_achievable': is_achievable,
                        'status_title': status_title,
                        'status_desc': status_desc,
                        'bg_color': bg_color,
                        'shadow_color': shadow_color,
                        'advice': advice
                    }
                    st.session_state.calculate_clicked = True
                    st.rerun()
                except Exception as finder_err:
                    st.error(f"Error calculating booking windows: {finder_err}")
                
        with col_find_pred:
            if st.session_state.finder_results is not None:
                res = st.session_state.finder_results
                predictions_f = res['predictions_f']
                predictions_by_cat = res['predictions_by_cat']
                cat_to_range = res['cat_to_range']
                target_price_f = res['target_price_f']
                min_price_f = res['min_price_f']
                min_window_range = res['min_window_range']
                is_achievable = res['is_achievable']
                status_title = res['status_title']
                status_desc = res['status_desc']
                bg_color = res['bg_color']
                shadow_color = res['shadow_color']
                advice = res['advice']
                
                status_card_html = f'<div class="price-card" style="background: {bg_color}; box-shadow: 0 12px 30px {shadow_color};">' \
                                  f'<div class="price-label" style="font-size: 1.4rem; color: #ffffff;">{status_title}</div>' \
                                  f'<div class="price-val" style="font-size: 2.2rem; margin: 10px 0;"><span class="currency-symbol" style="color: #ffffff;">S$</span>{min_price_f:,.2f}</div>' \
                                  f'<div style="font-size: 0.95rem; color: rgba(255, 255, 255, 0.9); line-height: 1.4; font-weight: 400; padding: 0 10px;">{status_desc}</div>' \
                                  f'</div>'
                st.markdown(status_card_html, unsafe_allow_html=True)
                
                # Visual comparison chart
                with st.container(key="chart_container", border=True):
                    st.markdown('<h3 style="margin-top: 0; color: #0f172a; margin-bottom: 15px; font-size: 1.25rem; font-weight: 600;">📊 Price Comparison by Booking Date</h3>', unsafe_allow_html=True)
                    
                    import altair as alt
                    chart_df_f = pd.DataFrame({
                        'Booking Window Period': list(predictions_f.keys()),
                        'Predicted Price (S$)': list(predictions_f.values())
                    })
                    
                    # Highlight colors depending on target
                    chart_df_f['Color'] = chart_df_f['Predicted Price (S$)'].apply(
                        lambda p: '#10b981' if p <= target_price_f else '#1d4ed8'
                    )
                    
                    # Calculate Y-axis bounds to ensure the target line is always visible
                    max_y = max(max(predictions_f.values()) * 1.15, target_price_f * 1.15)
                    
                    bars_f = alt.Chart(chart_df_f).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                        x=alt.X('Booking Window Period:N', sort=list(predictions_f.keys()), title="Booking Period (Dates)", axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('Predicted Price (S$):Q', scale=alt.Scale(domain=[0, max_y]), title="Predicted Price (S$)"),
                        color=alt.Color('Color:N', scale=None),
                        tooltip=[
                            alt.Tooltip('Booking Window Period:N', title="Booking Period"),
                            alt.Tooltip('Predicted Price (S$):Q', format=',.2f', title="Predicted Price (S$)")
                        ]
                    )
                    
                    # Target price line (highly visible bright red)
                    line_f = alt.Chart(pd.DataFrame({'y': [target_price_f]})).mark_rule(color='#ef4444', strokeWidth=2.5, strokeDash=[6,4]).encode(
                        y='y:Q'
                    )
                    
                    # Label for target line (high-contrast red-600)
                    label_f = alt.Chart(pd.DataFrame({'y': [target_price_f], 'text': [f'Target: S$ {target_price_f:,.0f}']})).mark_text(
                        align='left', dx=10, dy=-8, color='#dc2626', fontWeight='bold', fontSize=12
                    ).encode(
                        y='y:Q',
                        text='text:N'
                    )
                    
                    chart_f = (bars_f + line_f + label_f).properties(height=480).configure(
                        padding={"left": 10, "right": 20, "top": 10, "bottom": 60}
                    )
                    st.altair_chart(chart_f, use_container_width=True)
                    
                # Helpful Tip Card
                with st.container(key="tips_container", border=True):
                    st.markdown('<h3 style="margin-top: 0; color: #0f172a; margin-bottom: 12px; font-size: 1.25rem; font-weight: 600;">💡 Recommendation Insights</h3>', unsafe_allow_html=True)
                    
                    for adv in advice:
                        st.markdown(f"<div style='margin-bottom: 10px; font-size: 0.95rem; color: #334155;'>{adv}</div>", unsafe_allow_html=True)
            else:
                # Glass card instructions empty state
                st.markdown(
                    '<div style="background: rgba(255, 255, 255, 0.9); border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 16px; padding: 60px 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.05); color: #475569; margin-top: 10px;">'
                    '<div style="font-size: 3rem; margin-bottom: 15px;">📅</div>'
                    '<h3 style="color: #0f172a; margin-top: 0; font-size: 1.3rem; font-weight: 600;">Optimal Booking Window Finder</h3>'
                    '<p style="font-size: 0.95rem; margin-bottom: 0;">Adjust the flight parameters and your desired target budget on the left, then click <strong>Calculate</strong> to search for the cheapest dates to book your flight.</p>'
                    '</div>',
                    unsafe_allow_html=True
                )

