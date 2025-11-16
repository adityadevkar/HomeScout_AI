#libraries
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine # 👈 ADD THIS
import urllib.parse

# Page Configuration
st.set_page_config(
    page_title="Pune Property Insights",
    page_icon="📈",
    layout="wide"
)

# Apply the Custom CSS Theme 
st.markdown("""
<style>
    /* --- Font Import --- */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    /* --- Global Theme --- */
    .stApp {
        background: linear-gradient(160deg, #b57aff 0%, #9333ea 50%, #4c1d95 100%);
        color: white;
        font-family: 'Poppins', sans-serif;
    }

    /* --- Main Title & Subheaders --- */
    h1, h2 {
        color: white;
        text-align: center;
        font-weight: 700;
        text-shadow: 0px 3px 10px rgba(0,0,0,0.3);
    }
    h2 { /* Specific style for subheaders */
        color: #e9d5ff;
        border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
    }
    
    /* --- Metric Boxes --- */
    .stMetric {
        background-color: rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 1rem;
        border-left: 5px solid #d8b4fe;
        backdrop-filter: blur(8px);
    }
    /* Change metric label color */
    .st-emotion-cache-1qg05ue p {
        color: #e9d5ff !important;
    }
</style>
""", unsafe_allow_html=True)

try:
    # Get credentials from Streamlit Secrets
    db_user = st.secrets["db_credentials"]["user"]
    db_pass = st.secrets["db_credentials"]["password"]
    db_host = st.secrets["db_credentials"]["host"]
    db_port = st.secrets["db_credentials"]["port"]
    db_name = st.secrets["db_credentials"]["dbname"]

    # Fix Special Characters in Password
    encoded_pass = urllib.parse.quote_plus(db_pass)

    # Create the connection string
    db_uri = f"postgresql+psycopg2://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

    # Create the engine
    engine = create_engine(db_uri, connect_args={'sslmode': 'require'})

except KeyError:
    st.error("Database credentials not found. Check your .streamlit/secrets.toml file.")
    st.stop()
except Exception as e:
    st.error(f"An error occurred connecting to the database: {e}")
    st.stop()

# Load Data 

def load_data():
    try:
        # Query the database to get all data from the 'searches' table
        df = pd.read_sql("SELECT * FROM searches", engine)
        df['location'] = df['location'].str.title()
        return df
    except Exception as e:
        # If the table doesn't exist yet or another error occurs, return None
        st.error(f"Could not connect to the database: {e}")
        return None

df = load_data()

# Main Page 
st.title("Pune Property Search Insights")

if df is None or df.empty:
    st.warning("No search data available yet. Perform searches on the Home page to see insights.", icon="⚠️")
else:
    # Key Metrics (KPIs) 
    st.subheader("Top-Level Metrics")
    col1, col2, col3 = st.columns(3)
    
    total_searches = len(df)
    most_popular_location = df['location'].mode()[0]
    avg_predicted_price = df['predicted_price_lakhs'].mean()

    col1.metric("Total Searches", f"{total_searches}")
    col2.metric("Most Popular Location", most_popular_location)
    col3.metric("Avg. Predicted Price", f"₹ {avg_predicted_price:,.2f} L")
    
    #  Visualizations 
    
    c1, c2 = st.columns((6, 4))

    with c1:
        # 1 Most Searched Locations
        st.subheader("Top Searched Locations")
        top_locations = df['location'].value_counts().nlargest(10).sort_values(ascending=True)
        fig_locations = px.bar(top_locations, x=top_locations.values, y=top_locations.index, orientation='h', text=top_locations.values)
        
        fig_locations.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#e9d5ff', yaxis_title=None, xaxis_title="Number of Searches",
            xaxis={'gridcolor': 'rgba(255, 255, 255, 0.1)'}
        )
        fig_locations.update_traces(marker_color='#d8b4fe', textfont_color='white')
        st.plotly_chart(fig_locations, use_container_width=True)

    with c2:
        # 2 BHK Distribution
        st.subheader("BHK Distribution")
        bhk_counts = df['bhk'].value_counts()
        fig_bhk = px.pie(bhk_counts, values=bhk_counts.values, names=bhk_counts.index, hole=0.4)
     
        fig_bhk.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', font_color='#e9d5ff',
            legend_font_color='white'
        )
        fig_bhk.update_traces(textinfo='percent+label', marker_colors=['#d8b4fe', '#a855f7', '#9333ea', '#7e22ce', '#4c1d95'])
        st.plotly_chart(fig_bhk, use_container_width=True)

    # 3 Average Price by Location
    st.subheader("Average Predicted Price by Location")
    avg_price_by_loc = df.groupby('location')['predicted_price_lakhs'].mean().nlargest(10).sort_values(ascending=False)
    fig_avg_price = px.bar(avg_price_by_loc, x=avg_price_by_loc.index, y=avg_price_by_loc.values, labels={'x': 'Location', 'y': 'Average Price (in Lakhs)'}, color=avg_price_by_loc.values, color_continuous_scale=px.colors.sequential.Purples)
  
    fig_avg_price.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#e9d5ff', coloraxis_showscale=False,
        yaxis={'gridcolor': 'rgba(255, 255, 255, 0.1)'}
    )
    st.plotly_chart(fig_avg_price, use_container_width=True)

    # 4 Show Raw Data
    with st.expander("📂 View Raw Search Data"):
        st.dataframe(df)