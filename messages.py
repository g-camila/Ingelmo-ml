import logging
import smtplib
from email.message import EmailMessage

def send_email(asunto, mensaje, programa):
    #no tiene sentido esto de los programas, deberia ser 1 o 2, hay 2 modos nomas.
    if programa == 'sincro' or programa == 'conexion':
        EMAIL_ADDRESS = 'camilagiron154@gmail.com'
        EMAIL_PASSWORD = 'mauc ilnp ggai hdmm'
        destinatario = EMAIL_ADDRESS
    elif programa == 'preguntas' or programa == 'envio':
        EMAIL_ADDRESS = 'ingelmosa@gmail.com'
        EMAIL_PASSWORD = 'hlxm uafk wvcj jjrz'
        destinatario = "Francopace45@gmail.com,Franco@ingelmo.com.ar,hernan@ingelmo.com.ar,hernancortez12467@gmail.com "
        destinatario2="fabiana@ingelmo.com.ar,javier@ingelmo.com.ar,gdgiron@gmail.com"
    
    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = destinatario
    if programa == 'preguntas':
        msg['CC'] = destinatario2

    if programa == 'conexion':
        msg.set_content('No se logró finalizar el log antes de enviar el email')
    else:
        msg.set_content(mensaje)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    return


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


def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = 'X', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()
    return