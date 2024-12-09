from flask import Flask, request, jsonify
import re
# from markupsafe import Markup

app = Flask(__name__)

def parse_single_subject_schedules(text):
    day_map = {
        'Thứ 2': 'Monday',
        'Thứ 3': 'Tuesday',
        'Thứ 4': 'Wednesday',
        'Thứ 5': 'Thursday',
        'Thứ 6': 'Friday',
        'Thứ 7': 'Saturday'
    }

    lines = text.strip().split('\n')
    i = 0

    first_line = lines[i].strip()
    i += 1
    subject_match = re.match(r'^([A-Za-z0-9]{6})\s*-\s*(.+)$', first_line)
    if subject_match:
        subject_id = subject_match.group(1)
        subject_name = subject_match.group(2)
    else:
        subject_id = ''
        subject_name = first_line

    # skip Nhóm lớp...
    while i < len(lines) and ('Nhóm lớp' in lines[i] or lines[i].strip() == '' or lines[i].strip().startswith('#')):
        i += 1

    classes = []
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if not line.startswith('CC'):
            i += 1
            continue
        class_cols = line.split('\t')
        class_cols = [c.strip() for c in class_cols]
        
        cg = class_cols[0] if len(class_cols) > 0 else ''
        reg_cap = class_cols[1] if len(class_cols) > 1 else ''
        language = class_cols[2] if len(class_cols) > 2 else ''
        main_class = class_cols[3] if len(class_cols) > 3 else ''
        main_lecturer = class_cols[4] if len(class_cols) > 4 else ''
        side_class = class_cols[5] if len(class_cols) > 5 else ''
        side_lecturer = class_cols[6] if len(class_cols) > 6 else ''
        mcc_str = class_cols[7] if len(class_cols) > 7 else '0'
        try:
            main_class_capacity = int(mcc_str)
        except:
            main_class_capacity = 0

        i += 1
        # skip Thứ Tiết...
        while i < len(lines) and (lines[i].strip().startswith("Thứ ") or lines[i].strip() == '' or lines[i].strip().startswith('#')):
            i += 1

        schedules = []
        while i < len(lines):
            day_line = lines[i].strip()
            if not day_line:
                i += 1
                continue
            if day_line.startswith('CC'):
                # next class
                break
            if day_line.startswith("Nhóm lớp") or day_line.startswith("Thứ ") or day_line.startswith('#'):
                i += 1
                continue
            if day_line.startswith("Thứ"):
                day_cols = day_line.split('\t')
                day_cols = [c.strip() for c in day_cols]

                dow = day_cols[0] if len(day_cols) > 0 else ''
                time_pattern = day_cols[1] if len(day_cols) > 1 else ''
                room = day_cols[2] if len(day_cols) > 2 else ''
                campus_str = day_cols[3] if len(day_cols) > 3 else ''
                btn_tn = day_cols[4] if len(day_cols) > 4 else ''
                weeks_str = day_cols[5] if len(day_cols) > 5 else ''

                day_of_week = day_map.get(dow, dow)
                experiment = False

                time_slots = [int(x) for x in time_pattern.split() if x.isdigit()]
                if time_slots:
                    start_slot = min(time_slots)
                    end_slot = max(time_slots)
                    start_time = start_slot + 5
                    end_time = end_slot + 5 + 1
                    start_str = f"{start_time}:00"
                    end_str = f"{end_time}:00"
                else:
                    start_str = None
                    end_str = None

                try:
                    campus = int(campus_str)
                except:
                    campus = None

                study_weeks = [int(d) for d in re.findall(r'\d', weeks_str)]

                schedules.append({
                    'day_of_week': day_of_week,
                    'start_time': start_str,
                    'end_time': end_str,
                    'room': room,
                    'campus': campus,
                    'experiment': experiment,
                    'study_weeks': study_weeks
                })
                i += 1
            else:
                i += 1

        classes.append({
            'class_group': cg,
            'registered_capacity': reg_cap,
            'language': language,
            'main_class': main_class,
            'main_lecturer': main_lecturer,
            'side_class': side_class,
            'side_lecturer': side_lecturer,
            'main_class_capacity': main_class_capacity,
            'schedules': schedules
        })

    return {
        'subject_id': subject_id,
        'subject_name': subject_name,
        'classes': classes
    }


