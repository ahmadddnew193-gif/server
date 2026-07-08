import streamlit as st
import cv2
import requests
import time
import numpy as np
from PIL import Image, ImageSequence
import io

st.set_page_config(page_title="NEON RENDER ENGINE", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #020205; color: #ff00ff; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #ff00ff !important; text-shadow: 0 0 10px #ff00ff; }
    .stFileUploader { border: 1px dashed #ff00ff !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🌈 CHROMATIC RGB RENDER ENGINE")
st.write("---")

# --- 1. THE FULL COLOR ANSI ENGINE ---
def rgb_matrix_to_ansi(rgb_matrix):
    """
    Converts a color RGB matrix into Discord ANSI escape sequences.
    Uses half-blocks '▄' to display 2 full-color pixels per character slot!
    """
    h, w, _ = rgb_matrix.shape
    h = h - (h % 2)
    
    output = []
    for y in range(0, h, 2):
        line = ""
        for x in range(w):
            r1, g1, b1 = rgb_matrix[y, x]
            r2, g2, b2 = rgb_matrix[y+1, x]
            line += f"\u001b[38;2;{r1};{g1};{b1};48;2;{r2};{g2};{b2}m▄"
        output.append(line)
        
    return "```ansi\n" + "\n".join(output) + "\n```"

# --- 2. MONOCHROME ENGINES ---
def dynamic_braille_render(gray_matrix):
    h, w = gray_matrix.shape
    gray_matrix = gray_matrix[:h - (h % 4), :w - (w % 2)]
    h, w = gray_matrix.shape
    output = []
    binary = (gray_matrix > 127).astype(int)
    for y in range(0, h, 4):
        line = ""
        for x in range(0, w, 2):
            code = 0
            if binary[y+0, x+0]: code |= 0x01
            if binary[y+1, x+0]: code |= 0x02
            if binary[y+2, x+0]: code |= 0x04
            if binary[y+0, x+1]: code |= 0x08
            if binary[y+1, x+1]: code |= 0x10
            if binary[y+2, x+1]: code |= 0x20
            if binary[y+3, x+0]: code |= 0x40
            if binary[y+3, x+1]: code |= 0x80
            line += chr(0x2800 + code)
        output.append(line)
    return "```\n" + "\n".join(output) + "```"

def standard_matrix_render(gray_matrix, matrix_type):
    ramps = {
        "High-Contrast Blocks": [" ", "░", "▒", "▓", "█"],
        "Classic Matrix ASCII": [" ", ".", "-", "+", "*", "=", "%", "#", "@"]
    }
    chars = ramps[matrix_type]
    output = []
    for row in gray_matrix:
        line = "".join([chars[int((pixel / 255) * (len(chars) - 1))] for pixel in row])
        output.append(line)
    return "```\n" + "\n".join(output) + "```"

# --- 3. FRAME PROCESSING LOOP ---
def compile_frames(file_bytes, is_gif, w, h, style):
    frames = []
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        for frame in ImageSequence.Iterator(img):
            if style == "TrueColor RGB (ANSI)":
                rgb_img = np.array(frame.convert("RGB"))
                resized = cv2.resize(rgb_img, (w, h))
                frames.append(rgb_matrix_to_ansi(resized))
            else:
                gray = np.array(frame.convert("L"))
                resized = cv2.resize(gray, (w, h))
                if style == "True High-Res Braille Matrix":
                    frames.append(dynamic_braille_render(resized))
                else:
                    frames.append(standard_matrix_render(resized, style))
    else:
        with open("temp.mp4", "wb") as f: 
            f.write(file_bytes)
        cap = cv2.VideoCapture("temp.mp4")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break
            if style == "TrueColor RGB (ANSI)":
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                resized = cv2.resize(rgb_frame, (w, h))
                frames.append(rgb_matrix_to_ansi(resized))
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (w, h))
                if style == "True High-Res Braille Matrix":
                    frames.append(dynamic_braille_render(resized))
                else:
                    frames.append(standard_matrix_render(resized, style))
        cap.release()
    return frames

# --- 4. SIDEBAR TOKEN AUTH ---
st.sidebar.header("🔑 TOKENS")
USER_TOKEN = st.sidebar.text_input("User Token", type="password")
TARGET_CHANNEL = st.sidebar.text_input("Channel ID")
authenticated = False

if USER_TOKEN:
    res = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": USER_TOKEN})
    if res.status_code == 200:
        st.sidebar.success(f"Authenticated: {res.json()['username']}")
        authenticated = True
    else:
        st.sidebar.error("Invalid Handshake Protocol.")

# --- 5. FILE UPLOADER & AUTO-CALCULATOR ---
uploaded_file = st.file_uploader("Upload Asset (.mp4, .mov, .gif)", type=["mp4", "mov", "gif"])

auto_w, auto_h, auto_delay = 40, 20, 0.6
is_gif = False

if uploaded_file:
    is_gif = uploaded_file.name.split(".")[-1].lower() == "gif"
    file_bytes = uploaded_file.read()
    
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        auto_delay = max(0.5, img.info.get("duration", 60) / 1000.0)
    else:
        with open("temp_probe.mp4", "wb") as f: 
            f.write(file_bytes)
        cap = cv2.VideoCapture("temp_probe.mp4")
        fps = cap.get(cv2.CAP_PROP_FPS)
        auto_delay = max(0.6, 1.0 / fps if fps > 0 else 0.6)
        cap.release()

# --- 6. INTERFACE SETUP ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🛠️ Engine Configurations")
    render_style = st.selectbox("Render Mode", [
        "TrueColor RGB (ANSI)",
        "True High-Res Braille Matrix", 
        "High-Contrast Blocks", 
        "Classic Matrix ASCII"
    ])
    
    if render_style == "TrueColor RGB (ANSI)":
        max_w, default_w = 24, 16
        max_h, default_h = 20, 12
    elif render_style == "True High-Res Braille Matrix":
        max_w, default_w = 100, 60
        max_h, default_h = 60, 30
    else:
        max_w, default_w = 50, 35
        max_h, default_h = 40, 20

    width = st.slider("Render Width (Pixels)", 6, max_w, default_w, help="Auto-bounded to fit Discord limitations.")
    height = st.slider("Render Height (Pixels)", 6, max_h, default_h, help="Auto-bounded to fit Discord limitations.")
    delay = st.slider("Frame Hold Delay (Seconds)", 0.2, 2.0, auto_delay)

with col2:
    st.subheader("📺 Production Monitor")
    if not authenticated or not uploaded_file:
        st.info("System awaiting pipeline credentials and raw asset uploads.")
    else:
        if st.button("🚀 TRANSMIT LIVE RGB STREAM"):
            frames = compile_frames(file_bytes, is_gif, width, height, render_style)
            st.success(f"Buffer populated. Total frames loaded: {len(frames)}")
            
            headers = {"Authorization": USER_TOKEN, "Content-Type": "application/json"}
            url = f"https://discord.com/api/v9/channels/{TARGET_CHANNEL}/messages"
            
            init = requests.post(url, headers=headers, json={"content": "```ansi\n\u001b[35mSyncing Chromatic Core...```"})
            if init.status_code == 200:
                msg_id = init.json()["id"]
                patch_url = f"{url}/{msg_id}"
                
                status_box = st.empty()
                preview_box = st.empty()
                
                for idx, frame in enumerate(frames):
                    status_box.text(f"Displaying Frame: {idx+1}/{len(frames)}")
                    preview_box.code(frame.replace("```ansi\n", "").replace("\n```", ""), language="text")
                    
                    res = requests.patch(patch_url, headers=headers, json={"content": frame})
                    if res.status_code == 429:
                        time.sleep(res.json().get("retry_after", 1.5))
                    else:
                        time.sleep(delay)
                        
                requests.patch(patch_url, headers=headers, json={"content": "```ansi\n\u001b[32m[RGB TRANSMISSION SUCCESSFUL]```"})
                st.success("Playback execution loop finished.")
            else:
                st.error("Discord API connection refused initialization request.")
