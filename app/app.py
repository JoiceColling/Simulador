import simpy
import numpy as np
import pandas as pd
from scipy import stats
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Carregar os dados (ajustar o caminho conforme necessário)
tempo_entre_chegadas = pd.read_csv('../data/tc.txt', delimiter='\t', header=None, names=['tempo_entre_chegadas'], skiprows=1)
tempo_de_servico = pd.read_csv('../data/ts.txt', delimiter='\t', header=None, names=['tempo_de_servico'], skiprows=1)


# Converter para numpy array
tempo_entre_chegadas = tempo_entre_chegadas['tempo_entre_chegadas'].values.astype(float)
tempo_de_servico = tempo_de_servico['tempo_de_servico'].values.astype(float)

# Ajustar distribuições
chegadas_distr = stats.expon.fit(tempo_entre_chegadas)
servico_distr = stats.expon.fit(tempo_de_servico)

def suporte_online(env, num_profissionais, chegadas_params, servico_params, metrics):
    fila = simpy.Resource(env, capacity=num_profissionais)
    
    def atendimento(env, cliente):
        chegada = env.now
        with fila.request() as request:
            yield request
            espera = env.now - chegada
            metrics['espera'].append(espera)
            yield env.timeout(stats.expon.rvs(*servico_params))
    
    cliente = 0
    while True:
        yield env.timeout(stats.expon.rvs(*chegadas_params))
        cliente += 1
        env.process(atendimento(env, cliente))

def run_simulation(num_profissionais, run_time=1000):
    env = simpy.Environment()
    metrics = {'espera': []}
    env.process(suporte_online(env, num_profissionais, chegadas_distr, servico_distr, metrics))
    env.run(until=run_time)
    return metrics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    num_profissionais = int(request.form['num_profissionais'])
    run_time = int(request.form['run_time'])
    metrics = run_simulation(num_profissionais, run_time)
    avg_wait_time = np.mean(metrics['espera'])
    return jsonify(avg_wait_time=avg_wait_time)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
