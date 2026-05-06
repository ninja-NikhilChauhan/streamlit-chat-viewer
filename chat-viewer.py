import streamlit as st
import pandas as pd
import os
import glob

# Directory to store the uploaded CSV
DUMP_DIR = "csv_dump"
if not os.path.exists(DUMP_DIR):
    os.makedirs(DUMP_DIR)

st.set_page_config(page_title="Chat Viewer", layout="centered")
st.title("Chat Sessions Viewer")

# File Uploader
uploaded_file = st.file_uploader("Upload Chat CSV Dump", type=['csv'])

if uploaded_file is not None:
    # Clear the existing files in the directory
    existing_files = glob.glob(os.path.join(DUMP_DIR, "*.csv"))
    for f in existing_files:
        os.remove(f)
    
    # Save the new file
    file_path = os.path.join(DUMP_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Clear cache to ensure fresh data is loaded
    st.cache_data.clear()
    
    # Reset session states
    if 'current_date' in st.session_state:
        del st.session_state['current_date']
    if 'current_index' in st.session_state:
        del st.session_state['current_index']

# Check if there is any CSV in csv_dump to read
existing_files = glob.glob(os.path.join(DUMP_DIR, "*.csv"))
if not existing_files:
    st.info("Please upload a CSV file to view chat sessions.")
    st.stop()

# Use the only CSV present in the folder
file_path = existing_files[0]
st.success(f"Reading data from: `{os.path.basename(file_path)}`")

# Load data function
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    # Sort the dataframe by ai_chat_id and then message_number or message_id to ensure order
    sort_column = 'message_number' if 'message_number' in df.columns else 'message_id'
    if 'ai_chat_id' in df.columns and sort_column in df.columns:
        df = df.sort_values(by=['ai_chat_id', sort_column], ascending=[True, True])
    
    # Parse the dates from created_at
    if 'created_at' in df.columns:
        df['parsed_datetime'] = pd.to_datetime(df['created_at'], errors='coerce')
        df['date'] = df['parsed_datetime'].dt.date
    else:
        st.error("Column 'created_at' not found in the CSV.")
        st.stop()
    
    # Map each ai_chat_id to its first date and rm_name
    agg_funcs = {'date': 'min'}
    if 'rm_name' in df.columns:
        agg_funcs['rm_name'] = 'first'
        
    chat_date_map = df.groupby('ai_chat_id').agg(agg_funcs).reset_index()
    if 'rm_name' not in chat_date_map.columns:
        chat_date_map['rm_name'] = 'Unknown'
        
    chat_date_map = chat_date_map.dropna(subset=['date'])
    
    # Ensure df is cleaned of NaT dates if any
    df = df.dropna(subset=['date'])
    
    return df, chat_date_map

try:
    df, chat_date_map = load_data(file_path)
except Exception as e:
    st.error(f"Error loading the CSV file: {e}")
    st.stop()

# Add RM Name Filter
unique_rms = ["All RMs"] + sorted([str(rm) for rm in chat_date_map['rm_name'].unique() if pd.notna(rm)])
selected_rm = st.selectbox("Filter by RM Name", unique_rms)

if selected_rm != "All RMs":
    filtered_map = chat_date_map[chat_date_map['rm_name'] == selected_rm]
else:
    filtered_map = chat_date_map

# Get unique dates and sort them
unique_dates = sorted(filtered_map['date'].unique())

if len(unique_dates) == 0:
    st.warning("No dates found for the selected criteria.")
    st.stop()

# Date selection dropdown
selected_date = st.selectbox("Select Date", unique_dates, format_func=lambda x: x.strftime('%d %b, %Y'))

# Filter chat IDs by the selected date AND RM
date_chat_ids = filtered_map[filtered_map['date'] == selected_date]['ai_chat_id'].unique()

if len(date_chat_ids) == 0:
    st.warning(f"No chat sessions found for {selected_date.strftime('%d %b, %Y')}.")
    st.stop()

# Initialize session states
if 'current_rm' not in st.session_state:
    st.session_state.current_rm = selected_rm
if 'current_date' not in st.session_state:
    st.session_state.current_date = selected_date
    st.session_state.current_index = 0

# If the user changed the RM or the date, reset the index to 0
if st.session_state.current_rm != selected_rm or st.session_state.current_date != selected_date:
    st.session_state.current_rm = selected_rm
    st.session_state.current_date = selected_date
    st.session_state.current_index = 0

# Bound index just in case the new date/RM has fewer chats
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
    cp_name = session_df['cp_name'].iloc[0] if 'cp_name' in session_df.columns else "Unknown"
    user_id = session_df['user_id'].iloc[0] if 'user_id' in session_df.columns else "Unknown"
    rm_name = session_df['rm_name'].iloc[0] if 'rm_name' in session_df.columns else "Unknown"
    st.caption(f"**User ID:** {user_id} | **Course/Program:** {cp_name} | **RM Name:** {rm_name}")

st.markdown("---")

for index, row in session_df.iterrows():
    sender = str(row['sender_type']).lower().strip() if 'sender_type' in row else 'user'
    content = row['message_content'] if 'message_content' in row else ''
    time = row['parsed_datetime'].strftime('%H:%M') if pd.notna(row['parsed_datetime']) else ''
    
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
