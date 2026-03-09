import os
import sys
import pandas as pd
import argparse
import logging
import json
import settings as s
import pickle
import messages
import connections
from spin import Spinner
from objetos import Neumatico, Items
os.environ['PYTHONIOENCODING'] = 'utf-8'

def precio_real(precio, precio2, dir):
    fpago = Items.get_fpago(dir)
    if fpago == 0:
            return precio * Items.get_cant(dir)
    elif fpago == 1:
            return precio2 * Items.get_cant(dir)
        #es un % mas que el precio real, no hace falta andar enviando variables

def stock_real(stock, dir):
    return stock // Items.get_cant(dir)

def check_incompletos(incompletos):
    df = pd.DataFrame(incompletos, columns=["id", "activo", "causa", "link"])
    activos = df[df['activo'] == True]
    inactivos = df[df['activo'] == False]
    df_reordered = pd.concat([activos, inactivos])
    df_reordered.to_excel('incompletos.xlsx', index=False)


def leer_neums(items_list, batch_size=20):
    i=0
    access_token = s.get_config_value('access_token')

    incompletos=[]

    #lo que se deberia estar haciendo aca es guardar la info de la ultima vez que lei los items
    #y solo buscar los atributos de todo de lo que no se leyo todavia para agregarlo
    #y borrar lo que no encuentre
    length = len(items_list)
    messages.printProgressBar(0, length, prefix = 'Leyendo items:', suffix = 'Complete', length = 50)

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
            messages.send_email(0, "Error al traer un batch de items",  response.json())
            sys.exit()

        for item_data in batch_data:
            if item_data['code'] != 200:
                messages.send_email(0, "No se pudo leer un item",  item_data)
                sys.exit()

            item_data = item_data['body']

            #BORRAR ESTO ANTES DEL DEPLOY
            #with open("test.json", "w") as json_file:#
            #    json.dump(item_data, json_file, indent=4)#
            
            if item_data['status'] == 'closed' or (item_data['category_id'] != 'MLA22195' and item_data['category_id'] != 'MLA6530'):
                continue
            try:
                Items(item_data)
            except ValueError as err:
                if item_data['category_id'] == 'MLA22195' or item_data['category_id'] == 'MLA6530':
                    info = {
                        'id':item_data['id'],
                        'activo':True if item_data['status']=='active' else False,
                        'link':item_data['permalink']
                    }
                    info.update(Items.curr_error)
                    incompletos.append(info)
                continue

            current = Items.ultimo_dir
            sku = Items.get_sku(current)
            cant = Items.get_cant(current)
            catalog = Items.get_catalogo(current)

            #garantizar que haya precio de 1 de precio2 
            #cuando se crea el neumatico si es de fpago 1 se asigna el precio de 1
            if cant == 1 and sku not in Neumatico.dict and catalog is False:
                n = Neumatico(item_data)
                n.item_dir = current

        messages.printProgressBar(i, length, prefix = 'Leyendo items:', suffix = 'Complete', length = 50)
    return incompletos

    #picklear todo
    #file_path = 'C:\\fuentes\\pickled_lectura.pk1'
    #Items.df.to_pickle(file_path)
    #esto hace que todo este en el mismo stream?
    #pickle.dump(Items.repetidos, file_path)
    #pickle.dump(Neumatico.dict, file_path)


def main(idempresa):
    spinner = Spinner()
    spinner.start()

    fmyapplog = f'{idempresa}_myapp.log'
    
    s.update_config('GENERAL', 'idempresa', idempresa)

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    logging.info(f"INICIO DEL PROCESO DE SINCRONIZACION ")
    logging.info("\n")

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    items_list = connections.get_items()
    
    spinner.stop()

    incompletos = leer_neums(items_list)
    check_incompletos(incompletos)



    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Procesar el ID de la empresa.')
    parser.add_argument('idempresa', type=str, help='El ID de la empresa')
    try:
        args = parser.parse_args()
        main(args.idempresa)
    except SystemExit as e:
        if e.code != 0:
            print(f"Error: {e}")
        main(3)