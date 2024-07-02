# app/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pandas as pd
import numpy as np
from scipy import stats
import random
import subprocess
import json
from flask_socketio import SocketIO, emit
import time
from threading import Thread, Event
from queue import Queue

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data_upload')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DIR_ = os.path.join(os.getcwd())
JSON_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data_output')
os.makedirs(JSON_DATA, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'csv'}

# Caminhos para os arquivos de dados randômicos
data_folder = os.path.join(os.getcwd(), 'data_output')
random_chegada_path = os.path.join(data_folder, 'random_chegada.txt')
random_servico_path = os.path.join(data_folder, 'random_servico.txt')


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['JSON_DATA'] = JSON_DATA
app.config['DIR_'] = DIR_

# Evento para parar a simulação
stop_event = Event()

# Evento para parar a simulação aleatória
random_stop_event = Event()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_uploaded_files(file1, file2):
    try:
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)
        return df1, df2
    except Exception as e:
        return None, None

# Função para ler médias do arquivo JSON
def read_medias_from_json():
    with open(os.path.join(app.config['JSON_DATA'], 'resultados.json'), 'r') as f:
        dados = json.load(f)
    media_chegada = dados['stats_chegadas'][0]['media']
    media_servico = dados['stats_servico'][0]['media']
    return media_chegada, media_servico

# Função para contar número de linhas em um arquivo
def count_lines(filepath):
    with open(filepath, 'r') as f:
        return sum(1 for line in f)
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/postData', methods=['POST'])
def postData():
    try:
        file1 = request.files['tc']
        file2 = request.files['ts']

        print("Received files:", file1.filename, file2.filename)  # Depuração

        if file1.filename == '' or file2.filename == '':
            return jsonify({'error': 'Please select both files'})

        if file1 and allowed_file(file1.filename) and file2 and allowed_file(file2.filename):
            file1_path = os.path.join(app.config['UPLOAD_FOLDER'], 'tc.txt')
            file2_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ts.txt')
            
            file1.save(file1_path)
            file2.save(file2_path)

            print("Files saved to:", file1_path, file2_path)  # Depuração
            
            return jsonify({'success': 'Files uploaded successfully'})

        return jsonify({'error': 'Allowed file types are txt and csv'})
    except Exception as e:
        print("Error:", e)  # Depuração
        return jsonify({'error': str(e)})
    

