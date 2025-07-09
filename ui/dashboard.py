import streamlit as st
import time
import pandas as pd
import sys
import os
from datetime import datetime

# Add the parent directory to Python path to find the mentorship module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mentorship.embed_store import ingest_transcript, query_store, get_store_stats, clear_store

# Page configuration
st.set_page_config(
    page_title="JumpTrader Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Header
st.title("🚀 JumpTrader Dashboard")
st.markdown("**AI-Powered Trading & Mentorship Platform**")

# Create tabs
tabs = st.tabs(["Market", "Alerts History", "🔥 Chat with Spicy"])

# Market Tab (placeholder)
with tabs[0]:
    st.header("📈 Market Dashboard")
    st.info("Market dashboard functionality will be integrated here.")
    
    # Placeholder for market data
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Symbols", "0")
    with col2:
        st.metric("Total Volume", "$0")
    with col3:
        st.metric("Signals", "0")
    with col4:
        st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

# Alerts History Tab (placeholder)
with tabs[1]:
    st.header("🚨 Alerts History")
    st.info("Alerts history functionality will be integrated here.")
    
    # Placeholder for alerts
    st.dataframe(
        pd.DataFrame({
            "Time": [],
            "Symbol": [],
            "Alert Type": [],
            "Message": []
        }),
        use_container_width=True
    )

# Mentorship Chat Tab
with tabs[2]:
    st.header("🔥 Chat with Spicy - Your AI Trading Mentor")
    st.markdown("**Spicy** is your AI mentor trained on your trading lessons. Ask anything about trading strategies, risk management, or market analysis!")
    
    # Initialize Spicy's personality
    if "spicy_personality" not in st.session_state:
        st.session_state.spicy_personality = {
            "name": "Spicy",
            "style": "Direct, experienced, and slightly edgy",
            "greeting": "Hey trader! I'm Spicy, your AI mentor. I've learned from your lessons and I'm here to help you level up your trading game. What's on your mind?"
        }
    
    # Sidebar for Spicy's info and controls
    with st.sidebar:
        st.header("🔥 Spicy's Corner")
        
        # Spicy's avatar and status
        st.markdown("### 🤖 **Spicy** - AI Trading Mentor")
        st.markdown("*Direct, experienced, and slightly edgy*")
        
        # Knowledge base stats
        stats = get_store_stats()
        st.metric("📚 Lessons Learned", stats["total_documents"])
        st.metric("🧠 Knowledge Chunks", stats["total_chunks"])
        
        if stats["total_documents"] > 0:
            st.success("✅ Spicy is ready to help!")
        else:
            st.warning("⚠️ Spicy needs to learn first!")
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("📚 Upload New Lessons", type="primary"):
            st.session_state.show_upload = True
            st.rerun()
        
        if st.button("🗑️ Clear Spicy's Memory", type="secondary"):
            if clear_store():
                st.success("Spicy's memory cleared!")
                st.rerun()
            else:
                st.error("Failed to clear memory")
        
        # Show learned lessons
        if stats["documents"]:
            st.markdown("---")
            st.subheader("📖 Lessons Learned")
            for doc in stats["documents"]:
                st.text(f"• {doc.split('_')[0]}")
    
    # Main chat area
    st.markdown("---")
    
    # Upload section (collapsible)
    if st.session_state.get("show_upload", False):
        with st.expander("📚 Teach Spicy New Lessons", expanded=True):
            st.markdown("Upload your mentor's lesson transcripts to teach Spicy new knowledge.")
            
            uploaded_files = st.file_uploader(
                label="Upload lesson transcripts (.txt)",
                type="txt",
                accept_multiple_files=True,
                key="spicy_upload"
            )
            
            if uploaded_files:
                with st.spinner("🔥 Spicy is learning..."):
                    for file in uploaded_files:
                        try:
                            text = file.read().decode("utf-8")
                            doc_id = f"{file.name.rstrip('.txt')}_{int(time.time())}"
                            
                            if ingest_transcript(text, doc_id):
                                st.success(f"✅ Spicy learned from: {file.name}")
                            else:
                                st.error(f"❌ Failed to learn from: {file.name}")
                        except Exception as e:
                            st.error(f"❌ Error processing {file.name}: {str(e)}")
                
                st.success(f"🎉 Spicy successfully learned from {len(uploaded_files)} lesson(s)!")
                # Do NOT set st.session_state.show_upload = False here, so the section stays open
                st.rerun()
            
            if st.button("❌ Close Upload"):
                st.session_state.show_upload = False
                st.rerun()
    
    # After sidebar and before chat logic, handle persistent lesson uploads
    st.markdown("---")
    st.subheader("📚 Upload Lessons (Persistent)")

    uploaded = st.file_uploader("Upload a lesson (.txt)", type="txt", accept_multiple_files=True)
    if uploaded:
        for up in uploaded:
            dest = os.path.join(LESSONS_DIR, up.name)
            if not os.path.exists(dest):
                with open(dest, 'wb') as f:
                    f.write(up.read())
                st.success(f"Saved lesson: {up.name}")
            else:
                st.info(f"Lesson already saved: {up.name}")

    # On startup, load all lessons from the persistent folder and ingest if not already present
    lesson_texts = []
    for filename in sorted(os.listdir(LESSONS_DIR)):
        if filename.endswith('.txt'):
            path = os.path.join(LESSONS_DIR, filename)
            with open(path, 'r', encoding='utf-8') as f:
                lesson_texts.append(f.read())
            # Ingest into embed store if not already present
            doc_id = f"{filename.rstrip('.txt')}"
            stats = get_store_stats()
            if doc_id not in stats.get('documents', []):
                ingest_transcript(f.read(), doc_id)
    
    # Chat interface
    st.subheader("💬 Chat with Spicy")
    
    # Welcome message if no chat history
    if not st.session_state.chat_history:
        st.info(f"🔥 **{st.session_state.spicy_personality['greeting']}**")
    
    # Display chat history with better formatting
    if st.session_state.chat_history:
        st.markdown("### 📝 Conversation History")
        
        for i, (question, answer, excerpts) in enumerate(st.session_state.chat_history):
            # User message
            with st.container():
                col1, col2 = st.columns([1, 20])
                with col1:
                    st.markdown("👤")
                with col2:
                    st.markdown(f"**You:** {question}")
            
            # Spicy's response
            with st.container():
                col1, col2 = st.columns([1, 20])
                with col1:
                    st.markdown("🔥")
                with col2:
                    st.markdown(f"**Spicy:** {answer}")
                    
                    # Show relevant excerpts in expandable section
                    if excerpts:
                        with st.expander(f"📖 View {len(excerpts)} relevant lesson excerpts", expanded=False):
                            for j, excerpt in enumerate(excerpts, 1):
                                st.markdown(f"**{j}.** {excerpt[:300]}...")
                                st.markdown("---")
            
            st.markdown("---")
    
    # Pre-initialize spicy_question in session state before creating the input widget
    if "spicy_question" not in st.session_state:
        st.session_state.spicy_question = ""

    # Add a response placeholder at the top of the chat box section
    response_container = st.empty()

    # Quick question buttons
    st.markdown("**Quick Questions:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Best Entry Strategies", key="q1"):
            spicy_question = "What are the best entry strategies for mean reversion trades?"
            response_container.markdown("<span style='color: #888;'>Quick question selected: Best Entry Strategies</span>", unsafe_allow_html=True)
        else:
            spicy_question = st.session_state.spicy_question
    
    with col2:
        if st.button("⚠️ Risk Management", key="q2"):
            spicy_question = "What are the key risk management principles I should follow?"
            response_container.markdown("<span style='color: #888;'>Quick question selected: Risk Management</span>", unsafe_allow_html=True)
        else:
            spicy_question = st.session_state.spicy_question
    
    with col3:
        if st.button("📊 Market Context", key="q3"):
            spicy_question = "How should I analyze market context before entering trades?"
            response_container.markdown("<span style='color: #888;'>Quick question selected: Market Context</span>", unsafe_allow_html=True)
        else:
            spicy_question = st.session_state.spicy_question

    # Create the input widget
    spicy_question = st.text_input(
        "What do you want to ask Spicy?",
        value=spicy_question,
        key="spicy_question"
    )

    # Send button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔥 Ask Spicy", type="primary"):
            if not spicy_question.strip():
                response_container.warning("Please type a question before sending.")
            else:
                try:
                    with st.spinner("🔥 Spicy is thinking..."):
                        excerpts = query_store(spicy_question, k=3)
                    if excerpts:
                        answer = f"Great question! Based on your lessons, here's what I know:\n\n"
                        for i, excerpt in enumerate(excerpts, 1):
                            clean_excerpt = excerpt.replace('\n', ' ').strip()
                            answer += f"**{i}.** {clean_excerpt[:250]}...\n\n"
                        answer += "\n🔥 **Spicy's Take:** Remember, context is everything. Always check market conditions before applying these strategies!"
                        st.session_state.chat_history.append((spicy_question, answer, excerpts))
                        st.success("✅ Spicy responded!")
                        response_container.markdown(answer)
                    else:
                        response_container.info("🤔 Spicy doesn't have enough knowledge about that yet. Try uploading more lessons or rephrasing your question.")
                except Exception as e:
                    response_container.error(f"Error: {e}")
    
    with col2:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()
    
    with col3:
        if st.button("📚 Upload Lessons", type="secondary"):
            st.session_state.show_upload = True
            st.rerun()
    
    # Tips and suggestions
    st.markdown("---")
    st.subheader("💡 What to Ask Spicy")
    st.markdown("""
    **Trading Strategies:**
    - "What are the best entry triggers for mean reversion?"
    - "How do I identify perfect support levels?"
    - "When should I cut vs. hold a trade?"
    
    **Risk Management:**
    - "What are the key risk management principles?"
    - "How do I manage position sizing?"
    - "When should I exit a losing trade?"
    
    **Market Analysis:**
    - "How do I read market context?"
    - "What indicators should I watch?"
    - "How do I spot false breakouts?"
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    **About JumpTrader:**
    - Real-time Binance perpetual futures data
    - AI-powered signal detection
    - Mentorship chat with transcript analysis
    - Built with Streamlit and Python
    """
) 