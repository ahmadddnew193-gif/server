import streamlit as st
import cv2
import requests
import time
import numpy as np
from PIL import Image, ImageSequence
import io

st.set_page_config(page_title="NEON MATRIX PRODUCER", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #020205; color: #00ffff; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #00ffff !important; text-shadow: 0 0 10px #00ffff; }
    .stFileUploader { border: 1px dashed #00ffff !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📟 MATRIX MULTI-SHADED PIPELINE")
st.write("---")

# --- 1. THE SHADER MODULES ---
def rgb_matrix_to_ansi(rgb_matrix):
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

def gray_to_green_phosphor(gray_matrix):
    green_ramp = [" ", "\u001b[32m.", "\u001b[32m-", "\u001b[32m=", "\u001b[32m+", "\u001b[1;32m░", "\u001b[1;32m▒", "\u001b[1;32m▓", "\u001b[1;32m█"]
    output = []
    for row in gray_matrix:
        line = "".join([green_ramp[int((pixel / 255) * (len(green_ramp) - 1))] for pixel in row])
        output.append(line)
    return "```ansi\n" + "\n".join(output) + "\n```"

def gray_to_smooth_scan(gray_matrix):
    scan_ramp = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    output = []
    for row in gray_matrix:
        line = "".join([scan_ramp[int((pixel / 255) * (len(scan_ramp) - 1))] for pixel in row])
        output.append(line)
    return "```\n" + "\n".join(output) + "```"

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

# --- 2. PIPELINE COMPILER WITH FRAME SKIPPING ---
def compile_frames(file_bytes, is_gif, w, h, style, frame_step):
    frames = []
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        # Loop over the GIF frames with our step interval
        for idx, frame in enumerate(ImageSequence.Iterator(img)):
            if idx % frame_step != 0:
                continue
                
            if style == "TrueColor RGB (ANSI)":
                rgb_img = np.array(frame.convert("RGB"))
                resized = cv2.resize(rgb_img, (w, h))
                frames.append(rgb_matrix_to_ansi(resized))
            else:
                gray = np.array(frame.convert("L"))
                resized = cv2.resize(gray, (w, h))
                if style == "Green Cyber Phosphor (ANSI)":
                    frames.append(gray_to_green_phosphor(resized))
                elif style == "Horizontal Smooth-Scan":
                    frames.append(gray_to_smooth_scan(resized))
                elif style == "True High-Res Braille Matrix":
                    frames.append(dynamic_braille_render(resized))
                else:
                    frames.append(standard_matrix_render(resized, style))
    else:
        with open("temp.mp4", "wb") as f: f.write(file_bytes)
        cap = cv2.VideoCapture("temp.mp4")
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Check frame step constraint
            if frame_idx % frame_step == 0:
                if style == "TrueColor RGB (ANSI)":
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    resized = cv2.resize(rgb_frame, (w, h))
                    frames.append(rgb_matrix_to_ansi(resized))
                else:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    resized = cv2.resize(gray, (w, h))
                    if style == "Green Cyber Phosphor (ANSI)":
                        frames.append(gray_to_green_phosphor(resized))
                    elif style == "Horizontal Smooth-Scan":
                        frames.append(gray_to_smooth_scan(resized))
                    elif style == "True High-Res Braille Matrix":
                        frames.append(dynamic_braille_render(resized))
                    else:
                        frames.append(standard_matrix_render(resized, style))
            frame_idx += 1
        cap.release()
    return frames

# --- 3. TOKENS & SECURE CONNECTION ---
st.sidebar.header("🔑 TELEMETRY")
USER_TOKEN = st.sidebar.text_input("User Token", type="password")
TARGET_CHANNEL = st.sidebar.text_input("Channel ID")
authenticated = False

if USER_TOKEN:
    res = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": USER_TOKEN})
    if res.status_code == 200:
        st.sidebar.success(f"Linked: {res.json()['username']}")
        authenticated = True
    else:
        st.sidebar.error("Invalid Handshake Module.")

# --- 4. DATA INGESTION & HEADER LOGIC ---
uploaded_file = st.file_uploader("Upload Core Asset Matrix (.mp4, .mov, .gif)", type=["mp4", "mov", "gif"])

auto_w, auto_h, auto_delay = 40, 20, 0.6
is_gif = False

if uploaded_file:
    is_gif = uploaded_file.name.split(".")[-1].lower() == "gif"
    file_bytes = uploaded_file.read()
    
    if is_gif:
        img = Image.open(io.BytesIO(file_bytes))
        auto_delay = max(0.5, img.info.get("duration", 60) / 1000.0)
    else:
        with open("temp_probe.mp4", "wb") as f: f.write(file_bytes)
        cap = cv2.VideoCapture("temp_probe.mp4")
        fps = cap.get(cv2.CAP_PROP_FPS)
        auto_delay = max(0.6, 1.0 / fps if fps > 0 else 0.6)
        cap.release()

# --- 5. UI CONFIG INTERFACE ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("⚙️ Processing Settings")
    render_style = st.selectbox("Render Engine Module", [
        "TrueColor RGB (ANSI)",
        "Green Cyber Phosphor (ANSI)",
        "Horizontal Smooth-Scan",
        "True High-Res Braille Matrix", 
        "High-Contrast Blocks", 
        "Classic Matrix ASCII"
    ])
    
    if render_style in ["TrueColor RGB (ANSI)", "Green Cyber Phosphor (ANSI)"]:
        max_w, default_w = 24, 16
        max_h, default_h = 20, 12
    elif render_style == "True High-Res Braille Matrix":
        max_w, default_w = 100, 60
        max_h, default_h = 60, 30
    else:
        max_w, default_w = 50, 35
        max_h, default_h = 40, 20

    width = st.slider("Width Allocation (Pixels)", 6, max_w, default_w)
    height = st.slider("Height Allocation (Pixels)", 6, max_h, default_h)
    
    # NEW FRAME SKIP SLIDER
    frame_step = st.slider("Frame Step Interval", 1, 15, 1, 
                           help="1 reads every frame. 2 reads every second frame. 10 skips to every tenth frame.")
    
    # Scale delay automatically if frames are skipped to keep animation at a natural pace
    adjusted_delay = auto_delay * frame_step
    delay = st.slider("Frame Hold Timeline Delay (Sec)", 0.1, 3.0, min(adjusted_delay, 3.0))

with col2:
    st.subheader("📺 Output Status Console")
    if not authenticated or not uploaded_file:
        st.info("System offline. Input valid authorizations and files.")
    else:
        if st.button("🚀 IGNITE MATRIX SEQUENCE TRANSMISSION"):
            # Pass frame_step into compilation module
            frames = compile_frames(file_bytes, is_gif, width, height, render_style, frame_step)
            st.success(f"Buffer populated. Total compiled frames: {len(frames)}")
            
            headers = {"Authorization": USER_TOKEN, "Content-Type": "application/json"}
            url = f"https://discord.com/api/v9/channels/{TARGET_CHANNEL}/messages"
            
            init = requests.post(url, headers=headers, json={"content": "```\nLinking...```"})
            if init.status_code == 200:
                msg_id = init.json()["id"]
                patch_url = f"{url}/{msg_id}"
                
                status_box = st.empty()
                preview_box = st.empty()
                
                for idx, frame in enumerate(frames):
                    status_box.text(f"Injecting Sequence: {idx+1}/{len(frames)}")
                    preview_box.code(frame.replace("```ansi\n", "").replace("```\n", "").replace("\n```", ""), language="text")
                    
                    res = requests.patch(patch_url, headers=headers, json={"content": frame})
                    if res.status_code == 429:
                        time.sleep(res.json().get("retry_after", 1.5))
                    else:
                        time.sleep(delay)
                        
                requests.patch(patch_url, headers=headers, json={"content": "```\n[PIPELINE TERMINATED]```"})
                st.success("Playback clear.")
            else:
                st.error("Target pipeline connection timed out.")
