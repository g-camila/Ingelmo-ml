import os
from dotenv import load_dotenv
import logging
import smtplib
from email.message import EmailMessage
import json
import settings as s
from objetos import Items
from time import sleep


#def add_json(filename, data):
#    if not os.path.exists(filename):
#        with open(filename, 'w') as file:
#            json.dump({"emp_details": [data]}, file, indent=4)
#    else:
#        with open(filename, 'r+') as file:
#            file_data = json.load(file)
#            file_data["emp_details"].append(data)
#            file.seek(0)
#            json.dump(file_data, file, indent=4)

def send_email(programa, asunto, mensaje="", filename=""):
    load_dotenv()
    if programa == 0:
        EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS0')
        EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD0')
        destinatario = EMAIL_ADDRESS
    elif programa == 1:
        EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS1')
        EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD1')
    
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = destinatario

    msg.set_content(mensaje)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return



def add_json(filename, data):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            json.dump([data], file, indent=4)
    else:
        with open(filename, 'r+') as file:
            file_data = json.load(file)
            if not isinstance(file_data, list):
                file_data = [file_data]
            #except json.JSONDecodeError:
                #file_data = []

            file_data.append(data)
            file.seek(0)
            json.dump(file_data, file, indent=4)
            file.truncate()


def create_log(fmyapplog):
    #crear un log
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        #cambiar file name para configurar log
        filename= fmyapplog,
        level=logging.INFO,
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        filemode="w"
    )
    logger = logging.getLogger(__name__)
    return


def handle_error(response, loc, val, tipo):
    if response == None: #por alguna razon no actualice pero esta todo bien
        return
    if response.status_code != 200:
        logging.info(f"No se pudo actualizar el item: {val.id} de sku {Items.get_sku(loc)}. Resupuesta:")
        logging.info(response.json())
        logging.info("\n")
        idempresa = s.get_config_value('idempresa')
        errores_file = f'{idempresa}_errores.json'
        add_json(errores_file, {'dir':loc, 'tipo':tipo})
    else:
        logging.info(f"Se actualizo el item {val.id}") #lo tendria q sacar cuando termine el coso

    return


def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = 'X', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)

    if iteration == total: 
        print()
    return

