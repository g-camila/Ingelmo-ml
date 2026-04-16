import os
import argparse
from dotenv import load_dotenv
import settings as s
from objetos import Items, Neumatico
import connections
import messages
import requests
import json
import llamadas
import lectura
import messages
import pandas as pd

def main(idempresa = 3):
    comparar_db(3)

def tech_specs(idempresa):
    #conn = connections.start_conn(idempresa)
    #connections.get_user(conn)
    response = llamadas.tech_specs('MLA22195')
    data = response.json()
    with open("test.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

    specs_attrs = data['groups'][0]['components']
    required_attrs = []

    for attribute in specs_attrs:
        attrs = attribute['attributes'][0]
        id = attrs['id']
        if 'required' in attrs['tags']:
            required_attrs.append(id)
    
    print(required_attrs)
    
def info_user(idempresa = 4):
    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    response = llamadas.get_user_info()
    print(response.json())

def todos_neums(idempresa = 1):
    #dataframe y json
    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    lectura.leer_neums(items_list)

    #hacer un json grande
    

def comparar_db(idempresa):
    s.update_config('GENERAL', 'idempresa', idempresa)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    lectura.leer_neums(items_list)

    ml_skus = Items.df.index.get_level_values(0).unique().tolist()
    db_skus = df_db['cai'].unique().tolist()
    ml_menos_db = list(set(ml_skus) - set(db_skus))
    db_menos_ml = list(set(db_skus) - set(ml_skus))
    ml_y_db = list(set(db_skus) & set(ml_skus))

    list_items = []
    for sku in ml_y_db:
        for index, col, val in Items.iterar_sku(sku):
            item_info = {'sku':sku,
                    'id' : val.id,
                    'status' : True if val.status=='active' else False,
                    'link' : val.link}
            list_items.append(item_info)

    df_ml_y_db = pd.DataFrame(list_items)
    df_ml_y_db.rename(columns={"status": "activo"}, inplace=True)

    list_items2 = []
    for sku in ml_menos_db:
        for index, col, val in Items.iterar_sku(sku):
            item_info = {'sku':sku,
                    'id' : val.id,
                    'status' : True if val.status=='active' else False,
                    'link' : val.link}
            list_items2.append(item_info)

    df_ml_menos_db = pd.DataFrame(list_items2)
    df_ml_menos_db.rename(columns={"status": "activo"}, inplace=True)

    df_db_menos_ml = pd.DataFrame({'db_menos_ml': db_menos_ml})
    #df_ml_y_db = pd.DataFrame({'ml_y_db': list_items}, columns=["sku", "id", "activo", "link"])

    # Crear un Excel con varias hojas
    with pd.ExcelWriter("sku_comparisons.xlsx", engine="xlsxwriter") as writer:
        df_ml_menos_db.to_excel(writer, sheet_name="Sku en ml no en la db", index=False)
        df_db_menos_ml.to_excel(writer, sheet_name="Cai en la db no en ml", index=False)
        df_ml_y_db.to_excel(writer, sheet_name="Sku en ml y en la db", index=False)


    

            




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