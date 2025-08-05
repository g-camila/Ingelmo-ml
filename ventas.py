import requests
import connections
import json
import argparse
import sys
from datetime import datetime, timezone


#class Venta:
#    def __init__(self, item_id, cant, unidades, sku):
#        self.item_id = item_id
#        self.cant = cant
#        self.unidades = unidades
#        self.sku = sku

def armar_ventas(ordenes, access_token):
    dict_ventas = {}
    for orden in ordenes['results']:
        concretado = orden['fulfilled']
        if concretado != None:
            continue
        id_envio = orden['shipping']['id']
        item_id = orden['order_items'][0]['item']['id']
        cant = orden['order_items'][0]['quantity']
        sku = orden['order_items'][0]['item']['seller_sku']

        #tengo que fijarme si la orden fue despachada desde la id del envio
        #puede no marcar como que recibió el envio el cliente
        url = f"https://api.mercadolibre.com/shipments/{id_envio}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            #sys.exit()
        envio_status = response.json()["status"]
        envio_substatus = response.json()["substatus"]
        #fijarme si ya se mandó
        if envio_status == "shipped" or envio_status == "delivered" or (envio_status == "ready_to_ship" and envio_substatus != "ready_to_print"):
            continue

        #consultar la cantidad de gomas dentro de ese item
        url = f"https://api.mercadolibre.com/items/{item_id}?include_attributes=all"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)

        attribute = response.json()['attributes']

        for attribute in response.json()["attributes"]:
            if attribute["id"] == "UNITS_PER_PACK" or attribute["id"] == "TIRES_NUMBER":
                unidades = attribute["value_name"]
                break

        venta_total = cant * int(unidades)

        # Acumular venta_total por SKU
        if sku not in dict_ventas:
            dict_ventas[sku] = venta_total
        else:
            dict_ventas[sku] += venta_total

    return dict_ventas

def main(idempresa=1):
    frta = f'{idempresa}_rta.json'
    df, conn0, cursor, access_token, user_id = connections.get_connection(idempresa, frta)

    #traigo todas las ventas pagadas, no enviadas
    #de aca hay que seguir filtrando porque a vveces pueden igual haberse terminado los envios incluso asi
    url = f'https://api.mercadolibre.com/orders/search?seller={user_id}&tags=not_delivered&order.status=paid&sort=date_desc'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"No se pudieron traer las ordenes: {response.status_code}")
        sys.exit()

    #todas las ordenes 
    f = open("ordenes.json","w")
    ordenes = response.json()
    json.dump(ordenes,f)
    f.close()
    
    ventas_dict = armar_ventas(ordenes, access_token)
    return ventas_dict





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