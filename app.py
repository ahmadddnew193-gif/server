import streamlit as st
import cv2
import requests
import time

st.set_page_config(page_title="USER MATRIX PIPELINE", layout="wide")

# --- UI FOR TOKENS ---
st.title("📟 USER-TOKEN MATRIX STREAMER")

USER_TOKEN = st.text_input("Enter User Token:", type="password")
CHANNEL_ID = st.text_input("Target Channel ID:")
uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov"])

# --- RENDER ENGINE (Same downscaling logic) ---
def video_to_ascii_frames(video_bytes, width=30, height=15):
    with open("temp_user_video.mp4", "wb") as f:
        f.write(video_bytes)
    
    cap = cv2.VideoCapture("temp_user_video.mp4")
    frames = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (width, height))
        
        frame_text = ""
        for row in resized:
            for pixel in row:
                frame_text += "⣿" if pixel > 127 else "░"
            frame_text += "\n"
        frames.append(f"```\n{frame_text}```")
    cap.release()
    return frames

# --- DIRECT DISCORD API INTERACTION ---
if uploaded_file and USER_TOKEN and CHANNEL_ID:
    if st.button("🧬 LAUNCH USER-TOKEN STREAM"):
        frames = video_to_ascii_frames(uploaded_file.read())
        
        # Headers required to mimic a real user session
        headers = {
            "Authorization": USER_TOKEN,
            "Content-Type": "application/json"
        }
        
        # 1. Send the initial message
        base_url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages"
        init_response = requests.post(base_url, headers=headers, json={"content": "```\nInitializing...```"})
        
        if init_response.status_code == 200:
            message_id = init_response.json()["id"]
            edit_url = f"{base_url}/{message_id}"
            
            status_box = st.empty()
            
            # 2. Edit loop mimicking the user
            for idx, frame in enumerate(frames):
                status_box.text(f"Editing Frame {idx+1}/{len(frames)}")
                
                res = requests.patch(edit_url, headers=headers, json={"content": frame})
                
                # If hit by a rate limit, pause dynamically
                if res.status_code == 429:
                    retry_after = res.json().get("retry_after", 1.0)
                    time.sleep(retry_after)
                else:
                    # Strict delay to prevent instant account termination
                    time.sleep(0.6) 
                    
            requests.patch(edit_url, headers=headers, json={"content": "```\n[PLAYBACK FINISHED]```"})
            st.success("Finished rendering via user account.")
        else:
            st.error(f"Failed to connect. API Response: {init_response.text}")
