from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
import os
import webbrowser
import threading
import re

app = Flask(__name__)

# 전역 변수
excel_data = None
file_name = None
error_summary = None
threshold = 3


# 파일 분석 함수
def load_excel(file_path):
    global excel_data
    excel_data = pd.read_excel(file_path)
    excel_data["LOT"] = excel_data["Chip"].str[:-1]
    excel_data["position"] = excel_data["Chip"].str[-1]
    excel_data["onlyDate"] = excel_data["Date"].str[:8]


# 기본 페이지
@app.route('/')
def index():
    return render_template('index.html', file_name=file_name)


# 파일 업로드 및 불러오기
@app.route('/upload', methods=['POST'])
def upload_file():
    global file_name
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        return redirect(url_for('index'))

    if file:
        file_name = file.filename
        file_path = os.path.join("./uploads", file_name)
        file.save(file_path)

        # 엑셀 파일 불러오기
        load_excel(file_path)

    return redirect(url_for('index'))


@app.route('/summarize_db_info')
def summarize_db_info():
    global error_summary
    if excel_data is not None:
        df = excel_data
        result = []
        
        include_filepath = 'Path' in df.columns
        summary_header = "Chip" + " " * 8 + "|" + " " * 7 + "Rep"
        if include_filepath:
            summary_header += " " * 17 + "FilePath"

        result.append(summary_header)
        result.append("-" * len(summary_header))

        for term, group in df.groupby(['LOT', 'onlyDate', 'Device']):
            result.append(f"{term[0]}    ( 날짜 {term[1]}   기기 {term[2]} )")
            count = 0
            error_count = 0
            for _, row in group.iterrows():
                row_str = " " * 10 + f"  |   {row['position']}   {row['Rep']}"
                if include_filepath:
                    row_str += f"  {row['Path']}"
                    if 'error' in row['Path'].lower():
                        error_count += 1
                result.append(row_str)
                count += 1
            
            if include_filepath:
                result.append(f'Sample number : {count} ( {error_count} error files found )')
            else:
                result.append(f'Sample number : {count}')
            result.append("")

        prefix = ['\n']
        output_string = "\n".join(prefix + result)
    else:
        output_string = []

    return render_template('index.html', file_name=file_name, result=output_string,
                           analysis_type='Summarize_db_info', error_summary=error_summary)


@app.route('/check_error_files')
def check_error_files():
    global error_summary
    if excel_data is not None:
        df = excel_data
        df_error = df[df['Path'].str.contains('error', case=False, na=False)] if 'Path' in df.columns else None
        result = []
        result.append("[Error File Check]")
        if df_error is not None and not df_error.empty:
            result.append(f'{len(df_error)}개의 파일이 ERROR 폴더 내에 있습니다.')
            result.append("")
            summary_header = "Chip" + " " * 8 + "|" + " " * 7 + "Rep" + " " * 17 + "FilePath"
            result.append(summary_header)
            result.append("-" * len(summary_header))
            for term, group in df_error.groupby(['LOT', 'onlyDate', 'Device']):
                result.append(f"{term[0]}    ( 날짜 {term[1]}   기기 {term[2]} )")
                for _, row in group.iterrows():
                    row_str = " " * 10 + f"  |   {row['position']}   {row['Rep']}  {row['Path']}"
                    result.append(row_str)
            result.append("")
        else:
            result.append("Error 파일이 없습니다.")
            result.append("")
        
        prefix = ['\n']
        output_string = "\n".join(prefix + result)
    else:
        output_string = []
    return render_template('index.html', file_name=file_name, result=output_string,
                           analysis_type='Check_error_files', error_summary=error_summary)


@app.route('/samples_to_check')
def samples_to_check():
    global error_summary
    global threshold
    if excel_data is not None:
        df = excel_data
        df_filtered = df[~df['Path'].str.contains('error', case=False, na=False)] if 'Path' in df.columns else df
        result = []

        include_filepath = 'Path' in df.columns
        result.append("[Chip 정보 오류]")
        summary_header = "Chip" + " " * 8 + "|" + " " * 7 + "Rep"
        if include_filepath:
            summary_header += " " * 17 + "FilePath"
        result.append(summary_header)
        result.append("-" * len(summary_header))

        low_sample_count = 0
        for term, group in df_filtered.groupby(['LOT', 'onlyDate', 'Device']):
            count = len(group)
            if count < threshold or count > 8:
                result.append(f"{term[0]}    ( 날짜 {term[1]}   기기 {term[2]} )")
                low_sample_count += 1
                sample_count = 0
                for _, row in group.iterrows():
                    sample_count += 1
                    row_str = " " * 10 + f"  |   {row['position']}   {row['Rep']}"
                    if include_filepath:
                        row_str += f"  {row['Path']}"
                    result.append(row_str)
                result.append(f'Sample : {sample_count}')

        if low_sample_count != 0:
            result.insert(1, f'{low_sample_count}개의 칩정보 오기입이 예상됩니다.\n')
            result.append("")
        else:
            result.append("정보 오기입으로 예상되는 sample이 없습니다.")
            result.append("")

        prefix = ['\n']
        output_string = "\n".join(prefix + result)
    else:
        output_string = []
    return render_template('index.html', file_name=file_name, result=output_string,
                           analysis_type='Samples_to_check', error_summary=error_summary)


