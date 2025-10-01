import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import time
import os
from pathlib import Path
import base64

# Configure the page
st.set_page_config(
    page_title="MCQ Quiz App",
    page_icon="📚",
    layout="wide"
)

def load_data():
    """Load MCQ data from Excel file"""
    try:
        df = pd.read_excel('mcq_data.xlsx')
        return df
    except FileNotFoundError:
        st.error("MCQ data file 'mcq_data.xlsx' not found. Please ensure it exists in the same directory.")
        return None

def save_results(results_data):
    """Save results to Excel file"""
    try:
        # Try to read existing file
        try:
            existing_df = pd.read_excel('user_results.xlsx')
            updated_df = pd.concat([existing_df, results_data], ignore_index=True)
        except FileNotFoundError:
            updated_df = results_data
        
        # Save to Excel
        updated_df.to_excel('user_results.xlsx', index=False)
        return True
    except Exception as e:
        st.error(f"Error saving results: {e}")
        return False

def get_available_notes():
    """Get list of available PDF notes in the notes directory"""
    notes_dir = Path("notes")
    if not notes_dir.exists():
        notes_dir.mkdir(exist_ok=True)
        return []
    
    pdf_files = list(notes_dir.glob("*.pdf"))
    return pdf_files

def display_pdf_viewer():
    """Display PDF notes viewer"""
    st.header("📚 Study Notes")
    
    # Get available PDF files
    pdf_files = get_available_notes()
    
    if not pdf_files:
        st.warning("No PDF notes found in the 'notes' directory.")
        st.info("""
        **How to add notes:**
        1. Create a folder named 'notes' in the same directory as this app
        2. Add your PDF files to the 'notes' folder
        3. Refresh this page to see your notes
        """)
        return
    
    # PDF selection
    pdf_names = [pdf.name for pdf in pdf_files]
    selected_pdf = st.selectbox("Select a PDF note:", pdf_names)
    
    if selected_pdf:
        pdf_path = Path("notes") / selected_pdf
        
        try:
            # Display PDF info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Name", selected_pdf)
            with col2:
                file_size = pdf_path.stat().st_size / (1024 * 1024)
                st.metric("File Size", f"{file_size:.2f} MB")
            with col3:
                st.metric("File Type", "PDF")
            
            # Display PDF
            with open(pdf_path, "rb") as file:
                pdf_bytes = file.read()
            
            st.subheader(f"Viewing: {selected_pdf}")
            
            # Download button
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=selected_pdf,
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"Error loading PDF: {e}")

def initialize_session_state():
    """Initialize session state variables"""
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'quiz_questions' not in st.session_state:
        st.session_state.quiz_questions = None
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None
    if 'time_up' not in st.session_state:
        st.session_state.time_up = False
    if 'marked_questions' not in st.session_state:
        st.session_state.marked_questions = set()
    if 'visited_questions' not in st.session_state:
        st.session_state.visited_questions = set()

def start_quiz(exam, section, topic, df, user_name, num_questions):
    """Start a new quiz with selected parameters"""
    # Filter questions based on selection
    filtered_df = df[
        (df['Exam'] == exam) & 
        (df['Section'] == section) & 
        (df['Topic'] == topic)
    ]
    
    if len(filtered_df) < num_questions:
        st.error(f"Not enough questions available. Only {len(filtered_df)} questions found.")
        return False
    
    # Randomly select questions
    st.session_state.quiz_questions = filtered_df.sample(n=num_questions).reset_index(drop=True)
    st.session_state.quiz_started = True
    st.session_state.current_question = 0
    st.session_state.user_answers = {}
    st.session_state.marked_questions = set()
    st.session_state.visited_questions = {0}
    st.session_state.start_time = datetime.now()
    st.session_state.time_up = False
    st.session_state.user_name = user_name
    st.session_state.current_exam = exam
    st.session_state.current_section = section
    st.session_state.current_topic = topic
    st.session_state.total_questions = num_questions
    st.session_state.time_limit = num_questions  # 1 minute per question
    
    return True

