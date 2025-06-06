import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import geopy.geocoders
import geopandas
import folium
from folium.plugins import MarkerCluster
from streamlit.components.v1 import html
import os

st.session_state.clear()
# path = "./dataset/all_PRSA_Data.csv"
# cleaned_df = pd.read_csv(path)
dataset_path = './dataset'

csv_files = [f for f in os.listdir(dataset_path) if f.endswith('.csv')]

# Load Datasets
dataframes = []
for csv_file in csv_files:
    file_path = os.path.join(dataset_path, csv_file)
    df = pd.read_csv(file_path, index_col=[0])
    dataframes.append(df)
    print(f"Data from file {csv_file}")

df = pd.concat(dataframes, ignore_index=True)

# Cleaning Data
cleaned_placeholder = []
for station in df["station"].unique():
    station_df = df.loc[df["station"] == station]
    for column in df.select_dtypes(include="float64").columns:
        station_df[column] = pd.to_numeric(station_df[column], errors='coerce')
        station_df[column].interpolate(method="linear", limit_direction="forward", inplace=True)
        station_df[column].interpolate(method="linear", limit_direction="backward", inplace=True)
    cleaned_placeholder.append(station_df)

cleaned_df = pd.concat(cleaned_placeholder, ignore_index=True)

wd_mode = cleaned_df["wd"].mode()[0]
cleaned_df["wd"] = cleaned_df["wd"].fillna(wd_mode)
cleaned_df["date"] = pd.to_datetime(cleaned_df[["year", "month", "day", "hour"]])
cleaned_df["rain_cat"] = pd.cut(cleaned_df["RAIN"],
                            bins=[-0.1,0,2.5,7.6,50, cleaned_df["RAIN"].max()],
                            labels=["None", "Light", "Moderate", "Heavy", "Very Heavy"]
                        )

st.title("Analisis dan Visualisasi Data Air Quality")

# Hubungan antara RAIN dengan SO2, NO2, dan PM10
st.subheader("Scatter Plot antara RAIN dengan SO2, NO2, dan PM10")
fig, ax = plt.subplots(figsize=(20, 12))
sns.scatterplot(x="RAIN", y="SO2", hue="rain_cat", data=cleaned_df).set_title("Scatter Plot Kolerasi RAIN dengan SO2")
ax.set_title("Scatter Plot Korelasi RAIN dengan SO2")
st.pyplot(fig)

fig, ax = plt.subplots(figsize=(20, 12))
sns.scatterplot(x="RAIN", y="NO2", hue="rain_cat", data=cleaned_df).set_title("Scatter Plot Kolerasi RAIN dengan NO2")
ax.set_title("Scatter Plot Korelasi RAIN dengan NO2")
st.pyplot(fig)   

fig, ax = plt.subplots(figsize=(20, 12))
sns.scatterplot(x="RAIN", y="PM10", hue="rain_cat", data=cleaned_df).set_title("Scatter Plot Kolerasi RAIN dengan PM10")
ax.set_title("Scatter Plot Korelasi RAIN dengan PM10")
st.pyplot(fig)

st.subheader("Heatmap Korelasi RAIN dengan SO2, NO2, dan PM10")
sub = cleaned_df[["station", "date", "RAIN", "rain_cat","NO2", "SO2", "PM10"]]
data_by_station = sub.groupby('station')

rain_corr_by_station = data_by_station.apply(
    lambda x: pd.Series({
        'rain_no2_corr': x['RAIN'].corr(x['NO2']),
        'rain_so2_corr': x['RAIN'].corr(x['SO2']),
        'rain_pm10_corr': x['RAIN'].corr(x['PM10']),
    }), include_groups=False
)

fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(data=rain_corr_by_station, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5).set_title("Heatmap RAIN dengan SO2, NO2, dan PM10")
ax.set_title("Heatmap Korelasi RAIN dengan SO2, NO2, dan PM10")
st.pyplot(fig)

# Tren Rata-Rata Curah Hujan Tiap Kota
st.subheader("Visualisasi Tren Rata-Rata Curah Hujan Dari Tiap Kota")

# Year range filter
min_year = cleaned_df["year"].min()
max_year = cleaned_df["year"].max()

start_year, end_year = st.slider(
    "Pilih rentang tahun:",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    key="rain_trend_year_filter"
)

filtered_df_by_year = cleaned_df[
    (cleaned_df["year"] >= start_year) & (cleaned_df["year"] <= end_year)
]

sub = filtered_df_by_year[["station", "year","RAIN"]]

rain_by_station = sub.groupby(by="station").agg({
    "RAIN":  ["sum", "mean", "median","min", "max"]
})

