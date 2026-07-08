import streamlit as st
import cv2
import requests
import time
import numpy as np
from PIL import Image, ImageSequence
import io

st.set_page_config(page_title="MATRIX RENDER ENGINE", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #06060c; color: #00ffcc; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ffcc !important; text-shadow: 0 0 8px #00ffcc; }
    .stFileUploader { border: 1px dashed #00ffcc !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📟 MATRIX RENDER PIPELINE // V2")
st.write("---")

# --- TOKEN VERIFICATION FUNCTION ---
def verify_discord_token(token):
    """Pings Discord API to check if user token is valid."""
    headers = {"Authorization": token}
    response = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
    if response.status_code == 200:
        return True, response.json().get("username", "Unknown User")
    return False, None

# --- PROCESS IMAGE ARRAYS TO TEXT MATRIX ---
def pixel_matrix_to_braille(gray_img):
    """Converts a single grayscale image matrix to Braille/Block format strings."""
    frame_text = ""
    for row in gray_img:
        for pixel in row:
            frame_text += "⣿" if pixel > 127 else "░"
        frame_text += "\n"
    return f"```\n{frame_text}```"

# --- VIDEO FRAME EXTRACTION ---
def process_video_frames(video_bytes, width, height):
    with open("temp_input.mp4", "wb") as f:
        f.write(video_bytes)
    
    cap = cv2.VideoCapture("temp_input.mp4")
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (width, height))
        frames.append(pixel_matrix_to_braille(resized))
    cap.release()
    return frames

# --- GIF FRAME EXTRACTION (Using PIL) ---
def process_gif_frames(gif_bytes, width, height):
    frames = []
    img = Image.open(io.BytesIO(gif_bytes))
    
    # Iterate through every frame in the animated GIF
    for frame in ImageSequence.Iterator(img):
        # Convert frame to grayscale and resize
        frame_gray = frame.convert("L")
        frame_resized = frame_gray.resize((width, height))
        
        # Convert PIL frame to a NumPy matrix for pixel reading
        matrix = np.array(frame_resized)
        frames.append(pixel_matrix_to_braille(matrix))
    return frames

# --- SIDEBAR: AUTHENTICATION ---
st.sidebar.header("🔑 INSTANCE CREDENTIALS")
USER_TOKEN = st.sidebar.text_input("Discord User Token", type="password")
TARGET_CHANNEL_ID = st.sidebar.text_input("Target Channel ID", placeholder="11223344...")

token_valid = False
if USER_TOKEN:
    is_valid, username = verify_discord_token(USER_TOKEN)
    if is_valid:
        st.sidebar.success(f"CONNECTED AS: {username}")
        token_valid = True
    else:
        st.sidebar.error("INVALID TOKEN. ACCESS DENIED.")

# --- MAIN DASHBOARD INTERFACE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🗂️ Asset Ingestion")
    uploaded_file = st.file_uploader("Upload Target File (.mp4, .mov, .gif)", type=["mp4", "mov", "gif"])
    
    frame_width = st.slider("Matrix Width", 10, 50, 30)
    frame_height = st.slider("Matrix Height", 10, 40, 15)
    playback_speed = st.slider("Frame Hold Delay (Seconds)", 0.2, 1.5, 0.6)

with col2:
    st.subheader("📺 Telemetry Broadcast")
    
    if not token_valid:
        st.info("Awaiting valid Discord user validation token verification from sidebar...")
    elif uploaded_file is None:
        st.info("Upload a video or an animated GIF file payload to begin rendering.")
    else:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if st.button("🚀 INITIATE OVERWRITE STREAM"):
            file_bytes = uploaded_file.read()
            
            with st.spinner(f"Decompiling .{file_extension} timeline arrays..."):
                if file_extension == "gif":
                    frames = process_gif_frames(file_bytes, frame_width, frame_height)
                else:
                    frames = process_video_frames(file_bytes, frame_width, frame_height)
            
            st.success(f"Compiled {len(frames)} frames into memory matrix!")
            
            # --- TRANSMISSION HOOK ---
            headers = {"Authorization": USER_TOKEN, "Content-Type": "application/json"}
            base_url = f"https://discord.com/api/v9/channels/{TARGET_CHANNEL_ID}/messages"
            
            # Create base anchor message
            init_res = requests.post(base_url, headers=headers, json={"content": "```\nLinking stream...```"})
            
            if init_res.status_code == 200:
                msg_id = init_res.json()["id"]
                edit_url = f"{base_url}/{msg_id}"
                
                status_box = st.empty()
                preview_box = st.empty()
                
                for idx, frame_content in enumerate(frames):
                    status_box.text(f"Syncing Array: Frame {idx+1}/{len(frames)}")
                    preview_box.markdown(frame_content)
                    
                    res = requests.patch(edit_url, headers=headers, json={"content": frame_content})
                    
                    if res.status_code == 429:
                        # Adaptive fallback if Discord's gatekeeper flags rate-limiting
                        retry_sec = res.json().get("retry_after", 1.0)
                        time.sleep(retry_sec)
                    else:
                        time.sleep(playback_speed)
                        
                requests.patch(edit_url, headers=headers, json={"content": "```\n[PIPELINE OVERWRITE CONCLUDED]```"})
                st.success("Sequence successfully written directly to Discord channel via account session.")
            else:
                st.error(f"Failed connection sequence. Target destination error: {init_res.text}")
