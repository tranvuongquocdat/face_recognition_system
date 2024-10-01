import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from datetime import datetime, time
from datetime import datetime, timedelta
from calendar import monthrange
import pandas as pd

# Biến để set có ca tối hay không
include_evening_shift = False  # Set thành False nếu không có ca tối

# Định nghĩa khung giờ làm việc trong một từ điển
working_hours = {
    "morning": {"start": time(7, 15), "end": time(11, 15)},
    "afternoon": {"start": time(14, 0), "end": time(18, 0)}
}

# Nếu có ca tối, thêm vào từ điển working_hours
if include_evening_shift:
    working_hours["evening"] = {"start": time(20, 0), "end": time(22, 0)}

def calculate_hours(in_time, out_time):
    work_shift = []
    if in_time == "0" or out_time == "0":
        return 0, work_shift
        
    in_time = datetime.strptime(in_time, '%H:%M:%S').time()
    out_time = datetime.strptime(out_time, '%H:%M:%S').time()

    total_hours = 0
    
    # Tính giờ công cho từng ca làm việc
    for shift in working_hours.values():
        if in_time < shift["end"] and out_time > shift["start"]:
            start = max(in_time, shift["start"])
            end = min(out_time, shift["end"])
            total_hours += (datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)).seconds / 3600
            if shift["start"] == working_hours["morning"]["start"]:
                work_shift.append("morning")
            elif shift["start"] == working_hours["afternoon"]["start"]:
                work_shift.append("afternoon")

    return total_hours, work_shift

# Assume 'df' is your main DataFrame with employee attendance data
from datetime import datetime, timedelta
from calendar import monthrange
from datetime import time as time_convert

def calculate_minutes_difference(time1, time2):
    """
    Tính toán số phút chênh lệch giữa hai thời gian.
    
    Parameters:
    time1 (datetime.time): Thời gian thứ nhất.
    time2 (datetime.time): Thời gian thứ hai.

    Returns:
    int: Số phút chênh lệch giữa time1 và time2.
    """
    # Lấy ngày hiện tại
    date_today = datetime.today().date()
    
    # Kết hợp thời gian và ngày để tạo datetime object
    datetime1 = datetime.combine(date_today, time1)
    datetime2 = datetime.combine(date_today, time2)
    
    # Tính toán chênh lệch
    time_difference = datetime1 - datetime2
    
    # Chuyển đổi chênh lệch sang phút
    minutes_difference = time_difference.total_seconds() / 60
    
    return int(minutes_difference)