def visualize_calendar_html(subjects, selections):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_to_col = {d: i for i, d in enumerate(days)}

    min_hour = 6
    max_hour = 22
    found_any = False
    for subj in subjects:
        sid = subj['subject_id']
        chosen_class = selections.get(sid)
        if chosen_class is not None and 0 <= chosen_class < len(subj['classes']):
            for sch in subj['classes'][chosen_class]['schedules']:
                if sch['start_time'] and sch['end_time']:
                    start_h = int(sch['start_time'].split(':')[0])
                    end_h = int(sch['end_time'].split(':')[0])
                    if not found_any:
                        min_hour = start_h
                        max_hour = end_h
                        found_any = True
                    else:
                        min_hour = min(min_hour, start_h)
                        max_hour = max(max_hour, end_h)

    height = max_hour - min_hour
    width = 7

    # calendar_grid hold lists of schedule blocks, not just a single string
    calendar_grid = [[[] for _ in range(width)] for _ in range(height)]

    subject_colors = {}
    color_list = ["lightblue", "lightgreen", "lightpink", "lightyellow", "lightgray", "orange", "lightcoral"]
    for i, subj in enumerate(subjects):
        sid = subj['subject_id']
        subject_colors[sid] = color_list[i % len(color_list)]

    # calendar
    for subj in subjects:
        sid = subj['subject_id']
        sname = subj['subject_name']
        bgcolor = subject_colors[sid]
        chosen_class = selections.get(sid, None)
        if chosen_class is not None and 0 <= chosen_class < len(subj['classes']):
            chosen = subj['classes'][chosen_class]
            for sch in chosen['schedules']:
                day = sch['day_of_week']
                if day not in day_to_col:
                    continue
                col = day_to_col[day]
                if sch['start_time'] and sch['end_time']:
                    start_h = int(sch['start_time'].split(':')[0])
                    end_h = int(sch['end_time'].split(':')[0])
                    for hour in range(start_h, end_h):
                        row = hour - min_hour
                        if 0 <= row < height:
                            # collision
                            block_html = f'<div style="background:{bgcolor};width:100%;height:100%;border:1px solid #ccc;">{sname}</div>'
                            calendar_grid[row][col].append(block_html)

    html = ['<table border="1" cellspacing="0" cellpadding="2" style="border-collapse:collapse;">']
    html.append("<tr><th>Time</th>" + "".join(f"<th>{d}</th>" for d in days) + "</tr>")

    for hour in range(min_hour, max_hour):
        r = hour - min_hour
        row_html = [f"<td>{hour}:00</td>"]
        for c in range(width):
            cell_schedules = calendar_grid[r][c]
            if len(cell_schedules) == 0:
                cell_content = "&nbsp;"
            elif len(cell_schedules) == 1:
                # only one schedule, just display it
                cell_content = cell_schedules[0]
            else:
                # collision - show schedules side-by-side
                count = len(cell_schedules)
                width_percentage = 100 / count
                combined = ""
                for sched in cell_schedules:
                    combined += f'<div style="display:inline-block;width:{width_percentage}%;vertical-align:top;">{sched}</div>'
                # indicate collision
                cell_content = f'<div style="border:2px solid red;">{combined}</div>'

            row_html.append(f"<td style='width:100px;height:50px;vertical-align:top;'>{cell_content}</td>")

        html.append("<tr>" + "".join(row_html) + "</tr>")

    html.append("</table>")
    return "\n".join(html)


