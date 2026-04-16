import pandas as pd
import json
import argparse
import os
from objetos import Neumatico, Items
import lectura
import connections
os.environ['PYTHONIOENCODING'] = 'utf-8'

def main(idempresa=1):
    os.makedirs("diagnosticos", exist_ok=True)
    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    df_db = connections.get_db()
    items_list = connections.get_items()

    lectura.leer_neums(items_list)

    ml_skus = Items.df.index.get_level_values(0).unique().tolist()
    db_skus = df_db['cai'].unique().tolist()
    ml_y_db = list(set(db_skus) & set(ml_skus)) 
    #los neum que estan al mismo tiempo en ml y la db

    neumList = []
    #dos versiones: una con los neum nomas, otra con todos
    for sku in Neumatico.dict.values():
        for sku in ml_y_db:
            row = df_db.loc[df_db['cai'] == sku]
            neum = Neumatico.dict[sku]
            neum = {
                'sku' : neum.sku,
                'stock_ml' : neum.stock,
                'stock_db' : int(row.existencia),
                'precio_ml' : neum.precio,
                'precio_db' : int(row.precio)
            }
            neumList.append(neum)