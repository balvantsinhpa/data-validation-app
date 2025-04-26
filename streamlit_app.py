import streamlit as st
import pandas as pd
import numpy as np
import io

# Function to load the uploaded file
@st.cache_data
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        return pd.read_excel(uploaded_file, sheet_name=None)  # Load all sheets as dictionary
    elif file_type == "text/csv":
        df = pd.read_csv(uploaded_file)
        return {"Sheet1": df}  # Wrap CSV into a "sheet"
    else:
        st.error("Invalid file type. Please upload an Excel or CSV file.")
        return None

# Load validation rules template
@st.cache_data
def load_validation_rules():
    return pd.read_excel("data_validation_rules_template_with_context.xlsx")

# Function to apply validation rules
def apply_validation(df, selected_columns, rule_type, param=None):
    errors = []
    for column in selected_columns:
        if column not in df.columns:
            continue
        df[column] = df[column].fillna('')  # Fill NaN with blank string

        if rule_type == "contains_keyword_in_row":
            keyword = param
            for idx, value in df[column].items():
                if keyword not in str(value):
                    errors.append((idx, column, f"Keyword '{keyword}' not found in cell ({column})"))

        elif rule_type == "numeric_only":
            for idx, value in df[column].items():
                if not str(value).isnumeric():
                    errors.append((idx, column, f"Value '{value}' is not numeric"))

        elif rule_type == "fixed_length":
            length = int(param)
            for idx, value in df[column].items():
                if len(str(value)) != length:
                    errors.append((idx, column, f"Value '{value}' is not exactly {length} characters long"))

    return errors

# Function to highlight errors in dataframe
def highlight_errors(df, error_list):
    df_copy = df.copy()
    error_indices = {(row, col) for row, col, _ in error_list}

    def highlight(val, row_idx, col_name):
        if (row_idx, col_name) in error_indices:
            return 'background-color: red; color: white;'
        return ''

    styled_df = df_copy.style.apply(lambda col: [
        highlight(val, idx, col.name) for idx, val in enumerate(col)
    ], axis=0)
    return styled_df

# Streamlit UI
st.set_page_config(page_title="Data Validation Agent AI", page_icon="✅", layout="wide")
st.title('🛡️ Data Validation Agent AI')

# Upload file
uploaded_file = st.file_uploader("📤 Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    data = load_file(uploaded_file)
    validation_rules = load_validation_rules()

    if data:
        sheet_names = list(data.keys())
        selected_sheet = st.selectbox("📄 Select Sheet to Validate", sheet_names)

        if selected_sheet:
            df = data[selected_sheet]
            st.subheader(f"🔍 Preview of `{selected_sheet}`")
            st.dataframe(df)

            columns = df.columns.tolist()
            selected_columns = st.multiselect("🛠️ Select Columns to Validate", columns)

            rule_types = validation_rules['rule_type'].unique().tolist()
            selected_rule = st.selectbox("⚙️ Select Rule to Apply", rule_types)

            # Optional param input
            param = None
            if selected_rule == "contains_keyword_in_row":
                param = st.text_input("🔑 Enter Keyword to Search")
            elif selected_rule == "fixed_length":
                param = st.number_input("🔢 Enter Fixed Length", min_value=1, step=1)

            if st.button("🚀 Run Validation"):
                with st.spinner("Validating..."):
                    validation_results = apply_validation(df, selected_columns, selected_rule, param)

                if validation_results:
                    st.error(f"⚠️ Found {len(validation_results)} validation issues.")

                    st.subheader("📊 Highlighted DataFrame with Errors")
                    styled_df = highlight_errors(df, validation_results)
                    st.dataframe(styled_df)

                    # Create downloadable Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name="ValidatedData")
                        workbook = writer.book
                        worksheet = writer.sheets["ValidatedData"]

                        # Highlight cells with errors
                        red_format = workbook.add_format({'bg_color': '#FF6666'})
                        for row, column, _ in validation_results:
                            col_idx = df.columns.get_loc(column)
                            worksheet.write(row + 1, col_idx, df.iloc[row, col_idx], red_format)

                    output.seek(0)

                    # Safe rule label
                    rule_label_list = validation_rules.loc[validation_rules['rule_type'] == selected_rule, 'rule_label'].tolist()
                    rule_label = rule_label_list[0] if rule_label_list else selected_rule

                    download_filename = f"{selected_sheet}_{rule_label}_validated.xlsx"

                    st.download_button(
                        label=f"📥 Download Validated File ({rule_label})",
                        data=output,
                        file_name=download_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.balloons()
                    st.success("✅ No validation errors found! Your data looks perfect 🎉")

else:
    st.info("📂 Please upload a file to begin.")
