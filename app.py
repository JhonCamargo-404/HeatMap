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

# Definir intervalos de horas
time_intervals = {
    "Madrugada (00:00-06:00)": (0, 6),
    "Mañana (06:00-12:00)": (6, 12),
    "Tarde (12:00-18:00)": (12, 18),
    "Noche (18:00-24:00)": (18, 24)
}

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
            data['hora'] = pd.to_datetime(data['hora'], format='%I:%M %p').dt.hour  # Convertir horas a formato de 24 horas
            
            # Obtener la lista de barrios únicos
            barrios = sorted(data['barrio'].dropna().unique())
            
            # Generar el mapa de calor para toda la ciudad
            generate_heatmap(data, "heatmap.html")
            
            # Renderizar la página con el mapa de calor de toda la ciudad y la lista de barrios
            return render_template('index.html', barrios=barrios, time_intervals=time_intervals.keys(), heatmap=True)
    
    # Renderizar la página inicial
    return render_template('index.html', barrios=barrios, time_intervals=time_intervals.keys(), heatmap=False)

@app.route('/filter', methods=['POST'])
def filter_heatmap():
    global data
    if data is None:
        return redirect(url_for('index'))
    
    # Obtener el barrio y el intervalo de horas seleccionados
    selected_barrio = request.form.get('barrio')
    selected_time_interval = request.form.get('time_interval')
    
    # Filtrar por barrio
    if selected_barrio and selected_barrio != 'todos':
        data_filtered = data[data['barrio'] == selected_barrio]
    else:
        data_filtered = data
    
    # Filtrar por intervalo de horas
    if selected_time_interval:
        start_hour, end_hour = time_intervals[selected_time_interval]
        data_filtered = data_filtered[(data_filtered['hora'] >= start_hour) & (data_filtered['hora'] < end_hour)]
    
    # Generar el mapa de calor filtrado
    generate_heatmap(data_filtered, "heatmap.html")
    
    # Actualizar la lista de barrios y el título dinámico
    barrios = sorted(data['barrio'].dropna().unique())
    title = f"Mapa de Calor de Accidentes - {selected_barrio if selected_barrio != 'todos' else 'Todos los Barrios'} - {selected_time_interval}"
    return render_template('index.html', barrios=barrios, time_intervals=time_intervals.keys(), heatmap=True, title=title, selected_barrio=selected_barrio, selected_time_interval=selected_time_interval)

def generate_heatmap(dataframe, filename):
    # Filtrar las coordenadas y crear el mapa de calor
    data_filtered = dataframe[['longitud', 'latitud']].dropna()
    
    # Crear el mapa centrado en Medellín
    mapa_medellin = folium.Map(location=[6.2442, -75.5812], zoom_start=12)
    heat_data = data_filtered[['latitud', 'longitud']].values
    HeatMap(heat_data).add_to(mapa_medellin)
    
    # Guardar el mapa en un archivo HTML para incrustarlo en la página
    heatmap_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    mapa_medellin.save(heatmap_path)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
