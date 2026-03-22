import streamlit as st

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

import pandas as pd
import base64, random, os, re
import datetime
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
import pdfplumber
import io
import pymysql
from courses import ds_course,ml_course,web_course,android_course,ios_course,uiux_course,resume_videos,interview_videos
import plotly.express as px
import nltk

nltk.download('stopwords')
nltk.download('punkt')

# DATABASE CONNECTION 
def create_connection():
    try:
        connection = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            autocommit=True,
            ssl={'ssl': {}}
        )
        return connection
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

connection = create_connection()
cursor = connection.cursor() if connection else None

if cursor:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_data(
        ID INT AUTO_INCREMENT PRIMARY KEY,
        Name TEXT,
        Email_ID TEXT,
        resume_score VARCHAR(10),
        Timestamp VARCHAR(50),
        Page_no VARCHAR(5),
        Predicted_Field TEXT,
        User_level TEXT,
        Actual_skills LONGTEXT,
        Recommended_skills LONGTEXT,
        Recommended_courses LONGTEXT
    )
    """)

# FUNCTIONS
def clean_email(text):
    match = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    return match[0] if match else "Not Found"

def extract_skills(text):
    skill_keywords = [
        "python","java","c++","machine learning","data science",
        "pandas","numpy","tensorflow","keras","sql","excel",
        "power bi","tableau","html","css","javascript"
    ]
    found_skills = []
    for skill in skill_keywords:
        if skill in text:
            found_skills.append(skill.title())
    return list(set(found_skills))

def insert_data(values):
    check_sql = "SELECT * FROM user_data WHERE Email_ID=%s"
    cursor.execute(check_sql, (values[1],))
    result = cursor.fetchone()

    if result:
        st.warning("This resume email already exists in database.")
    else:
        insert_sql = """
        INSERT INTO user_data
        (Name, Email_ID, resume_score, Timestamp, Page_no,
         Predicted_Field, User_level, Actual_skills,
         Recommended_skills, Recommended_courses)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(insert_sql, values)

def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)

    text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode()
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="800"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def course_recommender(course_list):
    st.subheader("Courses & Certificates Recommendations 🎓")
    rec_course = []
    random.shuffle(course_list)

    for i, (name, link) in enumerate(course_list[:5], 1):
        st.markdown(f"{i}. [{name}]({link})")
        rec_course.append(name)

    return rec_course

def extract_name_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        first_page = pdf.pages[0]
        words = first_page.extract_words(extra_attrs=["size"])

        if not words:
            return "Candidate"

        words_sorted = sorted(words, key=lambda x: x['top'])
        top_words = words_sorted[:40]
        max_size = max(word["size"] for word in top_words)
        name_words = [w["text"] for w in top_words if w["size"] == max_size]

        possible_name = " ".join(name_words)
        possible_name = re.sub(r'[^A-Za-z ]', '', possible_name)

        if 2 <= len(possible_name.split()) <= 4:
            return possible_name.title()

    return "Candidate"

# MAIN APP
def run():
    os.makedirs("Uploaded_Resumes", exist_ok=True)
    col1, col2 = st.columns([1,2])

    with col1:
        st.markdown("<h2 style='color:#00E5FF; text-align:center;'>AI Resume Analyzer</h2>", unsafe_allow_html=True)

    choice = st.sidebar.selectbox("Select Panel", ["User", "Admin"])

    if choice == "User":

        pdf_file = st.file_uploader("Upload Resume", type=["pdf"])

        if pdf_file:
            save_path = os.path.join("Uploaded_Resumes", pdf_file.name)
            with open(save_path, "wb") as f:
                f.write(pdf_file.getbuffer())

            show_pdf(save_path)

            resume_text = pdf_reader(save_path).lower()

            name = extract_name_from_pdf(save_path)
            email = clean_email(resume_text)
            pages = resume_text.count("\f") + 1
            skills = extract_skills(resume_text)

            st.success(f"Hello {name}")
            st.info(f"Email: {email}")
            st.info(f"Pages: {pages}")

            # FIELD DETECTION
            reco_field = "General"
            recommended_skills = []
            rec_course = []

            if any(s in skills for s in ["Python","Machine Learning","Tensorflow"]):
                reco_field = "Machine Learning"
                recommended_skills = ["Python","ML","TensorFlow"]
                rec_course = course_recommender(ml_course)

            elif any(s in skills for s in ["Pandas","Numpy","Data Science"]):
                reco_field = "Data Science"
                recommended_skills = ["Pandas","Numpy","Visualization"]
                rec_course = course_recommender(ds_course)

            st.success(f"Predicted Field: {reco_field}")

            cand_level = "Fresher" if pages == 1 else "Experienced"

            resume_score = sum([10 for sec in ["skills","projects","experience"] if sec in resume_text])
            st.progress(resume_score/100)
            st.success(f"Resume Score: {resume_score}/100")

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            insert_data((
                name, email, str(resume_score), timestamp,
                str(pages), reco_field, cand_level,
                str(skills), str(recommended_skills), str(rec_course)
            ))

    else:
        st.subheader("Admin Panel")
        df = pd.read_sql("SELECT * FROM user_data", connection)
        st.dataframe(df)

run()
