from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import pandas as pd
import os
import random
from datetime import datetime
import geocoder
from weather_analysis import verzamel_en_bereken_weerdata

app = Flask(__name__)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    return value.strftime(format)

def split_naam_volledig(naam):
    delen = naam.strip().split()
    if len(delen) == 0:
        return "", "", ""
    elif len(delen) == 1:
        return delen[0], "", ""
    elif len(delen) == 2:
        return delen[0], "", delen[1]
    else:
        return delen[0], " ".join(delen[1:-1]), delen[-1]

def genereer_gebruiker_id(voornaam, tussenvoegsel, achternaam, gebruikers_df):
    bestaande = gebruikers_df[
        (gebruikers_df["Voornaam"].fillna('').str.lower() == voornaam.lower()) &
        (gebruikers_df["Tussenvoegsel"].fillna('').str.lower() == tussenvoegsel.lower()) &
        (gebruikers_df["Achternaam"].fillna('').str.lower() == achternaam.lower())
    ]
    if not bestaande.empty:
        return bestaande.iloc[0]["Gebruiker_ID"]
    else:
        while True:
            nieuwe_id = str(random.randint(100000, 999999))
            if nieuwe_id not in gebruikers_df["Gebruiker_ID"].astype(str).values:
                return nieuwe_id

