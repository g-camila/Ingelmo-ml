import pandas as pd
import argparse
import os
import messages
import time
import connections
import logging
import logging
import os
from objetos import Neumatico, Items
from lectura import leer_neums
os.environ['PYTHONIOENCODING'] = 'utf-8'

access_token = ""

def actualizar(data, col, val):
    if val.status == 'under_review':
        return 200
    if not col[1]:
        data['id'] = val.variation_id
        data = [data]
        xdata={}
        xdata["variations"] = data
        data = xdata

    url = f"https://api.mercadolibre.com/items/{val.id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = connections.make_request('put', url, headers, data)
    return response

def desactivar(col, val):
    data = {"available_quantity" : 0}
    if val.status != 'active':
        return 200
    else:
        response = actualizar(data, col, val)
        return response.status_code

def desact_grupo(sku, filtro="", desc=None):
    for index, col, val in Items.iterar_sku(sku, filtro):
        error = desactivar(col, val)
        if error != 200:
            print("aaa")
            continue
        if desc != None:
            desc.append(val.id)
    return desc

def descarte(row, stockdb):
    desc = []
    sku = row['cai']
    if row['observ'] == '*X4':
        desact_grupo(desc, ["4"], sku)
    match stockdb:
        case 1 | 2:
            filtro = str(stockdb)
            desact_grupo(sku, [filtro], desc)
        case 3:
            desact_grupo(sku, ["1", "2"], desc)
    return desc



def main(idempresa=1):
    start_time = time.time()
    fmyapplog = f'{idempresa}_myapp.log'

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    creds, conn = connections.start_conn(1)
    user = connections.get_user(1, creds, conn)
    df_db = connections.get_db(creds)
    items_list = connections.get_items(user)

    db_dict = df_db.set_index("cai")["precio2"].to_dict()
    global access_token
    access_token = user['access_token']
    leer_neums(items_list, access_token, db_dict)

    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")

    start_time = time.time()

    #ahora me tengo que fijar si hay diferencias entre la db y la info de cada uno de mis neum
    not_read = list(Neumatico.dict.keys())

    for index, row in df_db.iterrows():
        #fijarse si hay una diferencia entre el precio o stock entre la base d datos y mercado libre
        rsku = row['cai']
        try:
            rneum = Neumatico.dict[rsku]
        except KeyError:
            #no existe en ml
            continue

        mlprecio = rneum.precio
        mlstock = rneum.stock
        dbprecio = int(row['precio'])
        dbstock = int(row['existencia'])

        #si hay diferencias, actualizar
        difprecio = mlprecio != dbprecio
        difstock = mlstock != dbstock

        descartados = descarte(row, dbstock)

        #se deberia fijar la logica del stock clasica
        #si no hay diferencias se continua
        if not difprecio and not difstock:
            continue

        #mepa q esta forma de iterar deberia ser un metodo pero no se como escribirlo lol
        #encima queda horrible todo esto asi
        for index, col, val in Items.iterar_sku(rsku):
            if val.id in descartados:
                continue
            data={}
            cant = int(index)
            if difprecio:
                if col[0]=='gold_special':
                    new_precio = mlprecio * cant
                elif col[0]=='gold_pro':
                    new_precio = int(row['precio2']) * cant
                data["price"] = new_precio
            if difstock:
                new_stock = dbstock // cant
                data["available_quantity"] = new_stock

            #ahora toca actualizar, depende del cat
            #esto despues lo tengo que reutilizar para actualizar o desactualizar
            response = actualizar(data, col, val)
            if response == 200:
                continue
            if response.status_code != 200:
                print("aviso ooo")
    

        not_read.remove(rsku)
    
    for sku in not_read:
        desact_grupo(sku)


    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")



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