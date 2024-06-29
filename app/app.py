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
from threading import Thread, Event, current_thread  
from queue import Queue

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'data_upload')
DIR_ = os.path.join(os.getcwd())
JSON_DATA = os.path.join(os.getcwd(), 'data_output')
ALLOWED_EXTENSIONS = {'txt', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['JSON_DATA'] = JSON_DATA
app.config['DIR_'] = DIR_

# Evento para parar a simulação
stop_event = Event()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_uploaded_files(file1, file2):
    try:
        df1 = pd.read_csv(file1)
        df2 = pd.read_csv(file2)
        return df1, df2
    except Exception as e:
        return None, None

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
    
@app.route('/run_simulation', methods=['POST'])
def run_simulation():
    try:
        num_simulations = int(request.form['num_simulations'])
        # Simulate FIFO queue with random data
        simulated_data = [random.randint(1, 100) for _ in range(num_simulations)]
        return jsonify(simulated_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/random_simulation')
def random_simulation():
    return render_template('random_simulation.html')

@app.route('/run_random_simulation', methods=['POST'])
def run_random_simulation():
    try:
        num_simulations = int(request.form['num_simulations'])
        # Simulate random data
        random_data = [random.randint(1, 100) for _ in range(num_simulations)]
        return jsonify(random_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/evaluation')
def evaluation():
    return render_template('evaluation.html')

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@socketio.on('start_simulation')
def start_simulation(data):
    global stop_event
    stop_event.clear()  # Reseta o evento de parada

    try:
        tc_path = os.path.join(os.getcwd(), 'data_upload', 'tc.txt')
        ts_path = os.path.join(os.getcwd(), 'data_upload', 'ts.txt')

        if not os.path.exists(tc_path) or not os.path.exists(ts_path):
            emit('simulation_error', {'error': 'Files not found'})
            return

        # Ler arquivos .txt como DataFrames
        tc = pd.read_csv(tc_path, header=None, names=['chegada'], delim_whitespace=True, skiprows=1)
        ts = pd.read_csv(ts_path, header=None, names=['servico'], delim_whitespace=True, skiprows=1)

        queue = Queue()

        # Função para adicionar OSs à fila conforme o tempo de chegada
        def adicionar_os():
            start_time = time.time()  # Tempo de início da simulação
            chegada_anterior = 0

            for i in range(len(tc)):
                if stop_event.is_set():
                    break

                try:
                    chegada = float(tc.iloc[i]['chegada'])  # Converter para float
                    servico = float(ts.iloc[i]['servico'])  # Converter para float
                    os_name = f"OS-{i+1}"  # Nome da ordem de serviço

                    # Calcular o tempo absoluto de chegada
                    absolute_chegada = start_time + chegada_anterior + chegada
                    timestamp_chegada = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(absolute_chegada))
                    chegada_anterior += chegada

                    # Esperar até o tempo absoluto de chegada da OS
                    wait_time = absolute_chegada - time.time()
                    if wait_time > 0 and not stop_event.is_set():
                        time.sleep(wait_time)

                    if stop_event.is_set():
                        break

                    # Adicionar OS à fila com status pendente, timestamp de chegada e os_name
                    queue.put((timestamp_chegada, chegada, servico, os_name, 'pending'))

                    # Emitir atualização para exibir na tela
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

        # Thread para adicionar OSs à fila
        thread_adicionar_os = Thread(target=adicionar_os)
        thread_adicionar_os.start()

        # Lista para manter referência aos threads de funcionários
        threads_funcionarios = []

        # Função para simular o atendimento de cada observação
        def atender(funcionario_name):
            while not stop_event.is_set():
                try:
                    if not queue.empty():
                        timestamp_chegada, chegada, servico, os_name, status = queue.get(block=True, timeout=1)
                        if stop_event.is_set():
                            break

                        # Emitir atualização de progresso (status em progresso)
                        socketio.emit('simulation_update', {
                            'os_name': os_name,
                            'timestamp_chegada': timestamp_chegada,
                            'chegada': chegada,
                            'servico': servico,
                            'status': 'in_progress',
                            'funcionario': funcionario_name  # Nome do funcionário atual
                        })

                        # Simular tempo de serviço
                        time.sleep(servico)  # Simulação simples de tempo de serviço

                        if stop_event.is_set():
                            break

                        # Emitir atualização de conclusão (status concluído)
                        socketio.emit('simulation_update', {
                            'os_name': os_name,
                            'timestamp_chegada': timestamp_chegada,
                            'chegada': chegada,
                            'servico': servico,
                            'status': 'completed',
                            'funcionario': funcionario_name  # Nome do funcionário atual
                        })

                        # Indicar que o serviço foi concluído
                        queue.task_done()
                    else:
                        time.sleep(1)  # Aguardar um momento antes de verificar novamente a fila

                except Exception as e:
                    print(f"Exception in thread {funcionario_name}: {type(e).__name__} - {e}")
                    break

        # Criar e iniciar os threads de funcionários
        num_funcionarios = int(data['num_funcionarios'])
        for i in range(num_funcionarios):
            thread = Thread(target=atender, args=(f'{i+1}',))
            thread.start()
            threads_funcionarios.append(thread)

        # Aguardar até a thread de adicionar OSs à fila completar
        thread_adicionar_os.join()

        # Aguardar até todos os threads de funcionários concluírem
        for thread in threads_funcionarios:
            thread.join()

        if not stop_event.is_set():
            # Emitir mensagem de simulação completa
            emit('simulation_complete', {'message': 'Simulação completa'})

    except Exception as e:
        emit('simulation_error', {'error': str(e)})

@socketio.on('stop_simulation')
def stop_simulation():
    global stop_event
    stop_event.set()  # Define o evento de parada
    emit('simulation_complete', {'message': 'Simulação parada pelo usuário'})

if __name__ == '__main__':
    socketio.run(app, debug=True)