import streamlit as st
import time
from datetime import datetime
import json
import boto3
import random

sqs = boto3.client('sqs',
        region_name=st.secrets["aws"]["region"],
        aws_access_key_id=st.secrets["aws"]["access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["secret_access_key"])

def trigger_user_scrape(user_id):
    """Send message to SQS to trigger scrape"""

    new_scrape_queue_url = st.secrets["aws"]["new_scrape_queue_url"]

    if not new_scrape_queue_url:
        st.error("SQS Queue URL not configured")
        return False

    message = {
        'user_id': user_id,
        'source': 'streamlit_app',
        'action': 'new_user_scrape'
    }

    try:
        sqs.send_message(
            QueueUrl=new_scrape_queue_url,
            MessageBody=json.dumps(message)
        )
        st.session_state.scrape_requested = True
        st.session_state.scrape_time = datetime.now()
        st.session_state.initial_delay = True
        st.session_state.start_time = datetime.now()
        return True
    except Exception as e:
        st.error(f"Failed to trigger scrape: {str(e)}")
        return False

def verify_user_exists(conn, user_id):
    info_msg = st.empty()
    details_msg = st.empty()
    button_cols = st.empty()

    if 'waiting_for_update' in st.session_state and st.session_state.waiting_for_update:
        # Clear any existing content
        info_msg.empty()
        details_msg.empty()
        button_cols.empty()

        status_text = st.empty()
        status_text.text("Processing your data. This can take up to 15 minutes...")

        # Get initial message count for this user
        if 'total_messages' not in st.session_state:
            queue_status, total_messages = check_queue_status(user_id, sqs)
            st.session_state.total_messages = total_messages

        result = handle_queue_processing(conn, user_id, sqs)
        if result: 
            time.sleep(3)
            st.session_state.waiting_for_update = False
            st.session_state.show_info_message = True
            st.rerun()

    exists = check_if_user_exists(conn, user_id)
    if exists:
        latest_insert, latest_route, tick_date = get_latest_tick(conn, user_id)
        info_msg.info(f"Your ticks up to {tick_date.strftime('%Y-%m-%d')} are already in the database.\n\n"
                f"Your data was last updated on {latest_insert.strftime('%Y-%m-%d')}")
        details_msg.write(f"""
            Have you climbed and logged additional routes since {latest_route}?  \n    
            We want your data to be as accurate as possible.  \n
            Please only refresh if you have climbed and logged additional routes.  \n
            Data collection isn't free for the creator of this app. 🙏
        """)

        with button_cols:
            col1, col2 = st.columns([1,2])
            with col1:
                with st.empty():
                    if st.button("Refresh Data"):
                        info_msg.empty()
                        details_msg.empty()
                        button_cols.empty()
                        if trigger_user_scrape(user_id):
                            st.session_state.waiting_for_update = True
                            st.session_state.initial_delay = True
                            st.session_state.start_time = datetime.now()
                            st.rerun()
            with col2:
                if st.button("Continue with existing data"):
                    st.session_state.data_status = 'ready'
                    return True
            
            if st.session_state.get('data_status') != 'ready':
                st.stop()

    else:
        info_msg.warning("Your data has not been collected yet.")
        if trigger_user_scrape(user_id):
            st.session_state.waiting_for_update = True
            st.session_state.initial_delay = True
            st.session_state.start_time = datetime.now()
            st.rerun()
        return False


def get_user_id(conn):
    """Handle user identification"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'data_status' not in st.session_state:
        st.session_state.data_status = None

    status_container = st.empty()

    # First check if we're in an update
    if ('waiting_for_update' in st.session_state and 
        st.session_state.waiting_for_update):
        verify_user_exists(conn, st.session_state.user_id)
        return None

    if st.session_state.user_id is None:
        st.title("Mountain Project Racked")
        
        col1, col2 = st.columns([2,1])
        with col1:
            user_input = st.text_input(
                "Enter your Mountain Project URL or User ID",
                placeholder="e.g., https://www.mountainproject.com/user/200362278/doctor-choss or 200362278/doctor-choss"
            )
        
        with col2:
            if st.button("Submit"):
                if user_input:
                    # Extract user_id from URL or use direct input
                    if "mountainproject.com" in user_input:
                        try:
                            user_id = user_input.split("/user/")[1].strip("/")
                            st.write(f"Extracted from URL: {user_id}")
                        except IndexError:
                            st.error("Invalid Mountain Project URL")
                            return None
                    else:
                        user_id = user_input.strip().strip('/')
                    
                    st.session_state.user_id = user_id
                    st.session_state.data_status = None  # Reset data status
                    st.rerun()
                else:
                    st.error("Please enter a user ID")

        st.markdown("""
        ### How to find your User ID:
        1. Go to [Mountain Project](https://www.mountainproject.com)
        2. Log in and click your profile
        3. Copy your profile URL or ID from the address bar
        """)
        return None
    if st.session_state.data_status is None:     
        # Verify user exists in database
        if verify_user_exists(conn, st.session_state.user_id):
            st.session_state.data_status = 'ready'
            st.rerun()
        return None

    return st.session_state.user_id

def check_if_user_exists(conn, user_id):
    exists_query = """
    SELECT EXISTS (
        SELECT 1
        FROM routes.Ticks t
        WHERE t.user_id = :user_id
        LIMIT 1
    )
    """
    result = conn.query(exists_query, params={"user_id": user_id}, ttl=0)
    exists = result.iloc[0,0]
    return exists

def get_latest_tick(conn, user_id):
    latest_query = """
    SELECT 
        t.insert_date,
        r.route_name,
        t.date
    FROM routes.Ticks t
    JOIN routes.Routes r ON t.route_id = r.id
    WHERE t.user_id = :user_id
    ORDER BY t.date DESC
    LIMIT 1
    """
    latest_result = conn.query(latest_query, params={"user_id": user_id})
    latest_insert = latest_result.iloc[0]['insert_date']
    latest_route = latest_result.iloc[0]['route_name']
    tick_date = latest_result.iloc[0]['date']
    return latest_insert, latest_route, tick_date

def handle_queue_processing(conn, user_id, sqs):
    synthetic_progress_bar = st.empty()
    queue_progress_bar = st.empty()
    status_text = st.empty()
    pages_text = st.empty()

    # Initialize progress tracking with more precise timing
    if 'progress_start_time' not in st.session_state:
        st.session_state.progress_start_time = time.time()
        st.session_state.current_progress = 0.0
        st.session_state.last_increment_time = datetime.now()
        st.session_state.current_message = None  

    current_time = datetime.now()
    time_since_update = (current_time - st.session_state.last_increment_time).total_seconds()

    if time_since_update >= 3:
        increment = random.uniform(0.01, 0.07)
        st.session_state.current_progress = min(0.9, st.session_state.current_progress + increment)
        st.session_state.last_increment_time = current_time

    synthetic_progress_bar.progress(st.session_state.current_progress)
    status_text.text(f"Processing: {int(st.session_state.current_progress * 100)}%")

    # Handle initial delay in background
    if st.session_state.get('initial_delay', False):
        if 'delay_start_time' not in st.session_state:
            st.session_state.delay_start_time = datetime.now()
        
        elapsed_delay = (datetime.now() - st.session_state.delay_start_time).total_seconds()
        if elapsed_delay < 15:
            st.rerun()
        else:
            queue_status, total_messages = check_queue_status(user_id, sqs)
            pages_text.write(f"Total Pages: {total_messages}")
            st.session_state.total_messages = total_messages
            st.session_state.initial_delay = False
            if 'delay_start_time' in st.session_state:
                del st.session_state.delay_start_time
            st.rerun()

    queue_status, current_messages = check_queue_status(user_id, sqs)

    if queue_status:
        if 'total_messages' in st.session_state and st.session_state.total_messages > 0:
            pages_message = f"Processing {current_messages} remaining pages..."
            pages_text.write(pages_message)
            st.rerun()
    else:
        # Queue is empty, but let's verify data was actually inserted
        tick_count = verify_data_inserted(conn, user_id)
        if tick_count > 0:
            if 'total_messages' in st.session_state:
                del st.session_state['total_messages']
            if 'start_time' in st.session_state:
                del st.session_state['start_time']
            if 'delay_start_time' in st.session_state:
                del st.session_state.delay_start_time
            st.session_state.waiting_for_update = False
            st.session_state.data_status = 'ready'
            st.cache_data.clear()

            synthetic_progress_bar.empty()
            queue_progress_bar.empty()
            status_text.empty()
            pages_text.success(f"Update complete. Found {tick_count} ticks. Racking up...")
            time.sleep(3)
            return tick_count
        else:
            st.rerun()


# Keep checking messages until we either find the user or exhaust the queue
def check_messages(queue_url, sqs, user_id):

    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=10,  # Max messages we can get at once
        VisibilityTimeout=30,
        WaitTimeSeconds=1
    )

    # Check messages in batch of 10
    if 'Messages' in response:
        for message in response['Messages']:
            message_body = json.loads(message['Body'])
            if message_body.get('user_id') == user_id:
                return True  # User's job is still in queue
        return False

def check_queue(queue_url, sqs):
    queue_attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible',
            'ApproximateNumberOfMessagesDelayed'
        ]
    )
    visible_count = int(queue_attrs['Attributes']['ApproximateNumberOfMessages'])
    in_flight_count = int(queue_attrs['Attributes']['ApproximateNumberOfMessagesNotVisible'])
    return visible_count, in_flight_count

def check_queue_status(user_id, sqs):
    # Check overall queue status and look for user's job
    main_queue_url = st.secrets["aws"]["queue_url"]
    dlq_url = st.secrets["aws"]["dlq_url"]

    main_visible, main_inflight = check_queue(main_queue_url, sqs)
    dlq_visible, dlq_inflight = check_queue(dlq_url, sqs)
    
    """
    current_time = datetime.now()
    elapsed = (current_time - st.session_state.start_time).total_seconds()

    with st.empty():
        st.write(f"[{current_time.strftime('%H:%M:%S')}] (Elapsed: {elapsed:.1f}s):")
        st.write(f"  Main Queue - Visible: {main_visible}, In-flight: {main_inflight}")
        st.write(f"  DLQ - Visible: {dlq_visible}, In-flight: {dlq_inflight}")
    """

    total_messages = main_visible + main_inflight + dlq_visible + dlq_inflight

    if total_messages == 0:
        return False, 0
    
    user_in_main = check_messages(main_queue_url, sqs, user_id)
    user_in_dlq = check_messages(dlq_url, sqs, user_id)
    
    return (user_in_main or user_in_dlq or total_messages > 0), total_messages

def verify_data_inserted(conn, user_id):
    verify_query = """
    SELECT COUNT(*) 
    FROM routes.Ticks 
    WHERE user_id = :user_id
    """
    result = conn.query(verify_query, params={"user_id": user_id}, ttl=0)
    tick_count = result.iloc[0,0]
    return tick_count