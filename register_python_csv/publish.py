import random
import os
from dotenvs.load_dotenvs import *
from datetime import datetime
from paho.mqtt import client as mqtt_client
from register_python_csv.print_csv import print_inf

broker = os.getenv("MQTT_BROKER")
port = os.getenv("MQTT_PORT")
client_id = f'sma-{random.randint(0, 10000)}'
username = os.getenv("MQTT_USERNAME")
password = os.getenv("MQTT_PASSWORD")

topics = {
    "Pessoa": os.getenv("TOPICO_CONTAGEM_PESSOA"),
    "Moto": os.getenv("TOPICO_CONTAGEM_MOTO"),
    "Carro": os.getenv("TOPICO_CONTAGEM_CARRO"),
    "Onibus": os.getenv("TOPICO_CONTAGEM_ONIBUS"),
    "Caminhao": os.getenv("TOPICO_CONTAGEM_CAMINHAO")
}

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Conexão com o MQTT Broker feita com sucesso!")
        else:
            print("Conexão com o MQTT Broker não realizada, código de erro: %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    try:
        client.connect(broker, int(port))
        return client, 1
    except:
        return client, 0


def publish(client, counter, category, type, id, direcao):
    msg = str(counter) + " " + str(id) + " " + str(direcao)

    if category in topics and type == "contagem":
        result = client.publish(topics[category], msg)
        if result[0] == 0:
            print(
                f"Tópico: {topics[category]} -> Categoria: {category} -> Mensagem: {msg}")
        else:
            print(f"Erro ao enviar os dados no tópico: -> {topics[category]}")

def run(counter, category, type, id, direcao):
    client = connect_mqtt()
    if client[1] == 1:
        publish(client[0], counter, category, type, id, direcao)
    else:
        print_inf(datetime.today().strftime(
            '%Y-%m-%d'), datetime.today().strftime('%H:%M:%S'), category, type, counter, id, direcao)