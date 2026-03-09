import os
import argparse
from dotenv import load_dotenv
import settings as s
from objetos import Items, Neumatico
import connections
import messages
import requests
import json
import llamadas

def main(idempresa = 4):
    info_user()

def tech_specs(idempresa):
    #conn = connections.start_conn(idempresa)
    #connections.get_user(conn)
    response = llamadas.tech_specs('MLA22195')
    data = response.json()
    with open("test.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

    specs_attrs = data['groups'][0]['components']
    required_attrs = []

    for attribute in specs_attrs:
        attrs = attribute['attributes'][0]
        id = attrs['id']
        if 'required' in attrs['tags']:
            required_attrs.append(id)
    
    print(required_attrs)

def new_user():
    response = llamadas.grant_access_token(6553786730726743, 'AYyaMoSUjTWm5GmpgYcgOxollagCQr9v', 'TG-69a5ae2023452e0001a593a5-118448444', 'https://redirecturi.com')
    print(response.json())

def info_user(idempresa = 4):
    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    response = llamadas.get_user_info()
    print(response.json())



    

            




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Procesar el ID de la empresa.')
    parser.add_argument('idempresa', type=str, help='El ID de la empresa')
    try:
        args = parser.parse_args()
        main(args.idempresa)
    except SystemExit as e:
        if e.code != 0:
            print(f"Error: {e}")
        main(4)