@app.route('/upload', methods=['GET'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

@app.route('/result')
def result():
    try:
        # Caminho do arquivo JSON gerado pelo script R
        resultados_path = os.path.join(app.config['JSON_DATA'], 'resultados.json')

        # Verificar se o arquivo existe
        if os.path.exists(resultados_path):
            # Carregar dados do arquivo JSON
            with open(resultados_path, 'r') as f:
                resultados = json.load(f)
        else:
            # Caminho para o script R Markdown
            r_script_path = os.path.join(os.getcwd(), 'notebook', 'Simulador.Rmd')

            # Instalar o pacote rmarkdown, caso não esteja instalado
            subprocess.run(['Rscript', '-e', 'if(!requireNamespace("rmarkdown", quietly = TRUE)) install.packages("rmarkdown")'], check=True)

            # Executar o Rscript para renderizar o Rmd
            result = subprocess.run(['Rscript', '-e', 'rmarkdown::render("notebook/Simulador.Rmd", output_format="html_document", output_file="result.html")'], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"R script failed: {result.stderr}")

            # Carregar dados do arquivo JSON
            with open(resultados_path, 'r') as f:
                
                resultados = json.load(f)

        return render_template('result.html', 
                               stats_chegadas=resultados['stats_chegadas'], 
                               stats_servico=resultados['stats_servico'], 
                               outliers_chegadas=resultados['outliers_chegadas'], 
                               outliers_servico=resultados['outliers_servico'])
    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        return redirect(url_for('index'))
    
@app.route('/reprocess', methods=['POST'])
def reprocess():
    try:
        # Caminho para o script R Markdown
        r_script_path = os.path.join(os.getcwd(), 'notebook', 'Simulador.Rmd')

        # Instalar o pacote rmarkdown, caso não esteja instalado
        subprocess.run(['Rscript', '-e', 'if(!requireNamespace("rmarkdown", quietly = TRUE)) install.packages("rmarkdown")'], check=True)

        # Executar o Rscript para renderizar o Rmd
        result = subprocess.run(['Rscript', '-e', 'rmarkdown::render("notebook/Simulador.Rmd", output_format="html_document", output_file="result.html")'], capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"R script failed: {result.stderr}")

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/random_simulation')
def random_simulation():
    return render_template('random_simulation.html')

@app.route('/evaluation')
def evaluation():
    return render_template('evaluation.html')

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@socketio.on('start_simulation')
def start_simulation(data):
    global stop_event
    stop_event.clear()

    try:
        tc_path = os.path.join(UPLOAD_FOLDER, 'tc.txt')
        ts_path = os.path.join(UPLOAD_FOLDER, 'ts.txt')

        if not os.path.exists(tc_path) or not os.path.exists(ts_path):
            emit('simulation_error', {'error': 'Files not found'})
            return

        tc = pd.read_csv(tc_path, header=None, names=['chegada'], delim_whitespace=True, skiprows=1)
        ts = pd.read_csv(ts_path, header=None, names=['servico'], delim_whitespace=True, skiprows=1)

        queue = Queue()

        def adicionar_os():
            start_time = time.time()
            chegada_anterior = 0

            for i in range(len(tc)):
                if stop_event.is_set():
                    break

                try:
                    chegada = float(tc.iloc[i]['chegada'])
                    servico = float(ts.iloc[i]['servico'])
                    os_name = f"OS-{i+1}"

                    absolute_chegada = start_time + chegada_anterior + chegada
                    timestamp_chegada = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada))
                    chegada_anterior += chegada

                    wait_time = absolute_chegada - time.time()
                    if wait_time > 0 and not stop_event.is_set():
                        time.sleep(wait_time)

                    if stop_event.is_set():
                        break

                    queue.put((absolute_chegada, chegada, servico, os_name, 'pending'))

                    socketio.emit('simulation_update', {
                        'os_name': os_name,
                        'timestamp_chegada': timestamp_chegada,
                        'chegada': chegada,
                        'servico': servico,
                        'status': 'pending'
                    })

                except ValueError as e:
                    print(f"Erro de conversão na linha {i}: {e}")
                    emit('simulation_error', {'error': f'Erro de conversão na linha {i}: {e}'})
                    return

        thread_adicionar_os = Thread(target=adicionar_os)
        thread_adicionar_os.start()

        threads_funcionarios = []

        def atender(funcionario_name):
            while not stop_event.is_set():
                try:
                    if not queue.empty():
                        absolute_chegada, chegada, servico, os_name, status = queue.get(block=True, timeout=1)
                        if stop_event.is_set():
                            break

                        timestamp_atendimento = time.time()
                        tempo_espera = timestamp_atendimento - absolute_chegada

                        socketio.emit('simulation_update', {
                            'os_name': os_name,
                            'timestamp_chegada': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada)),
                            'chegada': chegada,
                            'servico': servico,
                            'status': 'in_progress',
                            'funcionario': funcionario_name,
                            'tempo_espera': tempo_espera
                        })

                        time.sleep(servico)

                        timestamp_conclusao = time.time()
                        tempo_conclusao = timestamp_conclusao - absolute_chegada

                        if stop_event.is_set():
                            break

                        socketio.emit('simulation_update', {
                            'os_name': os_name,
                            'timestamp_chegada': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada)),
                            'chegada': chegada,
                            'servico': servico,
                            'status': 'completed',
                            'funcionario': funcionario_name,
                            'tempo_espera': tempo_espera,
                            'tempo_conclusao': tempo_conclusao
                        })

                        queue.task_done()
                    else:
                        time.sleep(1)

                except Exception as e:
                    print(f"Exception in thread {funcionario_name}: {type(e).__name__} - {e}")
                    break

        num_funcionarios = int(data['num_funcionarios'])
        for i in range(num_funcionarios):
            thread = Thread(target=atender, args=(f'{i+1}',))
            thread.start()
            threads_funcionarios.append(thread)

        thread_adicionar_os.join()

        for thread in threads_funcionarios:
            thread.join()

        if not stop_event.is_set():
            emit('simulation_complete', {'message': 'Simulação completa'})

    except Exception as e:
        emit('simulation_error', {'error': str(e)})


@socketio.on('stop_simulation')
def stop_simulation():
    global stop_event
    stop_event.set()
    emit('simulation_complete', {'message': 'Simulação parada pelo usuário'})

@socketio.on('random_stop_simulation')
def stop_simulation():
    global random_stop_event
    random_stop_event.set()
    emit('random_simulation_complete', {'message': 'Simulação parada pelo usuário'})

def calculate_std_dev_from_json(tipo):
    with open(os.path.join(app.config['JSON_DATA'], 'resultados.json'), 'r') as f:
        dados = json.load(f)
    if tipo == 'chegadas':
        desvio_padrao = dados['stats_chegadas'][0]['desvio_padrao']
    elif tipo == 'servico':
        desvio_padrao = dados['stats_servico'][0]['desvio_padrao']
    return desvio_padrao

