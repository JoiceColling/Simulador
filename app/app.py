# app/app.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pandas as pd
import numpy as np
from scipy import stats
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'data')
ALLOWED_EXTENSIONS = {'txt', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_statistics(data):
    return {
        'media': np.mean(data),
        'mediana': np.median(data),
        'moda': float(stats.mode(data)[0]),
        'desvio_padrao': np.std(data),
        'maximo': np.max(data),
        'minimo': np.min(data)
    }

def identify_outliers(data):
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = [x for x in data if x < lower_bound or x > upper_bound]
    return outliers

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

@app.route('/postData', methods=['POST'])
def postData():
    try:
        file1 = request.files['file1']
        file2 = request.files['file2']

        if file1.filename == '' or file2.filename == '':
            return jsonify({'error': 'Please select both files'})

        if file1 and allowed_file(file1.filename) and file2 and allowed_file(file2.filename):
            file1.save(os.path.join(app.config['UPLOAD_FOLDER'], 'file1.csv'))
            file2.save(os.path.join(app.config['UPLOAD_FOLDER'], 'file2.csv'))
            
            flash('Files uploaded successfully', 'success')
            return jsonify({'success': 'Files uploaded successfully'})

        return jsonify({'error': 'Allowed file types are txt and csv'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/upload', methods=['GET'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

@app.route('/result')
def result():
    file1_path = os.path.join(app.config['UPLOAD_FOLDER'], 'file1.txt')
    file2_path = os.path.join(app.config['UPLOAD_FOLDER'], 'file2.txt')

    try:
        df1 = pd.read_csv(file1_path)
        df2 = pd.read_csv(file2_path)

        # Perform statistical analysis
        data1 = df1['x']
        data2 = df2['x']

        stats1 = calculate_statistics(data1)
        stats2 = calculate_statistics(data2)

        outliers1 = identify_outliers(data1)
        outliers2 = identify_outliers(data2)

        return render_template('result.html', stats1=stats1, stats2=stats2, outliers1=outliers1, outliers2=outliers2)

    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        return redirect(url_for('result'))

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

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

if __name__ == '__main__':
    app.run(debug=True)
