import os
import time
import pandas as pd
import folium
from folium.plugins import HeatMap
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import matplotlib
matplotlib.use('Agg')  # Usar backend 'Agg' para evitar problemas de hilos
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['CLEAN_FOLDER'] = os.path.join(os.getcwd(), 'fileClean')
os.makedirs(app.config['CLEAN_FOLDER'], exist_ok=True)

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
            # Leer el archivo directamente en la variable global `data` con codificación ISO-8859-1
            data = pd.read_csv(file, encoding='ISO-8859-1')
            data['hora'] = pd.to_datetime(data['hora'], format='mixed').dt.hour  # Convertir horas detectando formato automáticamente

            # Limpiar los datos
            data = clean_data(data)
            
            # Filtrar por el año más frecuente
            data, dominant_year = filter_by_dominant_year(data)
            
            # Guardar el archivo limpio solo con el año en el nombre
            clean_filename = f"{dominant_year}.csv"
            clean_filepath = os.path.join(app.config['CLEAN_FOLDER'], clean_filename)
            data.to_csv(clean_filepath, index=False, encoding='utf-8')
            
            # Obtener la lista de barrios y diseños únicos
            barrios = sorted(data['barrio'].dropna().unique())
            disenos = sorted(data['diseno'].dropna().unique())
            
            # Generar el mapa de calor y el gráfico de líneas para toda la ciudad
            generate_heatmap(data, "heatmap.html")
            generate_line_chart(data, "line_chart.png")
            
            # Renderizar la página con el mapa de calor y el gráfico de líneas
            return render_template('index.html', barrios=barrios, disenos=disenos, time_intervals=time_intervals.keys(), heatmap=True, line_chart=True)
    
    # Renderizar la página inicial
    return render_template('index.html', barrios=barrios, disenos=disenos, time_intervals=time_intervals.keys(), heatmap=False, line_chart=False)

def clean_data(df):
    # Diccionario de reemplazos
    replacements = {
        'DAÃ‘OS': 'DAÑOS',
        'SÃBADO': 'SÁBADO',
        'MIÃ‰RCOLES': 'MIÉRCOLES',
        "ExpansiÃ³n": "Expansión",
        "Ãrea": "Área",
        "CristÃ³bal": "Cristóbal",
        "AlejandrÃ­a": "Alejandría",
        "EchavarrÃ­a": "Echavarría",
        "SimÃ³n": "Simón",
        "BolÃ­var": "Bolívar",
        "MarÃ­a": "María",
        "Ãngeles": "Ángeles",
        "MÃ³nica": "Mónica",
        "LucÃ­a": "Lucía",
        "InÃ©s": "Inés",
        "FÃ©": "Fé",
        "MartÃ­n": "Martín",
        "MontaÃ±a": "Montaña",
        "LÃ³pez": "López",
        "JosÃ©": "José",
        "JoaquÃ­n": "Joaquín",
        "GermÃ¡n": "Germán",
        "BelÃ©n": "Belén",
        "PlayÃ³n": "Playón",
        "IguanÃ¡": "Iguaná",
        "AburrÃ¡": "Aburrá",
        "MoscÃº": "Moscú",
        "AmÃ©rica": "América",
        "AlcÃ¡zares": "Alcázares",
        "MansiÃ³n": "Mansión",
        "JesÃºs": "Jesús",
        "PaÃºl": "Paúl",
        "HÃ©ctor": "Héctor",
        "GÃ³mez": "Gómez",
        "FÃ¡tima": "Fátima",
        "EstaciÃ³n": "Estación",
        "VelÃ³dromo": "Velódromo",
        "RincÃ³n": "Rincón",
        "CorazÃ³n": "Corazón"
    }
    
    # Aplicar reemplazos a todas las columnas de texto
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip()  # Eliminar espacios adicionales
        df[col] = df[col].replace(replacements, regex=True)
    
    return df

def filter_by_dominant_year(df):
    # Convertir la columna 'fecha' a tipo datetime y extraer el año
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df['año'] = df['fecha'].dt.year
    
    # Calcular la moda del año
    dominant_year = df['año'].mode()[0]
    
    # Filtrar el DataFrame por el año dominante
    df = df[df['año'] == dominant_year]
    
    # Eliminar la columna auxiliar 'año' antes de devolver el DataFrame
    df = df.drop(columns=['año'])
    
    return df, dominant_year

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
    heatmap_path = os.path.join(app.config['CLEAN_FOLDER'], filename)
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

    # Guardar el gráfico como archivo en la carpeta de fileClean
    chart_path = os.path.join(app.config['CLEAN_FOLDER'], filename)
    plt.savefig(chart_path, bbox_inches='tight')  # bbox_inches='tight' asegura que el gráfico se ajuste bien
    plt.close()

@app.route('/fileClean/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['CLEAN_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
