import streamlit as st
from PIL import Image
import requests
import pandas as pd
from geopy.distance import geodesic

# --- CONFIGURATION ---
API_URL = "https://y-trust-003-51424904642.europe-west1.run.app/api/recipescore"
INGREDIENTS_API_URL = "https://y-trust-003-51424904642.europe-west1.run.app/api/ingredients/predict"
RECIPE_API_URL = "https://y-trust-003-51424904642.europe-west1.run.app/api/recipe"

# Load and set logo as icon
logo = Image.open("/Users/aurelie/code/Y-TRUST-FRONT-END/logo Y-trust.png")
st.set_page_config(page_title="Y-TRUST", page_icon=logo, layout="centered")
st.title("Y-TRUST")

# --- SEARCH BAR ---
st.markdown("#### 🔍 What recipe are you looking for?")
with st.form("search_form", clear_on_submit=False):
    col1, col2 = st.columns([5, 1])
    with col1:
        recipe_query = st.text_input("", placeholder="e.g. Bolognese sauce ...", key="recipe_input")
    with col2:
        submitted = st.form_submit_button("Search")
if submitted and recipe_query.strip():
    st.session_state["recipe_selected"] = recipe_query.strip()

# --- MEAL SELECTION & NUTRI SCORE ---
if "recipe_selected" in st.session_state:
    st.markdown("#### 🍽️ Select the meal type")
    meal_type = st.selectbox("Meal", ["🍽️ Select your meal", "breakfast", "lunch", "dinner"], key="meal_select")

    if meal_type != "🍽️ Select your meal":
        with st.spinner("Fetching nutrition score..."):
            try:
                resp = requests.post(API_URL, json={"recipe_name": st.session_state["recipe_selected"], "meal_type": meal_type})
                resp.raise_for_status()
                data = resp.json()

                nutri = data.get("nutri_score")
                if isinstance(nutri, dict):
                    st.markdown("#### 🥗 Nutrition Breakdown")
                    pictos = {"Energy_ratio":"⚡️","Carbohydrates_ratio":"🍞","Proteins_ratio":"🐟","Fat_ratio":"🧈"}
                    labels = {"Energy_ratio":"Energy","Carbohydrates_ratio":"Carbohydrates","Proteins_ratio":"Proteins","Fat_ratio":"Fat"}
                    for k, v in nutri.items():
                        if k in labels:
                            emoji, label = pictos[k], labels[k]
                            color = "#e74c3c" if v > 1 else "#2ecc71"
                            st.markdown(f"<div style='display:flex; align-items:center;'>"
                                        f"{emoji}<strong>{label}:</strong>"
                                        f"<span style='background:{color};color:#fff;padding:3px 8px;border-radius:8px;margin-left:4px;'>{v:.2f}</span>"
                                        f"</div>", unsafe_allow_html=True)
                else:
                    st.warning("No valid nutrition score returned.")
            except Exception as e:
                st.error(f"Nutri API error: {e}")

        # --- Address input ---
        st.markdown("---")
        st.markdown("### 📍 Enter your address to map suppliers")
        user_address = st.text_input("Enter your full address", placeholder="e.g. 15 rue de la paix, Paris", key="user_address")

        user_coords = None
        map_points = []
        if user_address:
            try:
                geo = requests.get("https://nominatim.openstreetmap.org/search", params={"q": user_address, "format": "json"}, headers={"User-Agent": "Y-TRUST-App"})
                geo.raise_for_status()
                geo_data = geo.json()
                if geo_data:
                    lat = float(geo_data[0]["lat"])
                    lon = float(geo_data[0]["lon"])
                    user_coords = (lat, lon)
                    map_points.append({"lat": lat, "lon": lon})
                    st.success("Address geolocated and added to the map.")
                else:
                    st.warning("Could not geolocate the address.")
            except Exception as e:
                st.error(f"Error during geolocation: {e}")

        # --- INGREDIENTS & ORIGIN FROM /api/recipe ---
        try:
            st.markdown("### 🧾 Ingredient origin and suppliers")
            recipe_data = requests.post(RECIPE_API_URL, json={"recipe_name": st.session_state["recipe_selected"]})
            recipe_data.raise_for_status()
            recipe_json = recipe_data.json()

            all_ings = recipe_json.get("quantities_g", [])
            if not all_ings:
                st.warning("No ingredients returned for this recipe.")
            else:
                idf_suppliers = []
                for i in all_ings:
                    if i.get("is_idf_supplier") and i.get("latitude") and i.get("longitude"):
                        lat = i.get("latitude")
                        lon = i.get("longitude")
                        supplier = {
                            "name": i.get("matched_product"),
                            "lat": lat,
                            "lon": lon,
                            "distance_km": geodesic(user_coords, (lat, lon)).km if user_coords else None
                        }
                        idf_suppliers.append(supplier)
                        map_points.append({"lat": lat, "lon": lon})

                if map_points:
                    st.map(pd.DataFrame(map_points))

                if idf_suppliers:
                    st.markdown("### 🛒 Local Suppliers (IDF)")
                    for s in idf_suppliers:
                        dist = f" ({s['distance_km']:.1f} km)" if s.get("distance_km") else ""
                        st.markdown(f"- **{s['name']}**{dist}")
                else:
                    st.info("No local suppliers for this recipe.")

                # Grouping by country code
                st.markdown("### 🌍 Ingredients by Origin")
                origin_map = {0: ("Île-de-France", "🏙️"), 1: ("France", "🇫🇷"), 2: ("Europe", "🇪🇺"), 3: ("World", "🌍")}
                grouped = {0: [], 1: [], 2: [], 3: []}

                for i in all_ings:
                    try:
                        code = int(i.get("country_code", 3))
                    except:
                        code = 3
                    grouped.setdefault(code, []).append(i.get("matched_product", "Unknown"))

                for code in [0, 1, 2, 3]:
                    label, emoji = origin_map[code]
                    items = grouped.get(code, [])
                    if items:
                        st.markdown(f"#### {emoji} {label}")
                        for item in items:
                            st.markdown(f"- {item}")

        except Exception as e:
            st.error(f"Error while loading ingredient data: {e}")
