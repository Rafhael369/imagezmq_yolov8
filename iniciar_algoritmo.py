import cv2
import time
import numpy as np
import imagezmq
import re
import threading
from multiprocessing import Process
from register_python_csv.publish import run
from centroidtracker import CentroidTracker
from shapely.geometry import Polygon, Point, LineString
from darknet.darknet import *
from dotenvs.load_dotenvs import *
from ultralytics import YOLO


class TrafficCounter:
    def __init__(self, cameras_file, lines_file, ip_hub, model_index):
        self.COLORS = [(0, 255, 255), (255, 255, 0), (0, 255, 0), (255, 0, 0)]
        self.camera_names = []
        self.cameras = self.ler_cameras_do_arquivo(cameras_file)
        self.linhas = self.ler_linhas_do_arquivo(lines_file)
        self.tracker = {name: CentroidTracker(
            maxDisappeared=5, maxDistance=50) for name in self.camera_names}
        self.image_hub = imagezmq.ImageHub(open_port=ip_hub)
        self.model = YOLO("best.pt")
        self.lista_centro_por_camera = {name: [] for name in self.camera_names}
        self.contador = {name: 0 for name in self.camera_names}
        self.objects = {name: None for name in self.camera_names}
        self.boxes_do_poligono = {name: [] for name in self.camera_names}
        self.objetos_rastreados_id = {name: set()
                                      for name in self.camera_names}
        self.objeto_contado = {name: None for name in self.camera_names}
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD"))
        self.nms_threshold = float(os.getenv("NMS_THRESHOLD"))
        self.start_time_per_camera = {
            name: time.time() for name in self.camera_names}

    def mqtt(self, counter, category, type, id, direcao):
        run(counter, category, type, id, direcao)

    def ler_cameras_do_arquivo(self, nome_arquivo):
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

    def ler_linhas_do_arquivo(self, nome_arquivo):
        linhas = {}
        coordenadas = ""
        with open(nome_arquivo, "r") as arquivo:
            for linha in arquivo:
                dados_camera = linha.strip().split(" ")
                id_camera = dados_camera[0]
                self.camera_names.append(id_camera)
                coordenadas = ' '.join(dados_camera[1:])
                linhas[id_camera] = eval(coordenadas)
                coordenadas = ""
        return linhas

    def is_point_in_polygon(self, point, polygon):
        point = Point(point)
        polygon = Polygon(polygon)
        return polygon.contains(point)

    def process_frame(self, rpi_name, image):
        start_time = time.time()
        for camera in self.cameras:
            if camera['id'] == rpi_name:
                camera_selecionada = camera
                break

        results = self.model.predict(source=image, imgsz=416, show=False, )

        self.lista_centro_por_camera[rpi_name].clear()

       # Check if there are any detections
        if len(results[0].boxes.data) > 0:
            for box in results[0].boxes.data:
                x1, y1, x2, y2, score, class_id = box
                color = self.COLORS[int(class_id) % len(self.COLORS)]
                if score > self.confidence_threshold:

                    # Ensure class_id is within the valid range
                    label = str(class_names[int(class_id)])
                    centro_box = (int((x1 + x2) / 2), int((y1 + y2) / 2))

                    cv2.rectangle(image, (int(x1), int(y1)),
                                  (int(x2), int(y2)), color, 1)
                    cv2.putText(
                        image, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    cv2.circle(image, centro_box, 5, color, -1)

                    if self.is_point_in_polygon(centro_box, self.linhas[rpi_name]) and label in camera_selecionada['objetos']:
                        self.boxes_do_poligono[rpi_name].append(
                            [int(x1), int(y1), int(x2), int(y2)])

                    self.lista_centro_por_camera[rpi_name].append(centro_box)

        self.objects[rpi_name] = self.tracker[rpi_name].update(
            self.boxes_do_poligono[rpi_name])
        self.boxes_do_poligono[rpi_name] = []

        for (objectId, bbox) in self.objects[rpi_name].items():
            cv2.putText(image, "ID: {}".format(objectId), (bbox[0] + 50, bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 0, 0), 1)

        for (objectId, bbox) in self.objects[rpi_name].items():
            centro_objeto = (int((bbox[0] + bbox[2]) / 2),
                             int((bbox[1] + bbox[3]) / 2))
            linha = LineString(self.linhas[rpi_name])

            if self.is_point_in_polygon(centro_objeto, self.linhas[rpi_name]) and linha.distance(Point(centro_objeto)) < 10:
                if objectId not in self.objetos_rastreados_id[rpi_name]:
                    self.objetos_rastreados_id[rpi_name].add(objectId)
                    self.contador[rpi_name] += 1

                    # for (classid, score, box) in zip(classes, scores, boxes):
                    #     centro_box = (
                    #         int((box[0] + (box[2] / 2))), int((box[1] + (box[3]) / 2)))
                    #     if centro_box == centro_objeto:
                    #         self.objeto_contado[rpi_name] = str(
                    #             class_names[classid])
                    #         break

                    for box in results[0].boxes.data:
                        x1, y1, x2, y2, score, class_id = box

                        if score > self.confidence_threshold:
                            centro_box = (int((x1 + x2) / 2),
                                          int((y1 + y2) / 2))
                            if centro_box == centro_objeto:
                                self.objeto_contado[rpi_name] = str(
                                    class_names[int(class_id)])
                                break

                    threading.Thread(target=self.mqtt, args=(
                        "1", self.objeto_contado[rpi_name], "contagem", rpi_name, camera_selecionada['direcao'],)).start()

        cv2.polylines(image, np.array(
            [self.linhas[rpi_name]]), True, (0, 0, 0), 2)
        cv2.rectangle(image, (0, 0), (416, 40), (0, 0, 0), -1)
        cv2.putText(image, "Passagens: " + str(self.contador[rpi_name]), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (38, 171, 58), 2)

        end_time = time.time()
        elapsed_time = end_time - self.start_time_per_camera[rpi_name]

        fps = 1.0 / elapsed_time if elapsed_time > 0 else 0.0
        print(f"FPS ({rpi_name}): {fps:.2f}")

        self.start_time_per_camera[rpi_name] = time.time()

        # cv2.namedWindow(rpi_name, cv2.WINDOW_NORMAL)
        cv2.imshow(rpi_name, image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False

        self.image_hub.send_reply(b'OK')

        if len(self.objetos_rastreados_id[rpi_name]) > 3:
            self.objetos_rastreados_id[rpi_name].clear()
            self.contador[rpi_name] -= 1

        return True

    def run(self):
        while True:
            rpi_name, image = self.image_hub.recv_image()
            if not self.process_frame(rpi_name, image):
                break

        self.image_hub.close()


def start_counter(cameras, coordenadas, ip, modelo):
    counter = TrafficCounter(cameras, coordenadas, ip, model_index=modelo)
    counter.run()


if __name__ == "__main__":
    Process(target=start_counter, args=("txt/cameras.txt",
            "txt/cameras_coordenadas.txt", 'tcp://*:5555', 0,)).start()

    # Process(target=start_counter, args=("txt/cameras2.txt",
    #         "txt/cameras_coordenadas2.txt", 'tcp://*:5556', 1,)).start()
