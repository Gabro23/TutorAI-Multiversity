import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re
import csv
import os
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Nova Uni AI", page_icon="🤖", layout="centered")

# CSS: Stile Bottoni Blu e interfaccia pulita
st.markdown("""
	<style>
	#MainMenu {visibility: hidden;}
	footer {visibility: hidden;}
	header {visibility: hidden;}
	
	/* Bottoni Blu */
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
	
	/* Chat bubbles arrotondate */
	.stChatMessage {border-radius: 15px;}
	</style>
	""", unsafe_allow_html=True)

# --- 2. RECUPERO CHIAVI ---
try:
	api_key = st.secrets["OPENAI_API_KEY"]
	assistant_id = st.secrets["ASSISTANT_ID"]
	sheet_id = st.secrets["SHEET_ID"]
	# Recupera l'email admin dai secrets (se non c'è, usa una stringa vuota)
	admin_email_secret = st.secrets.get("ADMIN_EMAIL", "").strip().lower()
except Exception as e:
	st.error(f"⚠️ Errore nei Secrets: {e}")
	st.stop()

client = OpenAI(api_key=api_key)
LOG_FILE = "storico_chat.csv"

# --- 3. FUNZIONI ---
def check_login(email_input):
	"""Verifica se l'email esiste nel Google Sheet"""
	# BACKDOOR PER ADMIN: Se l'email è quella dell'admin, entra sempre come "Amministratore"
	if admin_email_secret and email_input.strip().lower() == admin_email_secret:
		return "Amministratore"

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
	except Exception as e:
		st.error(f"Errore nel caricamento dati utenti: {e}")
		return None

def pulisci_testo(testo):
	"""Pulisce il testo dalle fonti e citazioni"""
	if not testo: return ""
	t = str(testo)
	t = re.sub(r"【.*?】", "", t)
	t = re.sub(r"<source>.*?</source>", "", t, flags=re.DOTALL)
	t = re.sub(r"\[\d+\]", "", t)
	t = re.sub(r"\s+", " ", t)
	return t.strip()

def salva_conversazione(utente, domanda, risposta):
	"""Salva la conversazione nel file CSV locale"""
	esiste = os.path.isfile(LOG_FILE)
	try:
		with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
			writer = csv.writer(f)
			# Se il file è nuovo, scriviamo l'intestazione
			if not esiste:
				writer.writerow(["Data", "Utente", "Domanda", "Risposta"])
			
			# Scriviamo i dati
			data_ora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			writer.writerow([data_ora, utente, domanda, risposta])
	except Exception as e:
		print(f"Errore salvataggio log: {e}")

# --- 4. LOGIN ---
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False
	st.session_state.user_email = "" # Teniamo traccia dell'email per sapere se è admin

if not st.session_state.authenticated:
	st.markdown("<h1 style='text-align: center;'>Nova Uni AI 🤖</h1>", unsafe_allow_html=True)
	
	col1, col2, col3 = st.columns([1, 6, 1])
	with col2:
		email = st.text_input("Email", placeholder="Inserisci la tua email")
		if st.button("Accedi", use_container_width=True):
			if email:
				nome = check_login(email)
				if nome:
					st.session_state.authenticated = True
					st.session_state.user_name = nome
					st.session_state.user_email = email.strip().lower()
					st.rerun()
				else:
					st.error("❌ Email non trovata nel sistema.")
			else:
				st.warning("⚠️ Inserisci un'email valida.")
	st.stop()

# --- 5. INTERFACCIA PRINCIPALE ---

# SIDEBAR
with st.sidebar:
	st.title("Area Studenti")
	st.write(f"Ciao, **{st.session_state.user_name}**! 👋")
	st.markdown("---")

	# --- SEZIONE ADMIN (Visibile solo se sei Admin) ---
	if admin_email_secret and st.session_state.user_email == admin_email_secret:
		st.subheader("🛠️ Pannello Admin")
		st.info("Sei loggato come Amministratore.")
		
		if os.path.isfile(LOG_FILE):
			# Legge il file per farlo scaricare
			with open(LOG_FILE, "rb") as f:
				st.download_button(
					label="📥 Scarica Storico Chat",
					data=f,
					file_name="storico_chat_completo.csv",
					mime="text/csv",
					use_container_width=True
				)
		else:
			st.caption("Nessuna conversazione registrata ancora.")
		st.markdown("---")
	# --------------------------------------------------
	
	# Tasto Logout
	if st.button("🔒 Logout", use_container_width=True):
		for key in list(st.session_state.keys()):
			del st.session_state[key]
		st.rerun()
	
	st.markdown("---")
	st.caption("Powered by **GPT-4o Mini**")
	st.caption("Polo Nova Uni © 2025")

# CHAT AREA
st.title("Nova Uni AI 🤖")

# Avviso
st.warning("⚠️ **ATTENZIONE**: L'Intelligenza Artificiale può commettere errori. Verifica sempre le informazioni importanti chiedendo direttamente all'assistenza del Polo.")

# Inizializza cronologia
if "messages" not in st.session_state:
	st.session_state.messages = []

# Inizializza Thread
if "thread_id" not in st.session_state:
	try:
		thread = client.beta.threads.create()
		st.session_state.thread_id = thread.id
	except Exception as e:
		st.error(f"Errore nella creazione del thread: {e}")
		st.stop()

# Mostra messaggi
for msg in st.session_state.messages:
	icona = "🤖" if msg["role"] == "assistant" else "👤"
	with st.chat_message(msg["role"], avatar=icona):
		st.markdown(msg["content"])

# Input utente
prompt = st.chat_input("Scrivi qui la tua domanda...")

if prompt:
	# Aggiungi messaggio utente
	st.session_state.messages.append({"role": "user", "content": prompt})
	with st.chat_message("user", avatar="👤"):
		st.markdown(prompt)

	# Invia messaggio all'assistente
	try:
		client.beta.threads.messages.create(
			thread_id=st.session_state.thread_id,
			role="user",
			content=prompt
		)

		with st.chat_message("assistant", avatar="🤖"):
			with st.spinner("Sto consultando i documenti ufficiali..."):
				# Crea run
				run = client.beta.threads.runs.create(
					thread_id=st.session_state.thread_id,
					assistant_id=assistant_id
				)
				
				# Attendi completamento
				max_attempts = 60
				attempts = 0
				while run.status != "completed" and attempts < max_attempts:
					time.sleep(0.5)
					run = client.beta.threads.runs.retrieve(
						thread_id=st.session_state.thread_id, 
						run_id=run.id
					)
					attempts += 1
					
					if run.status == "failed":
						st.error("❌ Errore tecnico nel recupero della risposta.")
						st.stop()
				
				if attempts >= max_attempts:
					st.error("⏱️ Timeout: la risposta sta impiegando troppo tempo.")
					st.stop()
				
				# Recupera risposta
				messages = client.beta.threads.messages.list(
					thread_id=st.session_state.thread_id
				)
				raw_text = messages.data[0].content[0].text.value
				
				# Pulizia
				clean_text = pulisci_testo(raw_text)
				
				# Mostra risposta
				st.markdown(clean_text)
				st.session_state.messages.append({
					"role": "assistant", 
					"content": clean_text
				})

				# --- SALVATAGGIO AUTOMATICO ---
				# Salviamo la domanda e la risposta nel file CSV
				salva_conversazione(st.session_state.user_name, prompt, clean_text)
				# ------------------------------
	
	except Exception as e:
		st.error(f"❌ Errore durante la comunicazione con l'assistente: {e}")
		st.stop()