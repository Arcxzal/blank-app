import streamlit as st
import pandas as pd
import requests
from datetime import datetime


main_page = st.Page("main_page.py", title="Main Page", icon="🎈")
page_2 = st.Page("page_2.py", title="Page 2", icon="❄️")
page_3 = st.Page("page_3.py", title="Page 3", icon="🎉")
page_4 = st.Page("page_4.py", title="Page 4", icon="🚀")
page_5 = st.Page("page_5.py", title="Page 5", icon="🌟")

# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5,])

# Run the selected page
pg.run()