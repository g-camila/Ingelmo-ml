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
CAMBIOS = {}

def log_change(data, val):
    logging.info(f"{val.titulo}")
    logging.info(f"Sku: {val.sku}")
    if 'price' in data:
        logging.info(f"Precio viejo: {val.precio}")
        logging.info(f"Precio nuevo:{data['price']}")
    if 'available_quantity' in data:
        logging.info(f"Stock viejo: {val.stock}")
        logging.info(f"Stock nuevo:{data['available_quantity']}")
    logging.info(f"{val.link}")
    logging.info("\n")


def check_cat(data, cat, val):
    #preparar el json data!!
    if val.formato_viejo: #no catalogo
        data['id'] = val.variation_id
        data = [data]
        xdata={}
        xdata["variations"] = data
        data = xdata
    return data


def desactivar(col, val):
    if val.status == 'under_review' or val.status == 'closed' or val.stock==0:
        return None
    else:
        data1 = {"available_quantity" : 0}
        data = check_cat(data1, col[1], val)
        if val.stock != 0:
            if val.sku not in CAMBIOS:
                CAMBIOS[val.sku] = {}
            CAMBIOS[val.sku][val.id] = data
            #CAMBIOS[val.sku][val.id]['stock'] = 0

        logging.info(f"{val.titulo}")
        logging.info(f"Sku: {val.sku}")
        logging.info(f"Stock viejo: {val.stock}")
        logging.info(f"Stock nuevo:{0}")
        logging.info(f"{val.link} \n")
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

       
    if stockdb == 1 or stockdb == 2:
        filtro = str(stockdb)
        desact_grupo(sku, [filtro], desc)
    elif stockdb == 3:
        desact_grupo(sku, ["1", "2"], desc)
    
    return desc


#limpiar los repetidos y los items sin trackear en neum
def corregir():
    for sku in Items.repetidos:
        for strdir in Items.repetidos[sku]:
            dir = eval(strdir)
            for val in Items.repetidos[sku][strdir]:
                response = desactivar(dir[1], val)
                messages.handle_error(response, dir, val, 'desact')



def sincro(loc, val):
    if val.status == 'under_review' or val.status == 'closed':
        return
    
    data = {}
    if 'precio' in CAMBIOS:
        precio = CAMBIOS['precio']
        precio2 = CAMBIOS['precio2']
        new_precio = lectura.precio_real(precio, precio2, loc)
        data['price'] = new_precio
    if 'stock' in CAMBIOS:
        stock = CAMBIOS['stock']
        new_stock = lectura.stock_real(stock, loc)
        data['available_quantity'] = new_stock

    catalogo = Items.get_catalogo(loc)
    data2 = check_cat(data, catalogo, val)
    response = llamadas.modificar(val.id, data2)
    messages.handle_error(response, loc, val, 'sincro')
    return


