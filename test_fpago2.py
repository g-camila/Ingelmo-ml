import requests
import json
import connections
import argparse
import messages
import logging
import pandas as pd
import sys
import os
import shutil
import time 
import messages
from typing import List, Dict, Optional

class Neumatico:
    def __init__(self, id:str, sku:str, cant:int, fpago:str, variation_id:int, precio:int, precio2:int):
        self.id = id
        self.sku = sku
        self.cant = cant
        self.fpago = fpago
        self.var_id = variation_id
        self.precio = precio
        self.precio2 = precio2

    #metodo de mapeo dentro de la clase para elegir precio y forma de pago
    @classmethod
    def nuevo_fpago_precio(cls, fpago:str, precio:int, precio2:int) -> Dict[str, int]:
        fpago_mapping = {
            'gold_special': ('gold_pro', precio2),
            'gold_pro': ('gold_special', precio)
        }
        return fpago_mapping.get(fpago, (None, None))


def consulta (atributo: Optional[dict], item_id: str, items_list: List[str]) -> Optional[dict]:
    try:
        existe = atributo
    except KeyError:
        logging.info(f"{item_id}: error. No se encontro {atributo}")
        items_list.remove(item_id)
        existe = None
    return existe


def update_attribute(json_data: Dict, attribute_key: str, target_id: str, replacement: Dict) -> None:
    attributes = json_data.get(attribute_key, [])
    if attributes == []:
        return attributes
    for attribute in attributes:
        if attribute.get("id") == target_id:
            attribute.update(replacement)
            break
    return attributes

#i responde a la cantidad de veces que quiero que se intente hacer la request
def make_request(method: str, url: str, headers: Dict[str, str], json: Optional[Dict], i: int) -> requests.Response:
    if method == "put":
        response = requests.put(url, headers=headers, json=json)
    elif method == "post":
        response = requests.post(url, headers=headers, json=json)
    elif method == "get":
        response = requests.get(url, headers=headers)

    #estos errores pueden ser por haber intentado hacer demasiadas requests, por eso lo hago 2 veces
    if response.status_code == 429:
        if i >= 1:
            time.sleep(65)
            response = make_request(method, url, headers, json, i-1)
    if response.status_code == 500 or response.status_code == 409:
        if i >= 1:
            time.sleep(15)
            response = make_request(method, url, headers, json, i-1)

    return response


def item_data(items_list: List[str], access_token: str, db_dict: Dict[str, int], batch_size:int=20):
    neum_lista = []
    #while pq necesito que se fije en la condicion todas las veces
    #voy a estar sacando cosas de items list mientras corro este programa
    i=0
    while i < len(items_list):
        #voy a buscar de a 20 items
        #por favor que esto apure
        batch = items_list[i:i + batch_size]
        i += batch_size

        url = f"https://api.mercadolibre.com/items?ids={','.join(batch)}&include_attributes=all"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        #response = requests.get(url, headers=headers)
        response = make_request('get', url, headers, None, 2)
        if response.status_code == 200:
            batch_data = response.json()
        else: #es mas rapido pero si falla un batch tengo que cortar todo, es el riesgo
            logging.info(f"Fallo el batch de los items: {response.status_code}")
            sys.exit()

        #este loop busca la info de cada item y crea un json en mi compu con la información que se guarda para despues duplicarlo si es que toca
        for item_data in batch_data:
            item_data = item_data['body']
            item_id = item_data['id'] #o item_list[i]

            #control de condiciones: que no sea de catalogo y que esté en la db
            catalog = consulta(item_data['catalog_listing'], item_id, items_list)
            if catalog:
                items_list.remove(item_id)
                continue

            #busco el sku
            dir_attributes = consulta(item_data['variations'][0]['attributes'], item_id, items_list)
            sku = None
            for ind in range(len(dir_attributes)):
                atributo = dir_attributes[ind]["id"]
                if atributo == "SELLER_SKU":
                    sku = dir_attributes[ind]['value_name']
                    break

            #aca buscaría si esta en la db, pero ahora mismo no puedo acceder a eso
            precio2 = db_dict.get(sku)
            if precio2 is None:
                items_list.remove(item_id)
                continue
            precio2 = int(precio2)

            variation_id = consulta(item_data['variations'][0]['id'], item_id, items_list)
            #busco la cant de gomas en la publicacion
            cant = None
            for ind in range(len(item_data['attributes'])):
                atributo = item_data['attributes'][ind]["id"]
                if atributo == "TIRES_NUMBER":
                    cant = item_data['attributes'][ind]['value_name']
                    cant = int(cant)
                    break
            fpago = consulta(item_data['listing_type_id'], item_id, items_list)
            precio = consulta(item_data['price'], item_id, items_list)

            #flag para ver si hubo algun error en un momento
            if catalog is None or dir_attributes is None or variation_id is None or fpago is None or precio is None or sku is None:
                continue

            neum = Neumatico(item_id, sku, cant, fpago, variation_id, precio, precio2)
            neum_lista.append(neum)

            #creo un json de la info del item y me lo guardo para poder duplicarlo despues
            fitem = os.path.join('item_files', f'{item_id}.json')
            with open(fitem, 'w', encoding='utf-8') as f:
                json.dump(item_data, f, ensure_ascii=False, indent=4)

            logging.info(f"{item_id}: se preparo correctamente el item")
    return neum_lista