@socketio.on('start_random_simulation')
def start_random_simulation(data):
    try:
        if 'num_simulations' not in data:
            emit('simulation_error', {'error': 'num_simulations not found in data'})
            return

        num_simulations = int(data['num_simulations'])

        tc_path = os.path.join(app.config['UPLOAD_FOLDER'], 'tc.txt')
        ts_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ts.txt')

        if not os.path.exists(tc_path) or not os.path.exists(ts_path):
            emit('simulation_error', {'error': 'Files not found'})
            return

        media_chegada, media_servico = read_medias_from_json()
        desvio_padrao_chegada = calculate_std_dev_from_json('chegadas')
        desvio_padrao_servico = calculate_std_dev_from_json('servico')

        random_chegada = np.random.normal(loc=media_chegada, scale=desvio_padrao_chegada, size=num_simulations).astype(int)
        random_servico = np.random.normal(loc=media_servico, scale=desvio_padrao_servico, size=num_simulations).astype(int)

        random_chegada = np.clip(random_chegada, 0, None)
        random_servico = np.clip(random_servico, 0, None)

        with open(os.path.join(app.config['UPLOAD_FOLDER'], 'random_chegada.txt'), 'w') as f_random_chegada:
            for value in random_chegada:
                f_random_chegada.write(f"{value}\n")

        with open(os.path.join(app.config['UPLOAD_FOLDER'], 'random_servico.txt'), 'w') as f_random_servico:
            for value in random_servico:
                f_random_servico.write(f"{value}\n")

        num_funcionarios = int(data['num_funcionarios'])
        simulate_queue(num_simulations, num_funcionarios, random_chegada, random_servico)

        emit('random_simulation_complete', {'message': 'Simulação completa'})
    except Exception as e:
        emit('simulation_error', {'error': str(e)})

def simulate_queue(num_simulations, num_funcionarios, random_chegada, random_servico):
    global random_stop_event
    random_stop_event.clear()

    queue = Queue()

    def adicionar_os():
        start_time = time.time()
        chegada_anterior = 0

        for i in range(len(random_chegada)):
            if random_stop_event.is_set():
                break

            chegada = int(random_chegada[i])
            servico = int(random_servico[i])
            os_name = f"OS-{i+1}"

            absolute_chegada = start_time + chegada_anterior + chegada
            timestamp_chegada = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada))
            chegada_anterior += chegada

            wait_time = absolute_chegada - time.time()
            if wait_time > 0 and not random_stop_event.is_set():
                time.sleep(wait_time)

            if random_stop_event.is_set():
                break

            queue.put((absolute_chegada, chegada, servico, os_name, 'pending'))

            socketio.emit('random_simulation_update', {
                'os_name': os_name,
                'timestamp_chegada': timestamp_chegada,
                'chegada': chegada,
                'servico': servico,
                'status': 'pending'
            })

    thread_adicionar_os = Thread(target=adicionar_os)
    thread_adicionar_os.start()

    threads_funcionarios = []

    def atender(funcionario_name):
        while not random_stop_event.is_set():
            try:
                if not queue.empty():
                    absolute_chegada, chegada, servico, os_name, status = queue.get(block=True, timeout=1)
                    if random_stop_event.is_set():
                        break
                    
                    timestamp_atendimento = time.time()
                    tempo_espera = timestamp_atendimento - absolute_chegada
                    
                    socketio.emit('random_simulation_update', {
                        'os_name': os_name,
                        'timestamp_chegada': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada)),
                        'chegada': chegada,
                        'servico': servico,
                        'status': 'in_progress',
                        'funcionario': funcionario_name,
                        'tempo_espera': tempo_espera
                    })

                    time.sleep(servico)

                    timestamp_conclusao = time.time()
                    tempo_conclusao = timestamp_conclusao - absolute_chegada

                    if random_stop_event.is_set():
                        break

                    socketio.emit('random_simulation_update', {
                        'os_name': os_name,
                        'timestamp_chegada': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada)),
                        'chegada': chegada,
                        'servico': servico,
                        'status': 'completed',
                        'funcionario': funcionario_name,
                        'tempo_espera': tempo_espera,
                        'tempo_conclusao': tempo_conclusao
                    })

                    queue.task_done()
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"Exception in thread {funcionario_name}: {type(e).__name__} - {e}")
                break

    for i in range(num_funcionarios):
        thread = Thread(target=atender, args=(f'{i+1}',))
        thread.start()
        threads_funcionarios.append(thread)

    thread_adicionar_os.join()

    for thread in threads_funcionarios:
        thread.join()

    if not random_stop_event.is_set():
        socketio.emit('random_simulation_complete', {'message': 'Simulação completa'})

@socketio.on('stop_random_simulation')
def stop_random_simulation():
    global random_stop_event 
    random_stop_event.set()
    emit('random_simulation_complete', {'message': 'Simulação parada pelo usuário'})

if __name__ == '__main__':
    socketio.run(app, debug=True)