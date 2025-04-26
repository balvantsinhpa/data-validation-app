import streamlit as st
import pandas as pd
import numpy as np
import time
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Data Validation Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------
# Caching Functions
# ------------------------------------

@st.cache_data(show_spinner="Loading validation rules...")
def load_validation_rules():
    return pd.read_excel("data_validation_rules_template_with_context.xlsx")

@st.cache_data(show_spinner="Reading file...")
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        return pd.read_excel(uploaded_file, sheet_name=None)  # Load all sheets
    elif file_type == "text/csv":
        return {"Sheet1": pd.read_csv(uploaded_file)}
    else:
        st.error("Unsupported file type. Please upload a CSV or Excel file.")
        return None

# ------------------------------------
# Validation Logic
# ------------------------------------

def apply_validation(df, column, rule, param=None):
    errors = []

    if column not in df.columns:
        return errors

    df[column] = df[column].fillna('')

    if rule == "contains_keyword_in_row":
        keyword = param
        errors = [
            (idx, f"Keyword '{keyword}' not found in value '{value}'")
            for idx, value in df[column].items()
            if keyword not in str(value)
        ]
    elif rule == "numeric_only":
        errors = [
            (idx, f"Value '{value}' is not numeric")
            for idx, value in df[column].items()
            if not str(value).isnumeric()
        ]
    elif rule == "fixed_length":
        length = int(param)
        errors = [
            (idx, f"Value '{value}' is not exactly {length} characters")
            for idx, value in df[column].items()
            if len(str(value)) != length
        ]

    return errors

def highlight_errors(df, error_indices):
    df_styled = df.copy()
    def highlight(val, row_idx, col_name):
        if (row_idx, col_name) in error_indices:
            return 'background-color: #FFCCCC'
        return ''
    
    styled_df = df_styled.style.applymap_index(
        lambda _: '', axis=0  # keep index unstyled
    ).apply(
        lambda col: [
            highlight(val, idx, col.name) for idx, val in enumerate(col)
        ],
        axis=0
    )
    return styled_df

# ------------------------------------
# Streamlit UI
# ------------------------------------

# Title
st.title("📋 Data Validation Agent AI")
st.caption("Validate your data intelligently with friendly error messages and easy downloads.")

# Upload File
uploaded_file = st.file_uploader("📂 Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    sheets_dict = load_file(uploaded_file)

    if sheets_dict:
        sheet_names = list(sheets_dict.keys())
        selected_sheets = st.multiselect("Select Sheets to Validate", sheet_names)

        if selected_sheets:
            validation_rules = load_validation_rules()
            rule_types = validation_rules['rule_type'].unique().tolist()

            for sheet_name in selected_sheets:
                st.subheader(f"Sheet: {sheet_name}")
                df = sheets_dict[sheet_name]

                with st.expander("Preview Data", expanded=False):
                    st.dataframe(df.head(20), use_container_width=True)

                columns = df.columns.tolist()
                selected_columns = st.multiselect(f"Select Columns to Validate (Sheet: {sheet_name})", columns, key=f"columns_{sheet_name}")

                if selected_columns:
                    selected_rule = st.selectbox(f"Select Rule to Apply (Sheet: {sheet_name})", rule_types, key=f"rule_{sheet_name}")

                    param = None
                    if selected_rule == "contains_keyword_in_row":
                        param = st.text_input("Enter Keyword", key=f"param_keyword_{sheet_name}")
                    elif selected_rule == "fixed_length":
                        param = st.number_input("Enter Fixed Length", min_value=1, step=1, key=f"param_length_{sheet_name}")

                    if st.button(f"Run Validation on {sheet_name}", key=f"validate_{sheet_name}"):

                        # Progress Bar Start
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        all_errors = []
                        error_indices = set()
                        total_columns = len(selected_columns)

                        for idx, column in enumerate(selected_columns):
                            # Update progress
                            progress_percent = int((idx / total_columns) * 100)
                            progress_bar.progress(progress_percent)
                            status_text.text(f"Validating column: {column}")

                            errors = apply_validation(df, column, selected_rule, param)
                            all_errors.extend([(row, col, err) for row, err in errors for col in [column]])
                            error_indices.update((row, column) for row, err in errors)

                            # Simulate time for better UX (optional)
                            time.sleep(0.2)  # You can remove or adjust this

                        # Finish Progress Bar
                        progress_bar.progress(100)
                        status_text.text("Validation complete! 🎯")

                        if all_errors:
                            error_df = pd.DataFrame(all_errors, columns=["Row", "Column", "Error Message"])
                            st.error(f"❌ {len(error_df)} validation issues found!")
                            st.dataframe(error_df, use_container_width=True)

                            styled_df = highlight_errors(df, error_indices)
                            
                            # Allow file download
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df.to_excel(writer, sheet_name='Validated', index=False)
                                workbook = writer.book
                                worksheet = writer.sheets['Validated']

                                # Apply red background formatting
                                format_red = workbook.add_format({'bg_color': '#FFCCCC'})
                                for row_idx, col_name in error_indices:
                                    col_idx = df.columns.get_loc(col_name)
                                    worksheet.write(row_idx + 1, col_idx, df.at[row_idx, col_name], format_red)


                            st.download_button(
                                label=f"Download {sheet_name} ({rule_label}) Validation",
                                data=output.getvalue(),
                                file_name=f"{sheet_name}_{rule_label.lower().replace(' ', '_')}_validated.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                        else:
                            st.success("✅ No validation errors found!")
