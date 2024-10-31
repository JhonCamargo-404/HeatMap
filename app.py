import os
import pandas as pd
import folium
from folium.plugins import HeatMap
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import matplotlib
matplotlib.use('Agg')  # Usar backend 'Agg' para evitar problemas de hilos
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Variable global para almacenar los datos del archivo cargado
data = None

# Definir intervalos de horas
time_intervals = {
    "General (Todas las Horas)": (0, 24),
    "Madrugada (00:00-06:00)": (0, 6),
    "Mañana (06:00-12:00)": (6, 12),
    "Tarde (12:00-18:00)": (12, 18),
    "Noche (18:00-24:00)": (18, 24)
}

@app.route('/', methods=['GET', 'POST'])
def index():
    global data
    barrios = []
    disenos = []
    
    if request.method == 'POST':
        # Procesar el archivo cargado
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Leer y almacenar el archivo en la variable global `data`
            data = pd.read_csv(filepath)
            data['hora'] = pd.to_datetime(data['hora'], format='%I:%M %p').dt.hour  # Convertir horas a formato de 24 horas
            
            # Obtener la lista de barrios y diseños únicos
            barrios = sorted(data['barrio'].dropna().unique())
            disenos = sorted(data['diseno'].dropna().unique())
            
            # Generar el mapa de calor para toda la ciudad
            generate_heatmap(data, "heatmap.html")
            
            # Renderizar la página con el mapa de calor de toda la ciudad y las listas de barrios y diseños
            return render_template('index.html', barrios=barrios, disenos=disenos, time_intervals=time_intervals.keys(), heatmap=True)
    
    # Renderizar la página inicial
    return render_template('index.html', barrios=barrios, disenos=disenos, time_intervals=time_intervals.keys(), heatmap=False)

@app.route('/filter', methods=['POST'])
def filter_heatmap():
    global data
    if data is None:
        return redirect(url_for('index'))
    
    # Obtener el barrio, el intervalo de horas y el diseño de vía seleccionados
    selected_barrio = request.form.get('barrio')
    selected_time_interval = request.form.get('time_interval')
    selected_diseno = request.form.get('diseno')
    
    # Filtrar por barrio
    if selected_barrio and selected_barrio != 'todos':
        data_filtered = data[data['barrio'] == selected_barrio]
    else:
        data_filtered = data
    
    # Filtrar por intervalo de horas
    if selected_time_interval and selected_time_interval != "General (Todas las Horas)":
        start_hour, end_hour = time_intervals[selected_time_interval]
        data_filtered = data_filtered[(data_filtered['hora'] >= start_hour) & (data_filtered['hora'] < end_hour)]
    
    # Filtrar por diseño de vía
    if selected_diseno and selected_diseno != 'todos':
        data_filtered = data_filtered[data_filtered['diseno'] == selected_diseno]
    
    # Generar el mapa de calor filtrado
    generate_heatmap(data_filtered, "heatmap.html")
    
    # Generar el gráfico de línea filtrado
    generate_line_chart(data_filtered, "line_chart.png")
    
    barrios = sorted(data['barrio'].dropna().unique())
    disenos = sorted(data['diseno'].dropna().unique())
    title = f"Mapa de Calor de Accidentes - {selected_barrio if selected_barrio != 'todos' else 'Todos los Barrios'} - {selected_time_interval} - {selected_diseno if selected_diseno != 'todos' else 'Todos los Diseños'}"
    
    return render_template('index.html', barrios=barrios, disenos=disenos, time_intervals=time_intervals.keys(), heatmap=True, title=title, selected_barrio=selected_barrio, selected_time_interval=selected_time_interval, selected_diseno=selected_diseno, line_chart=True)

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

def generate_line_chart(dataframe, filename):
    # Agrupar los datos por hora y contar incidentes
    hour_counts = dataframe.groupby('hora').size()

    # Configuración de la figura
    plt.figure(figsize=(12, 8))  # Aumentar tamaño de la figura
    hour_counts.plot(kind='line', marker='o', color='b', linewidth=2, markersize=6)

    # Ajustar el título y etiquetas
    plt.xlabel('Hora', fontsize=14)
    plt.ylabel('Cantidad de Incidentes', fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(True)

    # Guardar el gráfico como archivo en la carpeta de uploads
    chart_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    plt.savefig(chart_path, bbox_inches='tight')  # bbox_inches='tight' asegura que el gráfico se ajuste bien
    plt.close()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
