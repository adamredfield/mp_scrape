import streamlit as st
import os

def check_secrets():
    st.title("Checking Secrets Configuration")
    
    # Check project root secrets
    project_secrets = "/Users/adamredfield/mp_scrape/.streamlit/secrets.toml"
    if os.path.exists(project_secrets):
        st.success(f"✅ Found project secrets at: {project_secrets}")
        with open(project_secrets, 'r') as f:
            st.code(f.read(), language='toml')
    else:
        st.error(f"❌ No secrets file at: {project_secrets}")
    
    # Check global secrets
    home = os.path.expanduser("~")
    global_secrets = f"{home}/.streamlit/secrets.toml"
    if os.path.exists(global_secrets):
        st.success(f"✅ Found global secrets at: {global_secrets}")
    else:
        st.error(f"❌ No secrets file at: {global_secrets}")
    
    # Print current working directory
    st.write("Current working directory:", os.getcwd())
    
    # Try to access secrets
    try:
        st.write("Available secrets:", st.secrets)
    except Exception as e:
        st.error(f"Error accessing secrets: {e}")

if __name__ == "__main__":
    check_secrets()