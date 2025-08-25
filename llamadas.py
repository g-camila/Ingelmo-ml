import connections
import requests
import settings as s

#en este archivo voy a ir agregando todas las config de las llamadas api q vaya haciendo
#es lo mas practico para reutilizarlas a futuro es mi mini docu

def get_item_attrs(item_id):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/items/{item_id}?include_attributes=all"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = connections.make_request('get', url, headers)
    return response


def modificar(id, data):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/items/{id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = connections.make_request('put', url, headers, data)
    return response


def cambiar_estado(id, data):
    access_token = s.get_config_value('access_token')
    url = f'https://api.mercadolibre.com/items/{id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = connections.make_request('put', url, headers, data)
    return response
    #para cambiar el estado a pausado o cerrado no anda
    #osea no se pueden eliminar publicaciones desde el codigo basicamente
    #para pausar {'status': 'closed'} y borrar {"deleted": "true"} en data


    #traigo todas las ventas pagadas, no enviadas
    #de aca hay que seguir filtrando porque a veces pueden igual haberse terminado los envios incluso asi
def ordenes_sin_enviar():
    access_token = s.get_config_value('access_token')
    user_id = s.get_config_value('user_id')
    url = f'https://api.mercadolibre.com/orders/search?seller={user_id}&tags=not_delivered&order.status=paid&sort=date_desc'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = connections.make_request('get', url, headers)
    return response

def get_envio(id_envio):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/shipments/{id_envio}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = connections.make_request('get', url, headers)
    return response


##LLAMADAS A MI ENDPOINT

##sacar historial de notifs
def notif_historial(app_id):
    access_token = s.get_config_value('access_token')
    url = f'https://api.mercadolibre.com/missed_feeds?app_id={app_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = connections.make_request('get', url, headers=headers)
    return response
