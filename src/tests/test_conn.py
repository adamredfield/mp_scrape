import streamlit as st


def test_basic_query():
    st.title("Database Connection Test")
    
    try:
        # 1. Create connection
        st.write("1. Attempting connection...")
        conn = st.connection('postgresql', type='sql')
        st.success("✅ Connection object created")
        
        # 2. Test simple count query
        st.write("2. Testing simple COUNT query...")
        try:
            result = conn.query('SELECT COUNT(*) FROM routes.Routes')
            st.success(f"✅ Query successful! Found {result.iloc[0,0]} routes")
        except Exception as e:
            st.error(f"❌ Query failed: {str(e)}")
        except Exception as e:
            st.error(f"❌ Unexpected query error: {str(e)}")
            
        # 3. Test more complex query
        st.write("3. Testing complex query...")
        try:
            result = conn.query("""
                SELECT route_type, COUNT(*) 
                FROM routes.Routes 
                GROUP BY route_type 
                LIMIT 5
            """)
            st.success("✅ Complex query works!")
            st.dataframe(result)
        except Exception as e:
            st.error(f"❌ Complex query failed: {str(e)}")
            
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.write("Error type:", type(e).__name__)

if __name__ == "__main__":
    test_basic_query()