def convert_check_in_data_to_workshift(df, year = 2024, month = 1):

    df['Thời Gian'] = pd.to_datetime(df['Thời Gian'])
    # Extract year
    df['Year'] = df['Thời Gian'].dt.year

    # Extract month
    df['Month'] = df['Thời Gian'].dt.month

    # Extract day (date)
    df['Day'] = df['Thời Gian'].dt.day

    # Extract time
    df['Time'] = df['Thời Gian'].dt.time

    # Extract hour
    df['Hour'] = df['Thời Gian'].dt.hour

    # Extract minute
    df['Minute'] = df['Thời Gian'].dt.minute

    # Extract second
    df['Second'] = df['Thời Gian'].dt.second

    # Get the first day of the month and the number of days in the month
    first_day = datetime(year, month, 1)
    num_days = monthrange(year, month)[1]

    # Generate the lists for the days and the corresponding day of the week
    days_in_month = []
    days_of_week = []

    for i in range(num_days):
        current_day = first_day + timedelta(days=i)
        days_in_month.append(current_day.day)
        days_of_week.append(current_day.strftime('%A'))

    employee_workshift_tracking = {}

    # Iterate through each department
    for i, department in enumerate(df["Phòng Ban"].unique(), 1):
        print(f"{i}. {department}")
        employee_workshift_tracking[department] = {}
        
        # Filter the data for each department and get unique workshops
        workshops = df[df["Phòng Ban"] == department]["Xưởng"].unique()
        
        # Iterate through each workshop within the department
        for j, workshop in enumerate(workshops, 1):
            #add workshop to the dict
            employee_workshift_tracking[department][workshop] = {}
            print(f"   {i}.{j} {workshop}")
            
            # Filter the data for each workshop and get unique employees
            persons = df[(df["Phòng Ban"] == department) & (df["Xưởng"] == workshop)]["Mã Nhân Viên"].unique()
            
            # Iterate through each person within the workshop
            for k, person in enumerate(persons, 1):
                person_name = df[df["Mã Nhân Viên"] == person]["Tên Nhân Viên"].iloc[0]
                employee_workshift_tracking[department][workshop][person] = {}

                #add name to the dictionary
                employee_workshift_tracking[department][workshop][person]["name"] = person_name
                print(f"      {i}.{j}.{k} {person} : {person_name}")

                #add work_load tracking to the dictionary
                employee_workshift_tracking[department][workshop][person]["work_load"] = []
                
                # Filter the data for each person
                person_data = df[(df["Mã Nhân Viên"] == person) & (df["Phòng Ban"] == department) & (df["Xưởng"] == workshop)]

                total_hours_per_month = 0
                work_day_per_month = 0
                late_check_in = 0
                early_check_out = 0
                late_check_in_minute = 0
                early_check_out_minute = 0

                max_pair_len = 0

                late_check_in_status_morning = True
                late_check_in_status_afternoon = True
                early_check_out_time_morning = time_convert(23, 59)
                early_check_out_time_afternoon = time_convert(23, 59)
                
                absent_days = []

                for index, day in enumerate(days_in_month):
                    day_of_week = days_of_week[index]
                    # Bỏ qua nếu là Chủ nhật


                    day_data = person_data[person_data['Day'] == day]
                    
                    # Separate IN and OUT data and sort them by time
                    in_data = sorted(day_data[day_data['IN/OUT'] == 'IN']['Thời Gian'].tolist())
                    out_data = sorted(day_data[day_data['IN/OUT'] == 'OUT']['Thời Gian'].tolist())
                    
                    paired_time = []

                    while in_data or out_data:
                        if in_data and out_data:
                            in_time = in_data[0]
                            out_time = out_data[0]
                            
                            if in_time < out_time:
                                try:
                                    if len(in_data) > 1 and in_data[1] <= out_time:
                                        paired_time.append((in_time.strftime('%H:%M:%S'), "0"))
                                        in_data.pop(0)
                                    else:
                                        paired_time.append((in_time.strftime('%H:%M:%S'), out_time.strftime('%H:%M:%S')))
                                        in_data.pop(0)
                                        out_data.pop(0)
                                except IndexError:
                                    paired_time.append((in_time.strftime('%H:%M:%S'), out_time.strftime('%H:%M:%S')))
                                    in_data.pop(0)
                                    out_data.pop(0)
                            else:
                                paired_time.append(("0", out_time.strftime('%H:%M:%S')))
                                out_data.pop(0)
                        elif in_data:
                            in_time = in_data.pop(0)
                            paired_time.append((in_time.strftime('%H:%M:%S'), "0"))
                        elif out_data:
                            out_time = out_data.pop(0)
                            paired_time.append(("0", out_time.strftime('%H:%M:%S')))

                        if len(paired_time) > max_pair_len:
                            max_pair_len = len(paired_time)
                
                # Iterate through each day of the month using days_in_month and days_of_week
                for index, day in enumerate(days_in_month):
                    day_of_week = days_of_week[index]
                    day_data = person_data[person_data['Day'] == day]
                    
                    # Separate IN and OUT data and sort them by time
                    in_data = sorted(day_data[day_data['IN/OUT'] == 'IN']['Thời Gian'].tolist())
                    out_data = sorted(day_data[day_data['IN/OUT'] == 'OUT']['Thời Gian'].tolist())
                    
                    paired_time = []

                    while in_data or out_data:
                        if in_data and out_data:
                            in_time = in_data[0]
                            out_time = out_data[0]
                            
                            if in_time < out_time:
                                try:
                                    if len(in_data) > 1 and in_data[1] <= out_time:
                                        paired_time.append((in_time.strftime('%H:%M:%S'), "0"))
                                        in_data.pop(0)
                                    else:
                                        paired_time.append((in_time.strftime('%H:%M:%S'), out_time.strftime('%H:%M:%S')))
                                        in_data.pop(0)
                                        out_data.pop(0)
                                except IndexError:
                                    paired_time.append((in_time.strftime('%H:%M:%S'), out_time.strftime('%H:%M:%S')))
                                    in_data.pop(0)
                                    out_data.pop(0)
                            else:
                                paired_time.append(("0", out_time.strftime('%H:%M:%S')))
                                out_data.pop(0)
                        elif in_data:
                            in_time = in_data.pop(0)
                            paired_time.append((in_time.strftime('%H:%M:%S'), "0"))
                        elif out_data:
                            out_time = out_data.pop(0)
                            paired_time.append(("0", out_time.strftime('%H:%M:%S')))
                    
                    while len(paired_time) < max_pair_len:
                        paired_time.append(("0","0"))

                    if day_of_week == 'Sunday':
                        paired_time = []
                        while len(paired_time) < max_pair_len:
                            paired_time.append(("0","0"))

                    #print result of each day
                    print(f"         Day {day}: {paired_time}")
                    employee_workshift_tracking[department][workshop][person]["work_load"].append(paired_time)

                    total_hours_per_day = 0
                    for time in paired_time:
                        in_time, out_time = time
                        total_hours_per_work_shift, workshift = calculate_hours(in_time, out_time)
                        total_hours_per_day += total_hours_per_work_shift

                        #check morning late check in
                        if "morning" in workshift:
                            #convert time to datetime type
                            in_time_convert = datetime.strptime(in_time, '%H:%M:%S').time()
                            out_time_convert = datetime.strptime(out_time, '%H:%M:%S').time()
                            if late_check_in_status_morning:
                                if in_time_convert > working_hours["morning"]["start"]:
                                    late_check_in += 1
                                    late_check_in_status_morning = False 
                                    late_check_in_minute += calculate_minutes_difference(in_time_convert, working_hours["morning"]["start"])
                                    print(f"Di muon: {in_time}")

                            early_check_out_time_morning = out_time_convert
                            # print("ve sang som qua" + out_time_convert)
                        
                        if "afternoon" in workshift:
                            #convert time to datetime type
                            in_time_convert = datetime.strptime(in_time, '%H:%M:%S').time()
                            out_time_convert = datetime.strptime(out_time, '%H:%M:%S').time()
                            if late_check_in_status_morning:
                                if in_time_convert > working_hours["afternoon"]["start"]:
                                    late_check_in += 1
                                    late_check_in_status_afternoon = False 
                                    late_check_in_minute += calculate_minutes_difference(in_time_convert, working_hours["afternoon"]["start"])
                                    print(f"Di muon: {in_time}")

                            early_check_out_time_afternoon = out_time_convert
                            # print("ve chieu som qua" + out_time_co)


                    #check check out status
                    if early_check_out_time_morning < working_hours["morning"]["end"]:
                        early_check_out += 1
                        print(f"ve som: {str(early_check_out_time_morning)}")
                        early_check_out_minute += calculate_minutes_difference(working_hours["morning"]["end"], early_check_out_time_morning)
                    if early_check_out_time_afternoon < working_hours["afternoon"]["end"]:
                        early_check_out += 1
                        print(f"ve som: {str(early_check_out_time_afternoon)}")
                        early_check_out_minute += calculate_minutes_difference(working_hours["afternoon"]["end"], early_check_out_time_afternoon)
                            
                    
                    total_hours_per_month += total_hours_per_day

                    if include_evening_shift:
                        work_day_per_day = total_hours_per_day / 10
                    else:
                        work_day_per_day = total_hours_per_day / 8

                    work_day_per_month += work_day_per_day

                    # Check if total_hours_per_day is zero and the day is not a Sunday
                    if total_hours_per_day == 0 and day_of_week != 'Sunday':
                        absent_days.append((day, day_of_week))
                    
                    # Print the results for the day
                    print(total_hours_per_day)
                
                # After the loop, print the total hours and workdays
                employee_workshift_tracking[department][workshop][person]["total_hours_per_month"] = total_hours_per_month
                print(f"gio lam: {total_hours_per_month}")
                employee_workshift_tracking[department][workshop][person]["work_day_per_month"] = work_day_per_month
                print(f"ngay lam: {work_day_per_month}")
                
                # Print the absent days
                if absent_days:
                    print(f"Absent days (excluding Sundays): {absent_days}")
                    employee_workshift_tracking[department][workshop][person]["absent_count"] = len(absent_days)
                else:
                    employee_workshift_tracking[department][workshop][person]["absent_count"] = 0
                    print("No absences recorded on workdays.")

                if late_check_in >= 0:
                    employee_workshift_tracking[department][workshop][person]["late_check_in"] = late_check_in
                    employee_workshift_tracking[department][workshop][person]["late_check_in_minute"] = late_check_in_minute
                    print(f"Di muon {late_check_in} lan, thoi gian di muon {late_check_in_minute} phut")
                if early_check_out >= 0:
                    employee_workshift_tracking[department][workshop][person]["early_check_out"] = early_check_out
                    employee_workshift_tracking[department][workshop][person]["early_check_out_minute"] = early_check_out_minute
                    print(f"Ve som {early_check_out} lan, thoi gian di muon {early_check_out_minute} phut")


    # Create a DataFrame for the table with adjusted days
    columns = ['STT', 'Mã nhân viên', 'Tên nhân viên'] + [''] + days_in_month + [
        'Ngày công', 'Ngày công', 'Giờ công', 'Giờ công', 'Vào trễ', 'Vào trễ', 'Ra sớm', 'Ra sớm', 'Tăng ca (giờ)', 'Tăng ca (giờ)', 'Tăng ca (giờ)', 'Vắng KP', 'Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ','Ngày nghỉ',
    ]

    # Ensure sub_headers has the correct length
    sub_headers = [''] * 4 + days_of_week + ['NT', 'CT', 'NT', 'CT', 'Lần', 'Phút', 'Lần', 'Phút', 'TC1', 'TC2', 'TC3', 'Vắng KP', 'OM', 'TS', 'R', 'Ro', 'P', 'F', 'CO', 'CD', 'H', 'CT', 'Le']

    # Check if columns and sub_headers match
    assert len(columns) == len(sub_headers), "The number of sub-headers does not match the number of columns."

    # Create DataFrame and insert sub-headers
    output_df = pd.DataFrame(columns=columns)
    output_df.loc[-1] = sub_headers  # Adding sub-headers for days of the week
    output_df.index = output_df.index + 1  # Adjust the index
    output_df = output_df.sort_index()  # Sort by index

    information_row = ["Đơn vị: Công ty CP TM NT Toàn Cầu"] + (output_df.shape[1] - 1) * ['']
    # Append the new row to the DataFrame
    output_df.loc[len(output_df)] = information_row
    location_row = ["Địa chỉ: Thôn Viềng- Mỹ Phúc- Mỹ Lộc Nam Định"] + (output_df.shape[1] - 1) * ['']
    # Append the new row to the DataFrame
    output_df.loc[len(output_df)] = location_row
    ad_row_1 = ["BẢNG THỐNG KÊ CHẤM CÔNG"] + (output_df.shape[1] - 1) * ['']
    # Append the new row to the DataFrame
    output_df.loc[len(output_df)] = ad_row_1
    ad_row_1 = [f"Từ ngày 01/{month}/{year} đến ngày {num_days}/{month}/{year}"] + (output_df.shape[1] - 1) * ['']
    # Append the new row to the DataFrame
    output_df.loc[len(output_df)] = ad_row_1

    for department in employee_workshift_tracking.keys():
        department_row = [f"Phòng ban: {department}"] + (output_df.shape[1] - 1) * ['']
        # Append the new row to the DataFrame
        output_df.loc[len(output_df)] = department_row
        for workshop in employee_workshift_tracking[department].keys():
            workshop_row = [f"   Xưởng: {workshop}"] + (output_df.shape[1] - 1) * ['']
            # Append the new row to the DataFrame
            output_df.loc[len(output_df)] = workshop_row

            #start ordinal_number
            ordinal_number = 1

            for person in employee_workshift_tracking[department][workshop]:
                person_dict = employee_workshift_tracking[department][workshop][person]
                for i in range(len(person_dict["work_load"][0])):
                    for j in range(2):
                        if i == 0 and j == 0:
                            information_row = [str(ordinal_number)] + [person] + [person_dict["name"]]
                            ordinal_number += 1
                            if j == 0:
                                information_row += [f"Vào {i + 1}"]
                            else:
                                information_row += [f"Ra {i + 1}"]

                            for k in range(len(person_dict["work_load"])):
                                information_row.append(person_dict["work_load"][k][i][j])

                            #add ngay cong NT:
                            information_row += [person_dict["work_day_per_month"]] + [""]
                            #add gio cong NT
                            information_row += [person_dict["total_hours_per_month"]] + [""]
                            #add vao tre
                            information_row += [person_dict["late_check_in"]] + [person_dict["late_check_in_minute"]]
                            #add ra som
                            information_row += [person_dict["early_check_out"]] + [person_dict["early_check_out_minute"]]
                            #add tang ca
                            information_row += [""] * 3
                            #add ngay vang
                            information_row += [person_dict["absent_count"]]
                            #add ngay nghi
                            information_row += (output_df.shape[1] - len(information_row)) * ['']

                        else:
                            information_row = [""] * 3
                            if j == 0:
                                information_row += [f"Vào {i + 1}"]
                            else:
                                information_row += [f"Ra {i + 1}"]

                            for k in range(len(person_dict["work_load"])):
                                information_row.append(person_dict["work_load"][k][i][j])

                            information_row += (output_df.shape[1] - len(information_row)) * ['']

                        output_df.loc[len(output_df)] = information_row
                



    # Display the DataFrame
    print(output_df.shape)
    return output_df

