import requests

def get_live_weather_score(lat, lon, disaster_type):
    """
    Calls Open-Meteo to check if current weather matches the report.
    Returns a 'Weather Score' (0 to 20).
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation,wind_speed_10m&forecast_days=1"
        response = requests.get(url).json()
        
        # Get the most recent hourly data
        current_precip = response['hourly']['precipitation'][0]
        current_wind = response['hourly']['wind_speed_10m'][0]
        
        score = 0
        if disaster_type == 'FLOOD' and current_precip > 2.0:
            score = 20  # Strong match!
        elif disaster_type == 'STORM' and current_wind > 30:
            score = 20  # Strong match!
        elif current_precip > 0.5:
            score = 10  # Moderate match
            
        return score
    except:
        return 0