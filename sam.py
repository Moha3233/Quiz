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

def load_leaderboard():
    """Load leaderboard data"""
    try:
        leaderboard_df = pd.read_excel('user_results.xlsx')
        return leaderboard_df
    except FileNotFoundError:
        return pd.DataFrame()

def get_leaderboard_stats():
    """Calculate leaderboard statistics"""
    try:
        results_df = pd.read_excel('user_results.xlsx')
        
        # Calculate scores per quiz session
        session_stats = results_df.groupby(['User Name', 'Date', 'Exam', 'Section', 'Topic', 'Total Questions']).agg({
            'Result (Correct/Wrong)': lambda x: (x == 'Correct').sum()
        }).reset_index()
        
        session_stats.rename(columns={'Result (Correct/Wrong)': 'Score'}, inplace=True)
        
        # Overall user statistics
        user_stats = results_df.groupby('User Name').agg({
            'Result (Correct/Wrong)': lambda x: (x == 'Correct').sum(),
            'User Name': 'count'
        }).rename(columns={'Result (Correct/Wrong)': 'Total Correct', 'User Name': 'Total Attempted'})
        
        user_stats['Overall Accuracy'] = (user_stats['Total Correct'] / user_stats['Total Attempted'] * 100).round(2)
        
        return session_stats, user_stats
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame()

def get_available_notes():
    """Get list of available PDF notes in the notes directory"""
    notes_dir = Path("notes")
    if not notes_dir.exists():
        notes_dir.mkdir(exist_ok=True)
        return []
    
    pdf_files = list(notes_dir.glob("*.pdf"))
    return pdf_files

