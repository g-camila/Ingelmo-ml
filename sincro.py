import os
import argparse
import time
import logging
import pandas as pd
import json
import messages
import llamadas
import connections
import pandas as pd
from objetos import Neumatico, Items
import lectura
import settings as s
from ventas import armar_ventas

os.environ['PYTHONIOENCODING'] = 'utf-8'

def check_cat(data, cat, val):
    #preparar el json data!!
    if not cat: #no catalogo
        data['id'] = val.variation_id
        data = [data]
        xdata={}
        xdata["variations"] = data
        data = xdata
    return data

def desactivar(col, val):
    if val.status != 'active' or val.status == 'under_review':
        return 200
    else:
        data1 = {"available_quantity" : 0}
        data = check_cat(data1, col[1], val)
        response = llamadas.modificar(val.id, data)
        return response.status_code
    
def desact_grupo(sku, filtro=[""], desc=None):
    for index, col, val in Items.iterar_sku(sku, filtro):
        response = desactivar(col, val)
        messages.handle_error(response, dir, val, 'desact')
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

#limpiar los repetidos
def corregir_repetidos():
    if not Items.repetidos:
        return
    
    for sku in Items.repetidos:
        for strdir in Items.repetidos[sku]:
            dir = eval(strdir)

        #fijarse si hay algo del valor contrario de fpago
        #rfpago = dir[1][0]
        #cat = Items.get_catalogo(dir)
        #for pagos in Items.fpago:
        #    if pagos != rfpago:
        #        if pd.isna(Items.df.loc[dir[0], (pagos, cat)]):
        #            #nomas intentar cambiar fpago
        #            #si no mal recuerdo es un re quilombo <3 se pospone
        #            del Items.fpago[sku][valor]

            for val in Items.repetidos[sku][strdir]:
                #desactivar y mandar mail avisando que hay que borrar!!
                response = desactivar(dir[1], val)
                messages.handle_error(response, dir, val, 'desact')

def sincro(loc, val, cambios):
    if val.status == 'under_review':
        return
    
    recargo = s.get_config_value('recargo')
    data = {}
    if 'precio' in cambios:
        precio = cambios['precio']
        new_precio = lectura.precio_real(precio, precio*recargo, loc)
        data['price'] = new_precio
    if 'stock' in cambios:
        stock = cambios['stock']
        new_stock = lectura.stock_real(stock, loc)
        data['available_quantity'] = new_stock

    catalogo = Items.get_catalogo(loc)
    data2 = check_cat(data, catalogo, val)
    response = llamadas.modificar(val.id, data2)
    logging.info(f"Se actualizo el item {val.id}")
    messages.handle_error(response, loc, val, 'sincro')
    return

def main(idempresa=1):
    start_time = time.time()
    fmyapplog = f'{idempresa}_myapp.log'
    errores_file = f'{idempresa}_errores.json'

    s.update_config('GENERAL', 'idempresa', idempresa)

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    dict_ventas = armar_ventas()

    lectura.leer_neums(items_list, idempresa)
    corregir_repetidos()


    if not os.path.exists(errores_file):
        with open(errores_file, 'w') as file:
            json.dump({}, file)

    with open(errores_file, 'r') as file:
        errores = json.load(file)
        for error in errores:
            strdir = error['dir']
            dir = eval(strdir)
            sku = Items.get_sku(dir)
            errores_rows = df_db[df_db['cai'] == sku]
            normales_rows = df_db[df_db['cai'] != sku]

    if errores:
        #los errores previos toman prioridad!!
        df_db = pd.concat([errores_rows, normales_rows], ignore_index=True)


    #ahora me tengo que fijar si hay diferencias entre la db y la info de cada uno de mis neum
    not_read = list(Neumatico.dict.keys())
    cambios = {}

    for index, row in df_db.iterrows():
        #fijarse si hay una diferencia entre el precio o stock entre la base d datos y mercado libre
        rsku = row['cai']
        try:
            rneum = Neumatico.dict[rsku]
        except KeyError:
            return False #no existe en ml

        mlprecio = rneum.precio
        mlstock = rneum.stock
        dbprecio = int(row['precio']) - dict_ventas.get(sku)
        dbstock = int(row['existencia'])

        difprecio = mlprecio != dbprecio
        difstock = mlstock != dbstock

        #funcion que se fija si el item entra en los requisitos para desactivarlo por default
        descartados = descarte(row, dbstock, cambios)

        if not difprecio and not difstock:
            continue
        
        #guardar en un df los cambios
        if difstock:
            cambios[sku]['precio'] = dbprecio
        if difprecio:
            cambios[sku]['stock'] = dbstock

        for index, col, val in Items.iterar_sku(rsku):
            #el 99% que sea de catalogo va a significar que esta vinculado
            #lo voy a diferenciar por el 1% que seguro me va a cagar
            if val.id in descartados or val.sincronizada:
                continue
            loc = [(rsku, index), col]
            sincro(loc, val, cambios[sku])
            not_read.remove(rsku) #los que queden son cosas de la db que no estan en ml
    
    for sku in not_read:
        desact_grupo(sku)


    with open(errores_file, 'r') as file:
        errores = json.load(file)
        for error in errores:
            strdir = error['dir']
            dir = eval(strdir)
            val = error['val']
            tipo = error['tipo']
            if tipo == 'sincro':
                sincro(dir, val, cambios[sku])
            elif tipo == 'desact':
                sincro(dir, val, cambios[sku])

    logging.info("Sincronización hecha")

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