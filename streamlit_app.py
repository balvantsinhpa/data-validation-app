import streamlit as st
import pandas as pd

# Sample data_validation_rules_template_with_context.xlsx
rules_df = pd.read_excel("data_validation_rules_template_with_context.xlsx")

# Function to load the file
def load_file(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)

# Function to apply validation based on selected rule
def apply_validation(df, columns, rule, param=None):
    errors = []
    
    if rule == "contains_keyword_in_row":
        # Expecting a 'keyword' parameter
        keyword = param
        for column in columns:
            if column in df.columns:
                for idx, value in df[column].iteritems():
                    if keyword not in str(value):
                        errors.append(
                            f"'{keyword}' is not present in cell {value} in column '{column}'. "
                            f"Keyword '{keyword}' must exist in the column '{column}'."
                        )
    
    elif rule == "numeric_only":
        for column in columns:
            if column in df.columns:
                for idx, value in df[column].iteritems():
                    if not str(value).isnumeric():
                        errors.append(
                            f"Value '{value}' in cell {idx} in column '{column}' is not numeric. "
                            f"Column '{column}' must contain only numeric values."
                        )
    
    elif rule == "fixed_length":
        # Expecting a 'length' parameter
        length = int(param)
        for column in columns:
            if column in df.columns:
                for idx, value in df[column].iteritems():
                    if len(str(value)) != length:
                        errors.append(
                            f"Value '{value}' in cell {idx} in column '{column}' is not exactly {length} characters. "
                            f"Column '{column}' must be exactly {length} characters."
                        )
    
    return errors

# Streamlit app
def main():
    st.title("Data Validation App")

    # File upload
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

    if uploaded_file is not None:
        # Load data
        df = load_file(uploaded_file)
        
        # Select columns to validate
        columns = st.multiselect("Select Columns to Validate", options=df.columns)

        # Select rule to apply
        rule_options = rules_df['rule_value'].tolist()
        selected_rule = st.selectbox("Select Rule to Apply", options=rule_options)
        
        # Conditional input for parameters based on selected rule
        if selected_rule == "contains_keyword_in_row":
            keyword = st.text_input("Enter the keyword to check across selected columns:")
        elif selected_rule == "fixed_length":
            length = st.number_input("Enter the length for fixed-length check:", min_value=1, step=1)

        # Validate and show errors
        if st.button("Run Validation"):
            if selected_rule == "contains_keyword_in_row" and not keyword:
                st.error("Please enter a keyword for the 'contains_keyword_in_row' rule.")
            elif selected_rule == "fixed_length" and not length:
                st.error("Please enter a length for the 'fixed_length' rule.")
            else:
                errors = apply_validation(df, columns, selected_rule, keyword if selected_rule == "contains_keyword_in_row" else length)
                
                # Display errors if any
                if errors:
                    st.error("Validation Errors:")
                    for error in errors:
                        st.write(error)
                else:
                    st.success("No validation errors found.")
        
if __name__ == "__main__":
    main()
