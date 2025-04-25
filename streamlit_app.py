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
    
    # Handle NaN values
    df[column] = df[column].fillna('')
    
    # Apply validation based on rule
    if rule == "contains_keyword_in_row":
        keyword = param
        def check_keyword(value):
            if keyword not in str(value):
                return f"Keyword '{keyword}' not found in cell {value}. Keyword '{keyword}' must exist in at least one of the columns {column}."
            return None
        errors = df[column].apply(check_keyword).dropna().tolist()
        errors = [(idx, err) for idx, err in enumerate(errors) if err]

    elif rule == "numeric_only":
        def check_numeric(value):
            if not str(value).isnumeric():
                return f"Value '{value}' in cell {value} is not numeric. Column '{column}' must contain only numeric values."
            return None
        errors = df[column].apply(check_numeric).dropna().tolist()
        errors = [(idx, err) for idx, err in enumerate(errors) if err]

    elif rule == "fixed_length":
        length = int(param)
        def check_length(value):
            if len(str(value)) != length:
                return f"Value '{value}' in cell {value} is not exactly {length} characters. Column '{column}' must be exactly {length} characters."
            return None
        errors = df[column].apply(check_length).dropna().tolist()
        errors = [(idx, err) for idx, err in enumerate(errors) if err]

    elif rule == "allowed_values":
        allowed_values = param.split(",")  # Comma-separated list of allowed values
        def check_allowed(value):
            if str(value) not in allowed_values:
                return f"Value '{value}' in cell {value} is not one of the allowed values. Column '{column}' must contain only allowed values: {', '.join(allowed_values)}."
            return None
        errors = df[column].apply(check_allowed).dropna().tolist()
        errors = [(idx, err) for idx, err in enumerate(errors) if err]

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
            rule_values = validation_rules['rule_value'].unique().tolist()

            # Select Rule to apply
            selected_rule = st.selectbox("Select Rule to Apply", rule_values)
            
            # Provide parameters based on selected rule
            param = None
            if selected_rule == "Contains keyword in any selected column":
                param = st.text_input("Enter Keyword")
            elif selected_rule == "Fixed number of characters":
                param = st.number_input("Enter Fixed Length", min_value=1, step=1)
            elif selected_rule == "Allow only numbers":
                param = None  # No parameter needed for numeric_only
            elif selected_rule == "Limit to specific values":
                param = st.text_input("Enter Allowed Values (comma-separated)")

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
