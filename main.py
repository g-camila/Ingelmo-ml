import requests
import pandas as pd
import json
import argparse
import math
import os
import messages
import connections
import logging
import ventas as venta
os.environ['PYTHONIOENCODING'] = 'utf-8'


#Funcion para actualizar el item en si
#No quiero tocar info al pedo y mandarla asi q chequeo todo antes
def actualizar(price_ml, stock_ml, pprice_db, stock_db, variation_id, url, headers, catalog):
    error = False
    data = {}

    if price_ml != pprice_db:
        precio_key = "price"
        precio_value = pprice_db
        if not catalog:
            data = {
                    "variations":[
                        {
                            "id":variation_id,
                            precio_key : precio_value
                        }
                        ]
                    }
            data["variations"][0][precio_key] = precio_value
        else:
            data = {precio_key: precio_value}
        
        logging.info(f"Cambio de precio: {price_ml} a {pprice_db}")

    if(stock_ml != stock_db):
            stock_key = "available_quantity"
            stock_value = stock_db
            if not catalog:
                if "variations" not in data:
                    data["variations"] = [{"id":variation_id}]
                data["variations"][0][stock_key] = stock_value
            else:
                data[stock_key] = stock_value
            logging.info(f"Cambio de stock: {stock_ml} a {stock_db}")

            if(stock_ml == 0 and stock_db>0):
                logging.info("Reactivado")

    if data:
            response = requests.put(url, headers=headers, json=data)
            error = response.status_code != 200
            logging.info(f"Se intento actualizar: {response}")
    else:
            logging.info('No se actualizo, sin cambios entre ML y DB')
            
    return error
    
def desactivar(variation_id, url, headers, catalog):
    stock_key = "available_quantity"
    data = {}
    if not catalog:
        data = {
                "variations":[
                    {
                        "id":variation_id,
                    }
                    ]
                }
        data["variations"][0][stock_key] = 0
    else:
        data = {stock_key: 0}
    
    logging.info(f"Se desactivo la publicacion")

    response = requests.put(url, headers=headers, json=data)
    error = response.status_code != 200
    logging.info(f"Se intento desactivar: {response}")
    return error


