import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import plotly.express as px
import datetime
import os

# --- CONFIGURATION ---
PAGE_TITLE = "IOT-based Intruder Detection System"
COLLECTION_NAME = "security_logs"
GCP_KEY_PATH = "serviceAccountKey.json"

# --- INITIALIZATION ---
st.set_page_config(
    page_title=PAGE_TITLE, 
    page_icon="🛡️",  # Can be emoji, image path, or URL
    layout="wide"
)

# Remove top padding/margin
st.markdown("""
    <style>
    /* Remove default padding at the top */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 0rem !important;
    }
    /* Remove space above title */
    h1 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title(f"🛡️ {PAGE_TITLE}")

@st.cache_resource
def get_db():
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            if os.path.exists(GCP_KEY_PATH):
                # Local Development with Key File
                cred = credentials.Certificate(GCP_KEY_PATH)
                firebase_admin.initialize_app(cred)
            else:
                # Cloud Run (Application Default Credentials)
                firebase_admin.initialize_app()
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to connect to Firestore: {e}")
        return None

db = get_db()

# --- DATA LOADING ---
def load_data():
    """Load security logs from Firestore with document IDs."""
    if not db: return pd.DataFrame()
    
    docs = db.collection(COLLECTION_NAME).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
    
    data = []
    for doc in docs:
        d = doc.to_dict()
        # Handle different timestamp formats if legacy data exists
        if "datetime_str" in d:
            ts = d["datetime_str"]
        else:
            # Fallback to server timestamp conversion
            ts = d.get("timestamp", datetime.datetime.now())
            
        data.append({
            "DocID": doc.id,  # Store document ID for deletion
            "Time": ts,
            "Name": d.get("name", "Unknown"),
            "Status": d.get("status", "Unknown"),
            "Image": d.get("image_url", None)
        })
    
    return pd.DataFrame(data)

# --- DELETE FUNCTION ---
def delete_log(doc_id):
    """Delete a specific log entry from Firestore."""
    try:
        db.collection(COLLECTION_NAME).document(doc_id).delete()
        st.success("✅ Log deleted successfully!")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error deleting log: {e}")

# Auto-refresh button
if st.button('🔄 Refresh Data'):
    st.cache_data.clear()

df = load_data()

if not df.empty:
    # --- METRICS ---
    col1, col2, col3 = st.columns(3)
    
    total_detections = len(df)
    intruder_count = len(df[df["Status"] == "Intruder"])
    authorized_count = len(df[df["Status"] == "Authorized"])
    
    col1.metric("Total Events", total_detections)
    col2.metric("🚨 Intruders Detected", intruder_count, delta_color="inverse")
    col3.metric("✅ Authorized Access", authorized_count)

    st.markdown("---")

    # --- CHARTS ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Activity Overview")
        fig = px.pie(df, names='Status', title='Intruder vs Authorized Access Ratio', color='Status',
                     color_discrete_map={'Intruder':'red', 'Authorized':'green'})
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Recent Timeline")
        # Ensure time is datetime for plotting
        df["Time"] = pd.to_datetime(df["Time"])
        fig2 = px.histogram(df, x="Time", color="Status", nbins=20, title="Events over Time",
                            color_discrete_map={'Intruder':'red', 'Authorized':'green'})
        st.plotly_chart(fig2, use_container_width=True)

    # --- LOGS TABLE ---
    st.subheader("📝 Activity Logs")
    
    # Add column headers with minimal spacing
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([2, 2, 2, 3, 1])
    with header_col1:
        st.markdown("**Time**")
    with header_col2:
        st.markdown("**Name**")
    with header_col3:
        st.markdown("**Status**")
    with header_col4:
        st.markdown("**Image**")
    with header_col5:
        st.markdown("**Action**")
    
    # Thin divider with reduced spacing
    st.markdown("<hr style='margin: 8px 0 8px 0; border: none; border-top: 1px solid rgba(250, 250, 250, 0.2);'>", unsafe_allow_html=True)
    
    # Create scrollable container for logs with fixed height (500px)
    # Using st.container with height parameter (Streamlit 1.32+)
    try:
        # Try using height parameter if available (Streamlit 1.32.0+)
        with st.container(height=500):
            # Create expandable rows with delete buttons for each log
            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
                
                with col1:
                    st.text(str(row['Time']))
                with col2:
                    st.text(row['Name'])
                with col3:
                    # Color-coded status
                    if row['Status'] == 'Intruder':
                        st.markdown(f"🚨 **{row['Status']}**")
                    else:
                        st.markdown(f"✅ **{row['Status']}**")
                with col4:
                    if row['Image']:
                        st.markdown(f"[View Image]({row['Image']})")
                    else:
                        st.text("No Image")
                with col5:
                    # Delete button for each log
                    if st.button("Delete", key=f"delete_{row['DocID']}", help="Delete this log", type="primary", 
                                 kwargs={"style": "background-color:#d9534f;color:white;border:none;"} if hasattr(st, "button") else None):
                        delete_log(row['DocID'])
                
                # Add subtle divider between rows
                if idx < len(df) - 1:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)
    except TypeError:
        # Fallback for older Streamlit versions - just display all logs
        for idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
            
            with col1:
                st.text(str(row['Time']))
            with col2:
                st.text(row['Name'])
            with col3:
                # Color-coded status
                if row['Status'] == 'Intruder':
                    st.markdown(f"🚨 **{row['Status']}**")
                else:
                    st.markdown(f"✅ **{row['Status']}**")
            with col4:
                if row['Image']:
                    st.markdown(f"[View Image]({row['Image']})")
                else:
                    st.text("No Image")
            with col5:
                # Delete button for each log
                if st.button("Delete", key=f"delete_{row['DocID']}", help="Delete this log"):
                    delete_log(row['DocID'])
            
                # Add subtle divider between rows
                if idx < len(df) - 1:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

    # Large spacing between Activity Logs and Gallery sections
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # --- GALLERY ---
    st.subheader("🚨 Intruder Evidence Gallery")
    st.caption("Tip: Delete logs from Activity Logs section will also remove images from this gallery")
    st.markdown("")  # Minimal spacing before gallery content
    intruders = df[df["Status"] == "Intruder"]
    
    if not intruders.empty:
        # Pagination settings
        images_per_page = 8
        total_intruders = len(intruders)
        total_pages = (total_intruders + images_per_page - 1) // images_per_page  # Ceiling division
        
        # Initialize session state for page number
        if 'gallery_page' not in st.session_state:
            st.session_state.gallery_page = 0
        
        # Navigation controls
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        
        with nav_col1:
            if st.button("<- Previous", disabled=(st.session_state.gallery_page == 0), use_container_width=True):
                st.session_state.gallery_page -= 1
                st.rerun()
        
        with nav_col2:
            st.markdown(f"<h4 style='text-align: center;'>Page {st.session_state.gallery_page + 1} of {total_pages}</h4>", unsafe_allow_html=True)
        
        with nav_col3:
            if st.button("Next ->", disabled=(st.session_state.gallery_page >= total_pages - 1), use_container_width=True):
                st.session_state.gallery_page += 1
                st.rerun()
        
        # Minimal divider with reduced spacing between navigation and images
        st.markdown("<hr style='margin: 8px 0 8px 0; border: none; border-top: 1px solid rgba(250, 250, 250, 0.2);'>", unsafe_allow_html=True)
        
        # Calculate start and end indices for current page
        start_idx = st.session_state.gallery_page * images_per_page
        end_idx = min(start_idx + images_per_page, total_intruders)
        
        # Get intruders for current page
        intruder_list = list(intruders.iloc[start_idx:end_idx].itertuples())
        
        # Display images in grid (2 rows of 4)
        for row_num in range(0, len(intruder_list), 4):
            cols = st.columns(4)
            for col_idx, item in enumerate(intruder_list[row_num:row_num+4]):
                with cols[col_idx]:
                    if item.Image:
                        st.image(item.Image, caption=f"{item.Time}", use_container_width=True)
                    else:
                        st.caption("No Image")
        
        # Show total count
        st.caption(f"Showing {start_idx + 1}-{end_idx} of {total_intruders} intruder detections")
    else:
        st.info("No intruders detected recently.")

else:
    st.warning("No data found in Firestore yet. Run the Gateway script to generate logs.")
