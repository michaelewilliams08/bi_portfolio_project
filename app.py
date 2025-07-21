
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="NYC 311 Transparency", layout="wide")
st.title("NYC 311 Transparency: Complaint Demand, Backlog, and Help Likelihood")
st.write("Upload your CSV or use the live NYC 311 data (last 5000 rows for demo)")

# Data load
@st.cache_data
def get_data():
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv?$order=created_date%20DESC&$limit=5000"
    df = pd.read_csv(url, parse_dates=["created_date", "closed_date"])
    df['hour'] = df['created_date'].dt.hour
    df['is_closed'] = ~df['closed_date'].isna()
    df['closed_same_day'] = (df['is_closed'] & (df['created_date'].dt.date == df['closed_date'].dt.date)).astype(int)
    df = df.dropna(subset=["latitude", "longitude"])
    return df

uploaded = st.file_uploader("Upload CSV (exported from notebook, or use default)", type="csv")
if uploaded:
    df = pd.read_csv(uploaded, parse_dates=["created_date", "closed_date"])
    if "hour" not in df.columns:
        df['hour'] = df['created_date'].dt.hour
    if "is_closed" not in df.columns:
        df['is_closed'] = ~df['closed_date'].isna()
    if "closed_same_day" not in df.columns:
        df['closed_same_day'] = (df['is_closed'] & (df['created_date'].dt.date == df['closed_date'].dt.date)).astype(int)
    df = df.dropna(subset=["latitude", "longitude"])
else:
    df = get_data()

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    ctype = st.selectbox("Complaint Type", ["All"] + sorted(df['complaint_type'].dropna().unique()))
    borough = st.selectbox("Borough", ["All"] + sorted(df['borough'].dropna().unique()))
    hour = st.selectbox("Hour", ["All"] + sorted(df['hour'].dropna().unique()))

df2 = df.copy()
if ctype != "All":
    df2 = df2[df2['complaint_type'] == ctype]
if borough != "All":
    df2 = df2[df2['borough'] == borough]
if hour != "All":
    df2 = df2[df2['hour'] == int(hour)]

# Pie chart (Complaint Distribution)
st.subheader("Complaint Distribution")
fig_pie = px.pie(df2, names='complaint_type', title='Complaints by Type')
st.plotly_chart(fig_pie, use_container_width=True)

# Bar chart (Backlog and Closure Rate by Borough)
st.subheader("Backlog & Same-Day Closure Rate by Borough")
agg = df2.groupby('borough').agg(
    total=('unique_key', 'count'),
    backlog=('is_closed', lambda x: (~x).sum()),
    pct_closed_same_day=('closed_same_day', 'mean')
).reset_index()
agg['pct_closed_same_day'] = (agg['pct_closed_same_day'] * 100).round(1)
fig_bar = px.bar(
    agg, x='borough', y='backlog', color='pct_closed_same_day',
    color_continuous_scale='RdYlGn', text='pct_closed_same_day',
    title="Open Backlog and % Same-Day Closure"
)
st.plotly_chart(fig_bar, use_container_width=True)

# Map (Complaints colored by Same-Day Closure)
st.subheader("Complaint Map (Color = Same-Day Closure Rate)")
if len(df2) > 0:
    map_fig = px.scatter_mapbox(
        df2, lat="latitude", lon="longitude",
        color="closed_same_day", size_max=12,
        color_continuous_scale="RdYlGn",
        hover_data=["complaint_type", "borough", "is_closed"],
        zoom=10, height=550
    )
    map_fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(map_fig, use_container_width=True)
else:
    st.info("No data for selected filter.")

# Table (Top 10 Backlog)
st.subheader("Top 10 Complaint Locations by Backlog")
top = df2.groupby(['complaint_type', 'borough', 'hour']).agg(
    demand=('unique_key', 'count'),
    backlog=('is_closed', lambda x: (~x).sum()),
    pct_closed_same_day=('closed_same_day', 'mean')
).reset_index()
top['priority_score'] = top['demand'] + top['backlog']
top = top.sort_values(['priority_score', 'backlog'], ascending=[False, False]).head(10)
top['pct_closed_same_day'] = (top['pct_closed_same_day'] * 100).round(1)
st.dataframe(top)

st.caption("Built with Streamlit & Plotly | Data: NYC Open Data")
