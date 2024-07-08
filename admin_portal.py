import streamlit as st
import json
import pandas as pd
from datetime import datetime
from io import BytesIO
import zipfile
import os
import random
import string
from PIL import Image
import base64

def generate_random_filename(extension):
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{random_string}.{extension}"

def is_image_file(file_path):
    try:
        Image.open(file_path)
        return True
    except IOError:
        return False

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

st.title("Admin Portal")

exam_name = st.text_input("Enter Exam Name")

uploaded_file = st.file_uploader("Upload a JPG file", type=["jpg", "jpeg"])

exam_questions_file = st.file_uploader("Upload an Excel or CSV file for exam questions", type=["xlsx", "xls", "csv"])

login_type = st.radio("Select Login Type", ("Login + Password", "User Input Model"), index=None)

login_column = None
password_column = None
rename_columns_dict = {}
csv_data = None
image_filename = None
csv_filename = None
user_inputs = []

exam_questions_csv_data = None
exam_questions_csv_filename = None

if login_type == "Login + Password":
    st.subheader("Upload File for Login Credentials")
    file = st.file_uploader("Upload an Excel or CSV file", type=["xlsx", "xls", "csv"])
    
    if file is not None:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        st.write("File Headers:")
        st.write(df.head())
        
        columns = df.columns.tolist()
        
        login_column = st.selectbox("Select column for Login", [""] + columns, key="login_column")

        if login_column and login_column != "":
            unique_values = df[login_column].nunique()
            total_values = len(df[login_column])
            if unique_values != total_values:
                st.error("Multiple similar logins are found in the selected login column.")
            else:
                filtered_columns = [""] + [col for col in columns if col != login_column]
                password_column = st.selectbox("Select column for Password", filtered_columns, key="password_column")

                if password_column and password_column != "":
                    remaining_columns = [col for col in columns if col not in [login_column, password_column]]
                    while remaining_columns:
                        col1, col2 = st.columns(2)
                        with col1:
                            rename_column = st.selectbox("Select column to rename", [""] + remaining_columns, key=f"rename_column_{len(rename_columns_dict)}")
                        with col2:
                            if rename_column:
                                new_column_name = st.text_input("Enter new name for the column", key=f"new_column_name_{len(rename_columns_dict)}")
                                if new_column_name:
                                    rename_columns_dict[rename_column] = new_column_name
                                    remaining_columns.remove(rename_column)
                    
                        if not rename_column or not new_column_name:
                            break
                
                    if rename_columns_dict:
                        df.rename(columns=rename_columns_dict, inplace=True)

                    selected_columns = [login_column, password_column] + list(rename_columns_dict.values())
                    missing_columns = [col for col in selected_columns if col not in df.columns]
                    if missing_columns:
                        st.error(f"Columns {missing_columns} are missing in the DataFrame.")
                    else:
                        final_df = df[selected_columns]
                        csv_data = final_df.to_csv(index=False).encode('utf-8')
                        csv_filename = generate_random_filename("csv")

