import streamlit as st
import requests
import json
import time
from datetime import datetime
from API.api_fast import *

# API Configuration - Azure Live API
API_BASE_URL = "https://dataplatformapp-grasim-abg-webapp-000-ccdqaudxemf9beej.centralindia-01.azurewebsites.net"
# API_BASE_URL='http://127.0.0.1:8000'

st.set_page_config(page_title="Query Builder - Azure Live API", layout="centered")

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'employee_id' not in st.session_state:
    st.session_state.employee_id = ""
if 'employee_email' not in st.session_state:
    st.session_state.employee_email = ""

# Simple user database (for demo purposes)
# In production, this should be in environment variables or a database
USERS_DB = {
    "demo@example.com": {
        "password": "demo123",
        "employee_id": "EMP001"
    },
    "test@example.com": {
        "password": "test123",
        "employee_id": "EMP002"
    }
}

def login(email, password):
    """Authenticate user and return True if successful"""
    if email in USERS_DB and USERS_DB[email]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.employee_id = USERS_DB[email]["employee_id"]
        st.session_state.employee_email = email
        return True
    return False

def logout():
    """Log out the user"""
    st.session_state.logged_in = False
    st.session_state.employee_id = ""
    st.session_state.employee_email = ""

# Login Page
if not st.session_state.logged_in:
    st.title("🔐 Login")
    st.markdown("---")
    
    with st.form("login_form"):
        email = st.text_input("📧 Email", placeholder="Enter your email")
        password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if email and password:
                with st.spinner("🔓 Logging in..."):
                    if login(email, password):
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password")
            else:
                st.warning("⚠️ Please enter both email and password")
    
    st.markdown("---")
    st.caption("Demo credentials: demo@example.com / demo123 or test@example.com / test123")
    
    st.stop()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_query_templates_from_api():
    """Load query templates from API with appname=sfa"""
    try:
        response = requests.get(f"{API_BASE_URL}/query_templates", params={"appname": "sfa"}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("templates", {})
        else:
            st.error(f"Failed to load templates from API: {response.status_code}")
            return {}
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to API to load templates")
        return {}
    except Exception as e:
        st.error(f"Error loading templates: {e}")
        return {}

# Sidebar with API info and template management
with st.sidebar:
    st.markdown("### 🌐 API Configuration")
    st.caption(f"**Endpoint:** Azure Live API")
    st.caption(f"**Status:** {'🟢 Connected' if API_BASE_URL else '🔴 Not configured'}")
    
    st.markdown("---")
    st.markdown("### 🔄 Template Management")
    
    # Refresh button
    if st.button("🔄 Refresh Templates", use_container_width=True):
        with st.spinner("Reloading templates from API..."):
            load_query_templates_from_api.clear()
            st.success("✅ Templates refreshed")
            st.rerun()
    
    st.markdown("---")

with st.sidebar:
    st.markdown("### 👤 User Info")
    st.markdown(f"**ID:** {st.session_state.employee_id}")
    st.markdown(f"**Email:** {st.session_state.employee_email}")
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()

st.title("Contractor Detail Query Builder")
st.caption("🌐 Connected to Azure Live API")

# Month-Year picker helper
MONTHS = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12"
}

# Load query templates from API
if 'templates_loaded' not in st.session_state:
    with st.spinner("📥 Loading query templates from Azure API..."):
        QUERY_TEMPLATES = load_query_templates_from_api()
        st.session_state.templates_loaded = True
        if QUERY_TEMPLATES:
            st.success(f"✅ Loaded {len(QUERY_TEMPLATES)} templates from API")
else:
    QUERY_TEMPLATES = load_query_templates_from_api()

if not QUERY_TEMPLATES:
    st.error("❌ No query templates available. Please check API connection.")
    st.stop()

FILTER_CONFIG = {
    "Dealercode": {"label": "Dealer Code", "placeholder": "e.g., 6100003089", "default": "6100008629"},
    "Zonename": {"label": "Zone Name", "placeholder": "e.g., North, Central, South", "default": "East"},
    "RegionName": {"label": "Region Name", "placeholder": "e.g., Delhi, UP West", "default": "Andhra Pradesh"},
    "Salesoffice": {"label": "Sales Office", "placeholder": "e.g., South Delhi, Meerut", "default": "Guntur"},
    "monthyear": {"label": "Month-Year", "placeholder": "e.g., Jan-2026", "default": "10-2025"},
    "TTYCode": {"label": "Territory Code", "placeholder": "e.g., AYJ, CDB", "default": "AJI"}
}

st.subheader("Step 1: Select Query Format")
selected_query = st.selectbox(
    "Choose an example query:",
    options=list(QUERY_TEMPLATES.keys()),
    help="Select the type of query you want to make"
)

st.subheader("Step 2: Enter Filter Values")
required_filters = QUERY_TEMPLATES[selected_query]["required_filters"]