def display_question(question_data, question_num):
    """Display a single question with options"""
    st.subheader(f"Question {question_num + 1}/{st.session_state.total_questions}")
    
    # Show mark status
    if question_num in st.session_state.marked_questions:
        st.info("📌 This question is marked for review")
    
    st.write(f"**{question_data['Question']}**")
    
    options = ['A', 'B', 'C', 'D']
    option_texts = [
        question_data['Option A'],
        question_data['Option B'], 
        question_data['Option C'],
        question_data['Option D']
    ]
    
    # Create radio buttons for options
    answer_key = f"q_{question_data['Id']}"
    current_answer = st.session_state.user_answers.get(question_data['Id'], None)
    
    user_answer = st.radio(
        "Select your answer:",
        options=options,
        index=options.index(current_answer) if current_answer in options else None,
        key=answer_key,
        format_func=lambda x: f"{x}: {option_texts[options.index(x)]}"
    )
    
    return user_answer

def create_question_palette():
    """Create a question navigation palette"""
    st.sidebar.markdown("### 📋 Question Palette")
    
    total_questions = st.session_state.total_questions
    cols = st.sidebar.columns(5)
    
    for i in range(total_questions):
        col_idx = i % 5
        with cols[col_idx]:
            status = ""
            btn_label = f"Q{i+1}"
            
            if i in st.session_state.visited_questions:
                if i in st.session_state.marked_questions:
                    status = " 📌"
                elif st.session_state.quiz_questions.iloc[i]['Id'] in st.session_state.user_answers:
                    status = " ✅"
                else:
                    status = " ⭕"
            
            btn_type = "primary" if i == st.session_state.current_question else "secondary"
            
            if st.button(f"{btn_label}{status}", key=f"pal_{i}", type=btn_type):
                st.session_state.current_question = i
                st.session_state.visited_questions.add(i)
                st.rerun()

def display_timer():
    """Display the timer"""
    if st.session_state.quiz_started and not st.session_state.time_up:
        current_time = datetime.now()
        elapsed_time = (current_time - st.session_state.start_time).total_seconds()
        remaining_time = max(0, st.session_state.time_limit * 60 - elapsed_time)
        
        if remaining_time <= 0:
            st.session_state.time_up = True
            st.error("⏰ Time's up!")
        else:
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            
            if minutes < 1:
                color = "red"
            elif minutes < 3:
                color = "orange"
            else:
                color = "green"
            
            st.markdown(
                f"<h3 style='color: {color}; text-align: center;'>"
                f"⏱️ Time Remaining: {minutes:02d}:{seconds:02d}"
                f"</h3>", 
                unsafe_allow_html=True
            )

def calculate_results():
    """Calculate and return quiz results"""
    questions_df = st.session_state.quiz_questions
    user_answers = st.session_state.user_answers
    
    results = []
    correct_count = 0
    attempted_count = 0
    
    for idx, question in questions_df.iterrows():
        question_id = question['Id']
        user_answer = user_answers.get(question_id, 'Not Attempted')
        correct_answer = question['Correct Answer']
        
        is_correct = user_answer == correct_answer
        if user_answer != 'Not Attempted':
            attempted_count += 1
            if is_correct:
                correct_count += 1
        
        results.append({
            'Question No': idx + 1,
            'Question': question['Question'],
            'User Answer': user_answer,
            'Correct Answer': correct_answer,
            'Result': 'Correct' if is_correct else 'Wrong' if user_answer != 'Not Attempted' else 'Not Attempted'
        })
    
    score_percentage = (correct_count / len(questions_df)) * 100
    
    return {
        'results_df': pd.DataFrame(results),
        'total_questions': len(questions_df),
        'attempted': attempted_count,
        'correct': correct_count,
        'incorrect': attempted_count - correct_count,
        'score_percentage': score_percentage
    }

def display_scorecard(results):
    """Display the scorecard after quiz completion"""
    st.success("🎉 Quiz Completed!")
    
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Questions", results['total_questions'])
    with col2:
        st.metric("Attempted", results['attempted'])
    with col3:
        st.metric("Correct", results['correct'])
    with col4:
        st.metric("Incorrect", results['incorrect'])
    with col5:
        st.metric("Score", f"{results['score_percentage']:.1f}%")
    
    # Detailed results
    st.subheader("Detailed Results")
    st.dataframe(results['results_df'], use_container_width=True)
    
    # Save results
    save_results_data(results)