# data
subject_data1 = """
IM1019 - Tiếp thị căn bản
Nhóm lớp	DK/ Sĩ số	Ngôn ngữ	Nhóm LT	Giảng viên	Nhóm BT	Giảng viên BT/TN	Sĩ số LT	#
CC01	70/70	TA	CC01				70	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - 8 9 - - - - - - -	B10-203	1		12--56789-12----789012--------
CC02	32/70	TA	CC02				70	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - - 9 10 - - - - - -	B1-208	1		12--56789-12----789012--------
CC03	31/70	TA	CC03				70	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - 7 8 - - - - - - - -	B8-304	1		12--56789-12----789012--------
"""
subject_data2 = """
MT2013 - Xác suất và thống kê
Nhóm lớp	DK/ Sĩ số	Ngôn ngữ	Nhóm LT	Giảng viên	Nhóm BT	Giảng viên BT/TN	Sĩ số LT	#
CC01	60/80	TA	CC01				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - - 8 9 10 - - - - - -	B4-306	1		12--56789-12345678------------
CC02	60/80	TA	CC02				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- 2 3 4 - - - - - - - - - - - -	B4-604	1		12--56789-12345678------------
CC03	61/80	TA	CC03				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- - - - - - - - - 10 11 12 - - - -	C5-301	1		12--56789-12345678------------
CC04	60/80	TA	CC04				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- 2 3 4 - - - - - - - - - - - -	B1-208	1		12--56789-12345678------------
CC05	60/80	TA	CC05				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- 2 3 4 - - - - - - - - - - - -	B4-604	1		12--56789-12345678------------
CC06	59/80	TA	CC06				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- - - - - - - - 9 10 11 - - - - -	B4-502	1		12--56789-12345678------------
CC07	59/80	TA	CC07				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - 8 9 10 - - - - - -	C4-403	1		12--56789-12345678------------
CC08	59/80	TA	CC08				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- 2 3 4 - - - - - - - - - - - -	B1-212	1		12--56789-12345678------------
CC09	53/80	TA	CC09				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - 4 5 6 - - - - - - - - - -	B4-604	1		12--56789-12345678------------
CC10	58/80	TA	CC10				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - - - 10 11 12 - - - -	B4-601	1		12--56789-12345678------------
CC11	59/80	TA	CC11				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - 8 9 10 - - - - - -	C4-502	1		12--56789-12345678------------
CC12	59/80	TA	CC12				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- 2 3 4 - - - - - - - - - - - -	C4-304	1		12--56789-12345678------------
"""
subject_data3 = """
CO2039 - Lập trình nâng cao
Nhóm lớp	DK/ Sĩ số	Ngôn ngữ	Nhóm LT	Giảng viên	Nhóm BT	Giảng viên BT/TN	Sĩ số LT	#
CC01	72/80	TA	CC01				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- - - - - - - - - 10 11 - - - - -	B4-505	1		12--56789-12345678------------
CC02	71/80	TA	CC02				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- - - - - - - 8 9 - - - - - - -	B4-601	1		12--56789-12345678------------
CC03	71/80	TA	CC03				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - 7 8 - - - - - - - -	C5-301	1		12--56789-12345678------------
CC04	71/80	TA	CC04				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - - 9 10 - - - - - -	C6-501	1		12--56789-12345678------------
CC05	70/80	TA	CC05				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- 2 3 - - - - - - - - - - - - -	B1-212	1		12--56789-12345678------------
"""
subject_data4 = """
SP1033 - K/tế chính trị Mác-Lênin
Nhóm lớp	DK/ Sĩ số	Ngôn ngữ	Nhóm LT	Giảng viên	Nhóm BT	Giảng viên BT/TN	Sĩ số LT	#
CC01	53/80	V	CC01				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - 4 5 - - - - - - - - - - -	B1-311	1		12--56789-12345---------------
CC02	55/80	V	CC02				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - - - - - 11 12 - - - -	B4-502	1		12--56789-12345---------------
CC03	60/80	V	CC03				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- 2 3 - - - - - - - - - - - - -	B1-311	1		12--56789-12345---------------
CC04	54/80	V	CC04				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - 4 5 - - - - - - - - - - -	C5-503	1		12--56789-12345---------------
CC05	59/80	V	CC05				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - - - - 11 12 - - - -	B1-208	1		12--56789-12345---------------
CC06	56/80	V	CC06				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- 2 3 - - - - - - - - - - - - -	B1-213	1		12--56789-12345---------------
CC07	57/80	V	CC07				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - - 9 10 - - - - - -	C4-304	1		12--56789-12345---------------
CC08	57/80	V	CC08				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - - - - 11 12 - - - -	C4-301	1		12--56789-12345---------------
CC09	55/80	V	CC09				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - 7 8 - - - - - - - -	C4-403	1		12--56789-12345---------------
CC10	55/80	V	CC10				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - - - 9 10 - - - - - -	C4-502	1		12--56789-12345---------------
CC11	58/80	V	CC11				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - 8 9 - - - - - - -	B4-305	1		12--56789-12345---------------
CC12	61/80	V	CC12				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- 2 3 - - - - - - - - - - - - -	C6-503	1		12--56789-12345---------------
CC13	56/80	V	CC13				80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- - - 4 5 - - - - - - - - - - -	B1-311	1		12--56789-12345---------------
"""
subject_data5 = """
CO2017 - Hệ điều hành
Nhóm lớp	DK/ Sĩ số	Ngôn ngữ	Nhóm LT	Giảng viên	Nhóm BT	Giảng viên BT/TN	Sĩ số LT	#
CC01_CC01	37/40	TA	CC01		CC01		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - 8 9 10 11 12 - - - -	B9-303	1		--------9-1-3-5---------------
Thứ 6	- 2 3 - - - - - - - - - - - - -	C5-303	1		12--56789-12345678------------
CC01_CC02	37/40	TA	CC01		CC02		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- - - - - - - 8 9 10 11 12 - - - -	B9-303	1		-------8---2-4-6--------------
Thứ 6	- 2 3 - - - - - - - - - - - - -	C5-303	1		12--56789-12345678------------
CC02_CC03	37/40	TA	CC02		CC03		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- 2 3 4 5 6 - - - - - - - - - -	C6-102	1		-------8---2-4-6--------------
Thứ 6	- - - - 5 6 - - - - - - - - - -	B4-502	1		12--56789-12345678------------
CC02_CC04	36/40	TA	CC02		CC04		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 6	- - - - 5 6 - - - - - - - - - -	B4-502	1		12--56789-12345678------------
Thứ 6	- - - - - - - 8 9 10 11 12 - - - -	C6-103	1		--------9-1-3-5---------------
CC03_CC05	37/40	TA	CC03		CC05		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - - 8 9 10 11 12 - - - -	C6-102	1		--------9-1-3-5---------------
Thứ 5	- - - - - - 7 8 - - - - - - - -	C5-303	1		12--56789-12345678------------
CC03_CC06	37/40	TA	CC03		CC06		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 3	- - - - - - - 8 9 10 11 12 - - - -	B9-303	1		--------9-1-3-5---------------
Thứ 5	- - - - - - 7 8 - - - - - - - -	C5-303	1		12--56789-12345678------------
CC04_CC07	35/40	TA	CC04		CC07		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- - - - - - - - 9 10 - - - - - -	C4-502	1		12--56789-12345678------------
Thứ 6	- - - - - - - 8 9 10 11 12 - - - -	C6-102	1		--------9-1-3-5---------------
CC04_CC08	37/40	TA	CC04		CC08		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 5	- - - - - - - - 9 10 - - - - - -	C4-502	1		12--56789-12345678------------
Thứ 6	- 2 3 4 5 6 - - - - - - - - - -	C6-102	1		--------9-1-3-5---------------
CC05_CC09	35/40	TA	CC05		CC09		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 2	- 2 3 4 5 6 - - - - - - - - - -	C6-102	1		--------9-1-3-5---------------
Thứ 4	- - - - - - - - 9 10 - - - - - -	B1-311	1		12--56789-12345678------------
CC05_CC10	36/40	TA	CC05		CC10		80	
Thứ	Tiết	Phòng	CS	BT/TN	Tuần học
Thứ 4	- - - - - - - - 9 10 - - - - - -	B1-311	1		12--56789-12345678------------
Thứ 5	- - - - - - - 8 9 10 11 12 - - - -	C6-102	1		--------9-1-3-5---------------
"""

