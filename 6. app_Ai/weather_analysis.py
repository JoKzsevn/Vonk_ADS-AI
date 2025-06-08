from datetime import datetime
from dateutil.relativedelta import relativedelta
from timezonefinder import TimezoneFinder
import pandas as pd
import numpy as np
from meteostat import Stations, Daily
from pvlib.location import Location
import ast

def splits_coordinaten(df):
    latitudes = []
    longitudes = []

    for coord in df['Coördinaten']:
        try:
            if isinstance(coord, str) and coord.startswith('['):
                coord = ast.literal_eval(coord)
            if isinstance(coord, (list, tuple)) and len(coord) == 2:
                latitudes.append(coord[0])
                longitudes.append(coord[1])
            else:
                latitudes.append(None)
                longitudes.append(None)
        except:
            latitudes.append(None)
            longitudes.append(None)

    df['Latitude'] = latitudes
    df['Longitude'] = longitudes
    return df

def verzamel_en_bereken_weerdata():
    gebruikers_df = pd.read_csv("Geb_data.csv")

    laatste_lat = gebruikers_df['Latitude'].iloc[-1]
    laatste_lon = gebruikers_df['Longitude'].iloc[-1]
    gebruikers_id = gebruikers_df['Gebruiker_ID'].iloc[-1]

    tf = TimezoneFinder()
    plaatsnaam = tf.timezone_at(lat=laatste_lat, lng=laatste_lon)

    end = datetime.now()
    start = (end - relativedelta(years=3)).replace(day=1)

    station = Stations().nearby(laatste_lat, laatste_lon).fetch(1)
    station_id = station.index[0]
    data = Daily(station_id, start, end).fetch()

    df_dag = data[['tavg', 'prcp', 'wspd']]
    df_dag.index = pd.to_datetime(df_dag.index)

    locatie = Location(laatste_lat, laatste_lon, plaatsnaam)

    zon_hoogtes = []
    zonsopkomst_tijden = []
    zonsondergang_tijden = []

    for datum in df_dag.index:
        uren = pd.date_range(datum.strftime('%Y-%m-%d 00:00:00'), periods=24, freq='H', tz=plaatsnaam)
        zonne_positie = locatie.get_solarposition(uren)
        zonhoogte_dag = zonne_positie['apparent_elevation'].mean()
        zon_hoogtes.append(zonhoogte_dag)

        try:
            zonsopkomst = zonne_positie[zonne_positie['apparent_elevation'] > 0].index[0]
            zonsondergang = zonne_positie[zonne_positie['apparent_elevation'] > 0].index[-1]
            zonsopkomst_tijden.append(zonsopkomst.strftime('%H:%M'))
            zonsondergang_tijden.append(zonsondergang.strftime('%H:%M'))
        except IndexError:
            zonsopkomst_tijden.append("00:00")
            zonsondergang_tijden.append("00:00")

    df_dag['zonhoogte (°)'] = zon_hoogtes
    df_dag['zonsopkomst'] = zonsopkomst_tijden
    df_dag['zonsondergang'] = zonsondergang_tijden

    df_dag['hitte_index (°F)'] = df_dag['tavg'].apply(lambda c: c * 1.8 + 32).round(2)

    df_dag = df_dag.rename(columns={
        'tavg': 'temp (°C)',
        'prcp': 'neerslag (mm)',
        'wspd': 'windsnelheid (m/s)',
    })

    df_dag['zonsondergang_dt'] = pd.to_datetime(df_dag['zonsondergang'], format='%H:%M', errors='coerce')
    df_dag['zonsopkomst_dt'] = pd.to_datetime(df_dag['zonsopkomst'], format='%H:%M', errors='coerce')
    df_dag['zonuren'] = (df_dag['zonsondergang_dt'] - df_dag['zonsopkomst_dt']).dt.total_seconds() / 3600

    df_dag = df_dag.drop(columns=['zonsondergang', 'zonsopkomst', 'zonsondergang_dt', 'zonsopkomst_dt'])
    df_dag = df_dag.fillna(0)

    df_maand = df_dag.resample('M').mean().round(2)
    df_maand['Gebruiker_ID'] = gebruikers_id

    df_maand = df_maand.reset_index()

    bestand_maand = f"data_maand_{gebruikers_id}.csv"
    df_maand.to_csv(bestand_maand, index=False)

    return df_maand