def main(idempresa=1):
    #ej: si idempresa es 1, sería 1_rta.json, 1_item.json, etc
    #en realidad creo que no hace tanta falta hacer tantos json, debería correr un benchmark apra ver si vale la pena
    frta = f'{idempresa}_rta.json'
    fitem = f'{idempresa}_item.json'
    fitems2 = f'{idempresa}_items2.json'
    fmyapplog = f'{idempresa}_myapp.log'

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    df_db, conn0, cursor, access_token, user_id = connections.get_connection(idempresa,frta)

    #CONULTA 1: BUSCAR TODOS LOS ITEMS DEL USUARIO
    #Esto se va a guardar en un array de ids
    #Recordar que solo se puede editar lo activo
    items_list = connections.get_items(access_token, user_id, fitems2)

    ventas_dict = venta.main(idempresa)
    for sku, ventas in ventas_dict.items():
        index = df_db[df_db['cai'].str.strip() == sku.strip()].index.tolist()
        index = index[0]
        nueva_exist = df_db.loc[index, 'existencia'] - ventas
        df_db.loc[index, 'existencia'] = nueva_exist if nueva_exist >= 0 else 0

    length = len(items_list)
    messages.printProgressBar(0, len(items_list), prefix = 'Progress:', suffix = 'Complete', length = 50)

    #Hacer una lista con todos los CAI de la base de datos e ir sacandolos cuando se los encuentra, al final fijarse que tiene que estar vacía
    check_df = pd.DataFrame({
        'cai' : [],
        'ml_check' : [], 
        'q_1' : [],
        'q_2' : [], 
        'q_4' : []
        })

    check_df['cai'] = df_db['cai'].tolist()
    not_db = []
    #evita un error de pandas
    check_df['ml_check'] = ""
    error=False

    for i, item_id in enumerate(items_list):
        logging.info("\n")
        logging.info(f"{item_id}")

        url = f"https://api.mercadolibre.com/items/{item_id}?include_attributes=all"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if (response.status_code != 200):
            error = True

        logging.info(f'{item_id} se intento leer: {response}')

        f = open(fitem,"w")
        json.dump(response.json(),f)
        f.close()

        #Conseguir informacion del item
        f = open(fitem,'r')
        item = json.load(f)
        df_item = pd.DataFrame.from_dict(item, orient='index')
        f.close()

        #fijarse si es catalogo!
        #catalog = df_item[0]['catalog_listing']
        #if not catalog:

        #else declarear lista append y desactivar y avisar

        catalog = df_item[0]['catalog_listing']

        if not catalog:
            dir_attributes = df_item[0]['variations'][0]['attributes']
            variation_id = df_item[0]['variations'][0]['id']
        else:
            dir_attributes = df_item[0]['attributes']

        # sku = None
        for ind in range(len(dir_attributes)):
            atributo = dir_attributes[ind]["id"]
            if atributo == "SELLER_SKU":
                sku = dir_attributes[ind]['value_name']
                break

        
        #PRIMERO si existe el SKU
        if(sku != None):
            index = df_db[df_db['cai'].str.strip() == sku.strip()].index.tolist()

            #Si existe en la DB
            if index:
                index = index[0]
                #Aclarar q ya se leyo al menos un item de ese cai
                check_df.loc[index, "ml_check"] = "read"

                #1. Fijarse si está activo
                #if df_item[0]['status'] == "active":

                #Conseguir toda la info q haga falta
                price_ml = df_item[0]['price']
                stock_ml = df_item[0]['available_quantity']
                fpago = df_item[0]['listing_type_id']

                #Hay q loopear dentro del json hasta encontrar tires_number, no siempre tiene la misma cantidad de atributos
                #declaro quantity por si no encuentra nada
                quantity = 0
                for ind in range(len(df_item[0]['attributes'])):
                    atributo = df_item[0]['attributes'][ind]["id"]
                    if atributo == "TIRES_NUMBER" or atributo == "UNITS_PER_PACK":
                        quantity = df_item[0]['attributes'][ind]['value_name']
                        quantity = int(quantity)
                        break

                f.close()

                if quantity == 0:
                    #no se encontró, se para todo
                    logging.info(f"No se encontró quantity en el file de: {item_id} \n")
                    continue

                #precio normal, pago sin cuotas
                price_db = df_db.loc[index, 'precio']
                price_db = int(price_db)    #precio sin decimal
                #precio 12% (por ahora) mayor, para 6 cuotas sin interes
                price_db2 = df_db.loc[index, 'precio2']
                price_db2 = int(price_db2)
                stock_db = df_db.loc[index, 'existencia']
                stock_db = int(stock_db)

                #HACER UPDATE DE STOCK Y PRECIO
                url = f"https://api.mercadolibre.com/items/{item_id}"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }

                #Este es el caso *D y x4 pero lo voy a usar por default para todo por ahora
                try:
                    is_x4 = '*X4' in df_db.loc[index, 'observ'] and (quantity != 1 or quantity != 2)
                except TypeError:
                    print("fijate aca")
                is_stock_1 = stock_db == 1 and (quantity == 2 or quantity == 4)
                is_stock_2 = stock_db == 2 and (quantity == 1 or quantity == 4)
                is_stock_3 = stock_db == 3 and quantity == 4
                #is_even_stock = stock_db % 2 == 0 and stock_db >= 4 and quantity == 1

                # Combine conditions
                if is_x4 or is_stock_1 or is_stock_2 or is_stock_3:
                    logging.info("No entra en los criterios de observaciones")
                    error = desactivar(variation_id, url, headers, catalog)
                else:
                    if fpago == "gold_special":
                        error = actualizar(price_ml, stock_ml, price_db*quantity, stock_db//quantity, variation_id, url, headers, catalog)
                    elif fpago == "gold_pro": #6 cuotas sin interes
                        error = actualizar(price_ml, stock_ml, price_db2*quantity, stock_db//quantity, variation_id, url, headers, catalog)
                    else:
                        logging.info(f"No se pudo actualizar, no se encontró forma de pago")

                #check_df tiene tres columnas al final que sirven para saber si el conjunto de 1, 2, 4 kits del producto esta completo
                x = quantity//2
                check_df.iloc[index, x+2] = quantity


            #MANEJO DE EXCEPCIONES
                #else:
                #No hace falta fijarse si es activo o no, parece que no le importa
                #MEJOR pq si no tiene stock y lo agrega lo reactiva

                messages.printProgressBar(i + 1, length, prefix = 'Progress:', suffix = 'Complete', length = 50)

            else:
                logging.info(f"No se encontro en la DB    SKU  {sku}  ")
                dict = {item_id, sku}
                not_db.append(dict)
                if(df_item[0]['status'] == "active"):
                    #desactivar
                    error = desactivar(variation_id, url, headers, catalog)
                messages.printProgressBar(i + 1, length, prefix = 'Progress:', suffix = 'Complete', length = 50)

        else:
            logging.info("No se encontro el codigo SKU en la informacion de ML, se desactivo la publicacion")
            error = desactivar(variation_id, url, headers, catalog)
            messages.printProgressBar(i + 1, length, prefix = 'Progress:', suffix = 'Complete', length = 50)
        # else:
        #     #caso de q sea de catalogo, necesito llenar ciertas listas para que no tire error
        #     logging.info("Se ignoro un item de catalogo")
        #     messages.messages.send_email("Se ignoro un item de catalogo", None)
        #     messages.printProgressBar(i + 1, length, prefix = 'Progress:', suffix = 'Complete', length=50)




    #Fijarse si todos los items de la db están en ml
    #Si no tienen stock hacer none lo mismo not db
    logging.info("\n")
    all_read = True
    for i,x in enumerate(check_df['ml_check']):
        if(x != "read"):
            #fijarse que se lea la misma linea, pero el cai
            all_read = False
            index_nr = df_db[df_db['cai'] == check_df["cai"][i]].index.tolist()
            index_nr = index_nr[0]
                        
            logging.info(f"{df_db.loc[index_nr, 'cai'].strip()} no se encontro en ml: {df_db.loc[index_nr, 'descripcion']}")

    if(all_read):
        logging.info("Todos los items de la db se encontraron en ml activos")

    #Fijarse si todos los items de ml estan en la db
    logging.info("\n")
    if(len(not_db) > 0):
        for x in not_db:
            logging.info(f"{x} no se encontro en la db, se desactivo")
    else:
        logging.info("Todos los items de ml estan en la db")


    #controlar si estan todos los kit completos
    logging.info("\n")
    for i in range(len(check_df['cai'])):
        #fijarse si en esa fila q_1, q_2, q_3 estan todos llenos
        falta = []
        if (check_df["q_1"][i] != 1):
            falta.append(1)
        if (check_df["q_2"][i] != 2):
            falta.append(2)
        if (check_df["q_4"][i] != 4):
            falta.append(4)

        #de forma ideal deberia referenciar al menos una publicacion de ml
        if len(falta) > 0 and len(falta) < 3:
            logging.info(f"{check_df['cai'][i].strip()} kit no completo, falta publicacion de: {falta}")


    
    with open(fmyapplog, 'r', encoding='utf-8') as file:
        log_content = file.read()

    
    cadena="insert into historial (idempresa,myapplog,status) values (?, ?, ?)"
    values=(idempresa,log_content,'ok')

    cursor = conn0.cursor()
    cursor.execute(cadena,values)
    cursor.commit()

    if error:
        mensaje="Hubo un error al intentar actualizar o desactvar el/los item/s"
        messages.send_email(mensaje, log_content, 'sincro')

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