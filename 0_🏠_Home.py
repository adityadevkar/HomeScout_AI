#Required libraries
import streamlit as st
import pickle
import json
import numpy as np
import pandas as pd
import datetime
import os
import urllib.parse
from sqlalchemy import create_engine, text

# --- Page Configuration ---
st.set_page_config(
    page_title="HomeScout AI",
    page_icon="🏠",
    layout="centered"
)

# --- Custom CSS for Styling ---
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

    /* --- Main Title --- */
    h1 {
        color: white;
        text-align: center;
        font-weight: 700;
        text-shadow: 0px 3px 10px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
    }
    
    /* --- Input Field Labels & Metrics --- */
    .st-emotion-cache-1qg05ue p { /* Targets the labels above input fields */
        color: #e9d5ff;
        font-weight: 600;
    }
    .stMetric { /* Styles the prediction result box */
        background-color: rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        padding: 1rem;
        border-left: 5px solid #d8b4fe;
    }

    /* --- Transparent Input Fields --- */
    /* Targets text, number, and selectbox inputs for a consistent look */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 10px;
        color: white;
    }
    /* Styles the text inside inputs */
    input, .st-emotion-cache-1tpl0xr {
        color: white !important;
    }
    
    /* --- Buttons --- */
    .stButton>button {
        background: linear-gradient(90deg, #9333ea, #7e22ce);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.8rem 1.6rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0px 4px 15px rgba(0,0,0, 0.2);
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #a855f7, #9333ea);
        transform: translateY(-2px);
        box-shadow: 0px 6px 20px rgba(147, 51, 234, 0.5);
    }

    /* --- Listing Bar Styles --- */
    .listing-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        background: rgba(255,255,255,0.15);
        border-left: 5px solid #d8b4fe;
        margin-bottom: 1rem;
        color: white;
        text-decoration: none;
        transition: all 0.25s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        backdrop-filter: blur(8px); /* The "glass" effect */
    }
    .listing-bar:hover {
        transform: translateY(-3px) scale(1.02);
        border-left-color: #ffffff;
        box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    }
    .site-info {
        display: flex;
        flex-direction: column;
    }
    .site-name {
        font-weight: 700;
        font-size: 1.15rem;
        color: #fff;
    }
    .listing-location {
        font-size: 0.9rem;
        color: #e9d5ff; /* A lighter purple for secondary text */
    }
    .arrow-icon {
        font-size: 1.5rem;
        font-weight: bold;
        color: #f3e8ff;
    }

</style>
""", unsafe_allow_html=True)

# DATABASE SETUP

db_user = st.secrets["db_credentials"]["user"]
db_pass = st.secrets["db_credentials"]["password"]
db_host = st.secrets["db_credentials"]["host"]
db_port = st.secrets["db_credentials"]["port"]
db_name = st.secrets["db_credentials"]["dbname"]

# Create the connection string for PostgreSQL
db_uri = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Create the engine
engine = create_engine(db_uri, connect_args={'sslmode': 'require'})

def setup_database():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS searches (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                location VARCHAR(255),
                house_type VARCHAR(255),
                area_sqft INT,
                bhk INT,
                predicted_price_lakhs FLOAT
            );
        """))
        conn.commit()


# Load Model and Columns
try:
    with open('pune_house_price_model', 'rb') as f:
        model = pickle.load(f)
    
    with open('columns.json', 'r') as f:
        data = json.load(f)
        model_columns = data['data_columns']

    locations = sorted([col for col in model_columns if col not in ['area', 'bhk', 'apartment', 'independent floor', 'independent house', 'studio apartment', 'villa']])
    house_types = sorted(['apartment', 'independent floor', 'independent house', 'studio apartment', 'villa'])

except FileNotFoundError:
    st.error("Model or column file not found! Ensure 'house_price_model.pkl' and 'columns.json' are in the directory.")
    st.stop()


#  Helper Functions 

def predict_price(area, bhk, location, house_type):
    """Creates the correct input array for the model."""
    try:
        loc_index = model_columns.index(location.lower())
        house_type_index = model_columns.index(house_type.lower())
    except ValueError: return None

    x = np.zeros(len(model_columns))
    x[0], x[1] = area, bhk
    if loc_index >= 0: x[loc_index] = 1
    if house_type_index >= 0: x[house_type_index] = 1
        
    return model.predict([x])[0]

def generate_listing_urls(location, bhk):
    """Generates dynamic URLs for all five requested real estate websites."""
    location_slug = location.lower().replace(' ', '-')
    urls = [
        {"name": "99acres", "url": f"https://www.99acres.com/property-for-sale-in-{location_slug}-pune-ffid?bedroom={bhk}"},
        {"name": "MagicBricks", "url": f"https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom={bhk}&cityName=Pune&localityName={location_slug}"},
        {"name": "Housing.com", "url": f"https://housing.com/in/buy/pune/{location_slug}?BHK={bhk}"},
        {"name": "NoBroker", "url": f"https://www.nobroker.in/property/sale/pune/multiple?search_type=city&city=pune&locality={location_slug}&type={bhk}_BHK"},
        {"name": "PropertyWala", "url": f"https://www.propertywala.com/properties/for-sale/in-{location_slug}-pune"}
    ]
    return urls


# DATABASE-BASED FUNCTION:
def save_user_search(area, bhk, location, house_type, predicted_price):
    """Saves the user's search details to the MySQL database."""
    search_data = {
        'timestamp': datetime.datetime.now(),
        'location': location,
        'house_type': house_type,
        'area_sqft': area,
        'bhk': bhk,
        'predicted_price_lakhs': predicted_price / 100000
    }
    df = pd.DataFrame([search_data])
    
    #  append the data to  'searches' table.
    df.to_sql('searches', con=engine, if_exists='append', index=False)

setup_database()
#  The Streamlit App Interface \

st.title("HomeScout AI 🏠")

st.markdown("Enter property details to get an estimated price and find similar listings from Pune .")

# Using a container for the input form for better visual grouping.
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        location = st.selectbox("📍 Location", options=[loc.title() for loc in locations])
        area = st.number_input("📐 Area (in Sq. Ft.)", min_value=300, max_value=5000, value=1000, step=50)

    with col2:
        house_type = st.selectbox("🏢 House Type", options=[ht.title() for ht in house_types])
        bhk = st.selectbox("🛏️ Bedrooms (BHK)", options=[1, 2, 3, 4, 5], index=1)

if st.button("Predict Price & Find Listings", type="primary", use_container_width=True):
    predicted_price = predict_price(area, bhk, location, house_type)
    
    if predicted_price is not None:
        price_in_lakhs = predicted_price / 100000
        
        st.metric(label="Predicted Price", value=f"₹ {price_in_lakhs:,.2f} Lakhs")
        st.divider()

        # Display Listings in Styled Horizontal Bars 
        st.subheader("Find Similar Properties Online")
        
        listings = generate_listing_urls(location, bhk)
        
        # Loop through the listings and render each one as a styled bar.
        for listing in listings:
            st.markdown(f"""
            <a href="{listing['url']}" target="_blank" class="listing-bar">
                <div class="site-info">
                    <span class="site-name">{listing['name']}</span>
                    <span class="listing-location">Search for {bhk} BHK in {location}</span>
                </div>
                <span class="arrow-icon">→</span>
            </a>
            """, unsafe_allow_html=True)
        

        save_user_search(area, bhk, location, house_type, round(predicted_price,2))