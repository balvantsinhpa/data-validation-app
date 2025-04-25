import streamlit as st
import pandas as pd
import numpy as np

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

# Load validation rules template
@st.cache_data
def load_validation_rules():
    rules_df = pd.read_excel("data_validation_rules_template_with_context.xlsx")  # Adjust path if needed
    return rules_df

# Function to apply user-friendly validation rules
def apply_validation(df, column, rule, param=None):
    errors = []
    
    # Ensure column exists in the dataframe
    if column not in df.columns:
        st.error(f"Column '{column}' does not exist in the uploaded data. Available columns are: {', '.join(df.columns)}")
        return errors

    # Apply validation based on rule
    if rule == "contains_keyword_in_row":
        keyword = param
        for idx, value in df[column].iteritems():
            if keyword not in str(value):
                errors.append((idx, f"Keyword '{keyword}' not found in {column} at row {idx}"))
    elif rule == "numeric_only":
        for idx, value in df[column].iteritems():
            if not str(value).isnumeric():
                errors.append((idx, f"Value '{value}' is not numeric in {column} at row {idx}"))
    elif rule == "fixed_length":
        length = int(param)
        for idx, value in df[column].iteritems():
            if len(str(value)) != length:
                errors.append((idx, f"Value '{value}' in {column} is not exactly {length} characters at row {idx}"))
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
            # Load validation rules
            validation_rules = load_validation_rules()
            rule_types = validation_rules['rule_type'].unique().tolist()

            # Select Rule to apply
            selected_rule = st.selectbox("Select Rule to Apply", rule_types)
            
            # Provide parameters based on selected rule
            param = None
            if selected_rule == "contains_keyword_in_row":
                param = st.text_input("Enter Keyword")
            elif selected_rule == "fixed_length":
                param = st.number_input("Enter Fixed Length", min_value=1, step=1)
            elif selected_rule == "numeric_only":
                param = None  # No parameter needed for numeric_only

            if st.button("Run Validation"):
                # Apply validation rule
                all_errors = []
                for column in selected_columns:
                    # Check if the column exists before applying validation
                    if column in df.columns:
                        errors = apply_validation(df, column, selected_rule, param)
                        if errors:
                            all_errors.extend(errors)
                    else:
                        st.error(f"Column '{column}' does not exist in the uploaded data.")

                # Show results
                if all_errors:
                    error_df = pd.DataFrame(all_errors, columns=["Row", "Error Message"])
                    st.write("Validation Errors:")
                    st.dataframe(error_df)
                    
                    # Provide option to download the report
                    @st.cache_data
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
