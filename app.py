import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Nova Uni AI", page_icon="🤖", layout="centered")

# CSS CORRETTO (Leggibile sia su sfondo chiaro che scuro)
st.markdown("""
	<style>
	/* Nascondiamo menu e footer */
	#MainMenu {visibility: hidden;}
	footer {visibility: hidden;}
	header {visibility: hidden;}
	
	/* I TITOLI ORA SI ADATTANO (Non forziamo il colore scuro) */
	
	/* BOTTONI BLU NOVA UNI (Testo bianco sempre leggibile) */
	div.stButton > button {
		background-color: #003366 !important;
		color: white !important;
		border: none;
		border-radius: 8px;
		font-weight: bold;
	}
	div.stButton > button:hover {
		background-color: #004080 !important; /* Blu leggermente più chiaro al passaggio */
		color: white !important;
	}
	
	/* Arrotondamento messaggi chat */
	.stChatMessage {border-radius: 15px;}
	</style>
	""", unsafe_allow_html=True)

# --- 2. SECRETS ---
try:
	api_key = st.secrets["OPENAI_API_KEY"]
	assistant_id = st.secrets["ASSISTANT_ID"]
	sheet_id = st.secrets["SHEET_ID"]
except:
	st.error("⚠️ Manca il file Secrets. Controlla le impostazioni su Streamlit.")
	st.stop()

client = OpenAI(api_key=api_key)

# --- 3. FUNZIONI (SENZA ERRORI) ---
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

# --- 4. LOGIN ---
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False

if not st.session_state.authenticated:
	# Titolo richiesto con Robot
	st.markdown("<h1 style='text-align: center;'>Nova Uni AI 🤖</h1>", unsafe_allow_html=True)
	
	col1, col2, col3 = st.columns([1, 6, 1])
	with col2:
		# Solo "Email" come richiesto
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

# Titolo interno
st.title("Nova Uni AI 🤖")

if "messages" not in st.session_state:
	st.session_state.messages = []

if "thread_id" not in st.session_state:
	thread = client.beta.threads.create()
	st.session_state.thread_id = thread.id

# Mostra messaggi
for msg in st.session_state.messages:
	icona = "🤖" if msg["role"] == "assistant" else "👤"
	with st.chat_message(msg["role"], avatar=icona):
		st.markdown(msg["content"])

# Input utente
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
					 st.error("Errore risposta.")
					 st.stop()
			
			# Recupero testo
			full_response = client.beta.threads.messages.list(thread_id=st.session_state.thread_id).data[0].content[0].text.value
			
			# Pulizia sicura
			full_response = full_response.replace("【", "").replace("】", "")
			# Rimuove pattern tipo in modo semplice
			import re
			full_response = re.sub(r'\', '', full_response)
			
			st.markdown(full_response)
			st.session_state.messages.append({"role": "assistant", "content": full_response})