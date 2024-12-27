# Streamlit Application for QCM Tracking, Forum, and Task Management

This Streamlit application provides a comprehensive interface for QCM tracking, forum discussions, and task management. The app integrates Google Sheets for data storage and offers a user-friendly interface for managing various features such as authentication, data visualization, and task organization.

## Features

### 1. **User Authentication**
- **Account Creation**: Users can create an account with a username and password. Passwords are securely hashed using SHA-256.
- **Login**: Users can log in to access their personalized dashboard.

### 2. **QCM Tracking**
- Allows users to track their QCM progress in subjects such as Maths, Biology, and Social Sciences.
- Provides data visualization with bar charts and line graphs to display progress over time.
- Users can add new QCM data through a form.

### 3. **Forum**
- Users can post messages with optional tags and images.
- A search functionality helps find posts by keywords or tags.
- Replies can be added to forum posts, and replies are stored and displayed in a threaded format.

### 4. **Task Manager**
- Users can create, view, and manage tasks with titles, descriptions, due dates, and statuses.
- Tasks are sortable by due date or status.
- Users can mark tasks as complete.

### 5. **Psychedelic Tab**
- An entertaining tab with animated visuals and a playful theme.

## Technologies Used
- **Streamlit**: For building the user interface.
- **Google Sheets API**: For data storage and retrieval using the `st-gsheets-connection` module.
- **Pandas**: For data manipulation.
- **Plotly**: For data visualization in the QCM tracking feature.

## Data Flow
1. **Google Sheets Integration**: Data is read from and written to Google Sheets using the `st-gsheets-connection` connection.
2. **Cache Management**: To ensure the most up-to-date data is displayed, the app clears the cache (`st.cache_data.clear()`) and reloads the page (`st.rerun()`) after any data modification.

## Installation

### Prerequisites
- Python 3.8+
- Google Sheets API credentials
- Dependencies listed in `requirements.txt`

### Steps
1. Clone the repository:
   ```bash
   git clone [<repository-url>](https://github.com/guepardlover77/CREM_stut.git)
   cd CREM_stut
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the Google Sheets API:
   - Place the credentials file (`credentials.json`) in the root directory.
   - Share the relevant Google Sheets with the email address from the API credentials.

4. Run the application:
   ```bash
   streamlit run tut_v2_CREM.py
   ```

## File Structure
```
|-- tut_v2_CREM.py  # Main application code
|-- forum_images/     # Directory for storing uploaded images
|-- requirements.txt  # Python dependencies
|-- credentials.json  # Google Sheets API credentials
```

## Usage
1. Navigate to the Streamlit app URL (e.g., `http://localhost:8501`).
2. Create an account or log in to access the dashboard.
3. Use the tabs to:
   - Track QCM progress.
   - Post or search forum messages.
   - Create and manage tasks.
4. Enjoy the psychedelic animations in the special tab.

## Troubleshooting
- **Cache Issues**: Ensure `st.cache_data.clear()` and `st.rerun()` are functioning correctly to reload updated data.
- **Google Sheets Errors**: Verify API credentials and sheet permissions.

## Future Enhancements
- Add email notifications for task deadlines.
- Implement real-time chat for the forum.
- Enhance the UI for mobile devices.