def save_results_data(results):
    """Prepare and save results data"""
    results_data = []
    
    for idx, row in results['results_df'].iterrows():
        question_data = st.session_state.quiz_questions.iloc[idx]
        results_data.append({
            'User Name': st.session_state.user_name,
            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Exam': st.session_state.current_exam,
            'Section': st.session_state.current_section,
            'Topic': st.session_state.current_topic,
            'Total Questions': st.session_state.total_questions,
            'Question ID': question_data['Id'],
            'Question': question_data['Question'],
            'User Answer': row['User Answer'],
            'Correct Answer': row['Correct Answer'],
            'Result (Correct/Wrong)': row['Result']
        })
    
    results_df = pd.DataFrame(results_data)
    if save_results(results_df):
        st.success("Results saved successfully!")

def main():
    st.title("📚 MCQ Quiz Application")
    st.markdown("---")
    
    # Initialize session state
    initialize_session_state()
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    if not st.session_state.quiz_started:
        page = st.sidebar.radio("Go to", ["🏠 Home", "📚 Notes"])
    else:
        page = "🎯 Quiz"
    
    if page == "📚 Notes":
        display_pdf_viewer()
        return
    
    # Home/Quiz page
    if not st.session_state.quiz_started:
        # Quiz setup
        st.header("Quiz Setup")
        
        user_name = st.text_input("Enter your name:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exams = sorted(df['Exam'].unique())
            selected_exam = st.selectbox("Select Exam:", exams)
        
        with col2:
            if selected_exam:
                sections = sorted(df[df['Exam'] == selected_exam]['Section'].unique())
                selected_section = st.selectbox("Select Section:", sections)
        
        with col3:
            if selected_exam and selected_section:
                topics = sorted(df[(df['Exam'] == selected_exam) & 
                                 (df['Section'] == selected_section)]['Topic'].unique())
                selected_topic = st.selectbox("Select Topic:", topics)
        
        num_questions = st.slider(
            "Number of Questions:",
            min_value=5,
            max_value=25,
            value=10
        )
        
        st.info(f"⏱️ Time allocated: {num_questions} minutes")
        
        if user_name and selected_exam and selected_section and selected_topic:
            if st.button("Start Quiz", type="primary"):
                if start_quiz(selected_exam, selected_section, selected_topic, df, user_name, num_questions):
                    st.rerun()
    
    else:
        # Quiz interface
        st.header("MCQ Quiz")
        
        # Display question palette
        create_question_palette()
        
        # Display timer
        display_timer()
        
        # Check if time is up
        if st.session_state.time_up:
            results = calculate_results()
            display_scorecard(results)
            if st.button("Start New Quiz"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            return
        
        # Display current question
        current_q = st.session_state.quiz_questions.iloc[st.session_state.current_question]
        user_answer = display_question(current_q, st.session_state.current_question)
        
        # Save answer
        if user_answer:
            st.session_state.user_answers[current_q['Id']] = user_answer
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            if st.session_state.current_question > 0:
                if st.button("Previous", type="secondary"):
                    st.session_state.current_question -= 1
                    st.session_state.visited_questions.add(st.session_state.current_question)
                    st.rerun()
        
        with col2:
            if st.button("Clear Answer", type="secondary"):
                if current_q['Id'] in st.session_state.user_answers:
                    del st.session_state.user_answers[current_q['Id']]
                st.rerun()
        
        with col3:
            if st.session_state.current_question in st.session_state.marked_questions:
                if st.button("Unmark", type="secondary"):
                    st.session_state.marked_questions.remove(st.session_state.current_question)
                    st.rerun()
            else:
                if st.button("Mark", type="secondary"):
                    st.session_state.marked_questions.add(st.session_state.current_question)
                    st.rerun()
        
        with col4:
            if st.button("Next", type="primary"):
                st.session_state.current_question += 1
                if st.session_state.current_question >= st.session_state.total_questions:
                    st.session_state.current_question = st.session_state.total_questions - 1
                st.session_state.visited_questions.add(st.session_state.current_question)
                st.rerun()
        
        # Finish quiz button
        if st.button("Finish Quiz", type="primary", use_container_width=True):
            results = calculate_results()
            display_scorecard(results)
            if st.button("Start New Quiz"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

if __name__ == "__main__":
    main()
