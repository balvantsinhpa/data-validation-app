import streamlit as st
import pandas as pd
import numpy as np
import io

# Function to load the file
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type == "application/vnd.ms-excel" or file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        df = pd.read_excel(uploaded_file)
    elif file_type == "text/csv":
        df = pd.read_csv(uploaded_file)
    else:
        st.error("Invalid file type. Please upload an Excel or CSV file.")
        return None
    return df

# Function to apply user-friendly validation rules (example: length check)
def apply_validation(df, column, rule, param=None):
    errors = []
    if rule == "Fixed Length":
        for idx, value in df[column].iteritems():
            if len(str(value)) != int(param):
                errors.append((idx, f"Length of value '{value}' is not {param} characters"))
    elif rule == "Allowed Values":
        if param:
            allowed_values = param.split(",")
            for idx, value in df[column].iteritems():
                if str(value) not in allowed_values:
                    errors.append((idx, f"Value '{value}' is not in allowed values"))
    return errors

# Streamlit UI
st.title('Data Validation Agent AI')

# Upload File
uploaded_file = st.file_uploader("Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = load_file(uploaded_file)
    if df is not None:
        st.write("Data Preview:")
        st.dataframe(df.head())  # Show preview of data
        
        # Auto-detect columns
        columns = df.columns.tolist()
        selected_columns = st.multiselect("Select Columns to Validate", columns)
        
        if selected_columns:
            # Select Rule to apply
            rules = ["Fixed Length", "Allowed Values"]  # Add other rules as needed
            selected_rule = st.selectbox("Select Rule to Apply", rules)
            
            # Provide parameters based on rule
            if selected_rule == "Fixed Length":
                param = st.number_input("Enter Fixed Length", min_value=1, step=1)
            elif selected_rule == "Allowed Values":
                param = st.text_input("Enter Allowed Values (comma-separated)")

            if st.button("Run Validation"):
                # Apply validation rule
                all_errors = []
                for column in selected_columns:
                    errors = apply_validation(df, column, selected_rule, param)
                    if errors:
                        all_errors.extend(errors)

                # Show results
                if all_errors:
                    error_df = pd.DataFrame(all_errors, columns=["Row", "Error Message"])
                    st.write("Validation Errors:")
                    st.dataframe(error_df)
                    
                    # Provide option to download the report
                    @st.cache
                    def convert_df(df):
                        return df.to_csv(index=False).encode('utf-8')

                    csv = convert_df(error_df)
                    st.download_button(
                        label="Download Validation Errors (CSV)",
                        data=csv,
                        file_name="validation_errors.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("No validation errors found!")

