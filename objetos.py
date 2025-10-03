import pandas as pd

#mepa que no se deberia hacer desde 0 todo esto
#se deberia guardar la ultima version del df y el dict y actualizar nomas
#osea solo sacar o agregar cosas


#la clase de Neumaticos es de cada goma individual
#es unico cada objeto
#se guarda cada uno en una lista
class Neumatico:
    dict = {}

    def __init__(self, item_data):
        self.ratio = None
        self.marca = None
        self.linea = None
        self.carga = None
        self.modelo = None
        self.diametro = None
        self.ancho = None
        self.servicio = None
        self.terreno = None
        self.construccion = None
        self.sku = None
        self.cae = None

        self.id = item_data['id']
        dir_attributes = item_data['attributes']
        for ind in range(len(dir_attributes)):
            atributo = dir_attributes[ind]["id"]
            value = dir_attributes[ind]['value_name']
            match atributo:
                case "AUTOMOTIVE_TIRE_ASPECT_RATIO":
                    self.ratio = value
                case "BRAND":
                    self.marca = value
                case "LINE":
                    self.linea = value
                case "LOAD_INDEX":
                    self.carga = value
                case "MODEL":
                    self.modelo = value
                case "RIM_DIAMETER":
                    self.diametro = value
                case "SECTION_WIDTH":
                    self.ancho = value
                case "SERVICE_TYPE":
                    self.servicio = value
                case "TERRAIN_TYPE":
                    self.terreno = value
                case "TIRE_CONSTRUCTION_TYPE":
                    self.construccion = value
                case _:
                    setattr(self, atributo.lower(), None) 

        catalog = item_data['catalog_listing']

        if not catalog:
            dir_attributes = item_data['variations'][0]['attributes']
            self.velocidad = item_data['variations'][0]['attribute_combinations'][0]['value_name']
            #tengo que ver como esta la velocidad si es que no hay variacion
        else:
            #esta adentro de atributos!!
            for ind in range(len(dir_attributes)):
                atributo = dir_attributes[ind]["id"]
                if atributo == "SPEED_INDEX":
                    self.velocidad = dir_attributes[ind]['value_name']

        for ind in range(len(dir_attributes)):
            atributo = dir_attributes[ind]["id"]
            value = dir_attributes[ind]['value_name']
            match atributo:
                case "SELLER_SKU":
                    self.sku = value
                case "GTIN":
                    self.cae = value

        self.link = item_data['permalink']
        self.titulo = item_data['title']
        self.status = item_data['status']
        self.stock = item_data['available_quantity']
        self.precio = None
        self.precio2 = None
        #self.tienda_oficial = False if item_data['official_store_id'] == None else True
        self.congruente = True

        #hago el dict para q sea mas rapida la busqueda
        Neumatico.dict[self.sku] = self

        #me fijo que el valor q pase sea el correcto
        self.asignar_valido(self.stock, self.sku, "stock")


    def asignar_valido(self, ref_value, dir, mode="precio"):
        #dependiendo de donde vengo el sku puede contener o ser el valor de dir
        #me quedaron confusos los nombres ups
        if mode == "precio":
            sku = Items.get_sku(dir)
            fpago = Items.get_fpago(dir)
            
        if mode == "stock":
            sku = dir

        items_ml = Items.df.loc[sku]

        if mode == "precio":
            if fpago == 0:
                self.precio = ref_value
                items_ml = items_ml.drop('gold_pro', axis=1, level=0, errors='ignore')
            elif fpago == 1:
                self.precio2 = ref_value
                items_ml = items_ml.drop('gold_special', axis=1,level=0, errors='ignore')

        congr = True
        if isinstance(items_ml, pd.DataFrame):
            non_null_count = items_ml.notnull().sum().sum()

            if non_null_count > 1:
                for index, row in items_ml.iterrows():
                    for col, val in row.items():
                        if pd.notnull(val):
                            cant = int(index)
                            if mode == "stock":
                                congr = val.stock * cant in {ref_value, ref_value+1, ref_value-1, 0} or ref_value==0
                            elif mode == "precio":
                                congr = val.precio//cant == ref_value

                            if not congr:
                                break
                    if not congr:
                        break

        if not congr:
            self.congruente = False


    #un control de que el item es congruente con el precio (logico) de los Neum
    #puedo controlar el stock que puede o no ser el stock o uno menos (si es 0 esta bien tambien)
    def validar_item(self, dir, iprecio, istock):
        congruente_p = True
        congruente_s = True
        if not self.congruente:
            return True
        cant = Items.get_cant(dir)
        fpago = Items.get_fpago(dir)
        #lo que viene es feo pero no puedo asumir que solo van a haber dos fpago siempre
        precio_maps = {
            0: 'precio',
            1: 'precio2'
        }
        field = precio_maps.get(fpago)
        nprecio = getattr(self, field, None)
        if nprecio is not None:
            congruente_p = iprecio // cant == nprecio
            
        #ahora controlo el stock, que pueden ser varios valores
        congruente_s = istock*cant in {self.stock, self.stock+1, self.stock-1, 0} and istock >= 0

        self.congruente = congruente_p and congruente_s
        


