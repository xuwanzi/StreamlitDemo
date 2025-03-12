import streamlit as st

st.title('你好，世界！')
st.write('欢迎使用 Streamlit！')

number = st.slider('选择一个数字', 0, 100)
st.write(f'你选择的数字是：{number}')
