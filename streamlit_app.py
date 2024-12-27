import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib
import os
from datetime import datetime, timedelta
import re
from PIL import Image

# --- Connexion Google Sheets & Config ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erreur de connexion Google Sheets : {e}")
    st.stop()

st.set_page_config(page_title="Tut-v2 | CREM", page_icon="logo-tut.png", initial_sidebar_state="expanded", menu_items={
    'Get Help': 'https://www.crem.fr/contact/',
    'Report a bug': "mailto:web@crem.fr",
    'About': "# Bienvenue dans votre espace Tutorat ! Faites en bon usage ;)"})

try:
    logo = Image.open("logo-tut.png")
except Exception as e:
    st.error(f"Erreur lors du chargement du logo : {e}")
    logo = None

st.markdown("""
<style>
@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

.welcome-message {
    margin-top: 2rem;
    text-align: center;
    font-size: 2em;
    font-weight: bold;
    animation: fadeIn 0.5s ease-in-out;
}

.sidebar-bottom {
    position: fixed;
    bottom: 20px;
    width: 100%;
    animation: fadeIn 0.5s ease-in-out;
}
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def sanitize_input(input_string):
    """Remove potentially malicious input."""
    return re.sub(r'[<>/\\]', '', input_string)

def save_image(image, username):
    """Save uploaded image securely to a permanent directory."""
    try:
        MAX_SIZE_MB = 2
        forum_images_dir = "forum_images"
        os.makedirs(forum_images_dir, exist_ok=True)

        image.seek(0, os.SEEK_END)
        size_mb = image.tell() / (1024 * 1024)
        image.seek(0)
        if size_mb > MAX_SIZE_MB:
            raise ValueError(
                f"Le fichier est trop volumineux ({size_mb:.2f} Mo). La taille maximale est de {MAX_SIZE_MB} Mo.")

        image_filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        image_path = os.path.join(forum_images_dir, image_filename)
        with open(image_path, "wb") as f:
            f.write(image.read())
        return image_path
    except Exception as e:
        raise RuntimeError(f"Erreur lors de l'enregistrement de l'image : {e}")


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

# --- Nouveau: Fonctions du tableau de bord ---
def create_dashboard_metrics():
    """Crée les métriques du tableau de bord dans la barre latérale."""
    st.sidebar.subheader("📊 Tableau de bord")

    # Lecture et calcul des statistiques
    qcm_data = read_sheet("qcm_data")
    forum_data = read_sheet("forum_data")
    task_data = read_sheet("task_data")

    user_qcm = qcm_data[qcm_data["username"] == st.session_state["username"]]
    user_posts = forum_data[forum_data["username"] == st.session_state["username"]]
    user_tasks = task_data[task_data["username"] == st.session_state["username"]]

    # Métriques principales
    col1, col2 = st.sidebar.columns(2)
    total_qcm = user_qcm[["maths", "biologie", "sciences_humaines"]].sum().sum()
    total_posts = len(user_posts)
    col1.metric("Total QCM", f"{int(total_qcm)}")
    col2.metric("Messages", f"{total_posts}")

    # Tâches urgentes
    st.sidebar.markdown("### ⚡ Tâches urgentes")
    today = datetime.now().date()
    urgent_tasks = user_tasks[
        (user_tasks["status"] == "En cours") &
        (pd.to_datetime(user_tasks["due_date"]).dt.date <= today + timedelta(days=3))
        ]

    if not urgent_tasks.empty:
        for _, task in urgent_tasks.iterrows():
            due_date = pd.to_datetime(task["due_date"]).date()
            days_left = (due_date - today).days
            status_color = "🔴" if days_left < 0 else "🟡" if days_left == 0 else "🟢"
            st.sidebar.markdown(f"{status_color} **{task['title']}** - {days_left} jours")
    else:
        st.sidebar.info("Aucune tâche urgente ! 🎉")

    # Progrès hebdomadaire
    st.sidebar.markdown("### 📈 Progrès de la semaine")
    week_start = today - timedelta(days=today.weekday())
    week_qcm = user_qcm[pd.to_datetime(user_qcm["date"]).dt.date >= week_start]

    if not week_qcm.empty:
        weekly_total = week_qcm[["maths", "biologie", "sciences_humaines"]].sum().sum()
        st.sidebar.progress(min(weekly_total / 50, 1.0), text=f"QCM: {int(weekly_total)}/50")
    else:
        st.sidebar.warning("Pas encore de QCM cette semaine")

    # Dernière activité
    st.sidebar.markdown("### 🕒 Dernière activité")
    if not user_posts.empty:
        last_post = user_posts.iloc[-1]
        st.sidebar.markdown(f"Forum: {last_post['title'][:30]}...")
    if not user_qcm.empty:
        last_qcm = user_qcm.iloc[-1]
        st.sidebar.markdown(f"QCM: {last_qcm['date']}")


if not st.session_state.get("authenticated"):
    # Logo centré pour la page de connexion
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if logo is not None:
            st.image(logo, use_container_width=True, output_format="PNG")

    st.sidebar.header("Connexion")
    username = sanitize_input(st.sidebar.text_input("Nom d'utilisateur"))
    password = st.sidebar.text_input("Mot de passe", type="password")
    login_button = st.sidebar.button("Se connecter")

    if username and password and login_button:
        user_data = read_sheet("user_data")
        if not user_data.empty and username in user_data["username"].values:
            hashed_password = hash_password(password)
            stored_password = user_data[user_data["username"] == username]["password"].values[0]
            if hashed_password == stored_password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.success("Connexion réussie !")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect.")
        else:
            st.error("Nom d'utilisateur ou mot de passe incorrect.")
else:
    st.markdown(f"""
            <div class="welcome-message">
                Bienvenue, {st.session_state['username']} !
            </div>
        """, unsafe_allow_html=True)

    # Ajouter le logo
    if logo is not None:
        st.sidebar.markdown("<div class='sidebar-bottom'>", unsafe_allow_html=True)
        st.sidebar.image(logo, use_container_width=True, output_format="PNG")
        st.sidebar.markdown("</div>", unsafe_allow_html=True)


# --- Application ---
if st.session_state.get("authenticated"):
    create_dashboard_metrics()

    # Onglets
    tab1, tab2, tab3 = st.tabs(["📊 Suivi des QCM", "💬 Forum", "📝 Task Manager"])

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
            post_button = st.form_submit_button("Poster")

        if post_button and title.strip() and message.strip():
            new_message = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "username": st.session_state["username"],
                "title": title,
                "message": message,
                "tags": tags
            }
            append_to_sheet("forum_data", new_message)
            st.success("Message posté avec succès !")

        st.subheader("Rechercher des messages")
        search_query = st.text_input("Rechercher par mot-clé ou tag")
        search_button = st.button("Rechercher")

        # Affichage des messages
        forum_data = read_sheet("forum_data")
        user_data = read_sheet("user_data")  # Chargement de la feuille des utilisateurs
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
                    st.write(row["message"])

                    # Afficher le statut de l'utilisateur (tuteur/tutrice)
                    username = row["username"]
                    user_info = user_data[user_data["username"] == username]
                    if not user_info.empty:
                        tutor_status = user_info.iloc[0]["tuteur/tutrice"]
                        if pd.notna(tutor_status):  # Vérifier si le statut est défini
                            st.write(f"✨ **{'Tuteur' if tutor_status.lower() == 'tuteur' else 'Tutrice'}** ✨")

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
                            reply_user = reply['username']
                            reply_user_info = user_data[user_data["username"] == reply_user]
                            if not reply_user_info.empty:
                                reply_tutor_status = reply_user_info.iloc[0]["tuteur/tutrice"]
                                role = "Tuteur" if reply_tutor_status.lower() == "✨ Tuteur ✨" else "✨ Tutrice ✨" if pd.notna(
                                    reply_tutor_status) else "Utilisateur"
                            else:
                                role = "Utilisateur"

                            st.write(f"- {reply['reply']} [**{role}**, le {reply['timestamp']}]")


    with tab3:
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
