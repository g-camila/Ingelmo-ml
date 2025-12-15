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
import objetos
from spin import Spinner
from objetos import Neumatico, Items
os.environ['PYTHONIOENCODING'] = 'utf-8'

def main(idempresa=1):
    s.update_config('GENERAL', 'idempresa', idempresa)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    items_list = connections.get_items()
    lectura.leer_neums(items_list)

    data={}

    for item in Items.lost_free_ship:
        #armar excel
        #agarrar y armar dict con arrays adentro
        #columna sku, Normal y columna Catalogo con [id, id, id] por la posibilidad de que sea mas de uno
        sku = item[0]
        direccion = item[1]
        goma = Items.df.loc[(direccion[0], direccion[1])]
        catalogo = Items.get_catalogo(direccion)
        if sku not in data:
            data[sku] = {}
        if not catalogo:
            data[sku].setdefault('normal', []).append(goma.id)
        else:
            data[sku].setdefault('catalogo', []).append(goma.id)

    print("listo")
    df = pd.DataFrame.from_dict(data, orient="index")
    df = df.applymap(lambda x: ", ".join(map(str, x)) if isinstance(x, list) else x)
    df.to_excel("resultado.xlsx", index=True)

        #if sku not in Items.lost_free_ship:
            

    #item_id = "MLA2055336480" #og normal
    #item_id="MLA2660746900" #nueva
    #item_id="MLA2055440172"

    





    #LO USO PARA CONTROLAR COSAS
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