filter_values = {}
for filter_name in required_filters:
    config = FILTER_CONFIG[filter_name]
    
    # Special handling for monthyear - use calendar picker with multi-select option
    if filter_name == "monthyear":
        st.markdown("**Month-Year Selection**")
        
        # Toggle for single vs multiple selection
        multi_select = st.checkbox("Select multiple months/years", key="multi_select_toggle")
        
        # Get current date for default
        current_date = datetime.now()
        
        col1, col2 = st.columns(2)
        
        if multi_select:
            # Multi-select mode
            with col1:
                selected_months = st.multiselect(
                    "Months",
                    options=list(MONTHS.keys()),
                    default=[list(MONTHS.keys())[current_date.month - 1]],
                    key="month_picker_multi"
                )
            
            with col2:
                years = list(range(2020, current_date.year + 2))
                selected_years = st.multiselect(
                    "Years",
                    options=years,
                    default=[current_date.year],
                    key="year_picker_multi"
                )
            
            # Generate all month-year combinations
            if selected_months and selected_years:
                month_year_list = []
                for year in sorted(selected_years):
                    for month in selected_months:
                        month_year_list.append(f"{MONTHS[month]}-{year}")
                
                # Store as comma-separated for backend
                filter_values[filter_name] = ",".join(month_year_list)
                
                # Create SQL IN clause ready format
                sql_format = "','".join(month_year_list)
                sql_in_clause = f"('{sql_format}')"
                
                # Display preview
                preview_items = [f"{m} {y}" for y in sorted(selected_years) for m in selected_months]
                st.caption(f"📅 Selected: **{', '.join(preview_items)}**")
                st.caption(f"Raw values: `{filter_values[filter_name]}`")
                st.caption(f"SQL IN clause format: `{sql_in_clause}`")
            else:
                filter_values[filter_name] = ""
                st.warning("Please select at least one month and one year")
        else:
            # Single select mode
            with col1:
                selected_month = st.selectbox(
                    "Month",
                    options=list(MONTHS.keys()),
                    index=current_date.month - 1,
                    key="month_picker_single"
                )
            
            with col2:
                years = list(range(2020, current_date.year + 2))
                selected_year = st.selectbox(
                    "Year",
                    options=years,
                    index=years.index(current_date.year),
                    key="year_picker_single"
                )
            
            # Format as MM-YYYY for backend
            filter_values[filter_name] = f"{MONTHS[selected_month]}-{selected_year}"
            st.caption(f"📅 Selected: **{selected_month} {selected_year}** (Format: {filter_values[filter_name]})")
    else:
        filter_values[filter_name] = st.text_input(
            config["label"],
            value=config.get("default", ""),
            placeholder=config["placeholder"],
            key=filter_name
        )

# User information is automatically from login session
st.subheader("Step 3: User Information")
st.success(f"✅ Logged in as: **{st.session_state.employee_email}** (ID: {st.session_state.employee_id})")

# Use session state values for Employee ID and Email
EmployeeId = st.session_state.employee_id
EmployeeEmailId = st.session_state.employee_email

if st.button("Submit Query"):
    start = time.time()
    
    missing_filters = [FILTER_CONFIG[f]["label"] for f in required_filters if not filter_values.get(f)]
    
    if missing_filters:
        st.error(f"Please fill: {', '.join(missing_filters)}")
    elif not EmployeeId or not EmployeeEmailId:
        st.error("Please fill Employee ID and Email")
    else:
        prompt = QUERY_TEMPLATES[selected_query]["template"].format(**filter_values)
        
        payload = {
            "prompttemp": QUERY_TEMPLATES[selected_query]['template'],
            "prompt": prompt,
            "employee_id": EmployeeId,
            "employee_email": EmployeeEmailId
        }
        print(QUERY_TEMPLATES[selected_query]['template'])
        print(prompt)
        try:
            with st.spinner("⏳ Sending request to Azure API..."):
                print('sending')
                response = requests.post(
                    f"{API_BASE_URL}/contractor/query_fast",
                    json=payload,
                    timeout=300  # 5 minute timeout
                )
                print(response)
            
            if response.status_code == 200:
                result = response.json()
                if "NotebookResponse" in result:
                    try:
                        notebook_data = json.loads(result["NotebookResponse"])
        
                        # Check if data is empty
                        if not notebook_data or len(notebook_data) == 0:
                            st.warning("⚠️ No Data Found!")
                            st.info("📝 Please check and verify your entered values again.")
                        else:
                            st.subheader("Output")
                            st.dataframe(notebook_data)
                            st.success(f"✅ Found {len(notebook_data)} record(s)")
                    except:
                        st.warning("NotebookResponse is not valid JSON.")
                        st.write(result["NotebookResponse"])
                
                end = time.time()
                st.info(f"⏱️ Response time: {end - start:.2f} seconds")
            else:
                st.error(f"API Error: {response.status_code}")
                st.write(response.text)
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The API is taking too long to respond.")
        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to Azure API. Please check your internet connection.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
