import streamlit as st
import pandas as pd
from openai import OpenAI
import time

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tutor Multiversity", page_icon="🎓")

# CSS per nascondere menu e footer (modalità pulita)
st.markdown("""
	<style>
	#MainMenu {visibility: hidden;}
	footer {visibility: hidden;}
	header {visibility: hidden;}
	</style>
	""", unsafe_allow_html=True)

# --- 2. RECUPERO CHIAVI ---
try:
	api_key = st.secrets["OPENAI_API_KEY"]
	assistant_id = st.secrets["ASSISTANT_ID"]
	sheet_id = st.secrets["SHEET_ID"] # Legge l'ID del foglio dai Secrets
except FileNotFoundError:
	st.error("⚠️ Errore: Secrets non trovati. Controlla le impostazioni su Streamlit Cloud.")
	st.stop()

client = OpenAI(api_key=api_key)

# --- 3. FUNZIONE DI LOGIN (GOOGLE SHEETS) ---
def check_login(email_input):
	"""Controlla se la mail è abilitata leggendo dal Google Sheet"""
	try:
		# Costruisce l'URL per scaricare il CSV da Google
		url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
		
		# Legge i dati direttamente da Internet
		df = pd.read_csv(url, dtype=str)
		
		# Puliamo l'email inserita dall'utente (minuscolo e senza spazi)
		email_clean = email_input.strip().lower()
		
		# Verifichiamo se la colonna 'email' esiste nel foglio
		if 'email' in df.columns:
			# Puliamo anche le email nel foglio per essere sicuri
			df['email'] = df['email'].astype(str).str.strip().str.lower()
			
			# Cerchiamo l'utente
			user = df[df['email'] == email_clean]
			
			if not user.empty:
				# Se trovato, restituisce il nome
				return user.iloc[0]['nome_studente']
		return None
			
	except Exception as e:
		st.error(f"Errore di connessione al database studenti: {e}")
		return None

# --- 4. GESTIONE SESSIONE (LOGIN) ---
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False

if not st.session_state.authenticated:
	st.markdown("<h1 style='text-align: center;'>🎓 Tutor Multiversity</h1>", unsafe_allow_html=True)
	st.markdown("<p style='text-align: center;'>Accesso riservato agli studenti del Polo</p>", unsafe_allow_html=True)
	
	col1, col2, col3 = st.columns([1,2,1])
	with col2:
		email_input = st.text_input("Inserisci la tua Email istituzionale", placeholder="nome.cognome@email.it")
		
		if st.button("Accedi", use_container_width=True):
			if email_input:
				nome_utente = check_login(email_input)
				if nome_utente:
					st.session_state.authenticated = True
					st.session_state.user_name = nome_utente
					st.success(f"Benvenuto, {nome_utente}!")
					time.sleep(1)
					st.rerun()
				else:
					st.error("Email non trovata nel database.")
			else:
				st.warning("Inserisci una email valida.")
	
	st.stop()

# --- 5. INTERFACCIA CHAT ---
# Sidebar
with st.sidebar:
	st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python_logo_notext.svg/1200px-Python_logo_notext.svg.png", width=50)
	st.markdown(f"### Ciao, {st.session_state.user_name}! 👋")
	st.markdown("---")
	if st.button("🚪 Esci", type="primary"):
		st.session_state.authenticated = False
		st.rerun()
	st.markdown("---")
	st.caption("🤖 Powered by **GPT-4o Mini**")

# Chat
st.title("Assistente Virtuale 🤖")
st.warning("⚠️ L'IA può commettere errori. Verifica sempre le info importanti.")

if "messages" not in st.session_state:
	st.session_state.messages = []

if "thread_id" not in st.session_state:
	thread = client.beta.threads.create()
	st.session_state.thread_id = thread.id

for msg in st.session_state.messages:
	with st.chat_message(msg["role"]):
		st.markdown(msg["content"])

if prompt := st.chat_input("Chiedimi info su esami, tesi, tasse..."):
	st.session_state.messages.append({"role": "user", "content": prompt})
	with st.chat_message("user"):
		st.markdown(prompt)

	client.beta.threads.messages.create(
		thread_id=st.session_state.thread_id,
		role="user",
		content=prompt
	)

	with st.chat_message("assistant"):
		with st.spinner("Consulto i regolamenti..."):
			run = client.beta.threads.runs.create(
				thread_id=st.session_state.thread_id,
				assistant_id=assistant_id
			)
			while run.status != "completed":
				time.sleep(0.5)
				run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
				if run.status == "failed": 
					st.error("Errore tecnico."); st.stop()
			
			msgs = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
			raw_text = msgs.data[0].content[0].text.value
			
			# Pulizia source
			import re
			clean_text = re.sub(r'【.*?】', '', raw_text)
			
			st.markdown(clean_text)
			st.session_state.messages.append({"role": "assistant", "content": clean_text})