@app.route('/count_user_device')
def count_user_device():
    global error_summary
    if excel_data is not None:
        df = excel_data
        result = []
        
        result.append("[User Name Count]")
        user_count = df['User'].value_counts()

        max_index_1 = max(len(str(index)) for index in user_count.index)
        max_value_1 = max(len(str(value)) for value in user_count.values)
        for index, value in user_count.items():
            result.append(f"{index:<{max_index_1}}   {value:>{max_value_1}}")
        result.append("")

        result.append("[Device Name Count]")
        device_count = df['Device'].value_counts()

        max_index_2 = max(len(str(index)) for index in device_count.index)
        max_value_2 = max(len(str(value)) for value in device_count.values)
        for index, value in device_count.items():
            result.append(f"{index:<{max_index_2}}   {value:>{max_value_2}}")

        prefix = ['\n']
        output_string = "\n".join(prefix + result)
    else:
        output_string = []
    return render_template('index.html', file_name=file_name, result=output_string,
                           analysis_type='Count_user_device', error_summary=error_summary)


@app.route('/detect_id_errors')
def detect_id_errors():
    global error_summary
    if excel_data is not None:
        df = excel_data
        result = []
        # 구현 x
        result.append("[ID Error Detection]")
        result.append("Not able to find errors")
        
        prefix = ['\n']
        output_string = "\n".join(prefix + result)
    else:
        output_string = []
    return render_template('index.html', file_name=file_name, result=output_string,
                           analysis_type='Detect_id_errors', error_summary=error_summary)


@app.route('/error_summary_report')
def error_summary_report():
    global error_summary  
    global threshold
    if excel_data is not None:
        df = excel_data
        df_error = df[df['Path'].str.contains('error', case=False, na=False)] if 'Path' in df.columns else None
        df_filtered = df[~df['Path'].str.contains('error', case=False, na=False)] if 'Path' in df.columns else df
        results = []
        
        # Check_error_files
        error_file_result = []
        error_file_result.append("[Error File Check]")
        if df_error is not None and not df_error.empty:
            error_file_result.append(f'{len(df_error)}개의 파일이 ERROR 폴더 내에 있습니다.')
            error_file_result.append(f'파일 정보는 [에러파일 확인]에서 확인할 수 있습니다.')
        error_file_result.append("")
        results.extend(error_file_result)

        # Detect_chip_errors - device / different folder / month / others
        results.append('아래 오류의 파일 정보는 [검토대상 확인]에서 확인할 수 있습니다.')
        results.append("")


        # device
        device_error_result = []
        device_error_result = ["[Device Name Count]"]
        device_error_result.append('모든 기기에 대한 데이터 개수는 [유저/기기 카운트]에서 확인할 수 있습니다.')
        device_error_result.append(f'기기번호 오류로 예상되는 이름은 다음과 같습니다. (threshold = {threshold})')
        
        device_count = df['Device'].value_counts()
        low_sample_devices = device_count[device_count < threshold]        
           
        if len(low_sample_devices) != 0:
            for device_number in low_sample_devices.index.values:
                device_error_result.append(device_number)
            device_error_result.append("")
        else:
            device_error_result.append("발견된 기기번호 오류가 없습니다.")
            device_error_result.append("")
        results.extend(device_error_result)

        # different folder
        if 'Path' in df_filtered.columns:
            folder_error_result = []
            folder_error_result.append("[Samples in wrong folder]")

            pattern = r'D\d{2}[A-L]\d{2}.\d{3}'

            grouped = df_filtered.groupby(['LOT', 'onlyDate', 'Device'])

            no_issues = True

            for term, group in grouped:
                matches = group['Path'].apply(lambda x: re.search(pattern, x))
                if matches.notnull().any():
                    for _, row in group.iterrows():
                        match = re.search(pattern, row['Path'])
                        if match and match.group(0) != row['LOT']:
                            folder_error_result.append(f"{term[0]} (날짜{term[1]} 기기{term[2]})")
                            no_issues = False
                            break 
            folder_error_result.append("")

            if no_issues:
                folder_error_result.append("모든 샘플이 옳은 폴더에 들어있습니다.")
                folder_error_result.append("")
            
            results.extend(folder_error_result)
        else:
            results.append("Path를 확인할 수 없습니다.")

        # month
        month_error_result = ["[Chip Error Detection]"]
        month_error_count = 0
        for chip in df['Chip']:
            if chip[3] not in 'ABCDEFGHIJKL':
                month_error_count += 1
                month_error_result.append(chip)
        month_error_result.insert(1, f'{month_error_count}개의 칩에 month 정보 오류가 존재합니다.')
        month_error_result.append("")
        results.extend(month_error_result)

        # others
        results.append('위 원인에 해당하지 않는 파일 정보는 [검토대상 확인]에서 확인할 수 있습니다.')
        results.append("")

        # Count_user_device
        user_count_result = ["[User Name Count]"]
        user_count = df['User'].value_counts()
        low_sample_users = user_count[user_count < threshold]
        if len(low_sample_users) != 0:
            user_count_result.append(f"유저정보 오류로 예상되는 이름은 다음과 같습니다. (threshold = {threshold})")
            for user in low_sample_users.index.values:
                user_count_result.append(user)
            user_count_result.append("")
        else:
            user_count_result.append("발견된 유저정보 오류가 없습니다.")
            user_count_result.append("")
        results.extend(user_count_result)

        # Detect_id_errors
        id_error_result = ["[ID Error Detection]"]
        # 구현되지 않음
        id_error_result.append("Not able to find errors")
        id_error_result.append("")
        results.extend(id_error_result)

        # Combine all results into a single string
        prefix = ['\n']
        error_summary = "\n".join(prefix + results)  
    else:
        error_summary = "No data available."

    return render_template('index.html', file_name=file_name, error_summary=error_summary, analysis_type='Error_summary_report')



# 브라우저 자동 실행 함수
def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')


# Flask 앱 실행
if __name__ == '__main__':
    if not os.path.exists('./uploads'):
        os.makedirs('./uploads')

    # 새로운 스레드에서 브라우저를 열도록 설정
    threading.Timer(1, open_browser).start()

    app.run(debug=False)