def main(idempresa):
    global CAMBIOS 
    CAMBIOS = {}
    
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
    df_db = connections.get_db()
    items_list = connections.get_items()

    spinner.stop()

    if idempresa == 3:
        incompletos = lectura.leer_neums(items_list)
    else:
        lectura.leer_neums(items_list)

    if idempresa == 1:
        corregir()

    dict_ventas = armar_ventas(idempresa)

    #ahora me tengo que fijar si hay diferencias entre la db y la info de cada uno de mis neum
    ml_skus = Items.df.index.get_level_values(0).unique().tolist()
    db_skus = df_db['cai'].unique().tolist()
    ml_menos_db = list(set(ml_skus) - set(db_skus))
    db_menos_ml = list(set(db_skus) - set(ml_skus))

    comp_precios = []

    length = len(df_db)
    print("\n")
    messages.printProgressBar(0, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)

    
    for i, (index, row) in enumerate(df_db.iterrows(), start=0):
        #fijarse si hay una diferencia entre el precio o stock entre la base d datos y mercado libre
        rsku = row['cai']
        if rsku not in ml_skus:
            messages.printProgressBar(i + 1, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)
            continue  #no existe en ml

        CAMBIOS[rsku] = {}

        #funcion que se fija si el item entra en los requisitos para desactivarlo por default
        dbstock = max(0, int(row['existencia']) - dict_ventas.get(rsku, 0))
        if (idempresa != 3):
            descartados = descarte(row, dbstock)
        dbprecio1 = int(row['precio'])
        dbprecio2 = int(row['precio2'])

        comp_flag = False

        for index, col, val in Items.iterar_sku(rsku):
            #el 99% que sea de catalogo va a significar que esta vinculado
            #lo voy a diferenciar por el 1% que seguro me va a cagar
            loc = [(rsku, index), col]
            catalogo = Items.get_catalogo(loc)
            validez = (val.sincronizada and catalogo) or val.status == 'under_review' or val.status=='closed'

            if validez:
                continue
            if idempresa != 3 and val.id in descartados:
                continue
            if idempresa == 3 and catalogo:
                desactivar(col, val)
                continue
            #if val.id in descartados or (val.sincronizada and catalogo) or val.status == 'under_review' or val.status=='closed':
            #if (val.sincronizada and catalogo) or val.status == 'under_review' or val.status=='closed':
                #continue

            cant = Items.get_cant(loc)
            fpago = Items.get_fpago(loc)
            precio_map = {
                0: dbprecio1,
                1: dbprecio2
            }
            dbprecio = precio_map.get(fpago)*cant
            idbstock = dbstock//cant

            #comparo los precios de mercado libre con la db para ver si tienen sentido
            #por la forma d iterar va a venir primero cantidad de 1
            if comp_flag == False and idempresa == 3:
                comparacion = {'Sku': val.sku, 
                    'Precio_ml': val.precio//cant, 
                    'Precio1': dbprecio1, 
                    'Precio2': dbprecio2,
                    'status' : val.status}
                comp_precios.append(comparacion)
                comp_flag = True

            data = { #ah usaba mapeo para todo
                'price': dbprecio if val.precio != dbprecio else None,
                'available_quantity': idbstock if val.stock != idbstock else None
            }
            data = {k: v for k, v in data.items() if v is not None}

            if not data:
                continue

            #tengo q hacer una asquerosidad aca
            log_change(data, val)

            CAMBIOS[rsku][val.id] = data
            data2 = check_cat(data, catalogo, val)
            response = llamadas.modificar(val.id, data2)
            messages.handle_error(response, loc, val, 'sincro')

        messages.printProgressBar(i + 1, length, prefix = 'Sincronizando items:', suffix = 'Complete', length = 50)
        #not_read.remove(rsku) #los que queden son cosas de la db que no estan en ml
    
    spinner = Spinner()
    spinner.start()

    for sku in ml_menos_db:
        if idempresa == 1:
            desact_grupo(sku)

    CAMBIOS = {sku: val for sku, val in CAMBIOS.items() if val}


    ##control para leandro: todo lo que esta en la db que no esta en ml por falta de sku
    if idempresa == 3:
        ##incompletos
        lectura.check_incompletos(incompletos)
        #db no ml
        #tengo q ver como esta hecho para formatearlo VOLVER ACA
        #db_menos_ml a excel

        df_db_menos_ml = pd.DataFrame(db_menos_ml, columns=["sku"])
        df_db_menos_ml.to_excel('productos_no_ml.xlsx', index=False)

        #pasar comp_precios a df y de ahi a excel
        df_comp = pd.DataFrame(comp_precios)
        df_comp.to_excel("comparar_precios.xlsx", index=False)

    spinner.stop()

    logging.info("Sincronización hecha")

    CAMBIOS_json = json.dumps(CAMBIOS)

    with open('CAMBIOS_output.json', 'w', encoding='utf-8') as outfile:
        json.dump(CAMBIOS, outfile, ensure_ascii=False, indent=2)


    cadena="insert into historial (idempresa,myapplog,status) values (?, ?, ?)"
    values=(idempresa,CAMBIOS_json,'ok')

    cursor = conn.cursor()
    cursor.execute(cadena,values)
    cursor.commit()

    print('\a')



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