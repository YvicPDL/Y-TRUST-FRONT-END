import streamlit as st
from PIL import Image
import requests
import os

# --- CONFIGURATION ---
API_URL = "https://y-trust-003-51424904642.europe-west1.run.app/api/recipescore"

# Try to load logo, fallback to text if not found
try:
    # First try current directory, then common locations
    logo_paths = [
        "logo Y-trust.png",
        "logo.png", 
        "assets/logo Y-trust.png",
        "images/logo Y-trust.png"
    ]
    
    logo = None
    for path in logo_paths:
        if os.path.exists(path):
            logo = Image.open(path)
            break
    
    if logo:
        st.set_page_config(
            page_title="Y-TRUST",
            page_icon=logo,
            layout="centered"
        )
    else:
        st.set_page_config(
            page_title="Y-TRUST",
            page_icon="🍽️",  # Using emoji as fallback
            layout="centered"
        )
except Exception:
    # If all fails, use emoji icon
    st.set_page_config(
        page_title="Y-TRUST",
        page_icon="🍽️",
        layout="centered"
    )

# --- PAGE TITLE ---
st.title("Y-TRUST")

# --- SEARCH BAR ---
st.markdown("#### 🔍 What recipe are you looking for?")

with st.form("search_form", clear_on_submit=False):
    col1, col2 = st.columns([5, 1])
    with col1:
        recipe_query = st.text_input(
            label="",
            placeholder="e.g. Bolognese sauce ...",
            label_visibility="collapsed",
            key="recipe_input"
        )
    with col2:
        submitted = st.form_submit_button("Search")

