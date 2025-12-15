import os
import argparse
import pandas as pd
import connections
import pandas as pd
from objetos import Neumatico, Items
import lectura
import settings as s
os.environ['PYTHONIOENCODING'] = 'utf-8'

def main(idempresa=1):
    s.update_config('GENERAL', 'idempresa', idempresa)

    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    lectura.leer_neums(items_list)

    ml_skus = Items.df.index.get_level_values(0).unique().tolist()

    #que queden solo las que no estan en ml
    df2 = df_db[~df_db['cai'].isin(ml_skus)].copy()

    #es rebuscado pero si no duplico la columna salta un warning
    df2['precio_x2'] = df2['precio'] * 2
    df2['precio_x4'] = df2['precio'] * 4
    df2['precio2_x2'] = df2['precio2'] * 2
    df2['precio2_x4'] = df2['precio2'] * 4

    columnas_ordenadas = [
        'cai',
        'descripcion',
        'precio',
        'precio2',
        'precio_x2',
        'precio2_x2',
        'precio_x4',
        'precio2_x4',
        'existencia',
        'observ'
    ]

    otras_columnas = [col for col in df2.columns if col not in columnas_ordenadas]
    df3 = df2[columnas_ordenadas + otras_columnas] #no se q es esto lo dejo por si acaso?

    df3.to_excel("productos_para_subir.xlsx", index=False)
    print("omg listo")

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