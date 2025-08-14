import configparser

def create_config():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {}
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def update_config(section, key, value):
    config = configparser.ConfigParser()
    config.read('config.ini')

    if not config.has_section(section):
        config.add_section(section)

    config.set(section, key, str(value))

    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def read_section(section):
    config = configparser.ConfigParser()
    config.read('config.ini')
    if config.has_section(section):
        s = dict(config.items(section))
    else:
        s = {'error' : 'no existe la seccion'}
    return s


def get_config_value(key):
    config = configparser.ConfigParser()
    config.read('config.ini')

    for section in config.sections():
        if key in config[section]:
            return config[section][key]
    
    print(f"key '{key}' no se encontro")
    return None



if __name__ == "__main__":
    create_config()