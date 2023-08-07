import csv
from datetime import datetime

def print_inf(date, hour, category, type, counter, id, direcao):
    with open('register_csv/registro_camera_'+id+'_' + str(datetime.today().strftime('%d-%m-%Y')) + '.csv', 'a+', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=' ')
        writer.writerow([date, hour, category, type, counter, id, direcao])
