import os
import sys
import pyodbc
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import requests
import math
import time
import settings as s

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
        sys.exit("Failed to execute query. Exiting...")
    return cursor.fetchall()


#comienza la conexion con la db, consigue credenciales iniciales
def start_conn(idempresa):
    
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
        if refreshed.status_code != 200:
            sys.exit()

        refreshed = refreshed.json()
        access_token = refreshed['access_token']
        s.update_config(x, 'access_token', access_token)
        s.update_config(x, 'modified', datetime.now())
        refresh_token = refreshed['refresh_token']
        s.update_config(x, 'refresh_token', refresh_token)

        cadena=f"insert into token_ml (Idempresa,token,refresh_token,user_id) values ({idempresa},'{access_token}','{refresh_token}',{user_id})"
        #cursor = conn0.cursor()
        cursor.execute(cadena)
        cursor.commit()
    
    return


#tiene en cuenta los limites de requests por ml, lo intenta por defecto 2 veces
def make_request(method, url, headers, json="", i=6, base_wait=2):
    if method == "put":
        response = requests.put(url, headers=headers, json=json)
    elif method == "post":
        response = requests.post(url, headers=headers, json=json)
    elif method == "get":
        response = requests.get(url, headers=headers)

    if response.status_code == 429:
        espera = base_wait * (2 ** (6-i))
        time.sleep(espera)            
        response = make_request(method, url, headers, json, i-1)
    if response.status_code == 500 or response.status_code == 409:
        time.sleep(30)
        response = make_request(method, url, headers, json, i-1)

    return response
