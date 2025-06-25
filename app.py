import streamlit as st
import google.generativeai as genai
from pdf2image import convert_from_bytes
from PIL import Image
import json
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="FormScanner AI 📄",
    page_icon="🤖",
    layout="wide"
)

# --- Gemini API Configuration ---
try:
    genai.configure(api_key=st.secrets["google_api_key"])
    # Using the latest Gemini 1.5 Pro model which is excellent for multimodal tasks
    GEMINI_MODEL = genai.GenerativeModel('gemini-2.0-flash')
except (KeyError, FileNotFoundError):
    st.error("⚠️ **Warning:** Google API key not found.", icon="🚨")
    st.info("Please add your Google API key to your Streamlit secrets. Name it `google_api_key`.")
    st.stop()


# --- Helper Functions ---

@st.cache_data(show_spinner="Converting PDF to image...")
def pdf_to_image(pdf_bytes, page_number=0):
    """Converts a specific page of a PDF from bytes into a PIL Image."""
    try:
        images = convert_from_bytes(pdf_bytes, first_page=page_number + 1, last_page=page_number + 1)
        return images[0] if images else None
    except Exception as e:
        st.error(f"Error converting PDF to image: {e}", icon="🖼️")
        return None

@st.cache_data(show_spinner="Gemini is analyzing the document...")
def analyze_document_with_gemini(_image, _placeholders):
    """
    Analyzes a document image using Gemini Pro Vision and extracts information based on placeholders.
    _image and _placeholders are prefixed with _ to indicate they are used for caching.
    """
    placeholders_str = ", ".join(_placeholders)
    prompt = f"""
    You are an expert document analysis AI. Your task is to analyze the provided image of a document and extract specific information.

    **Instructions**:
    1.  Carefully examine the document image.
    2.  Extract the values for the following fields: **{placeholders_str}**
    3.  Your response **MUST** be a single, valid JSON object.
    4.  The keys of the JSON object must exactly match the field names provided in the list.
    5.  If a value for a field cannot be found in the document, the corresponding value in the JSON object should be "N/A".

    **Example Request Fields**: ["Invoice Number", "Customer Name", "Total Amount"]
    **Example JSON Response**:
    {{
      "Invoice Number": "INV-12345",
      "Customer Name": "John Doe",
      "Total Amount": "$999.99"
    }}

    Now, analyze the provided image and extract the data for the requested fields.
    """

    try:
        # The model can take a list of inputs: a prompt and an image
        response = GEMINI_MODEL.generate_content([prompt, _image])
        
        # Clean up the response to ensure it's valid JSON
        json_str = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error during AI analysis: {e}", icon="🔥")
        return None


def pdf_to_image(pdf_bytes, page_number=0):
    try:
        # No need to specify poppler_path if it's in the system PATH
        images = convert_from_bytes(pdf_bytes, first_page=page_number + 1, last_page=page_number + 1)
        return images[0] if images else None
    except Exception as e:
        # The error will often tell you if poppler is not found
        print(f"Error: {e}") 
        return None


# --- Streamlit App UI ---

st.title("FormScanner AI 🤖")
st.markdown("Upload a document (e.g., invoice, form), define the data you need, and let AI extract it for you.")

# Initialize session state for results
if "result" not in st.session_state:
    st.session_state.result = None
if "image_to_display" not in st.session_state:
    st.session_state.image_to_display = None


# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("1. Upload Document")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    page_number = 0
    if uploaded_file:
        # This is a bit of a hack to show a page selector without a full PDF viewer
        page_number = st.number_input("Select page to analyze", min_value=1, value=1) - 1

    st.header("2. Define Placeholders")
    placeholder_help = """
    List each piece of information you want to extract, one per line.
    For example:
    Invoice Number
    Customer Name
    Total Amount
    Due Date
    """
    placeholders_text = st.text_area(
        "Fields to Extract (one per line)",
        height=150,
        help=placeholder_help,
        value="Invoice Number\nCustomer Name\nTotal Amount\nDue Date"
    )

    extract_button = st.button("Extract Information", type="primary", use_container_width=True)


# --- Main Content Area for Results ---
if extract_button and uploaded_file and placeholders_text:
    placeholders = [p.strip() for p in placeholders_text.strip().split('\n') if p.strip()]
    if not placeholders:
        st.warning("Please define at least one placeholder.", icon="⚠️")
    else:
        # Convert PDF to image
        pdf_bytes = uploaded_file.getvalue()
        image = pdf_to_image(pdf_bytes, page_number)

        if image:
            st.session_state.image_to_display = image
            # Analyze the document
            analysis_result = analyze_document_with_gemini(image, placeholders)
            st.session_state.result = analysis_result
        else:
            st.session_state.result = None
            st.session_state.image_to_display = None


# Display results if they exist in the session state
if st.session_state.result:
    st.header("Extracted Information")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Results")
        # Display results in a clean, form-like way
        for key, value in st.session_state.result.items():
            st.text_input(
                label=key,
                value=str(value),
                disabled=True,
                key=f"result_{key}"
            )

    with col2:
        st.subheader("Analyzed Document")
        if st.session_state.image_to_display:
            st.image(st.session_state.image_to_display, caption=f"Analyzed Page {page_number + 1}", use_column_width=True)

elif not extract_button:
     st.info("Upload a PDF and define placeholders in the sidebar to begin.")