def bepaal_locatie():
    try:
        g = geocoder.ip('me')
        provincie = g.state if g.state else "Onbekend"
        lat, lng = g.latlng if g.latlng else (None, None)
        return provincie, lat, lng
    except:
        return "Onbekend", None, None

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        data = {
            "Naam": request.form.get("naam"),
            "Geboortejaar": request.form.get("geboortejaar"),
            "Ervaring met tuinieren (jaren)": request.form.get("ervaring"),
            "Geslacht": request.form.get("geslacht"),
            "Soort woning": request.form.get("woning"),
            "Huisdieren": ', '.join(request.form.getlist("huisdieren")),
            "Tuinstijl": ', '.join(request.form.getlist("tuinstijl")),
            "Onderhoudsniveau": ', '.join(request.form.getlist("onderhoudsniveau")),
            "Allergieën": ', '.join(request.form.getlist("allergie")),
            "Budget": request.form.get("budget")
        }

        try:
            geboortejaar = int(data["Geboortejaar"])
            huidig_jaar = datetime.now().year
            leeftijd = huidig_jaar - geboortejaar
            if leeftijd < 0 or leeftijd > 120:
                raise ValueError("Ongeldige leeftijd")
            data["Leeftijd"] = leeftijd
            data["Ervaring met tuinieren (jaren)"] = int(data["Ervaring met tuinieren (jaren)"])
        except:
            message = "⚠️ Geboortejaar en ervaring moeten geldige getallen zijn."
            return render_template("index.html", message=message, jaren=range(1920, datetime.now().year + 1))

        voornaam, tussenvoegsel, achternaam = split_naam_volledig(data["Naam"])
        data["Voornaam"] = voornaam.lower()
        data["Tussenvoegsel"] = tussenvoegsel.lower()
        data["Achternaam"] = achternaam.lower()
        del data["Naam"]

        bestand = "Geb_data.csv"
        kolommen = [
            "Tijdstip", "Gebruiker_ID", "Voornaam", "Tussenvoegsel", "Achternaam", "Leeftijd",
            "Geslacht", "Provincie", "Latitude", "Longitude",
            "Ervaring met tuinieren (jaren)", "Soort woning",
            "Tuinstijl", "Onderhoudsniveau", "Allergieën", "Huisdieren", "Budget"
        ]

        if os.path.exists(bestand):
            gebruikers_df = pd.read_csv(bestand)
        else:
            gebruikers_df = pd.DataFrame(columns=kolommen)

        gebruiker_id = genereer_gebruiker_id(voornaam, tussenvoegsel, achternaam, gebruikers_df)
        provincie, lat, lng = bepaal_locatie()

        data["Gebruiker_ID"] = gebruiker_id
        data["Tijdstip"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data["Provincie"] = provincie
        data["Latitude"] = lat
        data["Longitude"] = lng

        for kolom in kolommen:
            if kolom not in data:
                data[kolom] = None

        gebruikers_df = pd.concat([gebruikers_df, pd.DataFrame([data])], ignore_index=True)
        gebruikers_df.to_csv(bestand, index=False)

        try:
            weerdata_df = verzamel_en_bereken_weerdata()
            laatste_maand = weerdata_df.iloc[-1].to_dict()
            return render_template("resultaat.html", 
                                   gebruiker_id=gebruiker_id,
                                   voornaam=voornaam.capitalize(),
                                   achternaam=achternaam.capitalize(),
                                   weerdata=laatste_maand)
        except Exception as e:
            print(f"Fout bij ophalen weerdata: {e}")
            return render_template("resultaat.html",
                                   gebruiker_id=gebruiker_id,
                                   voornaam=voornaam.capitalize(),
                                   achternaam=achternaam.capitalize(),
                                   weerdata={"error": "Kon weerdata niet ophalen"})

    return render_template("index.html", jaren=range(1920, datetime.now().year + 1))

@app.route("/tuinen", methods=["GET", "POST"])
def tuinen():
    df = pd.read_csv("tuinen.csv")
    if 'afbeelding_url' not in df.columns:
        df['afbeelding_url'] = None
        
    # de gebruiker id is de laatste gebruiker uit de Geb_data.csv
    gebruikers_df = pd.read_csv("Geb_data.csv")
    gebruiker_id = gebruikers_df["Gebruiker_ID"].iloc[-1]

    if request.method == "POST":
        tuin_id = request.form.get("tuin_id")
        beoordeling = request.form.get("beoordeling")  # 'like' of 'dislike'

        filename = f"tuin_feedback_{gebruiker_id}.csv"
        feedback = pd.DataFrame([[gebruiker_id, tuin_id, beoordeling]], 
                              columns=["Gebruiker_ID", "Tuin_ID", "Beoordeling"])

        if os.path.exists(filename):
            bestaand = pd.read_csv(filename)
            # Update bestaande beoordeling als deze tuin al beoordeeld was
            bestaand = bestaand[bestaand["Tuin_ID"] != tuin_id]
            feedback = pd.concat([bestaand, feedback], ignore_index=True)

        feedback.to_csv(filename, index=False)
        return jsonify({"success": True})

    # Toon alleen tuinen die nog niet beoordeeld zijn
    beoordeelde_tuinen = []
    feedback_file = f"tuin_feedback_{gebruiker_id}.csv"
    if os.path.exists(feedback_file):
        beoordeelde_tuinen = pd.read_csv(feedback_file)["Tuin_ID"].tolist()
    
    tuinen = df[~df['id'].isin(beoordeelde_tuinen)].to_dict(orient="records")
    
    return render_template("tuinen.html", tuinen=tuinen, gebruiker_id=gebruiker_id)

@app.route("/overzicht")
def overzicht():
    gebruiker_id = request.args.get("gebruiker_id")
    filename = f"tuin_feedback_{gebruiker_id}.csv"
    if os.path.exists(filename):
        feedback_df = pd.read_csv(filename)
        df = pd.read_csv("tuinen.csv")
        merged = feedback_df.merge(df, left_on="Tuin_ID", right_on="id", how="left")
        return render_template("overzicht.html", feedback=merged.to_dict(orient="records"))
    return "Geen feedback gevonden."

@app.route("/download_feedback/<gebruiker_id>")
def download_feedback(gebruiker_id):
    filename = f"tuin_feedback_{gebruiker_id}.csv"
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "Feedbackbestand niet gevonden.", 404

@app.route("/reset_feedback")
def reset_feedback():
    gebruiker_id = request.args.get("gebruiker_id")
    filename = f"tuin_feedback_{gebruiker_id}.csv"
    
    if os.path.exists(filename):
        os.remove(filename)
        return redirect(url_for('tuinen', gebruiker_id=gebruiker_id))
    return "Geen feedback gevonden om te resetten", 404

if __name__ == "__main__":
    app.run(debug=True)
