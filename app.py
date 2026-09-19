"""Local source-generation dashboard. Run with streamlit run app.py."""
import streamlit as st
import uuid

from generator import DURATION, EVENTS, FLAVORS, LIBRARY, TONES, save_event

st.set_page_config(page_title="Three-source studio", page_icon="🍦", layout="wide")
st.title("Three-source studio")
st.write("A small, controlled collection of image, audio, and text sources.")
st.caption("Choose each source independently. Preview or download it, then save all three as one event.")

expected_assets = [LIBRARY / "image" / f"{flavor}_{scoops}.png" for flavor in FLAVORS for scoops in (1, 2, 3)]
expected_assets += [LIBRARY / "audio" / f"{tone.lower()}.wav" for tone in TONES]
expected_assets += [LIBRARY / "text" / f"{flavor}.txt" for flavor in FLAVORS]
if any(not asset.is_file() for asset in expected_assets):
    st.error("Some source files are missing. The app owner can restore them by running python generator.py in the project folder.")
    st.stop()

if "export_session" not in st.session_state:
    st.session_state["export_session"] = uuid.uuid4().hex

image_tab, audio_tab, text_tab = st.tabs(["Image", "Audio", "Text"])

with image_tab:
    controls, preview = st.columns([1, 2])
    with controls:
        st.subheader("Build a cone")
        image_flavor = st.selectbox("Image flavor", FLAVORS, format_func=str.title)
        scoops = st.radio("Scoops", [1, 2, 3], horizontal=True)
        st.write("The background, cone, scoop size, and framing stay fixed. Extra scoops add more flavor-colored area.")
        image_source = LIBRARY / "image" / f"{image_flavor}_{scoops}.png"
        image_data = image_source.read_bytes()
        st.download_button("Download image", image_data, file_name=image_source.name, mime="image/png")
        st.caption("Stored PNG · 512 × 640 pixels")
    with preview:
        st.image(image_data, caption=f"{image_flavor.title()} · {scoops} scoop{'s' if scoops != 1 else ''}", width=360)

with audio_tab:
    st.subheader("Choose one tone")
    tone = st.selectbox("Tone", list(TONES), format_func=lambda label: f"{label} · {TONES[label]} Hz")
    audio_source = LIBRARY / "audio" / f"{tone.lower()}.wav"
    audio_data = audio_source.read_bytes()
    st.audio(audio_data, format="audio/wav")
    st.caption(f"{DURATION} seconds · mono WAV · 16,000 samples/second · same amplitude for all tones")
    st.write("Only frequency changes. Each clip has a short, identical fade at both ends to avoid clicks. Tones have no assigned flavor.")
    st.download_button("Download audio", audio_data, file_name=audio_source.name, mime="audio/wav")

with text_tab:
    st.subheader("Read the flavor story")
    text_flavor = st.selectbox("Text flavor", FLAVORS, format_func=str.title)
    text_source = LIBRARY / "text" / f"{text_flavor}.txt"
    text = text_source.read_text(encoding="utf-8")
    st.write(text)
    st.caption(f"{len(text.split())} words · same story, only the flavor word changes")
    st.download_button("Download text", text, file_name=text_source.name, mime="text/plain")

st.divider()
st.subheader("Save a complete event")
st.write(f"Image: **{image_flavor}, {scoops} scoop(s)** · Audio: **{tone.lower()}, {TONES[tone]} Hz** · Text: **{text_flavor}**")
st.caption("Saving copies the current three sources into a new event folder with a shared event ID and UTC timestamp. Changing controls afterward does not change saved events. On a hosted demo, download the ZIP to keep a durable copy.")
if st.button("Save event", type="primary"):
    directory, archive = save_event(image_flavor, scoops, tone, text_flavor,
                                    root=EVENTS / st.session_state["export_session"])
    st.session_state["last_event"] = {"directory": str(directory), "name": directory.name, "archive": archive}
if "last_event" in st.session_state:
    event = st.session_state["last_event"]
    st.success(f"Saved event: {event['name']}")
    st.download_button("Download saved event ZIP", event["archive"], file_name=f"{event['name']}.zip", mime="application/zip")
    with st.expander("Saved event location"):
        st.code(event["directory"], language=None)
st.caption("Sources remain separate raw files. This version does not perform analysis or fusion.")
