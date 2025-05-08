import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import numpy as np

# Load the COVID Data
url = "https://covid.ourworldindata.org/data/owid-covid-data.csv"
covid_df = pd.read_csv(url)

# Clean the Data
cols =["date", "location", "total_cases", "total_deaths", "population", "iso_code"]
covid_df = covid_df[cols].dropna(subset="total_cases")

# Initialize SQLite engine
engine = create_engine('sqlite:///your_database.db')
covid_df.to_sql('covid_data', engine, if_exists='replace', index=False)

# Configure page
st.set_page_config(
    page_title="COVID-19 Dashboard",
    page_icon=":bar_chart:",
    layout="wide"
)


# Load Data from SQLite
@st.cache_data
def load_data():
    return pd.read_sql_query("SELECT * FROM covid_data", engine)


df = load_data()

# Convert date column to datetime
df['date'] = pd.to_datetime(df['date'])

# Sidebar Filters
st.sidebar.title("Filters")
selected_countries = st.sidebar.multiselect(
    "Countries",
    options=df["location"].unique(),
    default=df["location"].unique()[:50:10]
)

min_date = df['date'].min().date()
max_date = df['date'].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Main Dashboard
st.title("COVID-19 Analysis Dashboard")
st.markdown("Interactive analysis of global COVID-19 data")

# Metrics row
col1, col2, col3 = st.columns(3)
with col1:
    total_cases = df["total_cases"].max()
    st.metric("Global Cases", f"{total_cases:,.0f}")

with col2:
    total_deaths = df["total_deaths"].max()
    st.metric("Global Deaths", f"{total_deaths:,.0f}")

with col3:
    avg_death_rate = (df["total_deaths"].sum() / df["total_cases"].sum()) * 100
    st.metric("Global Fatality Rate", f"{avg_death_rate:,.2f}%")

# Filter Data
if len(date_range) == 2:  # Ensure both dates are selected
    filtered_df = df[
        (df["location"].isin(selected_countries)) &
        (df["date"].dt.date.between(*date_range))
        ]
else:
    st.warning("Please select both start and end dates")
    filtered_df = df[df["location"].isin(selected_countries)]

# Interactive Charts
tab1, tab2, tab3 = st.tabs(["Trend Analysis", "Data Explorer", "Map of Cases"])

with tab1:
    if not filtered_df.empty:
        fig = px.line(filtered_df,
                      x="date",
                      y="total_cases",
                      color="location",
                      title="Total Cases Over Time",
                      labels={"total_cases": "Total Cases", "date": "Date"})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Case Fatality Rate")

        # Updated groupby syntax
        grouped_df = filtered_df.groupby("location").agg({
            "total_deaths": "max",
            "total_cases": "max"
        }).reset_index()

        fig2 = px.bar(grouped_df,
                      x="location",
                      y=["total_deaths", "total_cases"],
                      barmode="group",
                      title="Total Deaths vs Total Cases by Country")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No data available for the selected filters")

with tab2:
    st.subheader("Data Explorer")
    st.dataframe(filtered_df, use_container_width=True)

with tab3:
    latest_filtered_df = filtered_df.sort_values('date').groupby('location').last().reset_index()

    if not latest_filtered_df.empty:
        fig_map = px.scatter_geo(latest_filtered_df,
                                 locations="iso_code",
                                 size="total_cases",
                                 hover_name="location",
                                 hover_data="iso_code",
                                 color="Total cases",
                                 color_continuous_scale="Inferno",
                                 projection="natural earth",
                                 title="Global COVID-19 Cases Distribution",
                                 scope="world")

        # Adjust bubble sizing
        fig_map.update_traces(marker=dict(
            sizemode='area',
            sizeref=0.1,
            size=np.log(latest_filtered_df['total_cases'])
        ))

        # Improve map appearance
        fig_map.update_geos(
            showcountries=True,
            countrycolor="Black",
            showocean=True,
            oceancolor="LightBlue",
            showland=True,
            landcolor="WhiteSmoke"
        )

        # Show the figure
        st.plotly_chart(fig_map, use_container_width=True)


# Download button
st.sidebar.download_button(
    label="Download Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_covid_data.csv",
    mime="text/csv"
)
