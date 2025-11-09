import streamlit as st
import google.generativeai as genai
import json
import re
from gtts import gTTS
import speech_recognition as sr
from io import BytesIO
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Dynamic Company Chatbot",
    page_icon="Robot",
    layout="wide"
)

# Initialize session state
if 'configured' not in st.session_state:
    st.session_state.configured = False
if 'company_data' not in st.session_state:
    st.session_state.company_data = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
if 'chat_session' not in st.session_state:
    st.session_state.chat_session = None
if 'audio_allowed' not in st.session_state:
    st.session_state.audio_allowed = False

def extract_company_info(company_name, website_url, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')  # Latest model
        
        prompt = f"""Extract info for {company_name} ({website_url}) in JSON only:
{{
  "companyName": "",
  "tagline": "",
  "description": "",
  "services": [],
  "tone": "",
  "industry": "",
  "welcomeMessage": ""
}}
Return ONLY JSON."""

        response = model.generate_content(prompt)
        text = re.sub(r'```json\s*|\s*```', '', response.text).strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("JSON not found")
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return {
            "companyName": company_name,
            "tagline": "Your trusted partner",
            "description": f"{company_name} offers great services.",
            "services": ["Support", "Info", "Help"],
            "tone": "friendly",
            "industry": "Tech",
            "welcomeMessage": f"Hi! Welcome to {company_name}!"
        }

def get_chatbot_response(user_message, company_data, api_key):
    try:
        genai.configure(api_key=api_key)
        if st.session_state.chat_session is None:
            model = genai.GenerativeModel('gemini-2.5-flash')
            st.session_state.chat_session = model.start_chat(history=[])

        prompt = f"""You are {company_data['companyName']}'s assistant.
Tone: {company_data['tone']}
Services: {', '.join(company_data['services'])}

User: {user_message}
Respond in 2-3 sentences, {company_data['tone']} tone."""
        
        response = st.session_state.chat_session.send_message(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except:
        return None

def speech_to_text():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("Listening... Speak now!")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        st.info("Processing...")
        return recognizer.recognize_google(audio)
    except sr.WaitTimeoutError:
        st.error("No speech detected")
    except sr.UnknownValueError:
        st.error("Could not understand")
    except Exception as e:
        st.error(f"Error: {e}")
    return None

# CSS
st.markdown("""
<style>
    .main-header {background: linear-gradient(135deg, #667eea, #764ba2); padding: 2rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem;}
    .company-header {background: linear-gradient(135deg, #2563eb, #1e40af); padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1rem;}
    .message-user {background: #2563eb; color: white; padding: 1rem; border-radius: 15px; margin: 0.5rem 0; margin-left: 20%;}
    .message-bot {background: #f3f4f6; color: #1f2937; padding: 1rem; border-radius: 15px; margin: 0.5rem 0; margin-right: 20%;}
</style>
""", unsafe_allow_html=True)

# === MAIN APP ===
if not st.session_state.configured:
    st.markdown('<div class="main-header"><h1>Dynamic Company Chatbot</h1><p>Voice + Text | Powered by Gemini 2.5</p></div>', unsafe_allow_html=True)
    
    # Allow sound (browser policy)
    if not st.session_state.audio_allowed:
        if st.button("Enable Sound (Click Once)"):
            st.session_state.audio_allowed = True
            st.success("Sound enabled! Voice chat ready.")
            st.rerun()

    # API Key
    if st.session_state.api_key:
        st.success("API Key loaded!")
        api_key = st.session_state.api_key
    else:
        st.info("Get FREE key: [Google AI Studio](https://makersuite.google.com/app/apikey)")
        api_key = st.text_input("Enter Gemini API Key:", type="password")
        if not api_key:
            st.warning("Enter API key to continue")
            st.stop()

    if api_key:
        st.session_state.api_key = api_key
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("Company Name", placeholder="Tesla")
        with col2:
            company_website = st.text_input("Website", placeholder="www.tesla.com")

        if st.button("Launch Chatbot", type="primary"):
            if company_name and company_website:
                with st.spinner("Setting up..."):
                    data = extract_company_info(company_name, company_website, api_key)
                    st.session_state.company_data = data
                    st.session_state.configured = True
                    st.session_state.messages = [{"role": "assistant", "content": data['welcomeMessage']}]
                    st.rerun()
            else:
                st.error("Fill both fields")

else:
    data = st.session_state.company_data
    st.markdown(f'<div class="company-header"><h2>{data["companyName"]}</h2><p>{data["tagline"]}</p><p>{data["description"]}</p></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### Company")
        st.write(f"**Name:** {data['companyName']}")
        st.write(f"**Tone:** {data['tone'].title()}")
        st.markdown("### Services")
        for s in data['services']:
            st.write(f"• {s}")
        if st.button("Reset"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

    st.markdown("### Chat")
    chat = st.container()
    with chat:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="message-user">You: {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="message-bot">{data["companyName"]}: {msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Start the Conversation")
    tab1, tab2 = st.tabs(["Text", "Voice"])

    # TEXT CHAT
    with tab1:
        col1, col2 = st.columns([5,1])
        with col1:
            user_input = st.text_input("Message:", key="text_in", label_visibility="collapsed")
        with col2:
            send = st.button("Send", type="primary")
        if send and user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.spinner("Thinking..."):
                bot_reply = get_chatbot_response(user_input, data, st.session_state.api_key)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            st.rerun()

    # VOICE CHAT
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start Speaking", type="primary"):
                if not st.session_state.audio_allowed:
                    st.warning("Click 'Enable Sound' first!")
                else:
                    speech = speech_to_text()
                    if speech:
                        st.success(f"You: **{speech}**")
                        st.session_state.messages.append({"role": "user", "content": speech})
                        with st.spinner("AI is thinking..."):
                            bot_reply = get_chatbot_response(speech, data, st.session_state.api_key)
                        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                        st.success(f"AI: {bot_reply}")
                        # AUTO PLAY VOICE
                        with st.spinner("Speaking..."):
                            audio = text_to_speech(bot_reply)
                            if audio:
                                st.audio(audio, format='audio/mp3', autoplay=True)
                        st.rerun()
        with col2:
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                if st.button("Replay"):
                    last = st.session_state.messages[-1]["content"]
                    audio = text_to_speech(last)
                    if audio:
                        st.audio(audio, format='audio/mp3', autoplay=True)

        st.info("**Voice Chat:** Click 'Start Speaking' → Speak → AI replies in **voice automatically**!")
        st.warning("Click page once to allow sound if no audio.")

# Footer
st.markdown("---")
st.markdown("<p style='text-align:center; color:#666;'>Dynamic Chatbot | Gemini 2.5 + Voice | 2025</p>", unsafe_allow_html=True)