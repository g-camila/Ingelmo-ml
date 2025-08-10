import sys
import argparse
import llamadas
import settings as s
from datetime import datetime, timezone
from objetos import Items

#es una solucion bastante mala leo todas las ventas para restar las que no se despacharon
#se deberian detectar las ventas hechas con notificaciones en el momento
#pero hasta que haga eso puedo usar esta solucion vieja

def armar_ventas():
    response = llamadas.ordenes_sin_enviar()
    if response.status_code != 200:
        print("Hubo un error, no se pudieron traer las ordenes correctamente")
        sys.exit()

    #todas las ordenes 
    ordenes = response.json()
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
        response = llamadas.get_envio(id_envio)

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")

        envio_status = response.json()["status"]
        envio_substatus = response.json()["substatus"]
        #fijarme si ya se mandó
        if envio_status == "shipped" or envio_status == "delivered" or (envio_status == "ready_to_ship" and envio_substatus != "ready_to_print"):
            continue

        #consultar la cantidad de gomas dentro de ese item
        for index, col, val in Items.iterar_sku(sku):
            if val.id == item_id:
                unidades = index[1]

        venta_total = cant * int(unidades)

        # Acumular venta_total por SKU
        if sku not in dict_ventas:
            dict_ventas[sku] = venta_total
        else:
            dict_ventas[sku] += venta_total

    return dict_ventas





#if __name__ == "__main__":
#    parser = argparse.ArgumentParser(description='Procesar el ID de la empresa.')
#    parser.add_argument('idempresa', type=str, help='El ID de la empresa')
#    try:
#        args = parser.parse_args()
#        main(args.idempresa)
#    except SystemExit as e:
#        if e.code != 0:
#            print(f"Error: {e}")
#        main(1)