import streamlit as st
import pandas as pd
import numpy as np
import io
import re
from io import BytesIO

st.set_page_config(page_title="Data Validation Agent AI", layout="wide")

# Load validation rules template
@st.cache_data
def load_validation_rules():
    rules_df = pd.read_excel("data_validation_rules_template_with_context.xlsx")
    return rules_df

# Load file function
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        dfs = pd.read_excel(uploaded_file, sheet_name=None)
    elif file_type == "text/csv":
        dfs = {"Sheet1": pd.read_csv(uploaded_file)}
    else:
        st.error("Invalid file type. Please upload an Excel or CSV file.")
        return None
    return dfs

# Apply validation logic to a DataFrame
def apply_validation(df, columns, rule, param):
    error_records = []

    for idx, row in df.iterrows():
        for col in columns:
            cell_val = str(row[col]) if col in df.columns else ""
            error = None

            if rule == "contains_keyword_in_row":
                if param not in str(row[columns]).lower():
                    error = f"\"{param}\" is not present in cell {col}{idx + 2}. Keyword must exist in at least one of the selected columns."

            elif rule == "numeric_only":
                if not cell_val.isnumeric():
                    error = f"Value '{cell_val}' in {col}{idx + 2} is not numeric."

            elif rule == "fixed_length":
                if len(cell_val) != int(param):
                    error = f"Value '{cell_val}' in {col}{idx + 2} must be exactly {param} characters long."

            elif rule == "regex_match":
                if not re.match(param, cell_val):
                    error = f"Value '{cell_val}' in {col}{idx + 2} does not match the required pattern."

            if error:
                error_records.append({"Row": idx + 2, "Column": col, "Error Message": error})

    return pd.DataFrame(error_records)

# Streamlit UI
st.title("🧠 Data Validation Agent AI")

uploaded_file = st.file_uploader("📄 Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    dfs = load_file(uploaded_file)
    if dfs:
        validation_rules = load_validation_rules()
        rule_types = validation_rules['rule_type'].unique().tolist()

        selected_sheets = st.multiselect("📁 Select Sheet(s) to Validate", list(dfs.keys()))
        selected_rule = st.selectbox("✅ Select Rule to Apply", rule_types)

        # Set user-friendly rule label or fallback to rule_type
        rule_label_row = validation_rules.loc[validation_rules['rule_type'] == selected_rule, 'rule_label']
        rule_label = rule_label_row.values[0] if not rule_label_row.empty else selected_rule

        param = None
        if selected_rule == "contains_keyword_in_row":
            param = st.text_input("🌤️ Enter Keyword")
        elif selected_rule == "fixed_length":
            param = st.number_input("🔢 Enter Fixed Length", min_value=1, step=1)
        elif selected_rule == "regex_match":
            param = st.text_input("🔠 Enter Regex Pattern")

        if selected_sheets and st.button("🚀 Run Validation"):
            progress_text = "Validation in progress. Please wait..."
            progress_bar = st.progress(0, text=progress_text)

            for i, sheet_name in enumerate(selected_sheets):
                df = dfs[sheet_name]
                st.subheader(f"📋 {sheet_name} Preview")
                st.dataframe(df.head())

                selected_columns = st.multiselect(f"📌 Select Columns in '{sheet_name}'", df.columns.tolist(), key=sheet_name)

                if selected_columns:
                    errors_df = apply_validation(df, selected_columns, selected_rule, param)

                    if not errors_df.empty:
                        st.error(f"❌ Found {len(errors_df)} validation errors in sheet '{sheet_name}'")
                        st.dataframe(errors_df)

                        # Create highlighted Excel output
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='Validated')
                            workbook = writer.book
                            worksheet = writer.sheets['Validated']
                            red_format = workbook.add_format({'bg_color': '#FFC7CE'})
                            for _, row in errors_df.iterrows():
                                excel_row = row['Row'] - 1  # Excel index starts from 0
                                col_idx = df.columns.get_loc(row['Column'])
                                worksheet.write(excel_row + 1, col_idx, df.iloc[excel_row, col_idx], red_format)

                        st.download_button(
                            label=f"⬇️ Download {sheet_name} ({rule_label}) Validation",
                            data=output.getvalue(),
                            file_name=f"{sheet_name}_{rule_label.lower().replace(' ', '_')}_validated.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.success(f"✅ No validation errors found in sheet '{sheet_name}'!")
                else:
                    st.warning(f"⚠️ Please select columns to validate in sheet '{sheet_name}'")

                progress_bar.progress((i + 1) / len(selected_sheets), text=f"Completed {i+1}/{len(selected_sheets)}")

            st.success("🎉 Validation Completed!")
