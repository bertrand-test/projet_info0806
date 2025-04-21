import os
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

# Fonction pour analyser un fichier CSV et extraire les statistiques
def analyze_file(uploaded_file):
    # Charger le fichier CSV directement à partir de l'objet téléchargé
    df = pd.read_csv(uploaded_file)
    print("salut")
    
    # Exclure les valeurs où la vitesse est à 0 pour certaines analyses
    #df_filtered = df[df["Speed"] > 0]

    # Conversion de la vitesse de m/s en km/h
    df["Speed"] = df["Speed"] * 3.6
    
    # Appliquer un filtre Savitzky-Golay pour lisser les variations naturelles du capteur
    df["Accelerometer-X"] = savgol_filter(df["Accelerometer-X"], window_length=15, polyorder=2)
    df["Accelerometer-Y"] = savgol_filter(df["Accelerometer-Y"], window_length=15, polyorder=2)
    df["Speed"] = savgol_filter(df["Speed"], window_length=15, polyorder=2)  # Lissage de la vitesse
    
    # Paramètres sélectionnés
    mean_speed = np.mean(df["Speed"])  # Vitesse moyenne
    max_speed = np.max(df["Speed"])  # Vitesse maximale
    #min_speed = np.min(df["Speed"])  # Vitesse minimale
    
    std_x = np.std(df["Accelerometer-X"]) # Ecart type accélération en x
    std_y = np.std(df["Accelerometer-Y"]) # Ecart type accélération en y
    
    # Temps passé à l'arrêt (pourcentage)
    stop_time_percentage = (len(df[df["Speed"] == 0]) / len(df)) * 100
    
    # Nouvelle métrique : variation de la vitesse
    df["Speed_variation"] = df["Speed"].diff(periods=5).fillna(0)
    mean_speed_variation = np.mean(np.abs(df["Speed_variation"])) 

    # Retourner le DataFrame traité
    return {
        "Fichier": uploaded_file.name,  # Utilisation du nom du fichier téléchargé
        "Vitesse Moyenne (km/h)": mean_speed,
        "Vitesse Maximal (km/h)": max_speed,
        "Ecart type X (m/s²)": std_x,
        "Ecart type Y (m/s²)": std_y,
        "Stop Time (%)": stop_time_percentage,  # Temps passé à l'arrêt en %
        "Variation vitesse": mean_speed_variation
    }
