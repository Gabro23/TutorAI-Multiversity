import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Nova Uni AI", page_icon="🤖", layout="centered")

# CSS: Bottoni Blu, Testo che si adatta (bianco su scuro)
st.markdown("""
	<style>
	#MainMenu {visibility: hidden;}
	footer {visibility: hidden;}
	header {visibility: hidden;}
	
	/* Bottoni Blu Nova Uni */
	div.stButton > button {
		background-color: #003366 !important;
		color: white !important;
		border: none;
		border-radius: 8px;
		font-weight: bold; 
	}
	div.stButton > button:hover {
		background-color: #004080 !important;
		color: white !important;
	}
	
	/* Arrotondamento messaggi */
	.stChatMessage {border-radius: 15px;}
	</style>
	""", unsafe_allow_html=True)

# --- 2. RECUPERO CHIAVI ---
try:
	api_key = st.secrets["OPENAI_API_KEY"]
	assistant_id = st.secrets["ASSISTANT_ID"]
	sheet_id = st.secrets["SHEET_ID"]
except:
	st.error("⚠️ Secrets mancanti. Controlla le impostazioni su Streamlit.")
	st.stop()

client = OpenAI(api_key=api_key)

# --- 3. FUNZIONI ---
def check_login(email_input):
	try:
		url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
		df = pd.read_csv(url, dtype=str)
		email_clean = email_input.strip().lower()
		if 'email' in df.columns:
			df['email'] = df['email'].astype(str).str.strip().str.lower()
			res = df[df['email'] == email_clean]
			if not res.empty:
				return res.iloc[0]['nome_studente']
		return None
	except:
		return None

def pulisci_testo(testo):
	# Converte in stringa
	t = str(testo)
	# Rimuove le parentesi di OpenAI
	t = t.replace("【", "").replace("】", "")
	# Rimuove i tag source (Modificato per essere sicuro al 100%)
	t = re.sub(r"\", "", t)
	return t.strip()

# --- 4. LOGIN ---
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False

if not st.session_state.authenticated:
	st.markdown("<h1 style='text-align: center;'>Nova Uni AI 🤖</h1>", unsafe_allow_html=True)
	
	col1, col2, col3 = st.columns([1, 6, 1])
	with col2:
		email = st.text_input("Email")
		if st.button("Accedi", use_container_width=True):
			nome = check_login(email)
			if nome:
				st.session_state.authenticated = True
				st.session_state.user_name = nome
				st.rerun()
			else:
				st.error("Email non trovata.")
	st.stop()

# --- 5. CHAT ---
with st.sidebar:
	st.title("Area Studenti")
	st.write(f"Ciao, **{st.session_state.user_name}**!")
	st.markdown("---")
	if st.button("🚪 Esci"):
		st.session_state.authenticated = False
		st.rerun()

st.title("Nova Uni AI 🤖")

if "messages" not in st.session_state:
	st.session_state.messages = []

if "thread_id" not in st.session_state:
	thread = client.beta.threads.create()
	st.session_state.thread_id = thread.id

for msg in st.session_state.messages:
	icona = "🤖" if msg["role"] == "assistant" else "👤"
	with st.chat_message(msg["role"], avatar=icona):
		st.markdown(msg["content"])

prompt = st.chat_input("Scrivi qui la tua domanda...")

if prompt:
	st.session_state.messages.append({"role": "user", "content": prompt})
	with st.chat_message("user", avatar="👤"):
		st.markdown(prompt)

	client.beta.threads.messages.create(
		thread_id=st.session_state.thread_id,
		role="user",
		content=prompt
	)

	with st.chat_message("assistant", avatar="🤖"):
		with st.spinner("..."):
			run = client.beta.threads.runs.create(
				thread_id=st.session_state.thread_id,
				assistant_id=assistant_id
			)
			while run.status != "completed":
				time.sleep(0.5)
				run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
				if run.status == "failed":
					st.error("Errore tecnico.")
					st.stop()
			
			raw_text = client.beta.threads.messages.list(thread_id=st.session_state.thread_id).data[0].content[0].text.value
			
			# Pulizia sicura
			clean_text = pulisci_testo(raw_text)
			
			st.markdown(clean_text)
			st.session_state.messages.append({"role": "assistant", "content": clean_text})