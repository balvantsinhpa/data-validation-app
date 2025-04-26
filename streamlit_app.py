import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Function to load the file
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        dfs = pd.read_excel(uploaded_file, sheet_name=None)  # Load all sheets
    elif file_type == "text/csv":
        dfs = {"Sheet1": pd.read_csv(uploaded_file)}  # Wrap CSV into dict
    else:
        st.error("Invalid file type. Please upload an Excel or CSV file.")
        return None
    return dfs

# Load validation rules template
@st.cache_data
def load_validation_rules():
    return pd.read_excel("data_validation_rules_template_with_context.xlsx")  # Adjust path

# Function to apply user-friendly validation rules
def apply_validation(df, column, rule, param=None):
    errors = []

    if column not in df.columns:
        st.error(f"Column '{column}' does not exist in the uploaded data.")
        return errors

    df[column] = df[column].fillna('')

    if rule == "contains_keyword_in_row":
        keyword = param
        def check_keyword(value):
            if keyword not in str(value):
                return f"Keyword '{keyword}' not found"
            return None
        errors = df[column].apply(check_keyword).dropna()

    elif rule == "numeric_only":
        def check_numeric(value):
            if not str(value).isnumeric():
                return f"Value '{value}' is not numeric"
            return None
        errors = df[column].apply(check_numeric).dropna()

    elif rule == "fixed_length":
        length = int(param)
        def check_length(value):
            if len(str(value)) != length:
                return f"Value '{value}' is not exactly {length} characters"
            return None
        errors = df[column].apply(check_length).dropna()

    return errors

# Streamlit UI
st.set_page_config(page_title="Data Validation Agent AI", layout="wide")
st.title('📄 Data Validation Agent AI')

# Upload File
uploaded_file = st.file_uploader("Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    dfs = load_file(uploaded_file)
    if dfs is not None:
        st.success(f"Loaded {len(dfs)} sheet(s). Please proceed.")
        
        sheet_names = list(dfs.keys())
        selected_sheets = st.multiselect("Select Sheets to Validate", sheet_names)

        if selected_sheets:
            validation_rules = load_validation_rules()
            rule_types = validation_rules['rule_type'].unique().tolist()

            selected_rule = st.selectbox("Select Rule to Apply", rule_types)

            # Try to fetch rule_type safely
            rule_type_list = validation_rules.loc[validation_rules['rule_type'] == selected_rule, 'rule_type'].tolist()
            rule_type = rule_type_list[0] if rule_type_list else selected_rule  # fallback to rule_type if missing

            # Optional parameter input
            param = None
            if selected_rule == "contains_keyword_in_row":
                param = st.text_input("Enter Keyword")
            elif selected_rule == "fixed_length":
                param = st.number_input("Enter Fixed Length", min_value=1, step=1)

            if st.button("🚀 Run Validation"):
                for sheet_name in selected_sheets:
                    st.subheader(f"Validating sheet: {sheet_name}")
                    df = dfs[sheet_name]
                    columns = df.columns.tolist()

                    selected_columns = st.multiselect(f"Select Columns in {sheet_name} to Validate", columns, key=sheet_name)

                    if selected_columns:
                        progress_bar = st.progress(0)
                        n_rows = len(df)
                        validation_results = pd.DataFrame(index=df.index)

                        for idx, col in enumerate(selected_columns):
                            errors = apply_validation(df, col, selected_rule, param)
                            if not errors.empty:
                                validation_results[col] = errors
                            progress_bar.progress((idx + 1) / len(selected_columns))

                        # Combine validation results into final output
                        if not validation_results.dropna(how='all').empty:
                            styled_df = df.copy()

                            # Highlight cells with issues
                            def highlight_errors(val, col_name):
                                if not pd.isna(validation_results.at[val.name, col_name]):
                                    return 'background-color: red'
                                return ''
                            
                            styled = styled_df.style.apply(lambda col: [highlight_errors(val, col.name) for val in col], axis=0)

                            # Downloadable validated file
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                styled_df.to_excel(writer, sheet_name=sheet_name, index=False)
                                workbook = writer.book
                                worksheet = writer.sheets[sheet_name]

                                # Apply red fill where errors exist
                                red_format = workbook.add_format({'bg_color': '#FFC7CE'})
                                for col_idx, col in enumerate(styled_df.columns):
                                    for row_idx in range(len(styled_df)):
                                        if not pd.isna(validation_results.at[row_idx, col]):
                                            worksheet.write(row_idx + 1, col_idx, styled_df.at[row_idx, col], red_format)
                            
                            st.download_button(
                                label=f"📥 Download {sheet_name} ({rule_type}) Validation",
                                data=output.getvalue(),
                                file_name=f"{sheet_name}_{rule_type.lower().replace(' ', '_')}_validated.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.success(f"No validation errors found in {sheet_name}!")