rain_by_station.RAIN.reset_index().sort_values(by=["sum"], ascending=False)

rain_per_year = sub.groupby(by=["station", "year"]).agg({
    "RAIN": ["sum", "mean", "median","min", "max"]
})

rain_sum_per_year = (
    rain_per_year
    .RAIN
    .groupby(['station','year'])
    .mean()
    .reset_index()[["station", "year", "sum"]]
) 

rain_sum_per_year.rename(columns={'sum': 'total_rain'}, inplace=True)
if not rain_sum_per_year.empty:
    rain_pivot = rain_sum_per_year.pivot(
        index="year",
        columns="station",
        values="total_rain"
    )

    fig, ax = plt.subplots(figsize=(12,6))
    for station in rain_pivot.columns:
        plt.plot(
            rain_pivot.index,
            rain_pivot[station],
            marker='o',
            label=station
        )

    plt.title(f'Perkembangan Total Curah Hujan Tahun {start_year} - {end_year}')
    plt.xlabel('Tahun')
    plt.ylabel('Total Curah Hujan (mm)')
    if not rain_pivot.empty:
        plt.xticks(rain_pivot.index) # tampilkan tiap tahun
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', ncol=1)
    plt.tight_layout()
    st.pyplot(fig)
else:
    st.write("Tidak ada data untuk rentang tanggal yang dipilih.")

# Persebaran Polusi NO2 pada tahun 2017
st.subheader("Persebaran Jumlah Polusi NO2 di Tiap Kota pada Tahun 2017")
sub = cleaned_df[["station", "year", "NO2"]]

sub_2017 = sub[sub["year"] == 2017]

polution_by_station = sub_2017.groupby(by="station").agg({
    "NO2": ["sum", "mean", "min", "max"],
})


col1, col2 = st.columns(2)
sorted_polution = polution_by_station.NO2.reset_index().sort_values(by="sum", ascending=False)
sorted_polution.reset_index(drop=True, inplace=True)

with col1:
    st.metric("Jumlah NO2 Terbesar", value=sorted_polution["sum"][0])
with col2:
    st.metric("Kota dengan NO2 Terbesar", value=sorted_polution["station"][0])

polution_sum_by_station = polution_by_station.NO2.reset_index()

fig, ax = plt.subplots(figsize=(15,10))
plt.bar(polution_sum_by_station["station"], polution_sum_by_station["sum"], color="skyblue")
plt.xlabel("Station")
plt.ylabel("Jumlah Polus NO2")
plt.title("Jumlah Polusi NO2 untuk Tiap Kota di Tahun 2017")
st.pyplot(fig)

# Visualisasi Geo
st.subheader("Visualisasi Geografi Daerah Terkena Polusi NO2 Tahun 2017")
stations = cleaned_df["station"].unique()
geolocator = geopy.geocoders.Nominatim(user_agent="air_quality")
folium_html = "no2_pollution_map.html"

if not os.path.exists(folium_html):
    data_station = []
    data_lat = []
    data_lon = []

    for station in stations:
        location = geolocator.geocode(station)
        if location is None:
            continue
        data_station.append(station)
        data_lat.append(location.latitude)
        data_lon.append(location.longitude)

    geo_df = pd.DataFrame({
        "Station" : data_station,
        "Latitude" : data_lat,
        "Longitude" : data_lon,
        "NO2" : polution_sum_by_station[polution_sum_by_station["station"] != "Wanshouxigong"]["sum"]
    })

    gdf = geopandas.GeoDataFrame(
        geo_df, geometry=geopandas.points_from_xy(geo_df.Longitude, geo_df.Latitude)
    )

    map_center = [geo_df["Latitude"].mean(), geo_df["Longitude"].mean()]

    mymap = folium.Map(
        location=map_center,      
        zoom_start=6,
        min_zoom=5,
        max_zoom=10
    )
    bounds = [[geo_df["Latitude"].min(), geo_df["Longitude"].min()],
              [geo_df["Latitude"].max(), geo_df["Longitude"].max()]]

    mymap.fit_bounds(bounds)

    marker_cluster = MarkerCluster().add_to(mymap)
    for idx, row in geo_df.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=8,  
            popup=f'{row["Station"]}: {row["NO2"]:.2f} µg/m³',  
            tooltip=f'{row["Station"]}: {row["NO2"]:.2f} µg/m³',
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6
        ).add_to(marker_cluster)
    
    print("Folium html does not exist")
    mymap.save(folium_html)

with open(folium_html, "r") as f:
    map_html = f.read()

html(map_html, height=500)