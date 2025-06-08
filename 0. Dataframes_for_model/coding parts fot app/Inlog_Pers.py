import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk
import random
import geocoder  # Voor automatische locatiebepaling
from datetime import datetime  # Voor het bijhouden van het tijdstip

# Laad gebruikersdata met alleen de benodigde kolommen
def laad_gebruikers_data(bestand='gebruikers_data.csv'):
    try:
        df = pd.read_csv(bestand)
        # Zorg ervoor dat de 'Gebruiker_ID' kolom altijd aanwezig is
        if 'Gebruiker_ID' not in df.columns:
            df['Gebruiker_ID'] = np.nan  # Of een ander standaard ID als dat gewenst is
        # Zorg ervoor dat de 'Tijdstip' kolom aanwezig is
        if 'Tijdstip' not in df.columns:
            df['Tijdstip'] = np.nan  # Maak een lege 'Tijdstip' kolom aan als die er nog niet is
        # Filter de DataFrame om alleen de benodigde kolommen te behouden
        kolommen = ['Gebruiker_ID', 'Voornaam', 'Tussen voegsel', 'Achternaam', 'Provincie', 'Bodemtype', 'Tuin_m2', 'Coördinaten', 'Tijdstip']
        return df[kolommen] if all(kol in df.columns for kol in kolommen) else pd.DataFrame(columns=kolommen)
    except FileNotFoundError:
        # Als het bestand niet bestaat, maak een lege DataFrame met de vereiste kolommen
        return pd.DataFrame(columns=['Gebruiker_ID', 'Voornaam', 'Tussen voegsel', 'Achternaam', 'Provincie', 'Bodemtype', 'Tuin_m2', 'Coördinaten', 'Tijdstip'])


# Sla gebruikersdata op met alleen de benodigde kolommen
def sla_gebruikers_data_op(df, bestand='gebruikers_data.csv'):
    df.to_csv(bestand, index=False)

# Voeg nieuwe gebruiker toe of haal bestaande ID op
def voeg_nieuwe_gebruiker_toe(voornaam, tussenvoegsel, achternaam, gebruikers_df):
    bestaande = gebruikers_df[(
        gebruikers_df["Voornaam"].fillna('') == voornaam) & 
        (gebruikers_df["Tussen voegsel"].fillna('') == tussenvoegsel) & 
        (gebruikers_df["Achternaam"].fillna('') == achternaam)
    ]

    if not bestaande.empty:
        bestaande_id = bestaande.iloc[0]["Gebruiker_ID"]
        # Kijk of er al een Tijdstip is, anders voeg een nieuwe toe
        if pd.isna(bestaande.iloc[0]["Tijdstip"]):
            bestaande.iloc[0]["Tijdstip"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        while True:
            nieuwe_id = str(random.randint(100000, 999999))
            if nieuwe_id not in gebruikers_df["Gebruiker_ID"].astype(str).values:
                break
        bestaande_id = nieuwe_id

    nieuwe_gebruiker = pd.Series({
        'Tijdstip': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Gebruiker_ID': bestaande_id,
        'Voornaam': voornaam,
        'Tussen voegsel': tussenvoegsel,
        'Achternaam': achternaam,
        'Provincie': None,
        'Bodemtype': None,
        'Tuin_m2': None,
        'Coördinaten': None
    })

    return nieuwe_gebruiker, gebruikers_df

# Bepaal provincie via IP
def bepaal_provincie():
    try:
        g = geocoder.ip('me')
        provincie = g.state
        return provincie if provincie else "Onbekend"
    except Exception as e:
        print(f"⚠️ Fout bij bepalen provincie: {e}")
        return "Onbekend"

# Start de GUI
def start_gui():
    global gebruikers_df

    root = tk.Tk()
    root.title("Gebruikersvoorkeuren")

    entries = {}
    keuzes = {
        "Provincie": ["Zuid-Holland", "Groningen", "Utrecht", "Noord-Brabant", "Limburg"],
        "Bodemtype": ["Zand", "Klei", "Leem", "Kalkrijk"]
    }

    numeriek_invul = [
        "Tuin_m2"
    ]

    # Naamvelden
    tk.Label(root, text="Voornaam:").grid(row=0, column=0, sticky="w")
    voornaam_entry = tk.Entry(root)
    voornaam_entry.grid(row=0, column=1)

    tk.Label(root, text="Tussen voegsel:").grid(row=1, column=0, sticky="w")
    tussenvoegsel_entry = tk.Entry(root)
    tussenvoegsel_entry.grid(row=1, column=1)

    tk.Label(root, text="Achternaam:").grid(row=2, column=0, sticky="w")
    achternaam_entry = tk.Entry(root)
    achternaam_entry.grid(row=2, column=1)

    row = 3
    for kolom, opties in keuzes.items():
        tk.Label(root, text=kolom + ":").grid(row=row, column=0, sticky="w")
        cb = ttk.Combobox(root, values=opties, state="readonly")
        cb.grid(row=row, column=1)
        entries[kolom] = cb
        row += 1

    for kolom in numeriek_invul:
        tk.Label(root, text=kolom + ":").grid(row=row, column=0, sticky="w")
        entry = tk.Entry(root)
        entry.grid(row=row, column=1)
        entries[kolom] = entry
        row += 1

    # Automatisch provincie invullen
    provincie = bepaal_provincie()
    entries["Provincie"].set(provincie)

    def on_next():
        global gebruikers_df

        voornaam = voornaam_entry.get().strip()
        tussenvoegsel = tussenvoegsel_entry.get().strip()
        achternaam = achternaam_entry.get().strip()

        nieuwe_gebruiker, gebruikers_df_local = voeg_nieuwe_gebruiker_toe(
            voornaam, tussenvoegsel, achternaam, gebruikers_df)

        for kolom in keuzes:
            waarde = entries[kolom].get()
            if waarde:
                nieuwe_gebruiker[kolom] = waarde

        for kolom in numeriek_invul:
            invoer = entries[kolom].get()
            try:
                nieuwe_gebruiker[kolom] = float(invoer) if invoer else np.nan
            except ValueError:
                nieuwe_gebruiker[kolom] = np.nan

        # Voeg coördinaten toe aan deze gebruiker
        try:
            g = geocoder.ip('me')
            locatie = g.latlng
            nieuwe_gebruiker['Coördinaten'] = locatie if locatie else "Onbekend"
        except Exception as e:
            print(f"⚠️ Fout bij ophalen coördinaten: {e}")
            nieuwe_gebruiker['Coördinaten'] = "Onbekend"

        gebruikers_df_local = pd.concat([gebruikers_df_local, nieuwe_gebruiker.to_frame().T], ignore_index=True)

        # Update de globale gebruikers_df
        gebruikers_df = gebruikers_df_local
        sla_gebruikers_data_op(gebruikers_df)

        print("👍 Gebruiker succesvol toegevoegd.")
        
        # Sluit de GUI pas na het opslaan van de gegevens
        root.quit()
        root.destroy()

    tk.Button(root, text="Next", command=on_next).grid(row=row, column=0, columnspan=2, pady=10)
    root.mainloop()

# Hoofduitvoering
gebruikers_df = laad_gebruikers_data()
start_gui()

gebruikers_df