def hacer_par(dir: str, neum_list: List[Neumatico], access_token: str) -> None:
    lista_errores = []
    reemplazo = {
                    "id": "VEHICLE_TYPE",
                    "name": "Tipo de vehículo",
                    "value_id": "11377043",
                    "value_name": "Auto/Camioneta",
                    "values": [
                        {
                            "id": "11377043",
                            "name": "Auto/Camioneta",
                            "struct": None
                        }
                    ],
                    "value_type": "list"
                }
    for neum in neum_list:
        #primero tengo que preparar el archivo para duplicarlo
        fpath = f"{dir}\\{neum.id}.json"
        f = open(fpath, 'r', encoding="utf8")
        file_json = json.load(f)
        f.close()
        #hay que cambiarle unos atributos pq los forros de ml cambiaron el formato del json de los items desde que empece a publicar
        #osea que ml puede leer el formato viejo, pero no publicarlo
        existe = update_attribute(file_json, "attributes", "VEHICLE_TYPE", reemplazo)
        existe2 = update_attribute(file_json["variations"][0], "attributes", "VEHICLE_TYPE", reemplazo)
        if existe == [] or existe2 == []:
            logging.info(f"{neum.id}: hubo un error en el formato del json del item")
            continue

        #tambien tengo que borrarle unos parametros q no le pinta, despues los llena solo ml
        errors = ["original_price", "deal_ids", "id", "thumbnail", "last_updated", "inventory_id", "permalink", "differential_pricing", "stop_time", "sold_quantity", "item_relations", "base_price", "sub_status", "initial_quantity", "date_created", "expiration_time", "warnings", "end_time", "health", "listing_source", "international_delivery_mode", "thumbnail_id", "parent_item_id", "descriptions", "user_product_id", "seller_contact", "seller_id", "geolocation"]
        for error in errors:
            if error in file_json:
                del file_json[error]
        #se duplica con stock 0 para estar mas tranqui
        file_json['available_quantity'] = 0

        #ahora que ya fue preparado el item, toca posta duplicarlo
        #no voy a guardar el json del nuevo item no me sirve
        url = 'https://api.mercadolibre.com/items'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = make_request("post", url, headers, file_json, 2)
        if response.status_code != 200 and response.status_code != 201:
            logging.info(f"{neum.id}: no se pudo duplicar, error: {response.status_code}")
            continue

        new_item = response.json()
        new_id = new_item['id']
        new_var_id = new_item['variations'][0]['id']
        #ahora queda editar la fpago y el precio
        n_fpago, n_precio = Neumatico.nuevo_fpago_precio(neum.fpago, neum.precio, neum.precio2)

        #le cambio el precio
        url = f"https://api.mercadolibre.com/items/{new_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        data = {
            "variations":[
                {
                    "id" : new_var_id,
                    "price" : n_precio*neum.cant
                }
                ]
            }
        response = make_request("put", url, headers, data, 2)
        if response.status_code != 200 and response.status_code != 201:
            logging.info(f"{new_id}: no se pudo cambiar el precio, error: {response.status_code}")
            #response = borrar_item(neum2, access_token, error_dupl)
            lista_errores.append(new_id)
            continue

        #cambiar forma de pago
        url = f"https://api.mercadolibre.com/items/{new_id}/listing_type"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = {
            "id": f"{n_fpago}"
        }
        response = make_request("post", url, headers, data, 2)
        if response.status_code != 200 and response.status_code != 201:
            logging.info(f"{new_id}: no se logro cambiar la forma de pago de la publicacion, error: {response.status_code}")
            #response = borrar_item(neum2, access_token, error_dupl)
            lista_errores.append(new_id)
            continue

        logging.info(f"{neum.id}: se formo un par correctamente: {new_id}")
    return lista_errores



