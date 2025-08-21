import os
import argparse
from dotenv import load_dotenv
import settings as s
import connections
import llamadas

def main(idempresa=1):
    s.update_config('GENERAL', 'idempresa', idempresa)
    conn = connections.start_conn(idempresa)
    connections.get_user(conn)
    load_dotenv()
    APP_ID = os.getenv('APP_ID1')

    response = llamadas.notif_historial(APP_ID)
    print(response.json())


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