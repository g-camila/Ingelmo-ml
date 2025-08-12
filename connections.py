import os
import sys
import pyodbc
from dotenv import load_dotenv
import pandas as pd
from email.message import EmailMessage
from datetime import datetime
import requests
import random
import math
import time
import logging
import settings as s
import messages

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
        messages.send_email(0, mensaje, f'cadena: {query}')
        sys.exit("Failed to execute query. Exiting...")
    return cursor.fetchall()


#comienza la conexion con la db, consigue credenciales iniciales
def start_conn(idempresa):
    logger = logging.getLogger(__name__)
    
    load_dotenv()
    SERVER = os.getenv('SERVER')
    DATABASE = os.getenv('DATABASE')
    USER = os.getenv('USER')
    PASSWORD = os.getenv('PASSWORD')


    s.update_config('GENERAL', 'idempresa', idempresa)

    connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USER};PWD={PASSWORD};Encrypt=no'
    conn0 = pyodbc.connect(connectionString)
    SQL_QUERY = f"""
    SELECT top 1 cadena,client_id,client_secret,vista from empresas where Id={idempresa}"""
    cursor = conn0.cursor()
    records = fetch_records(cursor, SQL_QUERY, "Hubo un error al intentar leer la cadena de conexion de empresas", 'conexion')

    if not records:
        messages.send_email(0, "No se encontraron registros al conectarse a empresas",  "En empresa = {idempresa}")
        sys.exit()

    x = 'CREDS'
    for r in records:
        s.update_config(x, 'mcadena', [r.cadena][0])
        s.update_config(x, 'mclient_id', [r.client_id][0])
        s.update_config(x, 'mclient_secret', [r.client_secret][0])
        s.update_config(x, 'mvista', [r.vista][0])

    return conn0



#info del user de ml, refresh
def get_user(conn0):
    idempresa = s.get_config_value('idempresa')
    SQL_QUERY = f"""
    SELECT top 1 token,fecha,refresh_token,user_id from token_ml where Idempresa={idempresa} order by fecha desc
    """
    cursor = conn0.cursor()
    records = fetch_records(cursor, SQL_QUERY, "Hubo un error al intentar leer la cadena de conexion de token_ml", 'conexion')

    if not records:
        messages.send_email(0, f"No se encontraron registros al conectarse a token_ml", "En empresa = {idempresa}")
        sys.exit()

    x = 'USER'
    for r in records: 
        access_token = [r.token][0]
        s.update_config(x, 'access_token', access_token)
        modified = [r.fecha][0]
        s.update_config(x, 'modified', modified)
        refresh_token = [r.refresh_token][0]
        s.update_config(x, 'refresh_token', refresh_token)
        user_id = [r.user_id][0]
        s.update_config(x, 'user_id', user_id)

    #si pasaron mas de 6 horas, se debe refrescar el token
    if (datetime.now() - modified).total_seconds() >= 6 * 3600:
        creds = s.read_section('CREDS')
        refreshed = refreshtoken(creds['mclient_id'],creds['mclient_secret'],refresh_token)
        logging.info(f"Solicitud del token: {refreshed['status_code']}")
        logging.info("\n")
        if refreshed['status_code'] != 200:
            messages.send_email(0, "Hubo un error al intentar refrescar el token", refreshed.json())
            sys.exit()

        access_token = refreshed['access_token']
        s.update_config(x, 'access_token', access_token)
        s.update_config(x, 'modified', refreshed['modified'])
        refresh_token = refreshed['refresh_token']
        s.update_config(x, 'refresh_token', refresh_token)

        cadena=f"insert into token_ml (Idempresa,token,refresh_token,user_id) values ({idempresa},'{access_token}','{refresh_token}',{user_id})"
        #cursor = conn0.cursor()
        cursor.execute(cadena)
        cursor.commit()
    
    return



#conseguir las gomas de la base de datos!!
def get_db():
    creds = s.read_section('CREDS')

    connectionString = f'DRIVER={{ODBC Driver 18 for SQL Server}}'+creds['mcadena']
    try:
        conn = pyodbc.connect(connectionString)
    except pyodbc.Error as e:
        logging.error(f"Error connecting to database: {e}")
        sys.exit("Failed to connect to the database. Exiting...")
        messages.send_email(0, "Hubo un error al intentar conectarse a la base de datos")


    SQL_QUERY = f"""
    SELECT cai, descripcion, precio, precio2, existencia, observ from {creds['mvista']}
    """
    cursor = conn.cursor()
    cursor.execute(SQL_QUERY)
    records = cursor.fetchall()

    df_db = pd.DataFrame(columns=['cai', 'descripcion', 'precio', 'precio2','existencia', 'observ'])
    for r in records: 
        df_db = pd.concat([df_db, pd.DataFrame({'cai': [r.cai.strip()], 'descripcion': [r.descripcion], 'precio': [r.precio], 'existencia': [r.existencia], 'observ': [r.observ]})], ignore_index=True)


    recargo_values=[]
    for _ in range(5):
        idx = random.randint(0, len(df_db) - 1)
        p1 = df_db.iloc[idx]['precio']
        p2 = records[idx].precio2
        if p2 != 0:
            recargo = p1 / p2
            recargo_values.append(recargo)

    prom_recargo = round(sum(recargo_values) / len(recargo_values), 3)

    s.update_config('GENERAL', 'recargo', prom_recargo)
    
    return df_db



#lista de todos los items del usuario
def get_items(filtro=""):
    user = s.read_section("USER")

    logger = logging.getLogger(__name__)

    access_token = user['access_token']
    user_id = user['user_id']

    url = f"https://api.mercadolibre.com/users/{user_id}/items/search?search_type=scan&limit=100{filtro}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = make_request('get', url, headers)
    if (response.status_code != 200):
        logging.info(f"Hubo un error al leer los items del usuario: {response}")
        logging.info("\n")
        mensaje = "Hubo un error al intentar leer los items del usuario"
        messages.send_email(0, mensaje, response.json())
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
                logging.info(f"Hubo un error al leer los items del usuario: {response}")
                logging.info("\n")
                mensaje="Hubo un error al intentar leer los items del usuario"
                messages.send_email(0, mensaje, response.json())
                return

            litems = response.json()
            scroll_id = litems['scroll_id']
            items_list.extend(litems.get('results', []))

    return items_list



#tiene en cuenta los limites de requests por ml, lo intenta por defecto 2 veces
def make_request(method, url, headers, json="", i=2):
    if method == "put":
        response = requests.put(url, headers=headers, json=json)
    elif method == "post":
        response = requests.post(url, headers=headers, json=json)
    elif method == "get":
        response = requests.get(url, headers=headers)

    if response.status_code == 429:
        if i >= 1:
            time.sleep(61)
            response = make_request(method, url, headers, json, i-1)
    if response.status_code == 500 or response.status_code == 409:
        if i >= 1:
            time.sleep(30)
            response = make_request(method, url, headers, json, i-1)

    return response
