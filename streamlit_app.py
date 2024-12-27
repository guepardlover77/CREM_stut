import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import os
from datetime import datetime

st.set_page_config(page_title="Tut-v2 | CREM", page_icon="logo-tut.png", menu_items={
    'Get Help': 'https://www.crem.fr/contact/',
    'Report a bug': "mailto:web@crem.fr",
    'About': "# Bienvenue dans votre espace Tutorat ! Faites en bon usage ;)"})


# --- Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def save_image(image, username):
    """
    Save uploaded image to a permanent directory.
    Validate file size and store image if within limit.
    """
    MAX_SIZE_MB = 2
    forum_images_dir = "forum_images"
    os.makedirs(forum_images_dir, exist_ok=True)  # Ensure directory exists

    # Check file size
    image.seek(0, os.SEEK_END)
    size_mb = image.tell() / (1024 * 1024)
    image.seek(0)  # Reset pointer for reading
    if size_mb > MAX_SIZE_MB:
        raise ValueError(f"Le fichier est trop volumineux ({size_mb:.2f} Mo). La taille maximale est de {MAX_SIZE_MB} Mo.")

    # Save image
    image_filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    image_path = os.path.join(forum_images_dir, image_filename)
    with open(image_path, "wb") as f:
        f.write(image.read())
    return image_path


# --- Connexion Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)


# --- Fonctions Utilitaires ---
def read_sheet(sheet_name):
    """Lit les données d'une feuille Google Sheets en DataFrame."""
    return conn.read(worksheet=sheet_name, ttl=None)

def update_sheet(sheet_name, data):
    """Met à jour une feuille Google Sheets avec un DataFrame."""
    conn.update(worksheet=sheet_name, data=data)
    st.cache_data.clear()
    st.rerun()

def append_to_sheet(sheet_name, row):
    """Ajoute une ligne à une feuille Google Sheets."""
    data = read_sheet(sheet_name)
    data = pd.concat([data, pd.DataFrame([row])], ignore_index=True)
    update_sheet(sheet_name, data)

with st.sidebar.expander("Créer un compte"):
    new_username = st.text_input("Nouveau nom d'utilisateur")
    new_password = st.text_input("Nouveau mot de passe", type="password")
    create_account_button = st.button("Créer un compte")

if create_account_button and new_username and new_password:
    user_data = read_sheet("user_data")
    if new_username in user_data["username"].values:
        st.error("Ce nom d'utilisateur est déjà pris.")
    else:
        hashed_password = hash_password(new_password)
        new_user = {"username": new_username, "password": hashed_password}
        append_to_sheet("user_data", new_user)
        st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
        st.cache_data.clear()
        st.rerun()


# --- Authentification ---
st.sidebar.header("Connexion")
username = st.sidebar.text_input("Nom d'utilisateur")
password = st.sidebar.text_input("Mot de passe", type="password")
login_button = st.sidebar.button("Se connecter")


if username and password and login_button:
    st.session_state["authenticated"] = True
    st.session_state["username"] = username
    st.cache_data.clear()
    st.rerun()