# Clear previous data when new search is submitted
if submitted and recipe_query.strip():
    # Clear all previous session state data
    keys_to_clear = ["nutri_score", "user_lat", "user_lon", "ingredients_data", "address_processed"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state["recipe_selected"] = recipe_query.strip()

# --- MEAL SELECTION ---
if "recipe_selected" in st.session_state:
    st.markdown("#### 🍽️ Select the meal type")
    meal_type = st.selectbox("Meal", ["🍽️ Select your meal", "breakfast", "lunch", "dinner"], key="meal_select")

    if meal_type != "🍽️ Select your meal":
        # Create a unique key for this recipe + meal combination
        current_combo = f"{st.session_state['recipe_selected']}_{meal_type}"
        
        # Only fetch nutrition data if we don't have it for this specific combo
        if st.session_state.get("current_combo") != current_combo:
            # Clear previous nutrition data when meal type changes
            if "nutri_score" in st.session_state:
                del st.session_state["nutri_score"]
            
            with st.spinner("Fetching nutrition score..."):
                try:
                    payload = {
                        "recipe_name": st.session_state["recipe_selected"],
                        "meal_type": meal_type
                    }
                    response = requests.post(API_URL, json=payload)
                    response.raise_for_status()
                    data = response.json()

                    nutri_score = data.get("nutri_score")
                    if nutri_score:
                        st.session_state["nutri_score"] = nutri_score
                        st.session_state["current_combo"] = current_combo
                except Exception as e:
                    st.error(f"Error calling API: {e}")
        
        # Display nutrition score if available
        if "nutri_score" in st.session_state:
            nutri_score = st.session_state["nutri_score"] 
            st.markdown("#### 🥗 Nutrition Breakdown")
            st.markdown("*The ideal meal has a value close to 1 for each nutritional component.*")

            pictos = {
                "Energy_ratio": "⚡️",
                "Carbohydrates_ratio": "🍞",
                "Proteins_ratio": "🐟",
                "Fat_ratio": "🧈"
            }

            label_mapping = {
                "Energy_ratio": "Energy",
                "Carbohydrates_ratio": "Carbohydrates",
                "Proteins_ratio": "Proteins",
                "Fat_ratio": "Fat"
            }

            for key in label_mapping:
                value = nutri_score.get(key)
                if value is not None:
                    emoji = pictos.get(key, "🔹")
                    label = label_mapping[key]
                    color = "#e74c3c" if value > 1 else "#2ecc71"

                    st.markdown(
                        f"<div style='display: flex; align-items: center; font-size: 1.1rem;'>"
                        f"<span style='font-size: 1.5rem; margin-right: 0.5rem;'>{emoji}</span>"
                        f"<strong style='width: 120px; display:inline-block;'>{label}</strong>"
                        f"<span style='background-color:{color}; color: white; "
                        f"padding: 3px 10px; border-radius: 12px;'>{value:.2f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

            # --- ADDRESS INPUT (VISIBLE ONLY AFTER RESULTS) ---
            st.markdown("---")
            st.markdown("#### 🏡 Enter your address")
            st.markdown("*We will suggest local suppliers for each ingredient.*")

            user_address = st.text_input(
                label="",
                placeholder="e.g. 15 rue de la paix, Paris",
                label_visibility="collapsed",
                key="address_input"
            )
            
            # --- GEOCODING AND INGREDIENT PROCESSING ---
            if user_address and user_address.strip():
                # Only process if address changed or not processed yet
                current_address = user_address.strip()
                if (st.session_state.get("processed_address") != current_address or 
                    "user_lat" not in st.session_state):
                    
                    with st.spinner("📍 Locating your address..."):
                        try:
                            geo_url = "https://nominatim.openstreetmap.org/search"
                            params = {
                                "q": current_address,
                                "format": "json"
                            }
                            response = requests.get(geo_url, params=params, headers={"User-Agent": "Y-TRUST-App"})
                            results = response.json()

                            if results:
                                lat = float(results[0]["lat"])
                                lon = float(results[0]["lon"])
                                
                                # Store coordinates and mark as processed
                                st.session_state["user_lat"] = lat
                                st.session_state["user_lon"] = lon
                                st.session_state["processed_address"] = current_address
                                
                                # Clear previous ingredients data when address changes
                                if "ingredients_data" in st.session_state:
                                    del st.session_state["ingredients_data"]
                                    
                            else:
                                st.warning("❗️Address not found. Try a more specific one.")
                                st.stop()
                        except Exception as e:
                            st.error(f"Geolocation failed: {e}")
                            st.stop()

                # Show address confirmation and map
                if "user_lat" in st.session_state and "user_lon" in st.session_state:
                    st.success("📍 Address found and mapped!")
                    
                    # Get ingredients data if not already loaded
                    if "ingredients_data" not in st.session_state:
                        with st.spinner("🔍 Finding local suppliers..."):
                            try:
                                recipe_name = st.session_state.get("recipe_selected", "")
                                ingredients_url = "https://y-trust-003-51424904642.europe-west1.run.app/api/ingredients/predict"
                                payload = {
                                    "recipe_name": recipe_name,
                                    "user_lat": st.session_state["user_lat"],
                                    "user_lon": st.session_state["user_lon"]
                                }
                                headers = {"accept": "application/json", "Content-Type": "application/json"}

                                ing_response = requests.post(ingredients_url, json=payload, headers=headers)
                                ing_response.raise_for_status()
                                ing_data = ing_response.json()
                                
                                # Store ingredients data
                                st.session_state["ingredients_data"] = ing_data
                                
                            except Exception as e:
                                st.error(f"Failed to load ingredient data: {e}")
                                st.stop()
                    
                    # Process and display ingredients data
                    if "ingredients_data" in st.session_state:
                        ing_data = st.session_state["ingredients_data"]
                        
                        if "ingredients" not in ing_data and "matches" not in ing_data:
                            st.warning("No ingredients found in the API response.")
                        else:
                            # Handle both possible response formats
                            ingredients = ing_data.get("matches", ing_data.get("ingredients", []))
                            
                            # Debug: Show raw data structure
                            with st.expander("🔍 Debug: View raw ingredient data"):
                                st.json(ing_data)

                            # --- Process suppliers with location ---
                            suppliers_with_location = []
                            suppliers_without_location = []
                            
                            for ing in ingredients:
                                if isinstance(ing, dict):
                                    supplier_info = {
                                        "name": ing.get("matched_product", "Unknown"),
                                        "lat": ing.get("latitude"),
                                        "lon": ing.get("longitude"),
                                        "distance_km": ing.get("distance_km"),
                                        "is_idf_supplier": ing.get("is_idf_supplier", False),
                                        "country_code": ing.get("country_code", 3)
                                    }
                                    
                                    # Check if supplier has valid coordinates
                                    if supplier_info["lat"] and supplier_info["lon"]:
                                        try:
                                            # Ensure coordinates are valid numbers
                                            supplier_info["lat"] = float(supplier_info["lat"])
                                            supplier_info["lon"] = float(supplier_info["lon"])
                                            suppliers_with_location.append(supplier_info)
                                        except (ValueError, TypeError):
                                            suppliers_without_location.append(supplier_info)
                                    else:
                                        suppliers_without_location.append(supplier_info)

                            # --- Display map with user location and suppliers ---
                            if suppliers_with_location:
                                # Create map with user location and suppliers
                                map_data = {
                                    "lat": [st.session_state["user_lat"]] + [s["lat"] for s in suppliers_with_location],
                                    "lon": [st.session_state["user_lon"]] + [s["lon"] for s in suppliers_with_location]
                                }
                                st.map(map_data)
                            else:
                                # Show just user location if no suppliers have coordinates
                                st.map(data={"lat": [st.session_state["user_lat"]], "lon": [st.session_state["user_lon"]]})

                            # --- Display suppliers with location ---
                            if suppliers_with_location:
                                st.markdown("### 🛒 Local Suppliers")
                                
                                # Display supplier information
                                for s in suppliers_with_location:
                                    distance_text = ""
                                    if s["distance_km"] is not None:
                                        try:
                                            distance = float(s["distance_km"])
                                            distance_text = f" ({distance:.1f} km away)"
                                        except (ValueError, TypeError):
                                            distance_text = " (distance unknown)"
                                    else:
                                        distance_text = " (distance unknown)"
                                    
                                    origin_emoji = "🏙️" if s["is_idf_supplier"] else "🌍"
                                    st.markdown(f"- {origin_emoji} **{s['name']}**{distance_text}")
                            
                            # --- Display suppliers without location ---
                            if suppliers_without_location:
                                st.markdown("### 🛍️ Other Suppliers")
                                for s in suppliers_without_location:
                                    origin_emoji = "🏙️" if s["is_idf_supplier"] else "🌍"
                                    st.markdown(f"- {origin_emoji} **{s['name']}** (location not available)")

                            # --- Display all ingredients grouped by origin ---
                            st.markdown("### 🌍 Ingredients by Origin")
                            origin_map = {
                                0: ("Île-de-France (Local)", "🏙️"),
                                1: ("France", "🇫🇷"),
                                2: ("Europe", "🇪🇺"),
                                3: ("International", "🌍")
                            }

                            grouped = {0: [], 1: [], 2: [], 3: []}
                            for ing in ingredients:
                                if isinstance(ing, dict):
                                    code = int(ing.get("country_code", 3))
                                    name = ing.get("matched_product", "Unknown")
                                    distance_km = ing.get("distance_km")
                                    
                                    # Add distance info if available
                                    distance_info = ""
                                    if distance_km is not None:
                                        try:
                                            distance = float(distance_km)
                                            distance_info = f" ({distance:.1f} km)"
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    grouped.setdefault(code, []).append(f"{name}{distance_info}")

                            for code in [0, 1, 2, 3]:
                                label, emoji = origin_map[code]
                                items = grouped.get(code, [])
                                if items:
                                    st.markdown(f"#### {emoji} {label}")
                                    for item in items:
                                        st.markdown(f"- **{item}**")

        else:
            st.warning("No nutrition score available for this recipe.")