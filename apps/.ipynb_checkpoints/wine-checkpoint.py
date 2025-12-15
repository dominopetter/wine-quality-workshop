import streamlit as st
import requests
import os
import json
import plotly.graph_objects as go

# Define the prediction function
def get_prediction(density, volatile_acidity, chlorides, is_red, alcohol):
    # Get credentials from environment variables
    api_url = os.getenv("API_URL")
    username = os.getenv("API_USERNAME")
    password = os.getenv("API_PASSWORD")

    if not api_url:
        st.error("API_URL environment variable is not set.")
        return None

    # Construct Payload
    # Note: We format floats to 2 decimal places as strings to match the R sprintf logic
    payload = {
        "data": {
            "density": f"{density:.2f}",
            "volatile_acidity": f"{volatile_acidity:.2f}",
            "chlorides": f"{chlorides:.2f}",
            "is_red": int(is_red),
            "alcohol": f"{alcohol:.2f}"
        }
    }

    try:
        response = requests.post(
            api_url,
            auth=(username, password),
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if response is valid JSON
        try:
            result = response.json()
            return result
        except json.JSONDecodeError:
            st.error("API did not return valid JSON.")
            st.write(response.text)
            return None

    except requests.exceptions.RequestException as e:
        st.error(f"HTTP Request failed: {e}")
        return None

# Function to draw the Gauge using Plotly
def draw_gauge(value):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Quality Points"},
        gauge = {
            'axis': {'range': [3, 10]}, # Matches the breaks in R code
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [3, 7], 'color': "red"},
                {'range': [7, 9], 'color': "gold"},
                {'range': [9, 10], 'color': "forestgreen"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    return fig

# --- UI Setup ---
st.set_page_config(page_title="Wine Quality Prediction")

st.title("Wine Quality Prediction")

# Sidebar
with st.sidebar:
    st.header("Input Features")
    
    feat1 = st.number_input("Density", value=0.99, step=0.01, format="%.2f")
    feat2 = st.number_input("Volatile Acidity", value=0.25, step=0.01, format="%.2f")
    feat3 = st.number_input("Chlorides", value=0.05, step=0.01, format="%.2f")
    feat4 = st.number_input("Is Red (1=Yes, 0=No)", value=1, step=1)
    feat5 = st.number_input("Alcohol", value=10.0, step=0.1, format="%.2f")
    
    predict_btn = st.button("Predict", type="primary")

# Main Panel
tab1, = st.tabs(["Prediction"])

with tab1:
    if predict_btn:
        with st.spinner("Calling API..."):
            result = get_prediction(feat1, feat2, feat3, feat4, feat5)

        if result:
            try:
                # Get the 'result' part of the response
                raw_prediction = result.get('result')

                # Helper logic to handle different JSON structures safely
                # Case A: structure is [[5.67]] (Nested list)
                if isinstance(raw_prediction, list) and isinstance(raw_prediction[0], list):
                    pred_value = raw_prediction[0][0]
                # Case B: structure is [5.67] (Flat list) - This is likely what is happening
                elif isinstance(raw_prediction, list):
                    pred_value = raw_prediction[0]
                # Case C: structure is just 5.67 (Direct value)
                else:
                    pred_value = raw_prediction

                # Final check to ensure we have a valid number
                if pred_value is None:
                    st.error("Could not extract a prediction value.")
                else:
                    # Convert to float to be safe
                    pred_value = float(pred_value)

                    model_version = result.get('release', {}).get('model_version_number', 'Unknown')
                    response_time = result.get('model_time_in_ms', 0)

                    # Display Metrics
                    col1, col2 = st.columns(2)
                    col1.metric("Model Version", model_version)
                    col2.metric("Response Time", f"{response_time} ms")
                    
                    st.write(f"### Quality Estimate: {pred_value:.2f}")

                    # Plot Gauge
                    st.plotly_chart(draw_gauge(pred_value), use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error parsing API response: {e}")
                with st.expander("Debug: View Raw Response"):
                    st.json(result)