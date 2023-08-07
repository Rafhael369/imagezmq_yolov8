# importe os pacotes necessários
from scipy.spatial import distance as dist
from collections import OrderedDict
import numpy as np


class CentroidTracker:
    def __init__(self, maxDisappeared=50, maxDistance=50):
        # inicializa o próximo ID de objeto exclusivo junto com dois pedidos
        # dicionários usados para acompanhar o mapeamento de um determinado objeto
        # ID para seu centróide e número de quadros consecutivos que possui
        # foi marcado como "desaparecido", respectivamente
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()
        self.bbox = OrderedDict()  # CHANGE

        # armazena o número máximo de quadros consecutivos em um determinado
        # objeto pode ser marcado como "desaparecido" até que
        # precisa cancelar o registro do objeto de rastreamento
        self.maxDisappeared = maxDisappeared

        # armazena a distância máxima entre centroides a associar
        # um objeto -- se a distância for maior que este máximo
        # distância vamos começar a marcar o objeto como "desaparecido"
        self.maxDistance = maxDistance

    def register(self, centroid, inputRect):
        # ao cadastrar um objeto usamos o próximo objeto disponível
        # ID para armazenar o centróide
        self.objects[self.nextObjectID] = centroid
        self.bbox[self.nextObjectID] = inputRect  # CHANGE
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        # ao cadastrar um objeto usamos o próximo objeto disponível
        # ID para armazenar o centróide
        del self.objects[objectID]
        del self.disappeared[objectID]
        del self.bbox[objectID]

    def update(self, rects):
        # verifica se a lista de retângulos da caixa delimitadora de entrada
        # está vazia
        if len(rects) == 0:
            # faz um loop sobre quaisquer objetos rastreados existentes e os marca
            # como desaparecido
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1

                # se atingimos um número máximo de consecutivos
                # quadros onde um determinado objeto foi marcado como
                # faltando, cancele o registro
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)

            # retorna cedo, pois não há centróides ou informações de rastreamento
            # atualizar
            # retorna self.objects
            return self.bbox

        # inicializa uma matriz de centroides de entrada para o quadro atual
        inputCentroids = np.zeros((len(rects), 2), dtype="int")
        inputRects = []
        # loop sobre os retângulos da caixa delimitadora
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            # use as coordenadas da caixa delimitadora para derivar o centróide
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            inputCentroids[i] = (cX, cY)
            inputRects.append(rects[i])  # CHANGE

        # se não estivermos rastreando nenhum objeto no momento, pegue a entrada
        # centróides e registre cada um deles
        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.register(inputCentroids[i], inputRects[i])

        # caso contrário, estão rastreando objetos no momento, então precisamos
        # tente combinar os centróides de entrada com o objeto existente
        # centróides
        else:
            # pegue o conjunto de IDs de objetos e centroides correspondentes
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            # calcula a distância entre cada par de objetos
            # centróides e centróides de entrada, respectivamente -- nosso
            # objetivo será combinar um centróide de entrada com um existente
            # centroide do objeto
            D = dist.cdist(np.array(objectCentroids), inputCentroids)

            # para realizar esta correspondência devemos (1) encontrar o
            # menor valor em cada linha e então (2) classificar a linha
            # índices com base em seus valores mínimos para que a linha
            # com o menor valor na *frente* do índice
            # lista
            rows = D.min(axis=1).argsort()

            # em seguida, realizamos um processo semelhante nas colunas por
            # encontrando o menor valor em cada coluna e então
            # classificação usando a lista de índices de linha computada anteriormente
            cols = D.argmin(axis=1)[rows]

            # para determinar se precisamos atualizar, registrar,
            # ou cancela o registro de um objeto que precisamos para acompanhar qual
            # dos índices de linhas e colunas que já examinamos
            usedRows = set()
            usedCols = set()

            # loop sobre a combinação do índice (linha, coluna)
            # tuplas
            for (row, col) in zip(rows, cols):
                # se já examinamos a linha ou
                # valor da coluna antes, ignore
                if row in usedRows or col in usedCols:
                    continue

                # se a distância entre centroides for maior que
                # a distância máxima, não associe os dois
                # centróides para o mesmo objeto
                if D[row, col] > self.maxDistance:
                    continue

                # caso contrário, pegue o ID do objeto para a linha atual,
                # defina seu novo centróide e redefina o desaparecido
                # contador
                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.bbox[objectID] = inputRects[col]  # CHANGE
                self.disappeared[objectID] = 0

                # indica que examinamos cada uma das linhas e
                # índices de coluna, respectivamente
                usedRows.add(row)
                usedCols.add(col)

            # calcula o índice de linha e coluna que ainda NÃO temos
            # examinado
            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            # caso o número de centróides do objeto seja
            # igual ou maior que o número de centróides de entrada
            # precisamos verificar e ver se algum desses objetos tem
            # potencialmente desaparecido
            if D.shape[0] >= D.shape[1]:
                # loop sobre os índices de linha não utilizados
                for row in unusedRows:
                    # grab the object ID for the corresponding row
                    # index and increment the disappeared counter
                    objectID = objectIDs[row]
                    self.disappeared[objectID] += 1

                    # verifica se o número de consecutivos
                    # frames o objeto foi marcado como "desaparecido"
                    # para mandados de cancelamento de registro do objeto
                    if self.disappeared[objectID] > self.maxDisappeared:
                        self.deregister(objectID)

            # caso contrário, se o número de centróides de entrada for maior
            # do que o número de centroides de objetos existentes que precisamos
            # registra cada novo centróide de entrada como um objeto rastreável
            else:
                for col in unusedCols:
                    self.register(inputCentroids[col], inputRects[col])

        # retorna o conjunto de objetos rastreáveis
        # retorna self.objects
        return self.bbox