# --- Application ---
if "authenticated" in st.session_state and st.session_state["authenticated"]:
    st.title(f"Bienvenue, {st.session_state['username']} !")

    # Onglets
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Suivi des QCM", "💬 Forum", "🐈 Chats", "📝 Task Manager"])

    # --- Suivi des QCM ---
    with tab1:
        st.header("Suivi des QCM")

        # Charger les données des QCM
        qcm_data = read_sheet("qcm_data")  # Lire les données depuis la feuille Google Sheets

        # Vérifier si la colonne 'username' existe
        if "username" in qcm_data.columns:
            user_qcm_data = qcm_data[qcm_data["username"] == st.session_state["username"]]
        else:
            st.error("La colonne 'username' est absente des données QCM. Veuillez vérifier la feuille Google Sheets.")
            st.stop()

        # Formulaire pour ajouter des données
        with st.form("qcm_form"):
            maths_qcm = st.number_input("Maths", min_value=0, value=0, step=1)
            bio_qcm = st.number_input("Biologie cellulaire", min_value=0, value=0, step=1)
            shs_qcm = st.number_input("Sciences humaines et sociales", min_value=0, value=0, step=1)
            submit_button = st.form_submit_button("Ajouter")

        if submit_button:
            new_entry = {
                "username": st.session_state["username"],
                "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "maths": maths_qcm,
                "biologie": bio_qcm,
                "sciences_humaines": shs_qcm,
            }
            append_to_sheet("qcm_data", new_entry)
            st.success("Données ajoutées avec succès !")
            st.cache_data.clear()
            st.rerun()

        if not user_qcm_data.empty:
            st.subheader("Progrès par matière")
            st.bar_chart(user_qcm_data[["maths", "biologie", "sciences_humaines"]].sum())

            st.subheader("Graphique des QCM par date")
            scatter_data = user_qcm_data.melt(
                id_vars=["date"],
                value_vars=["maths", "biologie", "sciences_humaines"],
                var_name="Matière",
                value_name="Nombre de QCM"
            )

            # Scatter plot with lines
            import plotly.express as px

            fig = px.line(
                scatter_data,
                x="date",
                y="Nombre de QCM",
                color="Matière",
                markers=True,
                title="Nombre de QCM par matière en fonction du temps",
                labels={"date": "Date", "Nombre de QCM": "Nombre de QCM"},
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)


    # --- Forum ---
    with tab2:
        st.header("Forum")

        # Ajouter un message au forum
        st.subheader("Poster un message")
        with st.form("forum_form"):
            title = st.text_input("Titre du message")
            message = st.text_area("Votre message")
            tags = st.text_input("Tags (séparés par des virgules)")
            image = st.file_uploader("Ajouter une image (optionnel, max. 2 Mo)", type=["png", "jpg", "jpeg"])
            post_button = st.form_submit_button("Poster")

        if post_button and title.strip() and message.strip():
            image_path = None
            if image:
                try:
                    image_path = save_image(image, st.session_state["username"])
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.success("Image téléchargée avec succès.")

            new_message = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "username": st.session_state["username"],
                "title": title,
                "message": message,
                "tags": tags,
                "image_path": image_path or "",
            }
            append_to_sheet("forum_data", new_message)
            st.success("Message posté avec succès !")

        st.subheader("Rechercher des messages")
        search_query = st.text_input("Rechercher par mot-clé ou tag")
        search_button = st.button("Rechercher")

        # Affichage des messages
        forum_data = read_sheet("forum_data")
        filtered_messages = forum_data

        if search_button and search_query.strip():
            search_query = search_query.lower()
            filtered_messages = forum_data[
                forum_data["title"].str.lower().str.contains(search_query) |
                forum_data["message"].str.lower().str.contains(search_query) |
                forum_data["tags"].str.lower().str.contains(search_query)
                ]

        st.subheader("Fil de discussion")
        if filtered_messages.empty:
            st.info("Aucun message trouvé.")
        else:
            for _, row in filtered_messages.iterrows():
                with st.expander(f"### {row['title']} (Posté le : {row['timestamp']})"):
                    st.write(f"**Tags :** {row['tags']}")
                    st.write(row["message"])
                    if pd.notna(row["image_path"]) and os.path.exists(row["image_path"]):
                        st.image(row["image_path"], use_container_width=True)
                    else:
                        st.write("Pas d'image associée à ce message.")

                    # Ajouter une réponse au message
                    st.subheader("Répondre au message")
                    with st.form(f"reply_form_{row['timestamp']}"):
                        reply_message = st.text_area("Votre réponse")
                        reply_button = st.form_submit_button("Répondre")

                    if reply_button and reply_message.strip():
                        new_reply = {
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "username": st.session_state["username"],
                            "parent_timestamp": row["timestamp"],
                            "reply": reply_message,
                        }
                        append_to_sheet("forum_replies", new_reply)
                        st.success("Réponse ajoutée avec succès !")

                    # Afficher les réponses existantes
                    st.subheader("Réponses")
                    replies_data = read_sheet("forum_replies")
                    message_replies = replies_data[replies_data["parent_timestamp"] == row["timestamp"]]

                    if message_replies.empty:
                        st.info("Aucune réponse pour ce message.")
                    else:
                        for _, reply in message_replies.iterrows():
                            st.write(f"- {reply['reply']} (**{reply['username']}**, le {reply['timestamp']})")

    # --- Onglet ultra psychédélique ---
    with tab3:
        st.header("🌈 Vortex Félin Psychédélique 🌀")


        # CSS super psychédélique
        st.markdown("""
            <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            @keyframes colors {
                0% { background-color: #FF0000; }
                25% { background-color: #00FF00; }
                50% { background-color: #0000FF; }
                75% { background-color: #FFFF00; }
                100% { background-color: #FF00FF; }
            }

            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.2); }
            }

            @keyframes background-move {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            body {
                animation: background-move 15s infinite linear;
                background: linear-gradient(270deg, #ff6ec7, #ffc260, #6ec7ff, #a760ff);
                background-size: 400% 400%;
            }

            .psychedelic-container {
                animation: colors 5s infinite, spin 15s linear infinite, pulse 2s infinite;
                border: 5px dashed #fff;
                border-radius: 50%;
                box-shadow: 0 0 50px #fff, 0 0 100px #fff, 0 0 150px #fff;
                width: 300px;
                height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 20px auto;
            }

            .psychedelic-container img {
                width: 100%;
                border-radius: 50%;
            }

            .text-rainbow {
                font-size: 2rem;
                font-weight: bold;
                text-align: center;
                animation: colors 2s infinite, pulse 1s infinite alternate;
            }

            .video-container {
                margin: 20px auto;
                text-align: center;
                animation: spin 20s linear infinite;
            }

            .video-container video {
                width: 80%;
                border-radius: 20px;
                box-shadow: 0 0 30px #ff33ff;
            }
            </style>
        """, unsafe_allow_html=True)

        # Arrière-plan sonore
        audio_file = "https://www.myinstants.com/media/sounds/meow-mix.mp3"
        st.markdown(f"""
            <audio autoplay loop>
                <source src="{audio_file}" type="audio/mpeg">
                Votre navigateur ne supporte pas l'audio.
            </audio>
        """, unsafe_allow_html=True)

        # Contenu psychédélique
        st.markdown("""
            <div class="text-rainbow">✨ Chats cosmiques en rotation ✨</div>
            <div class="psychedelic-container">
                <img src="https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif" alt="Chat hypnotique">
            </div>
            <div class="psychedelic-container">
                <img src="https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif" alt="Chat galaxie">
            </div>
            <div class="video-container">
                <video autoplay loop muted>
                    <source src="https://media.giphy.com/media/3oriO0OEd9QIDdllqo/giphy.mp4" type="video/mp4">
                    Votre navigateur ne supporte pas la vidéo.
                </video>
            </div>
            <div class="psychedelic-container">
                <img src="https://media.giphy.com/media/ICOgUNjpvO0PC/giphy.gif" alt="Chat cosmique">
            </div>
        """, unsafe_allow_html=True)

    with tab4:
        st.header("📝 Task Manager")

        # Lire les données de tâches
        task_data = read_sheet("task_data")

        # Filtrer les tâches par utilisateur
        if "username" in task_data.columns:
            user_tasks = task_data[task_data["username"] == st.session_state["username"]]
        else:
            st.error("La colonne 'username' est absente des données de tâches. Veuillez vérifier la feuille Google Sheets.")
            st.stop()

        # Tri des tâches
        st.subheader("Options de tri")
        sort_by = st.selectbox("Trier les tâches par :", ["Date d'échéance", "Statut"])
        if sort_by == "Date d'échéance":
            user_tasks = user_tasks.sort_values(by="due_date")
        elif sort_by == "Statut":
            user_tasks = user_tasks.sort_values(by="status")

        # Formulaire pour ajouter une nouvelle tâche
        with st.form("add_task_form"):
            task_title = st.text_input("Titre de la tâche")
            task_description = st.text_area("Description de la tâche")
            due_date = st.date_input("Date d'échéance")
            add_task_button = st.form_submit_button("Ajouter la tâche")

        if add_task_button and task_title.strip() and task_description.strip():
            new_task = {
                "username": st.session_state["username"],
                "title": task_title,
                "description": task_description,
                "due_date": due_date.strftime('%Y-%m-%d'),
                "status": "En cours",
            }
            append_to_sheet("task_data", new_task)
            st.success("Tâche ajoutée avec succès !")

        # Afficher les tâches existantes
        st.subheader("Vos tâches")
        if user_tasks.empty:
            st.info("Aucune tâche pour le moment. Ajoutez-en une ci-dessus.")
        else:
            for index, task in user_tasks.iterrows():
                status_icon = "✅" if task['status'] == "Terminée" else "🕒"
                markdown_content = f"""
                ### {status_icon} {task['title']}  
                **Échéance :** {task['due_date']}  
                **Statut :** {task['status']}  
                {task['description']}
                """
                st.markdown(markdown_content)

                # Mettre en évidence les tâches en cours
                if task['status'] == "En cours":
                    st.markdown("<div style='background-color: #fff3cd; padding: 10px; border-radius: 5px;'>\
                                Cette tâche est toujours en cours. Pensez à la terminer avant l'échéance !</div>",
                                unsafe_allow_html=True)

                # Marquer la tâche comme terminée
                if task["status"] == "En cours":
                    if st.button(f"Marquer comme terminée", key=f"complete_{index}"):
                        task_data.loc[task_data.index == index, "status"] = "Terminée"
                        update_sheet("task_data", task_data)
                        st.success("Tâche marquée comme terminée.")

else:
    st.info("Veuillez vous connecter pour accéder à votre suivi.")
