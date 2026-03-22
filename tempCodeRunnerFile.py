from pdfminer3.layout import LAParams,LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager,PDFPageInterpreter
from pdfminer3.converter import TextConverter 
import io,random
from streamlit_tags import st_tags
from PIL import Image
# ---To perform the image function like open,etc.
import pymysql
# ---To connect the database to the python file
# from Courses import ds_course,web_course,android_course
# import pafy
# ---used to upload youtube vedio
import plotly.express as px