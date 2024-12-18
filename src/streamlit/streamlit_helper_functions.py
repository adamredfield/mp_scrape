import streamlit as st
import time
import boto3
from datetime import datetime
import json

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
    if st.session_state.get('initial_delay', False):
        with st.empty():
            st.info("⏳ Initializing data collection...")
        time.sleep(15)
        st.session_state.initial_delay = False

    queue_status = check_queue_status(user_id, sqs)

    if queue_status:
        with st.empty():
            st.info(
                "⏳ Still processing your data....\n\n"
                "   This can take up to 15 minutes.\n\n"
                "   Depending if routes you climb are already in the database.\n\n"
            )
        time.sleep(5)
        st.rerun()
    else:
        # Queue is empty, but let's verify data was actually inserted
        tick_count = verify_data_inserted(conn, user_id)
        if tick_count > 0:
            # No data yet, keep waiting
            with st.empty():
                st.success(f"Update complete. Found {tick_count} ticks. Racking up...")
            st.session_state.waiting_for_update = False
            st.session_state.data_status = 'ready'
            st.cache_data.clear()
            st.rerun()
        else:
            st.info("Waiting for data to be processed...")
            time.sleep(5)
            st.rerun()

# Keep checking messages until we either find the user or exhaust the queue
def check_messages(queue_url, sqs, user_id):

    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=10,  # Max messages we can get at once
        VisibilityTimeout=30,
        WaitTimeSeconds=5
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
    
    current_time = datetime.now()
    elapsed = (current_time - st.session_state.start_time).total_seconds()

    st.write(f"[{current_time.strftime('%H:%M:%S')}] (Elapsed: {elapsed:.1f}s):")
    st.write(f"  Main Queue - Visible: {main_visible}, In-flight: {main_inflight}")
    st.write(f"  DLQ - Visible: {dlq_visible}, In-flight: {dlq_inflight}")

    total_messages = main_visible + main_inflight + dlq_visible + dlq_inflight

    if total_messages == 0:
        return False
    
    user_in_main = check_messages(main_queue_url, sqs, user_id)
    user_in_dlq = check_messages(dlq_url, sqs, user_id)
    
    return user_in_main or user_in_dlq or total_messages > 0

def verify_data_inserted(conn, user_id):
    verify_query = """
    SELECT COUNT(*) 
    FROM routes.Ticks 
    WHERE user_id = :user_id
    """
    result = conn.query(verify_query, params={"user_id": user_id}, ttl=0)
    tick_count = result.iloc[0,0]
    return tick_count