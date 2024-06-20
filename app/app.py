import os
from flask import Flask, request, render_template, jsonify
import subprocess

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '../data'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('../app/templates', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file1 = request.files['file1']
    file2 = request.files['file2']
    if file1.filename == '' or file2.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    file1.save(os.path.join(app.config['UPLOAD_FOLDER'], 'tc.txt'))
    file2.save(os.path.join(app.config['UPLOAD_FOLDER'], 'ts.txt'))
    
    # Chamar o script R para gerar o relatório em HTML na pasta templates
    result = subprocess.run(
        ['Rscript', '-e', "rmarkdown::render('./notebook/Simulador.Rmd', output_format='html_document', output_file='../app/templates/result.html')"], 
        capture_output=True, text=True, cwd='../'
    )
    
    if result.returncode != 0:
        # Capturar e exibir o stderr detalhado
        return jsonify({'error': 'Failed to run R script', 'details': result.stderr}), 500
    
    return jsonify({'success': True, 'message': 'Files processed successfully. You can view the results at /result'})

@app.route('/result')
def show_result():
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