elif login_type == "User Input Model":
    st.subheader("Define User Input Fields")
    user_inputs = []  # Initialize the user_inputs list
    field_types = ["Text", "Number", "Date", "Time", "List"]
    input_index = 0

    while True:
        col1, col2, col3 = st.columns(3)
        with col1:
            field_name = st.text_input(f"Field Name {input_index + 1}", key=f"field_name_{input_index}")
        with col2:
            field_type = st.selectbox(f"Field Type {input_index + 1}", [""] + field_types, key=f"field_type_{input_index}")
        with col3:
            if field_type == "Text":
                text_type = st.selectbox(f"Text Input Type {input_index + 1}", ["All Characters", "Only Letters"], key=f"text_type_{input_index}")
            elif field_type == "Number":
                min_value = st.number_input(f"Min Value {input_index + 1}", value=0, step=1, key=f"min_value_{input_index}")
                max_value = st.number_input(f"Max Value {input_index + 1}", value=100, step=1, key=f"max_value_{input_index}")
            elif field_type == "Date":
                min_date = None
                max_date = None
                min_date = st.date_input(f"Min Date {input_index + 1}", key=f"min_date_{input_index}")
                max_date = st.date_input(f"Max Date {input_index + 1}", key=f"max_date_{input_index}")
                if min_date and max_date and min_date > max_date:
                    st.error(f"Min Date for {field_name} should be less than or equal to Max Date")
            elif field_type == "Time":
                time_format = st.selectbox(f"Time Format {input_index + 1}", ["", "24-hour", "12-hour"], key=f"time_format_{input_index}")
                min_time = None
                max_time = None
                if time_format and time_format != "":
                    if time_format == "24-hour":
                        min_time = st.time_input(f"Min Time {input_index + 1}", key=f"min_time_{input_index}", step=60)
                        max_time = st.time_input(f"Max Time {input_index + 1}", key=f"max_time_{input_index}", step=60)
                        if min_time and max_time and min_time > max_time:
                            st.error(f"Min Time for {field_name} should be less than or equal to Max Time")
                    elif time_format == "12-hour":
                        time_options = [f"{hour:02}:{minute:02} {period}" for hour in range(1, 13) for minute in range(0, 60) for period in ["AM", "PM"]]
                        min_time = st.selectbox(f"Min Time {input_index + 1}", time_options, key=f"min_time_{input_index}")
                        max_time = st.selectbox(f"Max Time {input_index + 1}", time_options, key=f"max_time_{input_index}")
                        if min_time and max_time:
                            min_time_dt = datetime.strptime(min_time, "%I:%M %p")
                            max_time_dt = datetime.strptime(max_time, "%I:%M %p")
                            if min_time_dt > max_time_dt:
                                st.error(f"Min Time for {field_name} should be less than or equal to Max Time")
            elif field_type == "List":
                list_items = st.text_area(f"Enter list items", key=f"list_items_{input_index}")
                if list_items:
                    items = list_items.split('\n')
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column;">
                        {"".join([f'<div style="border: 1px solid #ccc; padding: 5px; margin: 5px 0; width: fit-content;">{item}</div>' for item in items])}
                    </div>
                    """, unsafe_allow_html=True)

        if field_name and field_type:
            if field_type == "Text":
                user_inputs.append({"field_name": field_name, "field_type": field_type, "text_type": text_type})
            elif field_type == "Number":
                user_inputs.append({"field_name": field_name, "field_type": field_type, "min_value": min_value, "max_value": max_value})
            elif field_type == "Date":
                if not (min_date and max_date and min_date > max_date):
                    user_inputs.append({
                        "field_name": field_name,
                        "field_type": field_type,
                        "min_date": min_date.isoformat() if min_date else None,
                        "max_date": max_date.isoformat() if max_date else None})
            elif field_type == "Time":
                if time_format == "24-hour":
                    if not (min_time and max_time and min_time > max_time):
                        user_inputs.append({
                            "field_name": field_name,
                            "field_type": field_type,
                            "time_format": time_format,
                            "min_time": min_time.strftime("%H:%M") if min_time else None,
                            "max_time": max_time.strftime("%H:%M") if max_time else None})
                elif time_format == "12-hour":
                    if min_time and max_time and min_time_dt <= max_time_dt:
                        user_inputs.append({
                            "field_name": field_name,
                            "field_type": field_type,
                            "time_format": time_format,
                            "min_time": min_time_dt.strftime("%I:%M %p") if min_time else None,
                            "max_time": max_time_dt.strftime("%I:%M %p") if max_time else None})
            elif field_type == "List":
                if list_items:
                    items = list_items.split('\n')
                    user_inputs.append({
                        "field_name": field_name,
                        "field_type": field_type,
                        "items": items})
            input_index += 1
        else:
            break

if exam_questions_file is not None:
    st.subheader("Configure Exam Questions")
    if exam_questions_file.name.endswith('.csv'):
        df = pd.read_csv(exam_questions_file)
    else:
        df = pd.read_excel(exam_questions_file)

    st.write("File Headers:")
    st.write(df.head())

    columns = df.columns.tolist()

    topic_column = st.selectbox("Select column for Topic/Subject", [""] + columns, key="topic_column")
    if topic_column:
        columns.remove(topic_column)

    questions_column = st.selectbox("Select column for Questions", [""] + columns, key="questions_column")
    if questions_column:
        columns.remove(questions_column)

    answer_type_column = st.selectbox("Select column for Answer Type", [""] + columns, key="answer_type_column")
    if answer_type_column:
        columns.remove(answer_type_column)

    group_column = st.selectbox("Select column for Group", [""] + columns, key="group_column")
    if group_column:
        columns.remove(group_column)

    options_column = st.selectbox("Select column for Options", [""] + columns, key="options_column")

    if all([topic_column, questions_column, answer_type_column, group_column, options_column]):
        df.rename(columns={
            topic_column: "Topic/Subject",
            questions_column: "Questions",
            answer_type_column: "Answer Type",
            group_column: "Group",
            options_column: "Options"
        }, inplace=True)
        
        selected_columns = ["Topic/Subject", "Questions", "Answer Type", "Group", "Options"]
        missing_columns = [col for col in selected_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Columns {missing_columns} are missing in the DataFrame.")
        else:
            valid = True
            display_data = []
            image_files = []

            for index, row in df.iterrows():
                answer_type = str(row["Answer Type"]).strip().lower()
                options = str(row["Options"]).strip() if pd.notna(row["Options"]) else ''
                question = str(row["Questions"]).strip() if pd.notna(row["Questions"]) else ''

                if is_image_file(question):
                    question_display = f'<img src="data:image/png;base64,{image_to_base64(question)}" width="100">'
                    image_files.append(question)
                else:
                    question_display = question

                if answer_type in ["multiple choice", "single choice"]:
                    option_list = options.split('\n')
                    if len(option_list) < 2:
                        valid = False
                        st.warning(f"Row {index + 1}: For 'multiple choice' or 'single choice', 'Options' must have at least 2 options separated by new lines.")
                    else:
                        for i, option in enumerate(option_list, start=1):
                            if is_image_file(option):
                                option_display = f'<img src="data:image/png;base64,{image_to_base64(option)}" width="100">'
                                image_files.append(option)
                            else:
                                option_display = option

                            display_data.append({
                                "Topic/Subject": row["Topic/Subject"] if i == 1 else '',
                                "Questions": question_display if i == 1 else '',
                                "Answer Type": row["Answer Type"] if i == 1 else '',
                                "Group": row["Group"] if i == 1 else '',
                                "Option No": i,
                                "Option": option_display
                            })
                else:
                    if answer_type in ["number", "text"] and options != '':
                        valid = False
                        st.warning(f"Row {index + 1}: For 'number' or 'text' type, 'Options' should be blank. Please check and correct it.")
                    display_data.append({
                        "Topic/Subject": row["Topic/Subject"],
                        "Questions": question_display,
                        "Answer Type": row["Answer Type"],
                        "Group": row["Group"],
                        "Option No": '',
                        "Option": options
                    })

            if valid:
                display_df = pd.DataFrame(display_data)
                
                html_table = display_df.to_html(escape=False, index=False)
                st.markdown(html_table, unsafe_allow_html=True)

                final_df = df[selected_columns]
                exam_questions_csv_data = final_df.to_csv(index=False).encode('utf-8')
                exam_questions_csv_filename = generate_random_filename("csv")

if uploaded_file is not None and exam_name and login_type:
    image_filename = uploaded_file.name

    data_dict = {
        "exam_name": exam_name,
        "login_type": login_type,
        "login_page_image": image_filename
    }

    if login_type == "Login + Password":
        data_dict["login + Password_csv_filename"] = csv_filename
    elif login_type == "User Input Model":
        data_dict["user_inputs"] = user_inputs
    
    if exam_questions_csv_filename is not None:
        data_dict["exam_questions_csv_filename"] = exam_questions_csv_filename

    json_data = json.dumps(data_dict).encode('utf-8')
    json_filename = f"{exam_name}.json"

    with BytesIO() as zip_buffer:
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr(json_filename, json_data)
            if csv_data:
                zip_file.writestr(csv_filename, csv_data)
            if exam_questions_csv_data:
                zip_file.writestr(exam_questions_csv_filename, exam_questions_csv_data)
            zip_file.writestr(image_filename, uploaded_file.getvalue()) 
            for image_file in image_files:
                zip_file.write(image_file, os.path.basename(image_file))
        zip_buffer.seek(0)
        zip_data = zip_buffer.read()

    st.download_button(
        label="Download Exam Details File",
        data=zip_data,
        file_name=f"{exam_name}_exam_details.zip",
        mime="application/zip")
