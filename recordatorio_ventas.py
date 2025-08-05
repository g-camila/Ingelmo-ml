import requests
import connections
import json
import argparse
import messages
import sys
from datetime import datetime, timezone


class Venta:
    def __init__(self, iden, item_id, titulo, fecha, cant, comprador, id_envio, avisar_entrega):
        self.iden = iden
        self.item_id = item_id
        self.titulo = titulo
        self.fecha = fecha
        self.cant = cant
        self.comprador = comprador
        self.id_envio = id_envio
        self.avisar_entrega = avisar_entrega


#hace una fecha que viene en datetime legible para el mail
def fecha_legible(fecha):
    fecha_dt = datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S%z')
    return fecha_dt.strftime('%d/%m/%Y, %H:%M:%S')

def armar_ventas(ordenes, access_token):
    lVentas = []
    for orden in ordenes['results']:
        concretado = orden['fulfilled']
        if concretado != None:
            continue
        fecha = orden['date_created']
        fecha = datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S.%f%z')
        id_envio = orden['shipping']['id']
        iden = orden['id']
        item_id = orden['order_items'][0]['item']['id']
        titulo = orden['order_items'][0]['item']['title']
        comprador = orden['buyer']['id']
        cant = orden['order_items'][0]['quantity']
        avisar_entrega = False

        #tengo que fijarme si la orden fue despachada desde la id del envio
        #puede no marcar como que recibió el envio el cliente
        url = f"https://api.mercadolibre.com/shipments/{id_envio}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(url, headers=headers)
        #f = open("envio.json","w")
        #json.dump(response.json(),f)
        #f.close()

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            #sys.exit()
        envio_status = response.json()["status"]
        envio_substatus = response.json()["substatus"]
        #fijarme si ya se mandó
        if envio_status == "shipped" or envio_status == "delivered" or (envio_status == "ready_to_ship" and envio_substatus != "ready_to_print"):
            continue
        if envio_status == "pending" and envio_substatus == None: #envio a cargo de nosotros, no de mercado envios
            avisar_entrega = True

        venta = Venta(iden, item_id, titulo, fecha, cant, comprador, id_envio, avisar_entrega)
        lVentas.append(venta)

    return lVentas

def misma_hora(fecha1, fecha2):
    return (fecha1.year == fecha2.year and
            fecha1.month == fecha2.month and
            fecha1.day == fecha2.day and
            fecha1.hour == fecha2.hour)

#ahora puede recibir una x cantidad de ventas
def mail_combo(ordenes):
    if not ordenes[0].avisar_entrega:
        messages.send_email("Recordatorio de venta", 
                    f"Se hicieron {len(ordenes)} ventas de un {ordenes[0].titulo}, deben ser despachadas.", 
                    "envio")     
    else:
        messages.send_email("Recordatorio de venta", 
                    f"Se hicieron {len(ordenes)} ventas de un {ordenes[0].titulo}. Si ya se despacharon, se debe avisar la entrega en mercado libre.", 
                    "envio")  

def mail_simple(orden):
    if not orden.avisar_entrega:
        messages.send_email("Recordatorio de venta", 
                    f"Se hizo una venta de un {orden.titulo}, debe ser despachada.", 
                    "envio")
    else:
        messages.send_email("Recordatorio de venta", 
                    f"Se hizo una venta de un {orden.titulo}. Si ya se despachó, se debe avisar la entrega en mercado libre.", 
                    "envio")
        
def combo_compra(orden1, orden2):
    m_titulo = 'kit' not in orden1.titulo and 'kit' not in orden2.titulo
    m_comprador = orden1.comprador == orden2.comprador
    m_neum = orden1.item_id == orden2.item_id
    return m_titulo and m_comprador and m_neum


def main (idempresa=1):
    #dias de semana, de 8 a 20. solo se mandan mails si estamos en eso
    horario_laboral = (datetime.now().hour >= 8 and datetime.now().hour <= 20) and (datetime.now().weekday() < 5)
    if not horario_laboral:
        print("No estamos en horario laboral")
        sys.exit()


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
    
    lVentas = armar_ventas(ordenes, access_token)

    combo_ventas = []
    i = 0
    while i < len(lVentas):
        j = i+1
        flag = False
        while j < len(lVentas) and flag == False:
            if misma_hora(lVentas[i].fecha, lVentas[j].fecha):
                while combo_compra(lVentas[i], lVentas[j]):
                    #alguien compro mas de una de la misma goma en una sola sentada
                    flag = True
                    combo_ventas.append(lVentas[j])
                    lVentas.remove(lVentas[j])
                if flag == True:
                    combo_ventas.append(lVentas[i])
                    mail_combo(combo_ventas)
                j=j+1
            else:
                j=len(lVentas)
        if flag == False:
            mail_simple(lVentas[i])
        i=i+1



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