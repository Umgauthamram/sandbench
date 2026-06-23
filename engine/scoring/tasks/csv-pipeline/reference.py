"""Reference solution for csv-pipeline task."""
import csv
import io


def transform_csv(csv_text):
    """Transform CSV text into a department-level summary."""
    text = csv_text.strip()
    if not text:
        return {"departments": {}, "total_employees": 0, "highest_paid": None}

    reader = csv.DictReader(io.StringIO(text))
    departments = {}
    highest_paid = None
    total_employees = 0

    for row in reader:
        name = row["name"].strip()
        dept = row["department"].strip()
        salary = float(row["salary"].strip())
        total_employees += 1

        if dept not in departments:
            departments[dept] = {
                "count": 0,
                "total_salary": 0.0,
                "avg_salary": 0.0,
                "employees": [],
            }

        departments[dept]["count"] += 1
        departments[dept]["total_salary"] += salary
        departments[dept]["employees"].append(name)

        if highest_paid is None or salary > highest_paid["salary"]:
            highest_paid = {"name": name, "salary": salary}

    # Compute averages
    for dept_data in departments.values():
        dept_data["avg_salary"] = round(
            dept_data["total_salary"] / dept_data["count"], 2
        )

    return {
        "departments": departments,
        "total_employees": total_employees,
        "highest_paid": highest_paid,
    }
