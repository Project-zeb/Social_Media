import pandas as pd
import os

# Path to your CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), 'coordinate_districts_v3.csv')

# --- OPTIMIZED FALLBACKS ---
# These are major hubs in your grid range (23.0-31.5N, 76.0-89.5E) 
# that are missing from your current CSV.
CITY_REGISTRY = {
    'lucknow': (26.84, 80.94),
    'delhi': (28.61, 77.20),
    'new delhi': (28.61, 77.20),
    'noida': (28.53, 77.39),
    'ghaziabad': (28.66, 77.44)
}

def get_coords_from_district(district_name):
    try:
        search_name = str(district_name).strip().lower()
        
        # 1. Fast Lookup in Manual Registry
        if search_name in CITY_REGISTRY:
            raw_lat, raw_lon = CITY_REGISTRY[search_name]
        
        # 2. CSV Lookup (Optimized for performance)
        else:
            df = pd.read_csv(CSV_PATH)
            # Find exact match
            match = df[df['district'].str.lower().str.strip() == search_name]
            
            if not match.empty:
                raw_lat = float(match.iloc[0]['latitude'])
                raw_lon = float(match.iloc[0]['longitude'])
            else:
                return None, None

        # --- GRID SNAPPING (The "Logic" Layer) ---
        # Snaps to your 0.5 grid: np.arange(23.0, 31.5, 0.5)
        # 26.84 -> 27.0 | 25.59 -> 25.5
        lat = round(raw_lat * 2) / 2
        lon = round(raw_lon * 2) / 2
        
        # --- GRID BOUNDARY VALIDATION ---
        # Ensures coordinates are within your defined project zone
        if 23.0 <= lat <= 31.5 and 76.0 <= lon <= 89.5:
            return lat, lon
        
        print(f"⚠️ {district_name} snapped to ({lat}, {lon}) is outside the active grid.")
            
    except Exception as e:
        print(f"❌ Geo-Mapper Error: {e}")
        
    return None, None