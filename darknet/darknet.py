import os
import cv2
from dotenvs.load_dotenvs import *

class_names = []

with open("models/coco.txt", "r") as f:
    class_names = [cname.strip() for cname in f.readlines()]

weightsPath_vehicles = os.path.sep.join([os.getenv("DARKNET_WEIGHTS")])
configPath = os.path.sep.join([os.getenv("DARKNET_CONFIG")])

for n in range(1, 3):
    globals()['net%s' % n] = cv2.dnn.readNetFromDarknet(
        configPath, weightsPath_vehicles)
    globals()['net%s' % n].setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    globals()['net%s' % n].setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

    globals()['model%s' % n] = cv2.dnn_DetectionModel(globals()['net%s' % n])
    globals()['model%s' % n].setInputParams(
        size=(416, 416), scale=1/255, swapRB=True)


models = [globals()['model%s' % n] for n in range(1, 3)]
