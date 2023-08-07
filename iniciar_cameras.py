import socket
import time
import cv2
import os
import imagezmq
import threading
import queue
import re
import multiprocessing as mp
from register_python_csv.publish import run
from darknet.darknet import *


def mqtt(counter, category, type, id, direcao):
    run(counter, category, type, id, direcao)


def ler_cameras_do_arquivo(nome_arquivo):
    cameras = []
    padrao = r"\['(.*?)'\]"
    with open(nome_arquivo, "r") as arquivo:
        for linha in arquivo:
            resultado = re.findall(padrao, linha)
            if resultado:
                objetos = resultado[0].split("', '")
            url_rtsp, id_camera, direcao = linha.strip().split()[0:3]
            cameras.append({"rtsp_url": url_rtsp, "id": id_camera,
                            "direcao": direcao, "objetos": objetos})
    return cameras


class TrafficCounterServer:
    def __init__(self, cameras_file, ip='localhost', port=5555):
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
        self.cameras = ler_cameras_do_arquivo(cameras_file)
        self.ip = ip
        self.port = port
        self.frames_queues = {camera['id']: mp.Queue(
            maxsize=15) for camera in self.cameras}

    def is_port_open(self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        timeout = 2

        try:
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            return True
        except socket.error:
            return False

    def receive(self, rtsp_cam, id_camera, frames_queue):
        cap = cv2.VideoCapture(rtsp_cam, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 416)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 416)
        # cap.set(cv2.CAP_PROP_FPS, 30)

        for camera in self.cameras:
            if camera['id'] == id_camera:
                camera_selecionada = camera
                break

        while True:
            conectado = False
            ret, frame = cap.read()
            if ret:
                conectado = True
                frame = cv2.resize(frame, (416, 416))
                try:
                    frames_queue.put_nowait([frame, id_camera])
                except queue.Full:
                    pass

            if conectado == False:
                print("Falha na conexão com o RTSP: " + rtsp_cam)
                print("Tentativa de reconexão em 60 segundos ...")

                for categoria in class_names:
                    if categoria in camera_selecionada["objetos"]:
                        threading.Thread(target=mqtt, args=(
                            "-1", categoria, "contagem", id_camera, camera_selecionada["direcao"],)).start()

                time.sleep(60)
                self.receive(rtsp_cam, id_camera, frames_queue)

    def send_images(self, frames_queues):
        sender = imagezmq.ImageSender(
            connect_to=f'tcp://{self.ip}:{self.port}')
        while True:
            for camera_id, frames_queue in frames_queues.items():
                print(frames_queue.qsize())
                try:
                    frame, id_camera = frames_queue.get_nowait()
                    if frame is None:
                        continue
                    sender.send_image(camera_id, frame)
                except queue.Empty:
                    pass

    def process_camera(self, camera):
        rtsp_url = camera["rtsp_url"]
        camera_id = camera["id"]
        frames_queue = self.frames_queues[camera_id]
        self.receive(rtsp_url, camera_id, frames_queue)

    def run(self):
        if self.is_port_open(self.ip, self.port):
            processes = []
            for camera in self.cameras:
                process = mp.Process(
                    target=self.process_camera, args=(camera,))
                process.start()
                processes.append(process)

            time.sleep(2.0)

            send_process = mp.Process(
                target=self.send_images, args=(self.frames_queues,))
            send_process.start()

            for process in processes:
                process.join()

            send_process.join()

        else:
            print(f"A porta {self.port} não está aberta!")


if __name__ == "__main__":
    cameras_file1 = "txt/cameras.txt"
    traffic_counter_server = TrafficCounterServer(cameras_file1, port=5555)

    print("Iniciando contagem de veículos e pedestres...")

    # Criação dos processos para executar os servidores em paralelo
    process1 = mp.Process(target=traffic_counter_server.run)

    # Iniciar os processos
    process1.start()

    # Aguardar os processos terminarem
    process1.join()

    print("Contagem finalizada.")
