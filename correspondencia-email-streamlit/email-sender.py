from typing import Dict, Any, List
from io import StringIO
import streamlit as st
import json
import re
from hugchat import hugchat
from hugchat.login import Login
import smtplib
from email.mime.text import MIMEText
import configparser
import os

def generate_emails_from_json(json_text: str) -> List[Dict[str, str]]:
    """
    Generates emails from JSON data and returns them as a list of dictionaries.

    Args:
        json_text (str): JSON data containing email information.

    Returns:
        List[Dict[str, str]]: List of email dictionaries with keys 'to', 
                              'from', 'subject', and 'content'.
    """
    data = json.loads(json_text)
    emails = []
    for i, email in enumerate(data["emails"]):
        email_dict = {
            "to": email["to"],
            "from": email["from"],
            "subject": email["subject"],
            "content": email["content"]
        }
        emails.append(email_dict)
    return emails

def send_email(smtp_server: str, smtp_port: int, smtp_email: str, smtp_password: str,
               to_email: str, subject: str, content: str) -> None:
    """
    Sends an email using an SMTP server.

    Args:
        smtp_server (str): SMTP server address.
        smtp_port (int): SMTP server port.
        smtp_email (str): Sender's email address.
        smtp_password (str): Sender's email password.
        to_email (str): Recipient's email address.
        subject (str): Email subject.
        content (str): Email content.

    Returns:
        None
    """
    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = smtp_email
    msg['To'] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, to_email, msg.as_string())

def load_credentials_from_ini(ini_file: StringIO) -> Dict[str, str]:
    """
    Loads credentials from a string (loaded from an .ini file) and returns them as a
    dictionary.

    Args:
        ini_file (StringIO): .ini file content as a StringIO object.

    Returns:
        Dict[str, str]: Dictionary containing credentials, including 'hf-email', 'hf-passwd',
        'acc-email', 'sign-name', 'smtp_server', 'smtp_port', 'smtp_email', and 'smtp_password'.
    """
    config = configparser.ConfigParser()
    config.read_string(ini_file.getvalue().decode("utf-8"))
    return {
        "hf-email": config.get("hugging-chat", "hf-email", fallback=""),
        "hf-passwd": config.get("hugging-chat", "hf-passwd", fallback=""),
        "acc-email": config.get("email", "acc-email", fallback=""),
        "sign-name": config.get("email", "sign-name", fallback=""),
        # ------
        "smtp_server": config.get("smtp", "smtp_server", fallback=""),
        "smtp_port": config.getint("smtp", "smtp_port", fallback=587),
        "smtp_email": config.get("smtp", "smtp_email", fallback=""),
        "smtp_password": config.get("smtp", "smtp_password", fallback="")
    }

# Initialize session state for generated emails
if 'generated_emails' not in st.session_state:
    st.session_state['generated_emails'] = []

# Streamlit app
st.title("Generador de e-mails (Nivel Dios)")

# Sidebar for user input for credentials and SMTP details
with st.sidebar:
    st.header("Credenciales de usuario")

    ini_file = st.file_uploader("Sube un fichero de configuración (opcional)", type="ini")
    if ini_file:
        credentials = load_credentials_from_ini(ini_file)
    else:
        credentials = {}

    st.header("🤗 Credenciales de Hugging Face")
    
    hf_email = st.text_input("Usuario", type="password", value=credentials.get("hf-email", ""))
    hf_passwd = st.text_input("Clave", type="password", value=credentials.get("hf-passwd", ""))

    st.header("Datos de e-mail (FROM)")

    acc_email = st.text_input("e-mail (FROM)", type="password",
                              value=credentials.get("acc-email", ""))
    sign_name = st.text_input("Nombre/firma", value=credentials.get("sign-name", ""))

    st.header("SMTP Server Details")
    smtp_server = st.text_input("Servidor SMTP", type="password",
                                value=credentials.get("smtp_server", ""))
    smtp_port = st.number_input("Puerto SMTP", value=credentials.get("smtp_port", 587))
    smtp_email = st.text_input("e-mail (SMTP)", type="password",
                               value=credentials.get("smtp_email", acc_email))
    smtp_password = st.text_input("Clave SMTP", type="password",
                                  value=credentials.get("smtp_password", ""))

# Text area for message content
message_content = st.text_area("🤗 Prompt con las órdenes del correo")

# Upload CSV file
csv_file = st.file_uploader("🖹 Sube el fichero CSV", type="csv")