def main(idempresa: int = 1) -> None:
    frta = f'{idempresa}_rta.json'
    fitems2 = f'{idempresa}_items2.json'
    fmyapplog = 'fpago_myapp.log'
    ferror = f'{idempresa}_error_dupl.json'
    dir = "item_files"

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    df_db, conn0, cursor, access_token, user_id = connections.get_connection(1, frta)
    db_dict = df_db.set_index("cai")["precio2"].to_dict()

    with open(ferror, 'r', encoding='utf-8') as f:
        errores_previos = pd.read_json(f)
        errores_previos = list(errores_previos)

    items_gpro = connections.get_items(access_token, user_id, fitems2, "&listing_type_id=gold_pro&status=active")
    items_gspecial = connections.get_items(access_token, user_id, fitems2, "&listing_type_id=gold_special&status=active")

    if len(items_gpro) == 0 and len(items_gspecial) == 0:
        logging.info("No se pudo acceder a la info de los items del usuario")
        sys.exit()

    #Hay que fijarse cuales errores fueron corregidos
    #los errores son las id de las duplicaciones mal hechas
    #si la id no esta en ninguna de las dos listas fue borrada por el usuario
    #si no, ya no existe (o no nos importa) asi que la borro de los errores
    i=0
    while i < len(errores_previos):
        if errores_previos[i] in items_gpro:
            items_gpro.remove(errores_previos[i])
        elif errores_previos[i] in items_gspecial:
            items_gspecial.remove(errores_previos[i])
        else:
            errores_previos.remove(errores_previos[i])
        i += 1

    #ahora tengo que ir uno por uno y buscarles toda la info que voy a usar
    #guardo toda la info en mi compu en la carpeta items_files
    #borro lo que haya antes
    #try:
    #    shutil.rmtree(dir)
    #except OSError as e:
    #    logging.info("Error: %s - %s." % (e.filename, e.strerror))
    #    sys.exit()
    #creo el directorio de nuevo
    os.makedirs(dir)

    neum_gpro = item_data(items_gpro, access_token, db_dict)
    neum_gspecial = item_data(items_gspecial, access_token, db_dict)

    #me de descartar los pares ya creados
    i=0
    while i<len(neum_gspecial):
        j=0
        while j<len(neum_gpro):
            if neum_gspecial[i].sku == neum_gpro[j].sku and neum_gspecial[i].cant == neum_gpro[j].cant:
                neum_gspecial.remove(neum_gspecial[i])
                neum_gpro.remove(neum_gpro[j])
                j = len(neum_gpro)
            j+=1
        i+=1

    logging.info("\nItems listos para la duplicacion\n")

    if not neum_gspecial and not neum_gpro:
        logging.info("No hay pares para crear")
        sys.exit()
    #ahora debería ser que las gomas que quedan son las que hay que intentar duplicar nomas
    #empiezo por los items de gold special pq ahora mismo hay mas de eso
    errores_gspecial = hacer_par(dir, neum_gspecial, access_token)
    errores_gpro = hacer_par(dir, neum_gpro, access_token)

    #se concatenan los errores previos con los nuevos encontrados 
    lerrores = errores_previos + errores_gspecial + errores_gpro
    #fijarme si hubo alguna publicacion mal duplicada
    if len(lerrores) > 0:
        #mandar mail de aviso
        mensaje = "Las siguientes publicaciones fueron duplicadas, pero no pudo cambiarse el precio o la forma de pago. " \
        "No se pudieron borrar, por lo que deben ser borradas manualmente desde el sitio: \n"
        for item_id in lerrores:
            mensaje = mensaje + item_id + "\n"
        messages.send_email('Publicaciones incorrectamente duplicadas', mensaje, 'sincro')

    with open(ferror, 'w', encoding='utf-8') as f:
        json.dump(errores_previos, f, ensure_ascii=False, indent=4)

    


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