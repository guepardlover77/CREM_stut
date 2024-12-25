import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image
import hashlib
import os
from datetime import timedelta, time
from icalendar import Calendar, Event
import time


# --- Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def parse_icalendar(file):
    """
    Parse ICalendar file and extract events.
    """
    calendar = Calendar.from_ical(file.read())
    events = []
    for component in calendar.walk():
        if component.name == "VEVENT":
            start = component.get("dtstart").dt
            summary = component.get("summary")
            events.append({"start": start, "summary": summary})
    return pd.DataFrame(events)

def generate_revision_schedule_with_constraints(events, method, start_time, end_time, start_date, end_date, session_duration):
    """
    Generate a revision schedule with user-defined constraints and session duration.
    """
    lunch_start = time(12, 0)
    lunch_end = time(14, 0)

    revision_schedule = []
    for _, event in events.iterrows():
        for i in range(1, 6):  # Generate 5 revision sessions
            if method == "Méthode des J":
                revision_time = event["start"] + timedelta(days=i**2)
            elif method == "Leitner":
                revision_time = event["start"] + timedelta(days=i)
            else:  # Répétition classique
                revision_time = event["start"] + timedelta(days=2 * i)

            # Ensure the revision time is within the user's specified date range
            if start_date <= revision_time.date() <= end_date:
                revision_start = datetime.combine(revision_time.date(), start_time)
                revision_end = datetime.combine(revision_time.date(), end_time)
                revision_time_only = revision_time.time()

                # Exclude lunch break and outside user-defined hours
                if (
                    start_time <= revision_time_only <= end_time
                    and not (lunch_start <= revision_time_only < lunch_end)
                ):
                    revision_schedule.append({
                        "Date": revision_time,
                        "Cours": event["summary"],
                        "Méthode": method,
                        "Durée (minutes)": session_duration
                    })
    return pd.DataFrame(revision_schedule)

def create_icalendar_file(revision_schedule):
    """
    Create an iCalendar (.ics) file from the revision schedule.
    """
    calendar = Calendar()
    for _, row in revision_schedule.iterrows():
        event = Event()
        start_datetime = row["Date"]
        duration = timedelta(minutes=row["Durée (minutes)"])
        event.add("summary", f"Révision : {row['Cours']}")
        event.add("dtstart", start_datetime)
        event.add("dtend", start_datetime + duration)
        event.add("description", f"Méthode : {row['Méthode']}")
        calendar.add_component(event)

    return calendar.to_ical()


# --- Connexion Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)


# --- Fonctions Utilitaires ---
def read_sheet(sheet_name):
    """Lit les données d'une feuille Google Sheets en DataFrame."""
    return conn.read(worksheet=sheet_name)


def update_sheet(sheet_name, data):
    """Met à jour une feuille Google Sheets avec un DataFrame."""
    conn.update(worksheet=sheet_name, data=data)


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


# --- Authentification ---
st.sidebar.header("Connexion")
username = st.sidebar.text_input("Nom d'utilisateur")
password = st.sidebar.text_input("Mot de passe", type="password")
login_button = st.sidebar.button("Se connecter")


if username and password and login_button:
    st.session_state["authenticated"] = True
    st.session_state["username"] = username

# --- Application ---
if "authenticated" in st.session_state and st.session_state["authenticated"]:
    st.title(f"Bienvenue, {st.session_state['username']} !")

    # Onglets
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Suivi des QCM", "📅 Planning de révisions", "💬 Forum", "Chats"])

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



    with tab2:
        st.header("Génération d'un planning de révisions")
        uploaded_file = open("ADECal.ics", "rb")
        
        
        if uploaded_file:
            events = parse_icalendar(uploaded_file)
            st.write("Emploi du temps importé :", events)

            st.subheader("Paramètres du planning de révisions")
            start_date = st.date_input("Choisissez une date de début")
            end_date = st.date_input("Choisissez une date de fin")
            start_time = st.time_input("Début de journée", value=datetime.strptime("08:00", "%H:%M").time())
            end_time = st.time_input("Fin de journée", value=datetime.strptime("20:00", "%H:%M").time())
            session_duration = st.number_input("Durée de chaque session (minutes)", min_value=10, max_value=120,
                                               value=30)
            method = st.selectbox("Méthode de révision", ["Méthode des J", "Leitner", "Répétition classique"])

            if st.button("Générer le planning"):
                if start_date > end_date:
                    st.error("La date de début doit être antérieure ou égale à la date de fin.")
                else:
                    revision_schedule = generate_revision_schedule_with_constraints(
                        events, method, start_time, end_time, start_date, end_date, session_duration
                    )
                    st.write("Planning généré :", revision_schedule)

                    # Download as CSV
                    st.download_button("Télécharger le planning (CSV)", revision_schedule.to_csv(index=False),
                                       "planning_revisions.csv", "text/csv")

                    # Create and download iCalendar file
                    icalendar_file = create_icalendar_file(revision_schedule)
                    st.download_button("Télécharger le planning (iCalendar)", icalendar_file,
                                       "planning_revisions.ics", "text/calendar")

    # --- Forum ---
    with tab3:
        st.header("Forum")

        # Ajouter un message au forum
        st.subheader("Poster un message")
        with st.form("forum_form"):
            title = st.text_input("Titre du message")
            message = st.text_area("Votre message")
            tags = st.text_input("Tags (séparés par des virgules)")
            image = st.file_uploader("Ajouter une image (optionnel)", type=["png", "jpg", "jpeg"])
            post_button = st.form_submit_button("Poster")

        if post_button and title.strip() and message.strip():
            image_path = None
            if image:
                image_filename = f"{st.session_state['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                image_path = os.path.join("temp_images", image_filename)
                os.makedirs("temp_images", exist_ok=True)
                Image.open(image).save(image_path)

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

        # Recherche de messages
        st.subheader("Rechercher des messages")
        search_query = st.text_input("Rechercher par mot-clé ou tag")
        search_button = st.button("Rechercher")

        # Charger les messages
        forum_data = read_sheet("forum_data")
        filtered_messages = forum_data

        if search_button and search_query.strip():
            search_query = search_query.lower()
            filtered_messages = forum_data[
                forum_data["title"].str.lower().str.contains(search_query) |
                forum_data["message"].str.lower().str.contains(search_query) |
                forum_data["tags"].str.lower().str.contains(search_query)
                ]

        # Affichage des messages
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

    # --- Onglet ultra psychédélique ---
    with tab4:
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


else:
    st.info("Veuillez vous connecter pour accéder à votre suivi.")