#la clase item es de cada publicacion de mercado libre,
#hay multiples items por neumatico
#se guarda todo en un dataframe multijerarquico
#las filas indican la cantidad de goma por publicacion (kits, individual)
#las columnas corresponden a si es de tipo normal, catalogo y la forma de pago (por ahora solo hay 2)
class Items:
    #row_tuples = [('sku', '1'), ('sku', '2'), ('sku', '4')]
    row_index = pd.MultiIndex.from_tuples([], names=['sku', 'cantidad'])
    fpago = ['gold_special', 'gold_pro']
    catalogo = [True, False]
    column_index = pd.MultiIndex.from_product([fpago, catalogo], names=['fpago', 'catalogo'])
    df = pd.DataFrame(index=row_index, columns=column_index)

    #direccion del ultimo item agregado
    ultimo_dir = {}
    #items repetidos no deberian existir, habria que actualizarlos igual
    repetidos={}

    #llenar un valor en la tabla
    def __init__(self, item_data):
        self.id = item_data['id']

        dir_attributes = item_data['attributes']
        for ind in range(len(dir_attributes)):
            atributo = dir_attributes[ind]["id"]
            if atributo == "TIRES_NUMBER" or atributo == "UNITS_PER_PACK":
                cant = dir_attributes[ind]['value_name']

        catalog = item_data['catalog_listing']

        self.variation_id = None
        if not catalog:
            dir_attributes = item_data['variations'][0]['attributes']
            self.variation_id = item_data['variations'][0]['id']

        for ind in range(len(dir_attributes)):
            atributo = dir_attributes[ind]["id"]
            value = dir_attributes[ind]['value_name']
            if atributo == "SELLER_SKU":
                self.sku = value
        fpago = item_data["listing_type_id"]
        self.status = item_data['status']
        self.sincronizada = item_data['item_relations'] != []

        #ahora agrego precio y stock            :)
        self.precio = item_data['price']
        self.stock = item_data['available_quantity']

        direccion = [(self.sku, cant), (fpago, catalog)]
        #guardar direccion del ultimo item agregado!!
        Items.ultimo_dir = direccion

        #puede que se repitan los items
        if (self.sku, cant) in Items.df.index:
            #me fijo antes de que no es un espacio ya ocupado
            if not pd.isna(Items.df.loc[direccion[0], direccion[1]]):
                Items.repetidos.setdefault(self.sku, {}).setdefault(str(direccion), []).append(self)
                return

        if self.sku in Neumatico.dict:
            neum = Neumatico.dict[self.sku]
            neum.validar_item(direccion, self.precio, self.stock)

        Items.df.loc[direccion[0], direccion[1]] = self



    #iterar buscando los items correspondientes a un sku
    @classmethod
    def iterar_sku(cls, rsku, filtro=[""]):
        items_ml = cls.df.loc[rsku]
        if filtro != [""]:
            items_ml = items_ml.drop(filtro, errors='ignore')
            
        if isinstance(items_ml, pd.DataFrame):
            for index, row in items_ml.iterrows():
                for col, val in row.items():
                    if pd.notnull(val):
                        yield index, col, val


    #quiero abstraer el tema de la dir pq me da paja
    @classmethod #es una boludez pero me vivo olvidando
    def get_sku(cls, dir):
        return dir[0][0]
    @classmethod
    def get_cant(cls, dir):
        return int(dir[0][1])
    @classmethod
    def get_fpago(cls, dir): #q devuelva numeros necesito q sea mas dinamico
        pago = dir[1][0]
        return cls.fpago.index(pago)
    @classmethod
    def get_catalogo(cls, dir):
        return dir[1][1]
