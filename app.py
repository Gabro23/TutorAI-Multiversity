import streamlit as st
import pandas as pd
from openai import OpenAI
import time
import re

# --- 1. CONFIGURAZIONE PAGINA E STILE ---
st.set_page_config(page_title="Tutor Nova Uni", page_icon="🎓", layout="centered")

# CSS PERSONALIZZATO: Qui cambiamo i colori da Rosso a Blu!
st.markdown("""
	<style>
	/* Nasconde menu hamburger e footer standard */
	#MainMenu {visibility: hidden;}
	footer {visibility: hidden;}
	header {visibility: hidden;}
	
	/* TITOLI: Blu Istituzionale */
	h1, h2, h3 {
		color: #003366 !important; 
		font-family: 'Helvetica', sans-serif;
	}
	
	/* BOTTONI (Esci, Accedi, ecc): Diventano BLU invece che Rossi */
	div.stButton > button {
		background-color: #003366 !important; /* Blu scuro */
		color: white !important;
		border: none;
		border-radius: 8px;
		padding: 10px 20px;
		font-weight: bold;
	}
	/* Quando passi sopra col mouse diventa un po' più chiaro */
	div.stButton > button:hover {
		background-color: #004080 !important;
		color: white !important;
	}

	/* MESSAGGI CHAT: Arrotondati e puliti */
	.stChatMessage {
		border-radius: 15px;
	}
	</style>
	""", unsafe_allow_html=True)

# --- 2. RECUPERO CHIAVI ---
try:
	api_key = st.secrets["OPENAI_API_KEY"]
	assistant_id = st.secrets["ASSISTANT_ID"]
	sheet_id = st.secrets["SHEET_ID"]
except FileNotFoundError:
	st.error("⚠️ Errore Configurazione: Secrets non trovati.")
	st.stop()

client = OpenAI(api_key=api_key)

# --- 3. FUNZIONI UTILI ---
def check_login(email_input):
	"""Controlla login via Google Sheet"""
	try:
		url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
		df = pd.read_csv(url, dtype=str)
		email_clean = email_input.strip().lower()
		
		if 'email' in df.columns:
			df['email'] = df['email'].astype(str).str.strip().str.lower()
			user = df[df['email'] == email_clean]
			if not user.empty:
				return user.iloc[0]['nome_studente']
		return None
	except Exception as e:
		st.error(f"Errore connessione database: {e}")
		return None

def pulisci_testo(testo):
	"""Rimuove annotazioni e 【4:0†source】"""
	# Regex semplificate per evitare errori di sintassi
	testo = re.sub(r'【.*?】', '', testo)
	testo = re.sub(r'\', '', testo)
	return testo.strip()

# --- 4. GESTIONE LOGIN ---
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False

if not st.session_state.authenticated:
	col1, col2, col3 = st.columns([1, 6, 1])
	with col2:
		st.markdown("<br><br>", unsafe_allow_html=True)
		# Titolo elegante senza immagine rotta
		st.markdown("<h1 style='text-align: center;'>🏛️ Tutor Nova Uni</h1>", unsafe_allow_html=True)
		st.info("Benvenuto nell'Area Studenti Multiversity.")
		
		email_input = st.text_input("📧 Inserisci la tua email istituzionale")
		
		# Questo bottone ora sarà BLU grazie al CSS sopra
		if st.button("Accedi all'Area Riservata"):
			with st.spinner("Verifica in corso..."):
				if email_input:
					nome = check_login(email_input)
					if nome:
						st.session_state.authenticated = True
						st.session_state.user_name = nome
						st.rerun()
					else:
						st.error("❌ Email non trovata o non abilitata.")
				else:
					st.warning("Inserisci un indirizzo email.")
	st.stop()

# --- 5. INTERFACCIA PRINCIPALE ---

# Sidebar Pulita (Senza immagine rotta)
with st.sidebar:
	st.title("🎓 Area Studenti")
	st.write(f"Ciao, **{st.session_state.user_name}**!")
	st.markdown("---")
	
	# Bottone Logout (Ora Blu)
	if st.button("🚪 Esci"):
		st.session_state.authenticated = False
		st.rerun()
		
	st.markdown("---")
	st.caption("Polo Nova Uni © 2025")
	st.caption("Powered by AI")

# Intestazione Chat
st.markdown(f"## Tutor Multiversity 🤖")
st.markdown("*Chiedimi informazioni su esami, tasse, tesi e tirocini.*")
st.markdown("---")

# Inizializzazione Chat
if "messages" not in st.session_state:
	st.session_state.messages = []
	st.session_state.messages.append({"role": "assistant", "content": f"Ciao {st.session_state.user_name}! Come posso aiutarti oggi?"})

if "thread_id" not in st.session_state:
	thread = client.beta.threads.create()
	st.session_state.thread_id = thread.id

# Mostra Cronologia Chat
for msg in st.session_state.messages:
	# Qui impostiamo le icone: Robot per assistente, Persona per utente
	if msg["role"] == "assistant":
		with st.chat_message("assistant", avatar="🤖"):
			st.markdown(msg["content"])
	else:
		with st.chat_message("user", avatar="👤"):
			st.markdown(msg["content"])

# INPUT UTENTE
prompt = st.chat_input("Scrivi qui la tua domanda...")

if prompt:
	# 1. Mostra domanda utente
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
		message_placeholder = st.empty()
		with st.spinner("Sto consultando i documenti ufficiali..."):
			run = client.beta.threads.runs.create(
				thread_id=st.session_state.thread_id,
				assistant_id=assistant_id
			)
			
			while run.status != "completed":
				time.sleep(0.5)
				run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
				if run.status == "failed":
					st.error("Si è verificato un errore tecnico.")
					st.stop()
			
			msgs = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
			raw_text = msgs.data[0].content[0].text.value
			
			# Pulizia testo finale
			final_text = pulisci_testo(raw_text)
			
			message_placeholder.markdown(final_text)
			
			# Salva cronologia
			st.session_state.messages.append({"role": "assistant", "content": final_text})