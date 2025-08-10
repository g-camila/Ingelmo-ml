import pandas as pd
import argparse
import os
import messages
import connections
import logging
import settings as s
import sys
import os
from llamadas import cambiar_estado
from typing import List, Dict, Optional
from objetos import Neumatico, Items
os.environ['PYTHONIOENCODING'] = 'utf-8'

def precio_real(precio, precio2, dir):
    fpago = Items.get_fpago(dir)
    match fpago:
        case 0:
            return precio * Items.get_cant(dir)
        case 1:
            return precio2 * Items.get_cant(dir)
        #es un % mas que el precio real, no hace falta andar enviando variables

def stock_real(stock, dir):
    return stock // Items.get_cant(dir)

#asigno una prioridad dependiendo de la ubicacion del item
def prior(dir):
    map_fpago = {0:3, 1:0}
    map_cant = {1:2, 2:1, 4:0}
    return map_fpago[Items.get_fpago(dir)] + map_cant[Items.get_cant(dir)]


def leer_neums(items_list, idempresa, batch_size=20):
    i=0
    access_token = s.get_config_value('access_token')
    recargo = s.get_config_value('recargo')

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
            sku = Items.get_sku(current)

            #no puedo suponer que el neumatico modelo existe todas las veces
            #voy a hacer un cosito d prioridad para resolver el tema
            precio = item_data['price']
            if sku not in Neumatico.dict:
                n = Neumatico(item_data)
                n.item_dir = current
                n.precio = precio_real(precio, precio*recargo, current)
                n.stock = stock_real(item_data['available_quantity'], current)
            elif prior(current) > prior(Neumatico.dict[sku].item_dir):
                n.item_dir = current
                n.precio = precio_real(precio, precio*recargo, current)
                n.stock = stock_real(item_data['available_quantity'], current)



def main(idempresa=1):
    fmyapplog = f'{idempresa}_myapp.log'
    fmyapplog = f'{idempresa}_myapp.log'

    s.update_config('GENERAL', 'idempresa', idempresa)
    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    items_list = connections.get_items()

    leer_neums(items_list, idempresa)



    


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