import streamlit as st
import pandas as pd
import numpy as np
import io

# Function to load the uploaded file
@st.cache_data
def load_file(uploaded_file):
    file_type = uploaded_file.type
    if file_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        return pd.read_excel(uploaded_file, sheet_name=None)
    elif file_type == "text/csv":
        df = pd.read_csv(uploaded_file)
        return {"Sheet1": df}
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
        df[column] = df[column].fillna('')

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

# Function to humanize rule name
def humanize_rule_name(rule_type):
    return rule_type.replace('_', ' ').title()

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

                    view_option = st.radio(
                        "👀 View Options",
                        ("Selected Columns Only", "All Columns"),
                        horizontal=True
                    )

                    if view_option == "Selected Columns Only":
                        df_to_show = df[selected_columns]
                    else:
                        df_to_show = df

                    st.subheader("📊 Highlighted DataFrame with Errors")
                    styled_df = highlight_errors(df_to_show, validation_results)
                    st.dataframe(styled_df)

                    # Prepare downloadable Excel files
                    def create_excel(dataframe):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            dataframe.to_excel(writer, index=False, sheet_name="ValidatedData")
                            workbook = writer.book
                            worksheet = writer.sheets["ValidatedData"]

                            error_indices = {(row, col) for row, col, _ in validation_results}
                            if set(dataframe.columns) == set(df.columns):
                                red_format = workbook.add_format({'bg_color': '#FF6666'})
                                for row, column, _ in validation_results:
                                    col_idx = dataframe.columns.get_loc(column)
                                    worksheet.write(row + 1, col_idx, dataframe.iloc[row, col_idx], red_format)

                        output.seek(0)
                        return output

                    selected_output = create_excel(df[selected_columns])
                    full_output = create_excel(df)
                    rule_label = humanize_rule_name(selected_rule)

                    # --- Side-by-side download buttons ---
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 Download (Selected Columns)",
                            data=selected_output,
                            file_name=f"{selected_sheet}_{rule_label}_validated_selected_columns.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    with col2:
                        st.download_button(
                            label="📥 Download (All Columns)",
                            data=full_output,
                            file_name=f"{selected_sheet}_{rule_label}_validated_all_columns.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    # --------------------------------------

                else:
                    st.balloons()
                    st.success("✅ No validation errors found! Your data looks perfect 🎉")

else:
    st.info("📂 Please upload a file to begin.")
