import streamlit as st
import pandas as pd

# Load data
@st.cache_data
def load_data():
    file_path = 'support_bot___chat_dump___modified_2026-05-01T11_53_55.486115709+05_30.csv'
    df = pd.read_csv(file_path)
    # Sort the dataframe by ai_chat_id and then message_id to ensure order
    df = df.sort_values(by=['ai_chat_id', 'message_id'], ascending=[True, True])
    
    # Parse the dates from actual_created_at
    # Example format: "30 Apr, 2026, 10:13 AM"
    df['parsed_datetime'] = pd.to_datetime(df['actual_created_at'], errors='coerce')
    df['date'] = df['parsed_datetime'].dt.date
    
    # Map each ai_chat_id to its first date (min date)
    chat_date_map = df.groupby('ai_chat_id')['date'].min().reset_index()
    chat_date_map = chat_date_map.dropna()
    
    # Ensure df is cleaned of NaT dates if any
    df = df.dropna(subset=['date'])
    
    return df, chat_date_map

# Main app
st.set_page_config(page_title="Chat Viewer", layout="centered")
st.title("Chat Sessions Viewer")

try:
    df, chat_date_map = load_data()
except Exception as e:
    st.error(f"Error loading the CSV file: {e}")
    st.stop()

# Get unique dates and sort them descending (newest first) or ascending
unique_dates = sorted(chat_date_map['date'].unique())

if len(unique_dates) == 0:
    st.warning("No dates found.")
    st.stop()

# Date selection dropdown
selected_date = st.selectbox("Select Date", unique_dates, format_func=lambda x: x.strftime('%d %b, %Y'))

# Filter chat IDs by the selected date
date_chat_ids = chat_date_map[chat_date_map['date'] == selected_date]['ai_chat_id'].unique()

if len(date_chat_ids) == 0:
    st.warning(f"No chat sessions found for {selected_date.strftime('%d %b, %Y')}.")
    st.stop()

# Initialize session states
if 'current_date' not in st.session_state:
    st.session_state.current_date = selected_date
    st.session_state.current_index = 0

# If the user changed the date, reset the index to 0
if st.session_state.current_date != selected_date:
    st.session_state.current_date = selected_date
    st.session_state.current_index = 0

# Bound index just in case the new date has fewer chats
if st.session_state.current_index >= len(date_chat_ids):
    st.session_state.current_index = 0

# Navigation functions
def next_chat():
    if st.session_state.current_index < len(date_chat_ids) - 1:
        st.session_state.current_index += 1

def prev_chat():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

# Controls layout
st.markdown("### Navigation")
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.button("⬅️ Previous Session", on_click=prev_chat, disabled=(st.session_state.current_index == 0), use_container_width=True)

with col2:
    st.markdown(f"<div style='text-align: center;'><b>Session {st.session_state.current_index + 1} of {len(date_chat_ids)}</b><br><small>on {selected_date.strftime('%d %b')}</small></div>", unsafe_allow_html=True)

with col3:
    st.button("Next Session ➡️", on_click=next_chat, disabled=(st.session_state.current_index == len(date_chat_ids) - 1), use_container_width=True)

st.divider()

# Dropdown to jump directly to a chat session within the selected date
current_chat_id = date_chat_ids[st.session_state.current_index]
selected_chat_id = st.selectbox("Jump to ai_chat_id", date_chat_ids, index=st.session_state.current_index)

# If dropdown is changed manually, update session state
if selected_chat_id != current_chat_id:
    st.session_state.current_index = list(date_chat_ids).index(selected_chat_id)
    st.rerun()

current_chat_id = date_chat_ids[st.session_state.current_index]
st.subheader(f"Chat Session: `{current_chat_id}`")

# Display messages for the selected chat ID
session_df = df[df['ai_chat_id'] == current_chat_id]

# Information about the session
if not session_df.empty:
    cp_name = session_df['cp_name'].iloc[0]
    user_id = session_df['user_id'].iloc[0]
    st.caption(f"**User ID:** {user_id} | **Course/Program:** {cp_name}")

st.markdown("---")

for index, row in session_df.iterrows():
    sender = str(row['sender_type']).lower().strip()
    content = row['message_content']
    time = row['actual_created_at']
    
    # Render with Streamlit chat elements
    if sender == 'user':
        with st.chat_message("user"):
            st.markdown(f"**USER** • _{time}_")
            st.write(content)
    elif sender == 'ai':
        with st.chat_message("assistant"):
            st.markdown(f"**AI** • _{time}_")
            st.write(content)
    else:
        with st.chat_message("secondary"):
            st.markdown(f"**{sender.upper()}** • _{time}_")
            st.write(content)
