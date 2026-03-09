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

def get_item_simple(item_id):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/items/{item_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = connections.make_request('get', url, headers)
    return response

def cambiar_fam_name(item_id, new_fam_name):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/items/{item_id}/family_name"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "family_name": new_fam_name
    }
    response = connections.make_request('put', url, headers, payload)
    return response

def consulta_family(fam_id):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/sites/MLA/user-products-families/{fam_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = connections.make_request('get', url, headers)
    return response

def consulta_user_product(up_id):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/user-products/{up_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = connections.make_request('get', url, headers)
    return response

#esto es para cuando tenga q configurar un usuario nuevo
def grant_access_token(client_id, client_secret, code, redirect_uri):
    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded"
    }
    response = connections.make_request('post', url, headers, payload)
    return response

def tech_specs(category_id):
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/categories/{category_id}/technical_specs/input"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = connections.make_request('get', url, headers)
    return response

def get_user_info():
    user_id = s.get_config_value('user_id')
    access_token = s.get_config_value('access_token')
    url = f"https://api.mercadolibre.com/users/{user_id}"
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
