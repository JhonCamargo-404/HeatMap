import os
import pandas as pd
import folium
from folium.plugins import HeatMap
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Variable global para almacenar los datos del archivo cargado
data = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global data
    barrios = []

    if request.method == 'POST':
        # Procesar el archivo cargado
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Leer y almacenar el archivo en la variable global `data`
            data = pd.read_csv(filepath)
            
            # Obtener la lista de barrios únicos
            barrios = sorted(data['barrio'].dropna().unique())
            
            # Generar el mapa de calor para toda la ciudad
            heatmap_path = generate_heatmap(data)
            
            # Renderizar la página con el mapa de calor de toda la ciudad y la lista de barrios
            return render_template('index.html', barrios=barrios, heatmap=True)
    
    # Renderizar la página inicial
    return render_template('index.html', barrios=barrios, heatmap=False)

@app.route('/filter', methods=['POST'])
def filter_heatmap():
    global data
    if data is None:
        return redirect(url_for('index'))
    
    # Obtener el barrio seleccionado
    selected_barrio = request.form.get('barrio')
    
    # Filtrar los datos para el barrio seleccionado o mostrar toda la ciudad si no se selecciona ningún barrio
    if selected_barrio and selected_barrio != 'todos':
        data_filtered = data[data['barrio'] == selected_barrio]
    else:
        data_filtered = data
    
    # Generar el mapa de calor filtrado
    generate_heatmap(data_filtered)
    
    # Renderizar la página con el mapa embebido y el filtro de barrios
    barrios = sorted(data['barrio'].dropna().unique())
    return render_template('index.html', barrios=barrios, heatmap=True)

def generate_heatmap(dataframe):
    # Filtrar las coordenadas y crear el mapa de calor
    data_filtered = dataframe[['longitud', 'latitud']].dropna()
    
    # Crear el mapa centrado en Medellín
    mapa_medellin = folium.Map(location=[6.2442, -75.5812], zoom_start=12)
    heat_data = data_filtered[['latitud', 'longitud']].values
    HeatMap(heat_data).add_to(mapa_medellin)
    
    # Guardar el mapa en un archivo HTML para incrustarlo en la página
    heatmap_path = os.path.join(app.config['UPLOAD_FOLDER'], 'heatmap.html')
    mapa_medellin.save(heatmap_path)
    return heatmap_path

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
