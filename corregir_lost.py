import os
import argparse
import pandas as pd
import json
import logging
import settings as s
import messages
import connections
import llamadas
import lectura
from spin import Spinner
from objetos import Neumatico, Items
os.environ['PYTHONIOENCODING'] = 'utf-8'

def main(idempresa=1):
    s.update_config('GENERAL', 'idempresa', idempresa)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    items_list = connections.get_items()
    lectura.leer_neums(items_list)

    for sku in Items.lost_free_shipping:
        for strdir in Items.lost_free_shipping[sku]:
            dir = eval(strdir)
            for val in Items.lost_free_shipping[sku][strdir]:
                print("aaa")

        
    #despues de que ande agregar leer el lost como un metodo extra para todas las veces
    #hacer lista en items de todos los items que tengan true el is lost
    #y despues que eso se controle aca y que vea que caracteristicas tienen (indice)

    #item_id = "MLA2055336480" #og normal
    #item_id="MLA2660746900" #nueva
    #response = llamadas.get_item_simple(item_id)
    #item_data = response.json()["shipping"]["tags"]
    #is_lost = "lost_me2_by_dimensions" in item_data
    #print(is_lost)
    #with open("test.json", "w") as json_file:
    #    json.dump(response.json(), json_file, indent=4)



    

    


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