# Process the input when the user clicks the button
if st.button("📧 Genera los e-mails"):
    if hf_email and hf_passwd and acc_email and sign_name and smtp_server and smtp_port and smtp_email and smtp_password and csv_file and message_content:
        # Read CSV content
        csv_content = csv_file.read().decode("utf-8")

        # Create the instructions for the bot
        SYSTEM = f"""
        Eres un asistente para combinar correspondencia. El usuario te pasará una tabla en CSV el delimitador entre cada columna será el punto y coma (;).

        Sabiendo que el formato de esta tabla es:
        - Nombre
        - Apellidos
        - Nivel de amistad (0 es desconocido, 5 es mejor amigo)
        - Correo electrónico

        Crea un fichero JSON donde aparezcan los siguientes campos:
        ```json
        {{
        "emails":[
         {{
          "to": "Correo electrónico a mandar",
          "from": "",
          "subject": "",
          "content": ""
         }}
        ]
        }}
        ```

        Responde tan solo con el fichero json y ningún otro texto adicional. Sabiendo que el formato de esta tabla es:
        - Nombre
        - Apellidos
        - Nivel de amistad (0 es desconocido, 5 es mejor amigo)
        - Correo electrónico

        Escribe cada uno de los correos con un tono distinto según el nivel de amistad (0 es desconocido, para ello usa un tono formal, 5 es mi mejor amigo, usa un tono amistoso y de confianza) dentro del apartado "content" en el JSON. ¡En ningún caso indiques en el contenido el nivel de confianza que tengo con mis conocidos de forma explícita! Rellena el resto de campos como sea apropiado y usa {acc_email} como correo y {sign_name} como firmante del correo.

        {csv_content}

        El contenido del mensaje debe obedecer las siguientes instrucciones: 

        {message_content}
        """

        # Define the cookies directory and connect to Hugging Chat
        cookie_path_dir = "./cookies/"
        sign = Login(hf_email, hf_passwd)
        cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)

        # Create your ChatBot
        chatbot = hugchat.ChatBot(cookies=cookies.get_dict())  # or cookie_path="usercookies/<email>.json"

        message_result = chatbot.chat(SYSTEM)

        # Non stream message
        message_str: str = message_result.wait_until_done()

        # Clean the message from unnecessary markdown
        message_str = message_str.strip()
        message_str = re.sub(r'^```.*\n?', '', message_str, flags=re.MULTILINE)

        # Generate emails
        generated_emails = generate_emails_from_json(message_str)
        st.session_state.generated_emails = generated_emails
    else:
        st.error("Por favor, rellena todos los campos (incluyendo un prompt) y sube un fichero CSV.")

# Button to load generated emails from a file
uploaded_file = st.file_uploader("Cargar correos generados previamente", type="json")
if uploaded_file:
    st.session_state.generated_emails = json.load(uploaded_file)
    st.success("Correos generados cargados con éxito.")


# Display each email in a different section
if "generated_emails" in st.session_state and len(st.session_state.generated_emails) > 0:
    generated_emails = st.session_state["generated_emails"]
    st.subheader(f"E-mails: {len(generated_emails)} en total")
    for i, email_dict in enumerate(generated_emails):
        with st.expander(f"#{i+1}: <{email_dict['to']}> (*{email_dict['subject']}*)"):
            email_text = f"{email_dict['content']}"
            st.caption(f"**Destinatario:** <{email_dict['to']}>")
            st.caption(f"**Asunto:** *{email_dict['subject']}*")
            st.caption(email_text.strip())

            if st.button(f"📩 Enviar a: {email_dict['to']}", key=f"send_email_{i+1}"):
                send_email(smtp_server, smtp_port, smtp_email, smtp_password, email_dict['to'],
                           email_dict['subject'], email_dict['content'])
                st.success(f"Email {i+1} enviado a mailto:{email_dict['to']} con éxito!")

# Save generated emails
if "generated_emails" in st.session_state and len(st.session_state.generated_emails) > 0:
    with open('generated_emails.json', 'w') as f:
        json.dump(st.session_state.generated_emails, f)
    with open('generated_emails.json', 'r') as f:
        st.download_button(
            label="📥 Descarga los correos generados",
            data=f.read(),
            file_name="generated_emails.json",
            mime="text/json",
        )

# Button to send all emails at once
if "generated_emails" in st.session_state and len(st.session_state.generated_emails) > 0:
    if st.button("📩 Enviar todos los e-mails"):
        for i, email_dict in enumerate(st.session_state.generated_emails):
            send_email(smtp_server, smtp_port, smtp_email, smtp_password, email_dict['to'],
                       email_dict['subject'], email_dict['content'])
        n = len(st.session_state.generated_emails)
        st.success(f"Todos los correos ({n}) enviados con éxito!")
