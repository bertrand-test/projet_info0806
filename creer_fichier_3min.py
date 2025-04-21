import os
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter

# Durée d’un segment en secondes (3 minutes)
SEGMENT_DURATION = 3 * 60  # 180 secondes

def analyze_segment(segment, file_path, segment_index):
    # Conversion m/s → km/h
    segment["Speed"] *= 3.6

    # Lissage
    segment["Accelerometer-X"] = savgol_filter(segment["Accelerometer-X"], 15, 2)
    segment["Accelerometer-Y"] = savgol_filter(segment["Accelerometer-Y"], 15, 2)
    segment["Speed"] = savgol_filter(segment["Speed"], 15, 2)

    # Statistiques
    mean_speed = np.mean(segment["Speed"])
    max_speed = np.max(segment["Speed"])
    std_x = np.std(segment["Accelerometer-X"])
    std_y = np.std(segment["Accelerometer-Y"])
    stop_time_percentage = (len(segment[segment["Speed"] == 0]) / len(segment)) * 100
    segment["Speed_variation"] = segment["Speed"].diff(5).fillna(0)
    mean_speed_variation = np.mean(np.abs(segment["Speed_variation"]))

    return {
        "Fichier": file_path,
        "Vitesse Moyenne (km/h)": mean_speed,
        "Vitesse Maximal (km/h)": max_speed,
        "Ecart type X (m/s²)": std_x,
        "Ecart type Y (m/s²)": std_y,
        "Stop Time (%)": stop_time_percentage,
        "Variation vitesse": mean_speed_variation
    }

def process_file(file_path):
    df = pd.read_csv(file_path)

    # Si la fréquence est 1Hz, alors on découpe tous les 180 lignes
    segment_length = SEGMENT_DURATION  # nombre de lignes si 1Hz
    total_rows = len(df)
    num_segments = total_rows // segment_length

    results = []
    for i in range(num_segments):
        start = i * segment_length
        end = start + segment_length
        segment = df.iloc[start:end].copy()
        stats = analyze_segment(segment, file_path, i)
        results.append(stats)
    
    return results

def process_all_files():
    directory = "./"
    files = [f for f in os.listdir(directory) if f.endswith('.csv')]

    all_results = []
    for file in files:
        file_path = os.path.join(directory, file)
        all_results.extend(process_file(file_path))
    
    df_results = pd.DataFrame(all_results)
    df_results.to_csv("summary_by_3min.csv", index=False)

process_all_files()
