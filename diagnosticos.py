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
    lectura.main(idempresa=1)

    neums_dict = {}
    modelos_list = []
    for n in Neumatico.dict.values():
        modelo = {'Sku': n.sku, 
                    'Link': n.link, 
                    'Titulo': n.titulo, 
                    'Linea': n.linea, 
                    'Indice de carga': n.carga, 
                    'Modelo': n.modelo, 
                    'Diametro de llanta' : n.ratio,
                    'Marca' : n.marca,
                    "Diametro": n.diametro,
                    "Ancho": n.ancho,
                    "Tipo de servicio": n.servicio,
                    "Tipo de Terreno": n.terreno,
                    "Tipo de construccion": n.construccion,
                    "Cae" : n.cae}
        modelos_list.append(modelo)
        
        new_neum = {
            'Link': n.link,
            'Titulo': n.titulo,
            'Precio': n.precio,
            'Stock': n.stock,
            'Publicaciones': []
        }
        item_publs = Items.df.loc[n.sku]
        if isinstance(item_publs, pd.DataFrame):
            for index, row in item_publs.iterrows():
                for col, r in row.items():
                    if pd.notnull(r): #quiero evitar los null!!
                        n_publ = {'id': r.id,
                                    'status': r.status,
                                    'cantidad': index,
                                    'forma de pago': 'Sin cuotas' if col[0]=='gold_special' else '6 cuotas',
                                    'catalogo': col[1]}     
                        new_neum['Publicaciones'].append(n_publ)
        neums_dict[n.sku] = new_neum

    with open("modelos_ml.json", "w", encoding="utf-8") as f:
        json.dump(modelos_list, f, indent=4, ensure_ascii=False)

    with open("neums.json", "w", encoding="utf-8") as f:
        json.dump(neums_dict, f, indent=4, ensure_ascii=False)

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