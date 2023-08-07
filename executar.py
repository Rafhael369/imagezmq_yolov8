import subprocess
import time


def executar_scripts_sequencialmente():
    subprocess.run(["python3", "gerar_pontos.py"])
    subprocess.Popen(["python3", "iniciar_algoritmo.py"])
    time.sleep(3)
    subprocess.Popen(["python3", "iniciar_cameras.py"])


executar_scripts_sequencialmente()
