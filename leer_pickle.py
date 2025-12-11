import pickle

# Ruta al archivo pickle
ruta_archivo = 'C:\\fuentes\\pickled_lectura.pk1'

objs = []
#esto esta preparado para leer un stream
#el problema es q no se que poronga estoy leyendo
#por ahora en 0 esta el df, en 1 los repetidos
#mas hardcodeado no podia ser
with open(ruta_archivo, "rb") as f:
    while 1:
        try:
            objs.append(pickle.load(f))
        except EOFError:
            break

print("contenido:")
