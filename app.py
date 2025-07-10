import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import contextlib
import json
import textwrap
import re

# ------------------ Google Sheets Setup ------------------
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["google_sheets"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
SHEET_NAME = "CodingCourse"  # Google Sheet with tabs: Users, Submissions, Content

@st.cache_resource

def get_sheets():
    creds_dict = st.secrets["google_sheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet_users = client.open(SHEET_NAME).worksheet("Users")
    sheet_submissions = client.open(SHEET_NAME).worksheet("Submissions")
    sheet_content = client.open(SHEET_NAME).worksheet("Content")
    return sheet_users, sheet_submissions, sheet_content

sheet_users, sheet_submissions, sheet_content = get_sheets()

# ------------------ User System ------------------
def load_users():
    records = sheet_users.get_all_records()
    return {row["username"]: row["password"] for row in records}

def login_user(username, password):
    records = sheet_users.get_all_records()
    for row in records:
        if row["username"] == username:
            if row["password"] != password:
                return False, "Incorrect password."
            allowed_raw = row.get("allowed_categories", "").strip()
            allowed_categories = [c.strip() for c in allowed_raw.split(",")] if allowed_raw else None  # None means full access
            return True, {"username": username, "allowed_categories": allowed_categories}
    return False, "User does not exist."



# ------------------ Course Content ------------------
def load_course():
    records = sheet_content.get_all_records()
    # Must have 'category', 'section', and 'content' columns
    course = {}
    for row in records:
        category = row["category"]
        section = row["section"]
        content = row["content"]
        if category not in course:
            course[category] = {}
        if section not in course[category]:
            course[category][section] = []
        course[category][section].append(content)
    return course


def display_course_section(username, section_name, section_content):
    st.header(section_name)
    for content in section_content:
        st.markdown(f"### {section_name}")
        st.markdown(content.replace("\n", "\n\n"))

    with st.form(f"form_{section_name}"):
        st.subheader("Submit")
        submission_title = st.text_input("Submission Title")
        code = st.text_area("Paste your Python code here")
        submit = st.form_submit_button("Submit")
        if submit and submission_title:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet_submissions.append_row([username, section_name, submission_title, code, timestamp])
            st.success("Submission received!")
        elif submit:
            st.error("Please provide a title for your submission.")

# ------------------ User Submissions ------------------
def show_user_submissions(username, section):
    st.subheader("📂 Your Submissions for This Section")
    all_rows = sheet_submissions.get_all_records()

    user_notes = [(idx + 2, row) for idx, row in enumerate(all_rows)
                  if row.get("username") == username and row.get("section") == section]

    if not user_notes:
        st.info("No past submissions for this section.")
    else:
        for row_num, note in user_notes:
            feedback = note.get("feedback", "")
            grade = note.get("grade", "")
            is_graded = bool(feedback or grade)

            with st.expander(f"{note['title']} - {note['timestamp']}"):
                st.markdown("### Code:")
                st.code(note["code"], language="python")

                if is_graded:
                    st.markdown(f"**📝 Feedback:** {feedback}")
                    st.markdown(f"**✅ Grade:** {grade}")
                    st.info("This submission has been graded and cannot be edited.")
                else:
                    edited_code = st.text_area("Edit your code:", note["code"], key=f"edit_{row_num}")
                    if st.button("Save Changes", key=f"save_{row_num}"):
                        sheet_submissions.update_cell(row_num, 4, edited_code)  # column 4 = code
                        st.success("Updated successfully.")
                    if st.button("Delete Submission", key=f"delete_{row_num}"):
                        sheet_submissions.delete_rows(row_num)
                        st.warning("Submission deleted. Please refresh.")

def run_python_playground():
    st.title("🧪 Python Playground")
    st.write("Type Python code below and run it. You can't install packages or use `input()` directly.")

    # Simulated input value
    fake_input = st.text_input("Simulated input() value")

    code = st.text_area("Your Python Code", height=200)

    if st.button("Run Code"):
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                with contextlib.redirect_stderr(output):
                    # Restrict built-ins and override input()
                    exec(code, {
                        "__builtins__": {
                            "print": print,
                            "range": range,
                            "len": len,
                            "int": int,
                            "float": float,
                            "str": str,
                            "list": list,
                            "dict": dict,
                            "set": set,
                            "tuple": tuple,
                            "bool": bool,
                            "enumerate": enumerate,
                            "zip": zip,
                            "abs": abs,
                            "min": min,
                            "max": max,
                            "sum": sum,
                            "input": lambda prompt="": fake_input
                        }
                    })
        except Exception as e:
            output.write(f"⚠️ Error: {e}")

        st.code(output.getvalue(), language="text")

def main():
    st.set_page_config("Python Course Portal", layout="wide")
    st.title("Brainiac Learning")
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if not st.session_state.logged_in:
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            success, result = login_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.username = result["username"]
                st.session_state.allowed_categories = result["allowed_categories"]  # None = see all
                st.rerun()
            else:
                st.error(result)


    else:

        st.sidebar.success(f"Logged in as {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.allowed_categories = None
            for k in list(st.session_state.keys()):
                if k.startswith("select_"):
                    del st.session_state[k]  # Clear dropdown selections
            st.rerun()

        course = load_course()
        selected_section = None

        tool = st.sidebar.radio("Select a tool", ["Course", "Python Playground"])

        if tool == "Python Playground":
            run_python_playground()
        else:
            st.sidebar.markdown("## 📚 Course Sections")

            for category, sections in course.items():
                # Check if user has access
                allowed = st.session_state.allowed_categories
                if allowed is not None and category not in allowed:
                    continue  # Skip if not allowed

                section_names = ["None"] + list(sections.keys())
                selected = st.sidebar.selectbox(f"Select section under {category}", section_names, key=f"select_{category}")

                if selected != "None":
                    selected_section = (category, selected)

            if selected_section:
                category, section_name = selected_section
                display_course_section(st.session_state.username, section_name, course[category][section_name])
                st.markdown("---")
                show_user_submissions(st.session_state.username, section_name)
            else:
                st.info("Please select a lesson section from the sidebar.")


if __name__ == "__main__":
    main()
