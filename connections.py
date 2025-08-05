import pandas as pd
import pyodbc
import json
import logging
from email.message import EmailMessage
import sys
from datetime import datetime
import messages
import requests
import math
import time
from dotenv import load_dotenv
import os

#hace el refresh del nuevo token
def refreshtoken(client_id,client_secret,refresh_token):
    token = refresh_token

    url = "https://api.mercadolibre.com/oauth/token"
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "client_id":f"{client_id}",
        "client_secret":f"{client_secret}",
        "refresh_token":f"{token}"
    }

    response = requests.post(url, headers=headers, data=data)
    return response



#intenta ejecutar una query
def fetch_records(cursor, query, mensaje, file):
    try:
        cursor.execute(query)
    except pyodbc.Error as e:
        if file == 'conexion':
            logging.info(f"Error executing query: {e}")
        messages.send_email(mensaje, f'cadena: {query}', file)
        sys.exit("Failed to execute query. Exiting...")
    return cursor.fetchall()


#comienza la conexion con la db, consigue credenciales iniciales
def start_conn(idempresa):
    logger = logging.getLogger(__name__)
    
    load_dotenv()
    SERVER = os.getenv('SERVER')
    DATABASE = os.getenv('DATABASE')
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')

    connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};Encrypt=no'
    conn0 = pyodbc.connect(connectionString)
    SQL_QUERY = f"""
    SELECT top 1 cadena,client_id,client_secret,vista from empresas where Id={idempresa}"""
    cursor = conn0.cursor()
    records = fetch_records(cursor, SQL_QUERY, "Hubo un error al intentar leer la cadena de conexion de empresas", 'conexion')

    if not records:
        messages.send_email("No se encontraron registros al conectarse a empresas",  "En empresa = {idempresa}", 'conexion')
        sys.exit()

    for r in records:
        creds = {
            'mcadena' : [r.cadena][0],
            'mclient_id' : [r.client_id][0],
            'mclient_secret' : [r.client_secret][0],
            'mvista' : [r.vista][0]
        }

    return creds, conn0



#info del user de ml, refresh
def get_user(idempresa, creds, conn0):
    SQL_QUERY = f"""
    SELECT top 1 token,fecha,refresh_token,user_id from token_ml where Idempresa={idempresa} order by fecha desc
    """
    cursor = conn0.cursor()
    records = fetch_records(cursor, SQL_QUERY, "Hubo un error al intentar leer la cadena de conexion de token_ml", 'conexion')

    if not records:
        messages.send_email(f"No se encontraron registros al conectarse a token_ml", "En empresa = {idempresa}", 'conexion')
        sys.exit()

    for r in records: 
        user = {
            'access_token' : [r.token][0],
            'modified' : [r.fecha][0],
            'refresh_token' : [r.refresh_token][0],
            'user_id' : [r.user_id][0]
        }

    #si pasaron mas de 6 horas, se debe refrescar el token
    if (datetime.now() - user['modified']).total_seconds() >= 6 * 3600:
        refreshed = refreshtoken(creds['mclient_id'],creds['mclient_secret'],user['refresh_token'])
        logging.info(f"Solicitud del token: {refreshed['status_code']}")
        logging.info("\n")
        if refreshed['status_code'] != 200:
            messages.send_email("Hubo un error al intentar refrescar el token",  "En empresa = {idempresa}", 'conexion')
            sys.exit()
        
        user.update({
            'access_token' : refreshed['access_token'],
            'refresh_token' : refreshed['refresh_token']
        })

        cadena=f"insert into token_ml (Idempresa,token,refresh_token,user_id) values ({idempresa},'{user['access_token']}','{user['access_token']}',{user['user_id']})"
        #cursor = conn0.cursor()
        cursor.execute(cadena)
        cursor.commit()
   
    return user



#conseguir las gomas de la base de datos!!
def get_db(creds):
    connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}}'+creds['mcadena']
    try:
        conn = pyodbc.connect(connectionString)
    except pyodbc.Error as e:
        logging.error(f"Error connecting to database: {e}")
        sys.exit("Failed to connect to the database. Exiting...")
        messages.send_email("Hubo un error al intentar conectarse a la base de datos", "", 'conexion')


    SQL_QUERY = f"""
    SELECT cai, descripcion, precio, precio2, existencia, observ from {creds['mvista']}
    """
    cursor = conn.cursor()
    cursor.execute(SQL_QUERY)
    records = cursor.fetchall()

    df_db = pd.DataFrame(columns=['cai', 'descripcion', 'precio', 'precio2','existencia', 'observ'])
    for r in records: 
        df_db = pd.concat([df_db, pd.DataFrame({'cai': [r.cai.strip()], 'descripcion': [r.descripcion], 'precio': [r.precio], 'precio2': [r.precio2], 'existencia': [r.existencia], 'observ': [r.observ]})], ignore_index=True)


    return df_db



#lista de todos los items del usuario
def get_items(user, filtro=""):
    logger = logging.getLogger(__name__)

    access_token = user['access_token']
    user_id = user['user_id']

    url = f"https://api.mercadolibre.com/users/{user_id}/items/search?search_type=scan&limit=100{filtro}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = make_request('get', url, headers)
    logging.info(f"Se intentaron leer los items del usuario: {response}")
    logging.info("\n")
    if (response.status_code != 200):
        mensaje = "Hubo un error al intentar leer los items del usuario"
        messages.send_email(mensaje, response.json(), 'conexion')
        return

    litems = response.json()
    total= litems['paging']['total']
    items_list = litems['results']
    scroll_id = litems['scroll_id']

    if total/100 > 1:
        paginas = math.ceil(total/100)
        for i in range(paginas-1):
            url = f"https://api.mercadolibre.com/users/{user_id}/items/search?search_type=scan&limit=100&scroll_id={scroll_id}{filtro}"
            response = make_request('get', url, headers)
            if (response.status_code != 200):
                logging.info(f"Se intentaron leer los items del usuario: {response.status_code}")
                logging.info("\n")
                mensaje="Hubo un error al intentar leer los items del usuario"
                messages.send_email(mensaje, response.json(), 'conexion')
                return

            litems = response.json()
            scroll_id = litems['scroll_id']
            items_list.extend(litems.get('results', []))

    return items_list



#tiene en cuenta los limites de requests por ml, lo intenta por defecto 3 veces
def make_request(method, url, headers, json="", i=3):
    if method == "put":
        response = requests.put(url, headers=headers, json=json)
    elif method == "post":
        response = requests.post(url, headers=headers, json=json)
    elif method == "get":
        response = requests.get(url, headers=headers)

    if response.status_code == 429:
        if i >= 1:
            time.sleep(70)
            response = make_request(method, url, headers, json, i-1)
    if response.status_code == 500 or response.status_code == 409:
        if i >= 1:
            time.sleep(20)
            response = make_request(method, url, headers, json, i-1)

    return response
