def get_city_weather(city: str):
    """Return current weather info for a city using wttr.in."""
    import urllib.request, urllib.parse, json
    try:
        q = urllib.parse.quote(city)
        url = f'http://wttr.in/{q}?format=j1'
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.load(resp)
        cur = data.get('current_condition', [{}])[0]
        return {
            'temperature_C': cur.get('temp_C'),
            'temperature_F': cur.get('temp_F'),
            'weather_desc': cur.get('weatherDesc', [{}])[0].get('value'),
            'humidity': cur.get('humidity'),
            'wind_kph': cur.get('windspeedKmph'),
            'wind_dir': cur.get('winddir16Point')
        }
    except Exception as e:
        return f'Error: {e}'