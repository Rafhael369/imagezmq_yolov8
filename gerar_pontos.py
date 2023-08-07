import os
import cv2
import re
import time
import numpy as np
from dotenv import load_dotenv, dotenv_values

tentativas = 0
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"


def receber_linha(rtsp_cam, id_camera):
    global tentativas
    points, points_final = [], []
    cap = cv2.VideoCapture(rtsp_cam, cv2.CAP_FFMPEG)
    ret, frame = cap.read()
    conectado = False
    if ret:
        conectado = True
        frame = cv2.resize(frame, (416, 416))

        def click_event(event, x, y, flags, params):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

        cv2.namedWindow(id_camera)
        cv2.setMouseCallback(id_camera, click_event)

        while ret:
            cv2.rectangle(frame, (0, 0), (416, 50), (0, 0, 0), -1)
            cv2.putText(frame, "Selecione os pontos", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow(id_camera, frame)

            if cv2.waitKey(25) & 0xFF == ord('q'):
                break

            if len(points) % 4 == 0 and len(points) != 0:
                points_final.append(points.copy())

                for pts in points_final:
                    cv2.polylines(frame, [np.array(pts)], True, (0, 255, 0), 2)
                points.clear()

        points_final.append(id_camera)
        cv2.rectangle(frame, (0, 0), (416, 50), (0, 0, 0), -1)
        cv2.putText(frame, "Pontos selecionados", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow(id_camera, frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            pass

    if conectado == False:
        tentativas += 1
        print("Falha na conexão com o RTSP: " + rtsp_cam)
        print("Tentativa de reconexão em 5 segundos ...")
        time.sleep(5)
        if tentativas <= 2:
            points_final = receber_linha(rtsp_cam, id_camera)
        else:
            points_final = [[(0, 0), (0, 0), (0, 0), (0, 0)], id_camera]

    return points_final


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


def gerar_pontos():
    cameras = ler_cameras_do_arquivo("txt/cameras.txt")

    if len(cameras) > 0:
        # Ler todas as linhas do arquivo de coordenadas em uma lista
        coordenadas_existentes = []
        if os.path.isfile("txt/cameras_coordenadas.txt"):
            with open("txt/cameras_coordenadas.txt", "r") as arquivo:
                coordenadas_existentes = arquivo.read().splitlines()

        primeira_linha = True
        for camera in cameras:

            # Verificar se a câmera já foi selecionada as coordenadas
            camera_id = camera["id"]
            if any(camera_id in linha for linha in coordenadas_existentes):
                print("Pontos já selecionados para a câmera " + camera_id)
            else:
                pontos = receber_linha(camera["rtsp_url"], camera_id)
                if pontos[0] != (0, 0):
                    if primeira_linha:
                        primeira_linha = False
                        with open("txt/cameras_coordenadas.txt", "a") as arquivo:
                            arquivo.write(
                                "\n"+str(pontos[1]) + " " + str(pontos[0]) + "\n")
                    else:
                        with open("txt/cameras_coordenadas.txt", "a") as arquivo:
                            arquivo.write(
                                str(pontos[1]) + " " + str(pontos[0]) + "\n")
                else:
                    print("Pontos não selecionados para a câmera " + camera_id)
    else:
        print("Nenhuma câmera encontrada no arquivo txt/cameras.txt")
    os._exit(1)


gerar_pontos()
