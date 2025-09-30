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
from spin import Spinner

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
        return None
    else:
        data1 = {"available_quantity" : 0}
        data = check_cat(data1, col[1], val)
        response = llamadas.modificar(val.id, data)
        return response
    
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
    if  stockdb % 2 == 0:
        desact_grupo(sku, ["2","4"], desc)

    if '*X4' in row['observ'] and '*X2' in row['observ']:
         desact_grupo(sku, ["2","4"], desc)
    elif '*X4' in row['observ'] :
            desact_grupo(sku, ["4"], desc)
    elif '*X2' in row['observ']:
            desact_grupo(sku, ["2"], desc)

       
    match stockdb:
        case 1 | 2:
            filtro = str(stockdb)
            desact_grupo(sku, [filtro], desc)
        case 3:
            desact_grupo(sku, ["1", "2"], desc)
    
    return desc


#limpiar los repetidos y los items sin trackear en neum
def corregir():
    #quiero corregir que haya andado bien lo de asignar el precio2
    keys_to_delete = []
    for sku, neum in Neumatico.dict.items():
        if neum.precio2 is None:
            if not Items.df.loc[sku]['gold_pro'].isna().all().all():
                keys_to_delete.append(sku)

    for key in keys_to_delete:
        del Neumatico.dict[key]

    skus = Items.df.index.get_level_values(0)
    for sku in skus:
        if sku not in Neumatico.dict:
            if sku not in keys_to_delete:
                keys_to_delete.append(sku)
            for index_item, col, val in Items.iterar_sku(sku):
                dir = [(sku, index_item), col]
                response = desactivar(col, val)
                messages.handle_error(response, dir, val, 'desact')

    if keys_to_delete:
        lista = "\n".join(keys_to_delete)
        mensaje = (
            "No se pudo asignar precio2 a los siguientes skus: \n\n"
            f"{lista}"
        )
        messages.send_email(0, "Sku sin asignar", mensaje)


    for sku in Items.repetidos:
        for strdir in Items.repetidos[sku]:
            dir = eval(strdir)
            for val in Items.repetidos[sku][strdir]:
                #desactivar y mandar mail avisando que hay que borrar!!
                response = desactivar(dir[1], val)
                messages.handle_error(response, dir, val, 'desact')


def sincro(loc, val, cambios):
    if val.status == 'under_review':
        return
    
    data = {}
    if 'precio' in cambios:
        precio = cambios['precio']
        precio2 = cambios['precio2']
        new_precio = lectura.precio_real(precio, precio2, loc)
        data['price'] = new_precio
    if 'stock' in cambios:
        stock = cambios['stock']
        new_stock = lectura.stock_real(stock, loc)
        data['available_quantity'] = new_stock

    catalogo = Items.get_catalogo(loc)
    data2 = check_cat(data, catalogo, val)
    response = llamadas.modificar(val.id, data2)
    messages.handle_error(response, loc, val, 'sincro')
    return


def main(idempresa=1):
    start_time = time.time()

    spinner = Spinner()
    spinner.start()

    fmyapplog = f'{idempresa}_myapp.log'
    errores_file = f'{idempresa}_errores.json'
    
    s.update_config('GENERAL', 'idempresa', idempresa)

    messages.create_log(fmyapplog)
    logger = logging.getLogger(__name__)

    logging.info(f"INICIO DEL PROCESO DE SINCRONIZACION ")
    logging.info("\n")

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    spinner.stop()


    lectura.leer_neums(items_list)
    corregir()

    dict_ventas = armar_ventas()
    
    #los errores anteriores toman prioridad para actualizar
    if os.path.exists(errores_file):
        with open(errores_file, 'r') as file:
            errores = json.load(file)
            for error in errores:
                row = tuple(error['dir'][0])
                col = tuple(error['dir'][1])
                dir = [row, col]
                sku = Items.get_sku(dir)
                errores_rows = df_db[df_db['cai'] == sku]
                normales_rows = df_db[df_db['cai'] != sku]

        os.remove(errores_file)
        df_db = pd.concat([errores_rows, normales_rows], ignore_index=True)


    #ahora me tengo que fijar si hay diferencias entre la db y la info de cada uno de mis neum
    ml_skus = list(Neumatico.dict.keys())
    db_skus = df_db['cai'].unique()
    ml_not_db = [sku for sku in ml_skus if sku not in db_skus]

    cambios = {}

    length = len(df_db)
    print("\n")
    messages.printProgressBar(0, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)


    for i, (index, row) in enumerate(df_db.iterrows(), start=0):
        #fijarse si hay una diferencia entre el precio o stock entre la base d datos y mercado libre
        rsku = row['cai']
        try:
            rneum = Neumatico.dict[rsku]
        except KeyError:
            messages.printProgressBar(i + 1, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)
            continue  #no existe en ml

        mlprecio = rneum.precio
        mlprecio2 = rneum.precio2
        mlstock = rneum.stock
        dbprecio = int(row['precio'])
        dbprecio2 = int(row['precio2'])
        dbstock = max(0, int(row['existencia']) - dict_ventas.get(rsku, 0))

        difprecio = mlprecio != dbprecio or mlprecio2 != dbprecio2
        difstock = mlstock != dbstock

        #funcion que se fija si el item entra en los requisitos para desactivarlo por default
        descartados = descarte(row, dbstock)

        if not difprecio and not difstock:
            messages.printProgressBar(i + 1, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)
            continue
        
        cambios[rsku] = {}
        #guardar en un dict los cambios
        if difstock:
            cambios[rsku]['stock'] = dbstock
        if difprecio:
            cambios[rsku]['precio'] = dbprecio
            cambios[rsku]['precio2'] = dbprecio2

        for index_item, col, val in Items.iterar_sku(rsku):
            #el 99% que sea de catalogo va a significar que esta vinculado
            #lo voy a diferenciar por el 1% que seguro me va a cagar
            if val.id in descartados or val.sincronizada:
                continue
            loc = [(rsku, index_item), col]
            sincro(loc, val, cambios[rsku])

        messages.printProgressBar(i + 1, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)
        #not_read.remove(rsku) #los que queden son cosas de la db que no estan en ml
    
    spinner = Spinner()
    spinner.start()

    for sku in ml_not_db:
        desact_grupo(sku)

    #lo intento otra vez
    if os.path.exists(errores_file):
        with open(errores_file, 'r') as file:
            errores = json.load(file)
        os.remove(errores_file)
        for error in errores:
            row = tuple(error['dir'][0])
            col = tuple(error['dir'][1])
            val = Items.loc[row, col]
            tipo = error['tipo']
            if tipo == 'sincro':
                sincro(dir, val, cambios[sku])
            elif tipo == 'desact':
                desactivar(col, val)

    spinner.stop()

    logging.info("Sincronización hecha")

    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")

    with open(fmyapplog, 'r', encoding='latin-1') as file:
        log_content = file.read()


    cambios_json = json.dumps(cambios)

    cadena="insert into historial (idempresa,myapplog,status) values (?, ?, ?)"
    values=(idempresa,cambios_json,'ok')

    cursor = conn.cursor()
    cursor.execute(cadena,values)
    cursor.commit()

    #si siguen habiendo errores es preocupante
    if os.path.exists(errores_file):
        mensaje="Hubo un error al intentar modificar algunos items:"
        messages.send_email(0, mensaje, log_content)



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