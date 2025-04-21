import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
from fonctions import analyze_file
from IterativeNeighbors import IterativeNeighbors

# --- Titre ---
st.set_page_config(page_title="Analyse du Comportement Routier", layout="wide")
st.title("📊 Analyse du Comportement Routier")

# --- Sidebar : Chargement des fichiers CSV ---
st.sidebar.header("📂 Chargement du fichier")
uploaded_file = st.sidebar.file_uploader("Choisir un fichier CSV", type=["csv"])

if uploaded_file is not None:
    # Analyse du fichier uploadé
    file_features = analyze_file(uploaded_file)

    # Chargement du fichier général (historique de données)
    file_path = 'summary_by_3min.csv'
    df = pd.read_csv(file_path)

    # Création d’un DataFrame pour le fichier uploadé
    df_target = pd.DataFrame([file_features])

    # Vérification : si le point cible est déjà dans les données
    is_duplicate = (df == df_target.iloc[0]).all(axis=1).any()

    if is_duplicate:
        st.warning("⚠️ Le point cible est déjà présent dans les données historiques.")
        df_full = df.copy()
    else:
        df_full = pd.concat([df, df_target], ignore_index=True)

    # Ajout d’une colonne pour marquer la ligne cible
    df_full["Is_Target"] = False
    if not is_duplicate:
        df_full.loc[df_full.index[-1], "Is_Target"] = True
    else:
        # Marquer le premier doublon trouvé comme Target
        idx_target = (df == df_target.iloc[0]).all(axis=1)
        df_full.loc[idx_target.idxmax(), "Is_Target"] = True

    # Assure-toi que les noms de colonnes sont tous des chaînes
    df_full.columns = df_full.columns.astype(str)

    # Préparation des données pour le clustering
    df_full_without_name = df_full.drop(columns=[df_full.columns[0], "Is_Target"])
    scaler = StandardScaler()
    df_scaled = scaler.fit_transform(df_full_without_name)

    # --- Sidebar : Paramètres de clustering ---
    st.sidebar.subheader("🔍 Paramètres de clustering")
    clustering_method = st.sidebar.selectbox("Méthode de clustering", ["KMeans", "DBSCAN", "Agglomerative", "IterativeNeighbors"])

    if clustering_method == "DBSCAN":
        eps = st.sidebar.slider("eps (rayon)", 0.1, 5.0, 1.0, 0.1)
        min_samples = st.sidebar.slider("min_samples", 1, 20, 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
    elif clustering_method == "KMeans":
        n_clusters = st.sidebar.slider("Nombre de clusters", 2, 10, 3)
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    elif clustering_method == "Agglomerative":
        n_clusters = st.sidebar.slider("Nombre de clusters", 2, 10, 3)
        linkage_method = st.sidebar.selectbox("Méthode de liaison", ["ward", "complete", "average", "single"])
        model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage_method)
    elif clustering_method == "IterativeNeighbors":
        model = IterativeNeighbors(k=5, max_clusters=3)

    # Application du clustering
    clusters = model.fit_predict(df_scaled)
    df_full['Cluster'] = clusters

    # --- Affichage des résultats ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Nombre de valeurs par cluster")
        fig1, ax1 = plt.subplots(figsize=(4, 3))
        cluster_counts = df_full["Cluster"].value_counts().sort_index()
        ax1.bar(cluster_counts.index, cluster_counts.values, color=plt.cm.Set2.colors)
        ax1.set_xlabel("Cluster", fontsize=8)
        ax1.set_ylabel("Nombre", fontsize=8)
        ax1.tick_params(labelsize=6)
        fig1.tight_layout()
        st.pyplot(fig1)

    with col2:
        st.subheader("🧭 Clusters PCA")
        pca = PCA(n_components=2)
        df_pca = pca.fit_transform(df_scaled)

        fig2, ax2 = plt.subplots(figsize=(4, 3))
        clusters = df_full["Cluster"].unique()
        colors = plt.cm.Set2.colors

        # Tracer tous les points par cluster
        for i, cluster in enumerate(clusters):
            mask = (df_full["Cluster"] == cluster) & (~df_full["Is_Target"])
            ax2.scatter(
                df_pca[mask, 0],
                df_pca[mask, 1],
                label=f"Cluster {cluster}",
                color=colors[i % len(colors)],
                s=40,
                edgecolor='black',
                marker='o'
            )

        # Tracer le point cible avec la même couleur que son cluster
        target_mask = df_full["Is_Target"]
        if target_mask.any():
            target_cluster = df_full.loc[target_mask, "Cluster"].values[0]
            cluster_index = list(clusters).index(target_cluster)
            target_color = colors[cluster_index % len(colors)]
            ax2.scatter(
                df_pca[target_mask, 0],
                df_pca[target_mask, 1],
                color=target_color,
                s=120,
                marker='X',
                edgecolor='black',
                linewidths=2,
                label="Target"
            )

        ax2.set_title("PCA", fontsize=8)
        ax2.tick_params(labelsize=6)
        ax2.legend(loc='upper left', fontsize=6, title="Clusters", title_fontsize=7)
        fig2.tight_layout()
        st.pyplot(fig2)

    # --- Tableau final trié ---
    st.subheader("📋 Données triées par cluster")
    df_sorted = df_full.sort_values(by="Cluster")
    st.dataframe(df_sorted.reset_index(drop=True))
    
    # --- Reclustering en divisant chaque cluster en deux ---
    st.markdown("### 🔁 Reclustering (chaque cluster divisé en 2)")

    # Re-demander l'algo
    st.sidebar.subheader("🔁 Choix de l'algorithme pour diviser les clusters")
    reclustering_algo = st.sidebar.selectbox("Algorithme de reclustering", ["KMeans", "Agglomerative"])

    # Initialiser un DataFrame vide pour le nouveau clustering
    reclustered_points = []
    new_labels = []

    for cluster_id in sorted(df_full["Cluster"].unique()):
        mask = df_full["Cluster"] == cluster_id
        cluster_data = df_scaled[mask]

        if reclustering_algo == "KMeans":
            model = KMeans(n_clusters=2, random_state=42, n_init=10)
        else:
            model = AgglomerativeClustering(n_clusters=2)

        sub_labels = model.fit_predict(cluster_data)

        for idx, sub_label in zip(df_full[mask].index, sub_labels):
            reclustered_points.append(idx)
            new_labels.append(cluster_id * 2 + sub_label)

    df_full.loc[reclustered_points, "Recluster"] = new_labels

    # PCA
    pca = PCA(n_components=2)
    df_pca = pca.fit_transform(df_scaled)

    # Définir une palette bien contrastée
    color_palette = plt.cm.tab10.colors

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📍 Clustering initial")
        fig3, ax3 = plt.subplots(figsize=(4, 3))

        for cluster in sorted(df_full["Cluster"].unique()):
            mask = df_full["Cluster"] == cluster
            ax3.scatter(
                df_pca[mask, 0], df_pca[mask, 1],
                label=f"Cluster {cluster}",
                color=color_palette[cluster % len(color_palette)],
                s=40, edgecolor='black', marker='o'
            )

        # Tracer une seule croix pour la cible
        target_index = df_full[df_full["Is_Target"]].index[0]
        target_cluster = df_full.loc[target_index, "Cluster"]
        ax3.scatter(
            df_pca[target_index, 0], df_pca[target_index, 1],
            color=color_palette[target_cluster % len(color_palette)],
            s=100, marker='X', edgecolors='black', linewidths=1.5, label="Target"
        )

        ax3.set_title("PCA Clustering Initial", fontsize=8)
        ax3.tick_params(labelsize=6)
        ax3.legend(loc='upper left', fontsize=6, title_fontsize=7)
        fig3.tight_layout()
        st.pyplot(fig3)

    with col4:
        st.subheader("🔀 Reclustering en 6 clusters")
        fig4, ax4 = plt.subplots(figsize=(4, 3))

        for recluster in sorted(df_full["Recluster"].dropna().unique()):
            mask = df_full["Recluster"] == recluster
            ax4.scatter(
                df_pca[mask, 0], df_pca[mask, 1],
                label=f"Cluster {int(recluster)}",
                color=color_palette[int(recluster) % len(color_palette)],
                s=40, edgecolor='black', marker='o'
            )

        # Tracer la croix target bien visible dans son nouveau cluster
        target_index = df_full[df_full["Is_Target"]].index[0]
        target_recluster = int(df_full.loc[target_index, "Recluster"])
        ax4.scatter(
            df_pca[target_index, 0], df_pca[target_index, 1],
            color=color_palette[target_recluster % len(color_palette)],
            s=100, marker='X', edgecolors='black', linewidths=1.5, label="Target"
        )

        ax4.set_title("PCA Reclustering (6)", fontsize=8)
        ax4.tick_params(labelsize=6)
        ax4.legend(loc='upper left', fontsize=6, title_fontsize=7)
        fig4.tight_layout()
        st.pyplot(fig4)

    # --- Afficher les descriptions des clusters ---
    st.subheader("📌 Analyse des clusters : Vitesse moyenne et variation")

    cluster_descriptions = {}

    for cluster in sorted(df_full["Recluster"].dropna().unique()):
        cluster_data = df_full[df_full["Recluster"] == cluster]

        mean_speed = cluster_data['Vitesse Moyenne (km/h)'].mean()
        speed_variation = cluster_data['Variation vitesse'].std()

        cluster_descriptions[int(cluster)] = {
            "vitesse_moyenne": mean_speed,
            "variation": speed_variation
        }

    # Attribution relative des types de conduite
    cluster_labels = {}

    # Trier les clusters par vitesse moyenne (du plus rapide au plus lent)
    sorted_clusters = sorted(cluster_descriptions.items(), key=lambda x: x[1]['vitesse_moyenne'], reverse=True)

    # Regrouper en paires : [autoroute, périurbain, urbain]
    group_names = ["Autoroute", "Périurbain", "Urbain"]

    for i in range(0, 6, 2):
        c1_id, c1_metrics = sorted_clusters[i]
        c2_id, c2_metrics = sorted_clusters[i + 1]

        # Choisir l'agressif selon la variation la plus élevée
        if c1_metrics['variation'] > c2_metrics['variation']:
            agressif_id, normal_id = c1_id, c2_id
        else:
            agressif_id, normal_id = c2_id, c1_id

        route_type = group_names[i // 2]

        cluster_labels[normal_id] = route_type
        cluster_labels[agressif_id] = route_type + " + Agressif"


    # Affichage sous forme de graphique avec légende
    fig5, ax5 = plt.subplots(figsize=(3, 1))
    ax5.axis('off')  # Pas de grille ni d'axe

    for cluster_id, label in cluster_labels.items():
        ax5.scatter([], [], label=f"Cluster {cluster_id}: {label}",
                    color=color_palette[cluster_id % len(color_palette)], s=40)

    ax5.legend(loc='center', fontsize=7)
    fig5.tight_layout()
    st.pyplot(fig5)
else:
    st.info("Veuillez charger un fichier CSV dans la barre latérale.")
