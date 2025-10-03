import pandas as pd
import json
import argparse
import os
from objetos import Neumatico, Items
import lectura
os.environ['PYTHONIOENCODING'] = 'utf-8'

#este archivo es para hacer diagnosticos!!
#cualquier cosa que nos queramos fijar y logear la hacemos desde aca
#por ahora solo registro todos los items y todos la info de los modelos de gomas que tenemos

def main(idempresa=1):
    os.makedirs("diagnosticos", exist_ok=True)

    lectura.main(idempresa)
    congr_lectura = []
    congr_diagn = []
    incongr = {}

    for n in Neumatico.dict.values():
        sku = n.sku

        if not n.congruente:
            congr_lectura.append(sku)

        items_ml = Items.df.loc[sku]

        if isinstance(items_ml, pd.DataFrame):
            non_null_count = items_ml.notnull().sum().sum()

            if non_null_count > 1:
                for index, row in items_ml.iterrows():
                    for col, val in row.items():
                        if col[0] == 'gold_special':
                            ref_precio = n.precio
                        elif col[0] == 'gold_pro':
                            ref_precio = n.precio2
                        if pd.notnull(val):
                            if val.stock == 0 or n.stock == 0:
                                continue
                            cant = int(index)
                            congr_s = val.stock*cant in {n.stock, n.stock+1, n.stock-1, 0} or n.stock == 0
                            congr_p = val.precio // cant == ref_precio
                            if not (congr_s and congr_p):
                                if sku not in incongr:
                                    incongr[sku] = {}
                                    congr_diagn.append(sku)
                                    incongr[sku]['fue leido'] = not n.congruente
                                if not congr_p:
                                    if 'precio' not in incongr[sku]:
                                        incongr[sku]['precio']={}
                                    incongr[sku]['precio']['deberia valer'] = n.precio*cant
                                    incongr[sku]['precio']['error'] = val.precio
                                if not congr_s:
                                    if 'stock' not in incongr[sku]:
                                        incongr[sku]['stock']={}
                                    incongr[sku]['stock']['deberian haber'] = n.stock//cant
                                    incongr[sku]['stock']['error'] = val.stock

    #comparar lista de incongruencias de la lectura y del diagnostico de ahora
    incongr['lista de la lectura:'] = len(congr_lectura)
    incongr['lista del diagnostico:'] = len(congr_diagn)
    with open("diagnosticos/incongruencias.json", "w", encoding="utf-8") as f:
        json.dump(incongr, f, indent=4, ensure_ascii=False)




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