import os
import logging
import smtplib
from email.message import EmailMessage
import json
import settings as s

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

def add_json(filename, data):
    #directory = os.path.dirname(filename)
    #if directory and not os.path.exists(directory):
    #    os.makedirs(directory, exist_ok=True)
        
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
    else:
        with open(filename, 'r+') as file:
            try:
                file_data = json.load(file)
                if not isinstance(file_data, list):
                    file_data = [file_data]  # Convert to list if needed
            except json.JSONDecodeError:
                file_data = []

            file_data.append(data)  # Add new dict to the list
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
    logging.info(f"INICIO DE PROCESO DE SINCRONIZACION ")
    logging.info("\n")
    return


def handle_error(response, loc, val, tipo):
    if response != 200:
        logging.info(f"No se pudo actualizar el item: {val.id}")
        idempresa = s.get_config_value('idempresa')
        errores_file = f'{idempresa}_errores.json'
        add_json(errores_file, {'dir':loc, 'val':val, 'tipo':tipo})



def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = 'X', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()
    return