import configparser
import os

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

#no se si me sirve tanto tener algo asi
def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')

    access_token = config.get('General', 'access_token')
    user_id = config.get('Database', 'user_id')
    idempresa = config.get('Database', 'idempresa')
    recargo = config.get('Database', 'recargo')
    macdena = config.get('Database', 'mcadena')
    mclient_id = config.get('Database', 'mclient_id')
    mclient_secret = config.get('Database', 'mclient_secret')
    mvista = config.get('Database', 'mclient_secret')

    config_values = {
        'access_token': access_token,
        'user_id': user_id,
        'idempresa': idempresa,
        'recargo': recargo,
        'mcadena' : macdena,
        'mclient_id' : mclient_id,
        'mclient_secret' : mclient_secret,
        'mvista' : mvista

    }
    return config_values

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
    
    print(f"Key '{key}' not found in any section.")
    return None


    

if __name__ == "__main__":
    create_config()