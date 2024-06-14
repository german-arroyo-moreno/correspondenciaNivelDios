from typing import Dict, Any
from hugchat import hugchat
from hugchat.login import Login
import json
import configparser
import os
import re

def load_credentials_from_ini(file_name: str) -> Dict[str, Any]:
    """
    Loads credentials from an INI file.

    Args:
        file_name (str): The name of the INI file.

    Returns:
        Dict[str, Any]: A dictionary containing the loaded credentials.
    """
    with open(file_name, "r") as file1:
        ini_file = file1.read()

        config = configparser.ConfigParser()
        config.read_string(ini_file)
        return {
            "hf-email": config.get("hugging-chat", "hf-email", fallback=""),
            "hf-passwd": config.get("hugging-chat", "hf-passwd", fallback=""),
            "acc-email": config.get("email", "acc-email", fallback=""),
            "sign-name": config.get("email", "sign-name", fallback="")
        }
    return {}

def write_json_emails(path: str, json_text: str) -> None:
    """
    Parses the given JSON text and generates EML files for each email.

    Args:
        path (str): The directory path where EML files will be saved.
        json_text (str): The JSON text containing email data.

    Returns:
        None
    """
    data = json.loads(json_text)
    for i, email in enumerate(data["emails"]):
        email_text = ""
        email_text += f'TO: {email["to"]}' + "\n"
        email_text += f'FROM: {email["from"]}' + "\n"
        email_text += f'SUBJECT: {email["subject"]}' + "\n\n"
        email_text += f'{email["content"]}' + "\n"
        with open(os.path.join(path, f"{i}.eml"), "w") as file3:
            file3.write(email_text)


if __name__ == "__main__":
    credentials = load_credentials_from_ini('credentials.ini')
    hf_email = credentials.get("hf-email", "").strip()
    hf_passwd = credentials.get("hf-passwd", "").strip()
    acc_email = credentials.get("acc-email", "").strip()
    sign_name = credentials.get("sign-name", "").strip()

    # Create the instructions for the bot
    SYSTEM = """
    Eres un asistente para combinar correspondencia. El usuario te pasará una tabla en CSV el delimitador entre cada columna será el punto y coma (;).

    Sabiendo que el formato de esta tabla es:
    - Nombre
    - Apellidos
    - Nivel de amistad (0 es desconocido, 5 es mejor amigo)
    - Correo electrónico

    Crea un fichero JSON donde aparezcan los siguientes campos:
    ```json
    {
    "emails":[
     {
      "to": "Correo electrónico a mandar",
      "from": "",
      "subject": "",
      "content": ""
     }
    ]
    }
    ```

    Responde tan solo con el fichero json y ningún otro texto adicional. Sabiendo que el formato de esta tabla es:
    - Nombre
    - Apellidos
    - Nivel de amistad (0 es desconocido, 5 es mejor amigo)
    - Correo electrónico

    """

    SYSTEM += f"""
    Escribe cada uno de los correos con un tono distinto según el nivel de amistad (0 es desconocido, para ello usa un tono formal, 5 es mi mejor amigo, usa un tono amistoso y de confianza) dentro del apartado "content" en el JSON. ¡En ningún caso indiques en el contenido el nivel de confianza que tengo con mis conocidos de forma explícita! Rellena el resto de campos como sea apropiado y usa {acc_email} como correo y {sign_name} como firmante del correo.
    """

    with open("tabla.csv", "r") as file2:
        SYSTEM += file2.read()

    SYSTEM += """
    El contenido del mensaje debe obedecer las siguientes instrucciones:

    """

    with open("message.txt", "r") as file3:
        SYSTEM += file3.read()


    # Define the cookies directory and connect to Hugging Chat
    cookie_path_dir = "./cookies/"
    sign = Login(hf_email, hf_passwd)
    cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)

    # Create your ChatBot or cookie_path="usercookies/<email>.json"
    chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

    message_result = chatbot.chat(SYSTEM)

    # Non stream message
    message_str: str = message_result.wait_until_done()

    # Divide the message in lines
    message_str = message_str.strip()
    message_str = re.sub(r'^```.*\n?', '', message_str, flags=re.MULTILINE)

    print(message_str)

    # Parse the json data and generate the emails
    data = json.loads(message_str)
    write_json_emails('correos/', message_str)
