import os
import time
import pandas as pd
import folium
from folium.plugins import HeatMap
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['CLEAN_FOLDER'] = os.path.join(os.getcwd(), 'fileClean')
os.makedirs(app.config['CLEAN_FOLDER'], exist_ok=True)

data = None
all_data_file = os.path.join(app.config['CLEAN_FOLDER'], 'AllData.csv')

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
    periodos = []
    
    if request.method == 'POST':
        # Procesar el archivo cargado
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            data = pd.read_csv(file, encoding='ISO-8859-1')
            data['hora'] = pd.to_datetime(data['hora'], format='mixed').dt.hour 
            data = clean_data(data)
            data, dominant_year = filter_by_dominant_year(data)
            clean_filename = f"{dominant_year}.csv"
            clean_filepath = os.path.join(app.config['CLEAN_FOLDER'], clean_filename)
            data.to_csv(clean_filepath, index=False, encoding='utf-8')
            save_to_all_data(data)
    
    # Leer desde AllData.csv para mostrar datos y generar gráficos
    if os.path.exists(all_data_file):
        data = pd.read_csv(all_data_file, encoding='utf-8', on_bad_lines='skip')
        barrios = sorted(data['barrio'].dropna().unique())
        disenos = sorted(data['diseno'].dropna().unique())
        periodos = sorted(data['periodo'].dropna().unique())
        generate_heatmap(data, "heatmap.html")
        generate_line_chart(data, "line_chart.png")
        return render_template('index.html', barrios=barrios, disenos=disenos, periodos=periodos, time_intervals=time_intervals.keys(), heatmap=True, line_chart=True)

    return render_template('index.html', barrios=barrios, disenos=disenos, periodos=periodos, time_intervals=time_intervals.keys(), heatmap=False, line_chart=False)

def clean_data(df):
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
    
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip()  
        df[col] = df[col].replace(replacements, regex=True)
    
    return df

def filter_by_dominant_year(df):
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df['año'] = df['fecha'].dt.year
    dominant_year = df['año'].mode()[0]
    df = df[df['año'] == dominant_year]
    df = df.drop(columns=['año'])
    return df, dominant_year

@app.route('/filter', methods=['POST'])
def filter_heatmap():
    global data
    if not os.path.exists(all_data_file):
        return redirect(url_for('index'))

    data = pd.read_csv(all_data_file, encoding='utf-8', on_bad_lines='skip')
    selected_barrio = request.form.get('barrio')
    selected_time_interval = request.form.get('time_interval')
    selected_diseno = request.form.get('diseno')
    selected_periodo = request.form.get('periodo')

    # Filtro por año específico o todos los años
    if selected_periodo and selected_periodo != "todos":
        data = data[data['periodo'] == int(selected_periodo)]

    if selected_barrio and selected_barrio != 'todos':
        data = data[data['barrio'] == selected_barrio]

    if selected_time_interval and selected_time_interval != "General (Todas las Horas)":
        start_hour, end_hour = time_intervals[selected_time_interval]
        data = data[(data['hora'] >= start_hour) & (data['hora'] < end_hour)]

    if selected_diseno and selected_diseno != 'todos':
        data = data[data['diseno'] == selected_diseno]

    # Generar mapa de calor y gráfico con los datos filtrados
    generate_heatmap(data, "heatmap.html")
    generate_line_chart(data, "line_chart.png")
    
    barrios = sorted(data['barrio'].dropna().unique())
    disenos = sorted(data['diseno'].dropna().unique())
    periodos = sorted(data['periodo'].dropna().unique())
    title = f"Mapa de Calor de Accidentes - {selected_periodo if selected_periodo != 'todos' else 'Todos los Años'} - {selected_barrio if selected_barrio != 'todos' else 'Todos los Barrios'} - {selected_time_interval} - {selected_diseno if selected_diseno != 'todos' else 'Todos los Diseños'}"
    
    # Incluir selected_periodo para mantener el filtro activo en la interfaz
    return render_template('index.html', barrios=barrios, disenos=disenos, periodos=periodos, time_intervals=time_intervals.keys(), heatmap=True, title=title, selected_barrio=selected_barrio, selected_time_interval=selected_time_interval, selected_diseno=selected_diseno, selected_periodo=selected_periodo, line_chart=True)

def generate_heatmap(dataframe, filename):
    data_filtered = dataframe[['longitud', 'latitud']].dropna()
    mapa_medellin = folium.Map(location=[6.2442, -75.5812], zoom_start=12)
    heat_data = data_filtered[['latitud', 'longitud']].values
    HeatMap(heat_data).add_to(mapa_medellin)
    heatmap_path = os.path.join(app.config['CLEAN_FOLDER'], filename)
    mapa_medellin.save(heatmap_path)

def generate_line_chart(dataframe, filename):
    hour_counts = dataframe.groupby('hora').size()
    plt.figure(figsize=(12, 8)) 
    hour_counts.plot(kind='line', marker='o', color='b', linewidth=2, markersize=6)
    plt.xlabel('Hora', fontsize=14)
    plt.ylabel('Cantidad de Incidentes', fontsize=14)
    plt.grid(True)
    chart_path = os.path.join(app.config['CLEAN_FOLDER'], filename)
    plt.savefig(chart_path, bbox_inches='tight')  
    plt.close()

def save_to_all_data(data):
    if os.path.exists(all_data_file):
        existing_data = pd.read_csv(all_data_file, encoding='utf-8')
        # Concatena los datos nuevos y existentes, eliminando duplicados
        data = pd.concat([existing_data, data]).drop_duplicates()
    
    # Guardar el archivo actualizado sin duplicados
    data.to_csv(all_data_file, index=False, encoding='utf-8')

@app.route('/fileClean/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['CLEAN_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