parsed_subject1 = parse_single_subject_schedules(subject_data1)
parsed_subject2 = parse_single_subject_schedules(subject_data2)
parsed_subject3 = parse_single_subject_schedules(subject_data3)
parsed_subject4 = parse_single_subject_schedules(subject_data4)
parsed_subject5 = parse_single_subject_schedules(subject_data5)

subjects = [parsed_subject1, parsed_subject2, parsed_subject3, parsed_subject4, parsed_subject5]




# initial selections
selections = {
    parsed_subject1['subject_id']: 0,
    parsed_subject2['subject_id']: 0,
    parsed_subject3['subject_id']: 0,
    parsed_subject4['subject_id']: 0,
    parsed_subject5['subject_id']: 0
}


@app.route("/")
def index():
    calendar_html = visualize_calendar_html(subjects, selections)
    form_html = []
    form_html.append("<h2>Selection section:</h2>")
    for subj in subjects:
        sname = subj['subject_name']
        sid = subj['subject_id']
        form_html.append(f"<div><b>{sname}:</b> ")
        for idx, cinfo in enumerate(subj['classes']):
            checked = "checked" if selections.get(sid,0) == idx else ""
            form_html.append(f'<label style="margin-right:20px;">')
            form_html.append(f'<input type="radio" name="{sid}" value="{idx}" {checked} onchange="updateSelection(\'{sid}\', {idx})"> {cinfo["class_group"]}')
            form_html.append('</label>')
        form_html.append("</div><br>")

    full_html = f"""
<html>
<head><title>Schedule Viewer</title></head>
<body style="margin:0;padding:0;font-family:sans-serif;">
<h1 style="text-align:center;">Schedule Picker</h1>
<div style="display:flex;flex-direction:row;width:100%;height:90vh;">
  <div style="flex:1;padding:20px;overflow:auto;">
    <div id="calendar-container">
      {calendar_html}
    </div>
  </div>
  <div style="flex:1;padding:20px;overflow:auto;border-left:1px solid #ccc;">
    {''.join(form_html)}
  </div>
</div>
<script>
function updateSelection(subject_id, class_index) {{
    fetch('/update_selection', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json'
        }},
        body: JSON.stringify({{ subject_id: subject_id, class_index: class_index }})
    }})
    .then(response => response.json())
    .then(data => {{
        document.getElementById('calendar-container').innerHTML = data.calendar_html;
    }});
}}
</script>
</body>
</html>
"""
    return full_html

@app.route("/update_selection", methods=["POST"])
def update_selection():
    data = request.get_json()
    sid = data['subject_id']
    class_idx = data['class_index']
    selections[sid] = class_idx
    new_calendar = visualize_calendar_html(subjects, selections)
    return jsonify({"calendar_html": new_calendar})

if __name__ == "__main__":
    app.run(debug=True)

