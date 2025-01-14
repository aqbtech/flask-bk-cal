from flask import Flask, render_template, request
from bs4 import BeautifulSoup

app = Flask(__name__)


# Chuyển đổi điểm chữ sang hệ thống GPA
def letter_grade_to_gpa(letter_grade):
    gpa_scale = {
        'A+': 4.0,
        'A': 4.0,
        'B+': 3.5,
        'B': 3.0,
        'C+': 2.5,
        'C': 2.0,
        'D+': 1.5,
        'D': 1.0,
        'F': 0.0,
        'MT': None,  # Not included in GPA calculation
        'RT': None  # Not included in GPA calculation
    }
    return gpa_scale.get(letter_grade, None)


# Gán giá trị để sắp xếp và gợi ý môn cải thiện
def letter_grade_to_sort_value(letter_grade):
    grade_sort_value = {
        'A+': 4.0,
        'A': 4.0,
        'B+': 3.5,
        'B': 3.0,
        'C+': 2.5,
        'C': 2.0,
        'D+': 1.5,
        'D': 1.0,
        'F': 0.0,
        'MT': 4.5,  # Assign a value for sorting purpose
        'RT': 3.5  # Assign a value for sorting purpose
    }
    return grade_sort_value.get(letter_grade, 0)


def parse_course_info(html_string: str):
    soup = BeautifulSoup(html_string, 'html.parser')
    course_dict = {}

    tables = soup.find_all('table')
    for table in tables:
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            course_code = cols[0].text.strip()
            course_name = cols[1].text.strip()
            credits_num = int(cols[2].text.strip())
            score_text = cols[4].text.strip()
            letter_grade = cols[5].text.strip()

            try:
                score = float(score_text)
            except ValueError:
                score = score_text  # Keep as text if conversion fails

            gpa = letter_grade_to_gpa(letter_grade)

            if course_code not in course_dict:
                course_dict[course_code] = [course_code, course_name, credits_num, score, letter_grade, gpa]
            else:
                existing_entry = course_dict[course_code]
                if isinstance(score, float) and isinstance(existing_entry[3], float):
                    if score > existing_entry[3]:
                        course_dict[course_code] = [course_code, course_name, credits_num, score, letter_grade, gpa]
                elif isinstance(score, float) and score >= 4.0:
                    course_dict[course_code] = [course_code, course_name, credits_num, score, letter_grade, gpa]
                elif isinstance(existing_entry[3], float) and existing_entry[3] >= 4.0:
                    pass  # Keep existing entry
                else:
                    course_dict[course_code] = [course_code, course_name, credits_num, score, letter_grade, gpa]

    return list(course_dict.values())


def calculate_gpa(courses):
    total_credits = 0
    total_points = 0
    for course in courses:
        if course[5] is not None:
            total_credits += course[2]
            total_points += course[2] * course[5]
    return round(total_points / total_credits, 3) if total_credits > 0 else 0


def calculate_required_gpa(current_gpa, total_credits_earned, remaining_credits, target_gpa):
    required_gpa = ((target_gpa * (total_credits_earned + remaining_credits)) - (
            current_gpa * total_credits_earned)) / remaining_credits
    return round(required_gpa, 3)


def suggest_courses_to_improve(courses, num_suggestions):
    filtered_courses = [course for course in courses if course[3] not in ['MT', 'RT', 'DT'] and course[2] > 0]
    sorted_courses = sorted(filtered_courses, key=lambda x: (
        letter_grade_to_sort_value(x[4]) if x[4] else x[3] if isinstance(x[3], float) else 0))
    return sorted_courses[:num_suggestions]


def improve_gpa(courses, improvement_courses):
    improved_courses = courses.copy()
    for imp_course in improvement_courses:
        for i, course in enumerate(improved_courses):
            if course[0] == imp_course[0]:  # Compare course_code
                improved_courses[i] = imp_course  # Update with improved score
                break
    return improved_courses


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        courses_html = request.form["courses_html"]
        total_credits_cddt = request.form["total_credits_cddt"]
        parsed_courses = parse_course_info(courses_html)
        return render_template("index.html", parsed_courses=parsed_courses, total_credits_cddt=total_credits_cddt)

    return render_template("index.html")


@app.route("/calculate_gpa", methods=["POST"])
def calculate_gpa_route():
    courses_html = request.form["courses_html"]
    total_credits_cddt = int(request.form["total_credits_cddt"])
    parsed_courses = parse_course_info(courses_html)

    gpa = calculate_gpa(parsed_courses)
    total_credits_earned = sum([course[2] for course in parsed_courses])
    remaining_credits = total_credits_cddt - total_credits_earned
    return render_template("index.html", gpa=gpa, total_credits_earned=total_credits_earned,
                           parsed_courses=parsed_courses, total_credits_cddt=total_credits_cddt,
                           remaining_credits=remaining_credits)


@app.route("/calculate_required_gpa", methods=["POST"])
def calculate_required_gpa_route():
    target_gpa = float(request.form["target_gpa"])
    courses_html = request.form["courses_html"]
    total_credits_cddt = int(request.form["total_credits_cddt"])
    parsed_courses = parse_course_info(courses_html)

    gpa = calculate_gpa(parsed_courses)
    total_credits_earned = sum([course[2] for course in parsed_courses])
    remaining_credits = total_credits_cddt - total_credits_earned
    required_gpa = calculate_required_gpa(gpa, total_credits_earned, remaining_credits, target_gpa)

    return render_template("index.html", gpa=gpa, total_credits_earned=total_credits_earned, required_gpa=required_gpa,
                           parsed_courses=parsed_courses, total_credits_cddt=total_credits_cddt,
                           remaining_credits=remaining_credits)


@app.route("/suggest_courses", methods=["POST"])
def suggest_courses_route():
    num_suggestions = int(request.form["num_suggestions"])
    courses_html = request.form["courses_html"]
    total_credits_cddt = request.form["total_credits_cddt"]
    parsed_courses = parse_course_info(courses_html)

    suggested_courses = suggest_courses_to_improve(parsed_courses, num_suggestions)

    return render_template("index.html", suggested_courses=suggested_courses, parsed_courses=parsed_courses,
                           total_credits_cddt=total_credits_cddt)

@app.route("/improve_courses", methods=["POST"])
def improve_courses():
    courses_html = request.form["courses_html"]
    total_credits_cddt = int(request.form["total_credits_cddt"])

    parsed_courses = parse_course_info(courses_html)
    improvement_courses = []

    # Extract the improved courses from the form
    for course in parsed_courses:
        course_code = course[0]
        improved_grade = request.form.get(f"improved_grade_{course_code}", course[4])
        improved_score = request.form.get(f"improved_score_{course_code}", course[3])
        improved_score = float(improved_score) if improved_score else course[3]
        improved_gpa = letter_grade_to_gpa(improved_grade)
        improvement_courses.append([course_code, course[1], course[2], improved_score, improved_grade, improved_gpa])

    improved_courses = improve_gpa(parsed_courses, improvement_courses)
    gpa = calculate_gpa(improved_courses)
    total_credits_earned = sum([course[2] for course in improved_courses])
    remaining_credits = total_credits_cddt - total_credits_earned

    return render_template("index.html", gpa=gpa, total_credits_earned=total_credits_earned,
                           improved_courses=improved_courses, parsed_courses=parsed_courses,
                           total_credits_cddt=total_credits_cddt, remaining_credits=remaining_credits)

if __name__ == "__main__":
    app.run(port=5001)
