import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Nova Uni AI", page_icon="🤖", layout="centered")

# CSS: Bottoni Blu, Testo leggibile, Nascondere menu standard
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
	
	/* Messaggi Chat arrotondati */
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
	"""
	Rimuove le citazioni in modo SICURO per evitare SyntaxError.
	"""
	t = str(testo)
	# Rimuove le parentesi di OpenAI tipo 【4:0†source】
	t = re.sub(r"【.*?】", "", t)
	# Rimuove i tag source tipo - Uso le doppie virgolette per sicurezza
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

# --- 5. INTERFACCIA PRINCIPALE (DOPO LOGIN) ---

# SIDEBAR
with st.sidebar:
	st.title("Area Studenti")
	st.write(f"Ciao, **{st.session_state.user_name}**!")
	st.markdown("---")
	
	# Tasto Logout (Solo "Logout")
	if st.button("🔒 Logout"):
		st.session_state.authenticated = False
		st.rerun()
		
	st.markdown("---")
	# Scritta Powered By
	st.caption("Powered by **GPT-4o Mini**")
	st.caption("Polo Nova Uni © 2025")

# MAIN CHAT AREA
st.title("Nova Uni AI 🤖")

# Avviso importante
st.warning("⚠️ ATTENZIONE: L'Intelligenza Artificiale può commettere errori. Verifica sempre le informazioni importanti chiedendo direttamente all'assistenza del Polo.")

# Inizializza cronologia
if "messages" not in st.session_state:
	st.session_state.messages = []

# Inizializza Thread OpenAI
if "thread_id" not in st.session_state:
	thread = client.beta.threads.create()
	st.session_state.thread_id = thread.id

# Mostra messaggi precedenti
for msg in st.session_state.messages:
	icona = "🤖" if msg["role"] == "assistant" else "👤"
	with st.chat_message(msg["role"], avatar=icona):
		st.markdown(msg["content"])

# Input utente
prompt = st.chat_input("Scrivi qui la tua domanda...")

if prompt:
	# 1. Salva e mostra messaggio utente
	st.session_state.messages.append({"role": "user", "content": prompt})
	with st.chat_message("user", avatar="👤"):
		st.markdown(prompt)

	# 2. Invia a OpenAI
	client.beta.threads.messages.create(
		thread_id=st.session_state.thread_id,
		role="user",
		content=prompt
	)

	# 3. Risposta Bot
	with st.chat_message("assistant", avatar="🤖"):
		# Testo di caricamento personalizzato
		with st.spinner("Sto consultando i documenti ufficiali..."):
			run = client.beta.threads.runs.create(
				thread_id=st.session_state.thread_id,
				assistant_id=assistant_id
			)
			while run.status != "completed":
				time.sleep(0.5)
				run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
				if run.status == "failed":
					st.error("Errore tecnico nel recupero della risposta.")
					st.stop()
			
			# Recupero testo grezzo
			raw_text = client.beta.threads.messages.list(thread_id=st.session_state.thread_id).data[0].content[0].text.value
			
			# Pulizia testo (Funzione sicura)
			clean_text = pulisci_testo(raw_text)
			
			st.markdown(clean_text)
			st.session_state.messages.append({"role": "assistant", "content": clean_text})