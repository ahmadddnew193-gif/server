import streamlit as st
import cv2
import requests
import time
import numpy as np
from PIL import Image, ImageSequence
import io

st.set_page_config(page_title="QUANTUM RENDER PIPELINE", layout="wide")

# --- TECH-STYLED UI ---
st.markdown("""
    <style>
    .main { background-color: #030307; color: #00ff66; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ff66 !important; text-shadow: 0 0 10px #00ff66; }
    .stFileUploader { border: 1px dashed #00ff66 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎛️ QUANTUM 2D RENDER PIPELINE")
st.write("---")

# --- ADVANCED TRUE BRAILLE INTERPOLATION ENGINE ---
def dynamic_braille_render(gray_matrix):
    """
    Maps a 2D gray matrix into true Unicode Braille patterns.
    Each character represents a 2x4 sub-pixel matrix.
    """
    h, w = gray_matrix.shape
    # Ensure dimensions are multiples of 4 (height) and 2 (width)
    gray_matrix = gray_matrix[:h - (h % 4), :w - (w % 2)]
    h, w = gray_matrix.shape
    
    output = []
    # Binary thresholding
    binary = (gray_matrix > 127).astype(int)
    
    # Unicode Braille dot offsets:
    # Dot 1: r0,c0 (0x01) | Dot 4: r0,c1 (0x08)
    # Dot 2: r1,c0 (0x02) | Dot 5: r1,c1 (0x10)
    # Dot 3: r2,c0 (0x04) | Dot 6: r2,c1 (0x20)
    # Dot 7: r3,c0 (0x40) | Dot 8: r3,c1 (0x80)
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

# --- STANDARD RENDER ENGINE OPTIONS ---
def standard_matrix_render(gray_matrix, matrix_type):
    ramps = {
        "High-Contrast Blocks": [" ", "░", "▒", "▓", "█"],
        "Binary Terminal": ["0", "1"],
        "Classic Matrix ASCII": [" ", ".", "-", "+", "*", "=", "%", "#", "@"]
    }
    chars = ramps[matrix_type]
    output = []
    for row in gray_matrix:
        line = "".join([chars[int((pixel / 255) * (len(chars) - 1))] for pixel in row])
        output.append(line)
    return "```\n" + "\n".join(output) + "```"

# --- ASSET DISPATCH & CONVERSION ---
def compile_frames(file_bytes, is_gif, w, h, style):
    frames = []
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        for frame in ImageSequence.Iterator(img):
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
            if not ret: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (w, h))
            if style == "True High-Res Braille Matrix":
                frames.append(dynamic_braille_render(resized))
            else:
                frames.append(standard_matrix_render(resized, style))
        cap.release()
    return frames

# --- SECURITY HANDSHAKE ---
st.sidebar.header("🔑 TELEMETRY ACCESS")
USER_TOKEN = st.sidebar.text_input("User Token", type="password")
TARGET_CHANNEL = st.sidebar.text_input("Channel ID")
authenticated = False

if USER_TOKEN:
    res = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": USER_TOKEN})
    if res.status_code == 200:
        st.sidebar.success(f"Linked: {res.json()['username']}")
        authenticated = True
    else:
        st.sidebar.error("Invalid Handshake Protocol.")

# --- FILE ANALYSIS & AUTO CONFIG ---
uploaded_file = st.file_uploader("Drop Asset Matrix (.mp4, .mov, .gif)", type=["mp4", "mov", "gif"])

auto_w, auto_h, auto_delay = 40, 20, 0.6
is_gif = False

if uploaded_file:
    is_gif = uploaded_file.name.split(".")[-1].lower() == "gif"
    file_bytes = uploaded_file.read()
    
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        duration = img.info.get("duration", 60) # in ms
        auto_delay = max(0.4, duration / 1000.0) # convert to seconds, safety floor of 0.4
        # GIFs can render slightly wider because Braille packs space efficiently
        auto_w, auto_h = 56, 28
    else:
        with open("temp_probe.mp4", "wb") as f:
            f.write(file_bytes)
        cap = cv2.VideoCapture("temp_probe.mp4")
        fps = cap.get(cv2.CAP_PROP_FPS)
        auto_delay = max(0.5, 1.0 / fps if fps > 0 else 0.5) # match real fps, cap at 0.5 for rate limit
        auto_w, auto_h = 44, 20
        cap.release()

# --- CONFIG INTERFACE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🛠️ Engine Adjustments")
    render_style = st.selectbox("2D Architecture Style", [
        "True High-Res Braille Matrix", 
        "High-Contrast Blocks", 
        "Binary Terminal", 
        "Classic Matrix ASCII"
    ])
    
    # If using true Braille, we scale the matrix size up because 4 pixels fit in one text row!
    default_w = auto_w * 2 if render_style == "True High-Res Braille Matrix" else auto_w
    default_h = auto_h * 2 if render_style == "True High-Res Braille Matrix" else auto_h

    width = st.slider("Target Width (Pixels)", 10, 120, default_w, help="Auto-optimized for your file.")
    height = st.slider("Target Height (Pixels)", 10, 80, default_h, help="Auto-optimized for your file.")
    delay = st.slider("Telemetry Frame Delay (Sec)", 0.2, 2.0, auto_delay)

with col2:
    st.subheader("📡 Live Broadcast Stream")
    if not authenticated or not uploaded_file:
        st.info("System offline. Provide authorization credentials and target data assets.")
    else:
        if st.button("🚀 EXECUTE DYNAMIC FLIPBOOK"):
            frames = compile_frames(file_bytes, is_gif, width, height, render_style)
            st.success(f"Telemetry lock ready. Total Frame Matrices: {len(frames)}")
            
            headers = {"Authorization": USER_TOKEN, "Content-Type": "application/json"}
            url = f"https://discord.com/api/v9/channels/{TARGET_CHANNEL}/messages"
            
            init = requests.post(url, headers=headers, json={"content": "```\nSyncing Matrix...```"})
            if init.status_code == 200:
                msg_id = init.json()["id"]
                patch_url = f"{url}/{msg_id}"
                
                status_box = st.empty()
                preview_box = st.empty()
                
                for idx, frame in enumerate(frames):
                    status_box.text(f"Sync Frame: {idx+1}/{len(frames)}")
                    preview_box.markdown(frame)
                    
                    res = requests.patch(patch_url, headers=headers, json={"content": frame})
                    if res.status_code == 429:
                        time.sleep(res.json().get("retry_after", 1.0))
                    else:
                        time.sleep(delay)
                        
                requests.patch(patch_url, headers=headers, json={"content": "```\n[TRANSMISSION COMPLETE]```"})
                st.success("Pipeline clear.")
            else:
                st.error("Target endpoint refused injection request.")