def display_pdf(pdf_file):
    """Display PDF file using base64 encoding"""
    try:
        # Read file as bytes
        with open(pdf_file, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # Create PDF embed HTML
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
        return True
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return False

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
                file_size = pdf_path.stat().st_size / (1024 * 1024)  # Size in MB
                st.metric("File Size", f"{file_size:.2f} MB")
            with col3:
                st.metric("File Type", "PDF")
            
            st.subheader(f"Viewing: {selected_pdf}")
            
            # Display PDF using base64 method
            if not display_pdf(pdf_path):
                st.info("""
                **Alternative ways to view the PDF:**
                - Download the PDF and open it with your preferred PDF viewer
                - Use the download button below
                """)
                
                # Provide download option
                with open(pdf_path, "rb") as file:
                    btn = st.download_button(
                        label="📥 Download PDF",
                        data=file,
                        file_name=selected_pdf,
                        mime="application/pdf"
                    )
            
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")
            st.info("The PDF file might be corrupted or in an unsupported format.")

def initialize_session_state():
    """Initialize session state variables"""
    default_states = {
        'quiz_started': False,
        'current_question': 0,
        'user_answers': {},
        'quiz_questions': None,
        'start_time': None,
        'end_time': None,
        'time_up': False,
        'marked_questions': set(),
        'visited_questions': set(),
        'user_name': '',
        'current_exam': '',
        'current_section': '',
        'current_topic': '',
        'total_questions': 10,
        'time_limit': 10,
        'remaining_time': 600,
        'last_update': None
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def calculate_time_limit(num_questions):
    """Calculate time limit based on number of questions (1 minute per question)"""
    return num_questions

def start_quiz(exam, section, topic, df, user_name, num_questions):
    """Start a new quiz with selected parameters"""
    # Filter questions based on selection
    filtered_df = df[
        (df['Exam'] == exam) & 
        (df['Section'] == section) & 
        (df['Topic'] == topic)
    ]
    
    if len(filtered_df) < num_questions:
        st.error(f"Not enough questions available for the selected topic. Only {len(filtered_df)} questions found, but {num_questions} required.")
        return False
    
    # Randomly select questions
    st.session_state.quiz_questions = filtered_df.sample(n=num_questions).reset_index(drop=True)
    st.session_state.quiz_started = True
    st.session_state.current_question = 0
    st.session_state.user_answers = {}
    st.session_state.marked_questions = set()
    st.session_state.visited_questions = {0}
    st.session_state.start_time = datetime.now()
    st.session_state.end_time = None
    st.session_state.time_up = False
    st.session_state.user_name = user_name
    st.session_state.current_exam = exam
    st.session_state.current_section = section
    st.session_state.current_topic = topic
    st.session_state.total_questions = num_questions
    st.session_state.time_limit = calculate_time_limit(num_questions)
    st.session_state.remaining_time = st.session_state.time_limit * 60  # Convert to seconds
    st.session_state.last_update = datetime.now()
    
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
    cols_per_row = 5
    rows_needed = (total_questions + cols_per_row - 1) // cols_per_row
    
    for row in range(rows_needed):
        cols = st.sidebar.columns(cols_per_row)
        for col in range(cols_per_row):
            i = row * cols_per_row + col
            if i < total_questions:
                with cols[col]:
                    status = ""
                    btn_label = f"Q{i+1}"
                    
                    if i in st.session_state.visited_questions:
                        if i in st.session_state.marked_questions:
                            status = " 📌"
                            btn_label = f"Q{i+1} 📌"
                        elif st.session_state.quiz_questions is not None and \
                             st.session_state.quiz_questions.iloc[i]['Id'] in st.session_state.user_answers:
                            status = " ✅"
                            btn_label = f"Q{i+1} ✅"
                        else:
                            status = " ⭕"
                            btn_label = f"Q{i+1} ⭕"
                    
                    # Use primary only for current question, secondary for others
                    btn_type = "primary" if i == st.session_state.current_question else "secondary"
                    
                    if st.button(btn_label, key=f"palette_{i}", type=btn_type, use_container_width=True):
                        st.session_state.current_question = i
                        st.session_state.visited_questions.add(i)
                        st.rerun()
    
    # Legend
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Legend:**")
    st.sidebar.markdown("📌 Marked  ✅ Answered  ⭕ Visited")

def update_timer():
    """Update the remaining time"""
    if (st.session_state.quiz_started and 
        not st.session_state.time_up and 
        st.session_state.start_time):
        
        current_time = datetime.now()
        elapsed_time = (current_time - st.session_state.start_time).total_seconds()
        st.session_state.remaining_time = max(0, st.session_state.time_limit * 60 - elapsed_time)
        
        if st.session_state.remaining_time <= 0:
            st.session_state.time_up = True
            st.session_state.end_time = datetime.now()

def display_timer():
    """Display the timer without automatic reruns"""
    if st.session_state.quiz_started and not st.session_state.time_up:
        update_timer()
        
        if st.session_state.remaining_time > 0:
            minutes = int(st.session_state.remaining_time // 60)
            seconds = int(st.session_state.remaining_time % 60)
            
            # Color coding based on remaining time
            if minutes < 1:
                timer_color = "red"
                timer_emoji = "🔴"
            elif minutes < 3:
                timer_color = "orange"
                timer_emoji = "🟠"
            else:
                timer_color = "green"
                timer_emoji = "🟢"
            
            st.markdown(
                f"<h3 style='color: {timer_color}; text-align: center;'>"
                f"{timer_emoji} Time Remaining: {minutes:02d}:{seconds:02d}"
                f"</h3>", 
                unsafe_allow_html=True
            )
        else:
            st.error("⏰ Time's up! Quiz completed automatically.")
    elif st.session_state.time_up:
        st.error("⏰ Time's up! Quiz completed automatically.")

def calculate_results():
    """Calculate and return quiz results"""
    if st.session_state.quiz_questions is None:
        return None
    
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
            'Result': 'Correct' if is_correct else 'Wrong' if user_answer != 'Not Attempted' else 'Not Attempted',
            'Marked': 'Yes' if idx in st.session_state.marked_questions else 'No'
        })
    
    score_percentage = (correct_count / len(questions_df)) * 100 if len(questions_df) > 0 else 0
    
    return {
        'results_df': pd.DataFrame(results),
        'total_questions': len(questions_df),
        'attempted': attempted_count,
        'correct': correct_count,
        'incorrect': attempted_count - correct_count,
        'score_percentage': score_percentage,
        'time_taken': st.session_state.end_time - st.session_state.start_time if st.session_state.end_time else None,
        'marked_count': len(st.session_state.marked_questions)
    }

def display_scorecard(results, user_name, exam, section, topic):
    """Display the scorecard after quiz completion"""
    st.success("🎉 Quiz Completed!")
    
    # Summary metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
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
    with col6:
        st.metric("Marked", results['marked_count'])
    
    # Time taken
    if results['time_taken']:
        total_seconds = results['time_taken'].total_seconds()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        st.write(f"**Time Taken:** {minutes} minutes {seconds} seconds")
    
    # Time allocation info
    st.write(f"**Time Allocated:** {st.session_state.time_limit} minutes ({st.session_state.time_limit} minutes for {st.session_state.total_questions} questions)")
    
    # Detailed results table
    st.subheader("Detailed Results")
    st.dataframe(results['results_df'], use_container_width=True)
    
    # Save results
    save_results_data(user_name, exam, section, topic, results)

def save_results_data(user_name, exam, section, topic, results):
    """Prepare and save results data"""
    results_data = []
    
    for idx, row in results['results_df'].iterrows():
        question_data = st.session_state.quiz_questions.iloc[idx]
        results_data.append({
            'User Name': user_name,
            'Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Exam': exam,
            'Section': section,
            'Topic': topic,
            'Total Questions': st.session_state.total_questions,
            'Time Allocated (minutes)': st.session_state.time_limit,
            'Question ID': question_data['Id'],
            'Question': question_data['Question'],
            'User Answer': row['User Answer'],
            'Correct Answer': row['Correct Answer'],
            'Result (Correct/Wrong)': row['Result']
        })
    
    results_df = pd.DataFrame(results_data)
    if save_results(results_df):
        st.success("Results saved successfully!")
    else:
        st.error("Failed to save results.")

def show_leaderboard():
    """Display the leaderboard"""
    st.header("🏆 Leaderboard")
    
    session_stats, user_stats = get_leaderboard_stats()
    
    if session_stats.empty:
        st.info("No quiz results available yet. Complete a quiz to see leaderboard!")
        return
    
    # Top Performers (Best Scores)
    st.subheader("Top Performers (Best Scores)")
    top_scores = session_stats.nlargest(10, 'Score')[['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Date']]
    top_scores['Percentage'] = (top_scores['Score'] / top_scores['Total Questions'] * 100).round(1)
    
    if not top_scores.empty:
        st.dataframe(top_scores, use_container_width=True)
    else:
        st.info("No top scores available.")
    
    # Overall User Statistics
    st.subheader("Overall User Statistics")
    if not user_stats.empty:
        overall_stats = user_stats.reset_index()[['User Name', 'Total Correct', 'Total Attempted', 'Overall Accuracy']]
        st.dataframe(overall_stats, use_container_width=True)
    else:
        st.info("No user statistics available.")
    
    # Recent Attempts
    st.subheader("Recent Attempts")
    recent_attempts = session_stats.sort_values('Date', ascending=False).head(10)
    recent_attempts['Percentage'] = (recent_attempts['Score'] / recent_attempts['Total Questions'] * 100).round(1)
    st.dataframe(recent_attempts[['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Percentage', 'Date']], 
                 use_container_width=True)

def main():
    st.title("📚 MCQ Quiz Application")
    st.markdown("---")
    
    # Initialize session state
    initialize_session_state()
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    
    if not st.session_state.quiz_started:
        page = st.sidebar.radio("Go to", ["🏠 Home", "📚 Notes", "🏆 Leaderboard"])
    else:
        page = "🎯 Quiz"
    
    if page == "🏆 Leaderboard":
        show_leaderboard()
        return
    elif page == "📚 Notes":
        display_pdf_viewer()
        return
    
    # Home/Quiz page
    if not st.session_state.quiz_started:
        st.header("User Information")
        
        # User name input
        user_name = st.text_input("Enter your name:")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exams = sorted(df['Exam'].unique())
            selected_exam = st.selectbox("Select Exam:", exams)
        
        with col2:
            if selected_exam:
                sections = sorted(df[df['Exam'] == selected_exam]['Section'].unique())
                selected_section = st.selectbox("Select Section:", sections)
            else:
                selected_section = None
        
        with col3:
            if selected_section:
                topics = sorted(df[(df['Exam'] == selected_exam) & 
                                 (df['Section'] == selected_section)]['Topic'].unique())
                selected_topic = st.selectbox("Select Topic:", topics)
            else:
                selected_topic = None
        
        # Number of questions selection
        st.subheader("Quiz Settings")
        num_questions = st.slider(
            "Number of Questions:",
            min_value=5,
            max_value=25,
            value=10,
            help="Select how many questions you want in this quiz"
        )
        
        # Calculate and display time allocation
        time_limit = calculate_time_limit(num_questions)
        st.info(f"⏱️ Time allocated: {time_limit} minutes ({time_limit} minutes for {num_questions} questions)")
        
        # Start quiz button
        if user_name and selected_exam and selected_section and selected_topic:
            if st.button("Start Quiz", type="primary"):
                if start_quiz(selected_exam, selected_section, selected_topic, df, user_name, num_questions):
                    st.rerun()
    
    # Quiz interface
    else:
        st.header("MCQ Quiz")
        
        # Display question palette in sidebar
        create_question_palette()
        
        # Display timer (static - no auto rerun)
        display_timer()
        
        # Display current question
        if (st.session_state.quiz_questions is not None and 
            st.session_state.current_question < len(st.session_state.quiz_questions) and
            not st.session_state.time_up):
            
            current_q = st.session_state.quiz_questions.iloc[st.session_state.current_question]
            user_answer = display_question(current_q, st.session_state.current_question)
            
            # Save current answer automatically
            if user_answer:
                st.session_state.user_answers[current_q['Id']] = user_answer
            
            # Enhanced Navigation buttons
            col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
            
            with col1:
                if st.session_state.current_question > 0:
                    if st.button("⬅️ Previous", type="secondary"):
                        st.session_state.current_question -= 1
                        st.session_state.visited_questions.add(st.session_state.current_question)
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Clear Answer", type="secondary"):
                    if current_q['Id'] in st.session_state.user_answers:
                        del st.session_state.user_answers[current_q['Id']]
                    st.rerun()
            
            with col3:
                if st.session_state.current_question in st.session_state.marked_questions:
                    if st.button("📌 Unmark", type="secondary"):
                        st.session_state.marked_questions.remove(st.session_state.current_question)
                        st.rerun()
                else:
                    if st.button("📌 Mark", type="secondary"):
                        st.session_state.marked_questions.add(st.session_state.current_question)
                        st.rerun()
            
            with col4:
                if st.button("💾 Save & Next ➡️", type="primary"):
                    st.session_state.current_question += 1
                    if st.session_state.current_question < len(st.session_state.quiz_questions):
                        st.session_state.visited_questions.add(st.session_state.current_question)
                    else:
                        st.session_state.end_time = datetime.now()
                    st.rerun()
            
            with col5:
                if st.button("🏁 Finish Quiz", type="primary"):
                    st.session_state.end_time = datetime.now()
                    st.rerun()
        
        # Show results if quiz is completed
        if (st.session_state.end_time is not None or 
            st.session_state.time_up or
            (st.session_state.quiz_questions is not None and 
             st.session_state.current_question >= len(st.session_state.quiz_questions))):
            
            results = calculate_results()
            if results:
                display_scorecard(results, 
                                st.session_state.user_name, 
                                st.session_state.current_exam, 
                                st.session_state.current_section, 
                                st.session_state.current_topic)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Start New Quiz", type="primary"):
                        # Reset all quiz-related session state
                        for key in ['quiz_started', 'current_question', 'user_answers', 'quiz_questions', 
                                   'start_time', 'end_time', 'time_up', 'marked_questions', 'visited_questions',
                                   'current_exam', 'current_section', 'current_topic', 'total_questions',
                                   'time_limit', 'remaining_time', 'last_update']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                with col2:
                    if st.button("🏆 View Leaderboard", type="secondary"):
                        st.session_state.quiz_started = False
                        st.rerun()

if __name__ == "__main__":
    main()