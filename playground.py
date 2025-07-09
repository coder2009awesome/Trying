import streamlit as st
import io
import contextlib

st.set_page_config(page_title="Python Playground", layout="centered")

st.title("🐍 Python Playground")
st.markdown("Write and run Python code right here!")

code = st.text_area("Write your Python code below:", height=300, placeholder="print('Hello, world!')")

if st.button("Run Code"):
    with st.spinner("Running your code..."):
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                exec(code, {})
            result = output.getvalue()
            st.success("Code executed successfully!")
            st.code(result if result.strip() else "[No output]", language="text")
        except Exception as e:
            st.error("🚫 An error occurred:")
            st.code(str(e), language="text")
