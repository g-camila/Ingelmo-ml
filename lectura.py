import pandas as pd
import json
import argparse
import os
import messages
import connections
import logging
import logging
import sys
import os
from typing import List, Dict, Optional
from objetos import Neumatico, Items
os.environ['PYTHONIOENCODING'] = 'utf-8'

def leer_neums(items_list, access_token, db_dict, batch_size=20):
    i=0
    while i < len(items_list):
        batch = items_list[i:i+batch_size]
        i += batch_size

        url = f"https://api.mercadolibre.com/items?ids={','.join(batch)}&include_attributes=all"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = connections.make_request('get', url, headers)
        if response.status_code == 200:
            batch_data = response.json()
        else: #es mas rapido pero si falla un batch tengo que cortar todo
            logging.info(f"Fallo el batch de los items: {response.status_code}")
            sys.exit()

        for item_data in batch_data:
            item_data = item_data['body']
            
            Items(item_data)
            current = Items.ultimo_dir

            #los Neumaticos solo se leen de cant 1, y fijarse que no se repita
            if current['sku'] not in Neumatico.dict or current['cantidad'] == '1':
               Neumatico(item_data, db_dict)
        
    return Neumatico.dict



def main(idempresa=1):
    fmyapplog = f'{idempresa}_myapp.log'

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    creds, conn = connections.start_conn(1)
    user = connections.get_user(1, creds, conn)
    df_db = connections.get_db(creds)
    items_list = connections.get_items(user)

    db_dict = df_db.set_index("cai")["precio2"].to_dict()
    access_token = user['access_token']
    leer_neums(items_list, access_token, db_dict)



    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Procesar el ID de la empresa.')
    parser.add_argument('idempresa', type=str, help='El ID de la empresa')
    try:
        args = parser.parse_args()
        main(args.idempresa)
    except SystemExit as e:
        if e.code != 0:
            print(f"Error: {e}")
        main(1)