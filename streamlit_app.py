import streamlit as st
import pandas as pd
import numpy as np
import io

# ------------------------------------
# Cache data loading functions
# ------------------------------------
@st.cache_data
def load_validation_rules():
    return pd.read_excel("data_validation_rules_template_with_context.xlsx")  # Adjust path if needed

@st.cache_data
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type == "application/vnd.ms-excel" or file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return pd.read_excel(uploaded_file, sheet_name=None)
    elif file_type == "text/csv":
        df = pd.read_csv(uploaded_file)
        return {"Sheet1": df}
    else:
        st.error("Invalid file type. Please upload an Excel or CSV file.")
        return None

# ------------------------------------
# Validation Logic
# ------------------------------------
def apply_validation(df, columns, rule, param=None):
    error_records = []

    for idx, row in df.iterrows():
        for column in columns:
            value = str(row[column]) if column in df.columns else ''

            if rule == "contains_keyword_in_row" and param:
                if param not in value:
                    error_records.append((idx, column, f"Missing keyword '{param}' in {column}"))
            elif rule == "numeric_only":
                if not value.isnumeric():
                    error_records.append((idx, column, f"Non-numeric value in {column}: '{value}'"))
            elif rule == "fixed_length" and param:
                if len(value) != int(param):
                    error_records.append((idx, column, f"Value '{value}' in {column} is not {param} characters"))
            # Add more rules here easily...
    
    return error_records

# ------------------------------------
# Streamlit UI
# ------------------------------------
st.set_page_config(page_title="Data Validation Agent AI", page_icon="✅", layout="wide")
st.title('🧠 Data Validation Agent AI')

uploaded_file = st.file_uploader("📂 Upload your file (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    sheets_dict = load_file(uploaded_file)

    if sheets_dict:
        sheet_names = list(sheets_dict.keys())
        selected_sheets = st.multiselect("📝 Select Sheets to Validate", sheet_names)

        if selected_sheets:
            validation_rules = load_validation_rules()

            available_rules = validation_rules['rule_type'].dropna().unique().tolist()
            selected_rule = st.selectbox("🛡️ Select Validation Rule", available_rules)

            # Fetch user-friendly label
            try:
                label_column = None
                if 'rule_label' in validation_rules.columns:
                    label_column = 'rule_label'
                elif 'rule_value' in validation_rules.columns:
                    label_column = 'rule_value'

                if label_column:
                    rule_label_list = validation_rules.loc[validation_rules['rule_type'] == selected_rule, label_column].dropna().tolist()
                    rule_label = rule_label_list[0] if rule_label_list else selected_rule
                else:
                    rule_label = selected_rule
            except Exception:
                rule_label = selected_rule

            # Dynamic parameter input
            param = None
            if selected_rule == "contains_keyword_in_row":
                param = st.text_input("🔑 Enter Keyword to Check")
            elif selected_rule == "fixed_length":
                param = st.number_input("🔢 Enter Fixed Length", min_value=1, step=1)

            if st.button("🚀 Run Validation"):
                progress_text = "Validation in progress. Please wait..."
                progress_bar = st.progress(0, text=progress_text)

                for sheet_idx, sheet_name in enumerate(selected_sheets):
                    df = sheets_dict[sheet_name]
                    st.subheader(f"📄 Sheet: {sheet_name}")

                    columns = st.multiselect(f"Select Columns to Validate in {sheet_name}", df.columns.tolist(), key=sheet_name)

                    if columns:
                        errors = apply_validation(df, columns, selected_rule, param)

                        if errors:
                            error_df = pd.DataFrame(errors, columns=["Row", "Column", "Error Message"])
                            st.error(f"❌ Found {len(error_df)} validation issues in {sheet_name}.")

                            st.dataframe(error_df)

                            # Highlight errors in original dataframe
                            styled_df = df.style.apply(lambda x: [
                                'background-color: red' if (x.name, col) in [(row, column) for row, column, _ in errors] else ''
                                for col in df.columns
                            ], axis=1)

                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                styled_df.to_excel(writer, sheet_name=sheet_name, index=False)
                                writer.save()

                            output.seek(0)
                            st.download_button(
                                label=f"⬇️ Download {sheet_name} ({rule_label}) Validation",
                                data=output,
                                file_name=f"{sheet_name}_{selected_rule}_validated.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.success(f"✅ No validation errors in {sheet_name}!")

                    else:
                        st.warning(f"⚠️ No columns selected for {sheet_name}.")

                    # Update progress bar
                    progress_bar.progress((sheet_idx + 1) / len(selected_sheets), text=progress_text)

                progress_bar.empty()
