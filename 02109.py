import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import time

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
    """Calculate leaderboard statistics - COMPLETELY FIXED"""
    try:
        results_df = pd.read_excel('user_results.xlsx')
        
        if results_df.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        # Debug: Show raw data
        st.sidebar.write("Raw data count:", len(results_df))
        
        # Create a unique session identifier
        results_df['Session_ID'] = (
            results_df['User Name'] + '_' + 
            results_df['Date'].astype(str) + '_' + 
            results_df['Exam'] + '_' + 
            results_df['Section'] + '_' + 
            results_df['Topic']
        )
        
        # Group by session to get unique quiz attempts
        session_stats = results_df.groupby(['Session_ID', 'User Name', 'Date', 'Exam', 'Section', 'Topic']).agg({
            'Result (Correct/Wrong)': lambda x: (x == 'Correct').sum(),
            'Total Questions': 'first'
        }).reset_index()
        
        session_stats.rename(columns={'Result (Correct/Wrong)': 'Score'}, inplace=True)
        
        # Calculate user statistics from session stats (not raw data)
        user_stats = session_stats.groupby('User Name').agg({
            'Score': 'sum',
            'Total Questions': 'sum',
            'Session_ID': 'count'
        }).reset_index()
        
        user_stats.rename(columns={
            'Score': 'Total Correct',
            'Total Questions': 'Total Questions Attempted',
            'Session_ID': 'Total Quizzes'
        }, inplace=True)
        
        user_stats['Overall Accuracy'] = (user_stats['Total Correct'] / user_stats['Total Questions Attempted'] * 100).round(2)
        
        return session_stats, user_stats
        
    except FileNotFoundError:
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error processing leaderboard data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def show_leaderboard():
    """Display the leaderboard - COMPLETELY FIXED"""
    st.header("🏆 Leaderboard")
    
    try:
        session_stats, user_stats = get_leaderboard_stats()
        
        if session_stats.empty or user_stats.empty:
            st.info("No quiz results available yet. Complete a quiz to see leaderboard!")
            return
        
        # Debug information
        st.sidebar.write("Sessions found:", len(session_stats))
        st.sidebar.write("Users found:", len(user_stats))
        
        # Top Performers Section
        st.subheader("🏅 Top Performers (Best Scores)")
        
        # Ensure we have the required columns
        if all(col in session_stats.columns for col in ['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Date']):
            # Calculate percentage for each session
            session_stats['Percentage'] = (session_stats['Score'] / session_stats['Total Questions'] * 100).round(1)
            
            # Get top 10 scores by percentage
            top_scores = session_stats.nlargest(10, 'Percentage')[['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Percentage', 'Date']]
            
            if not top_scores.empty:
                # Format the display
                display_top_scores = top_scores.copy()
                display_top_scores['Score'] = display_top_scores['Score'].astype(str) + '/' + display_top_scores['Total Questions'].astype(str)
                display_top_scores = display_top_scores.rename(columns={'Score': 'Score (Correct/Total)'})
                st.dataframe(display_top_scores[['User Name', 'Exam', 'Section', 'Topic', 'Score (Correct/Total)', 'Percentage', 'Date']], 
                           use_container_width=True)
            else:
                st.info("No top scores available.")
        else:
            st.error("Missing required columns in session data")
        
        # Overall User Statistics Section
        st.subheader("📊 Overall User Statistics")
        
        if not user_stats.empty and all(col in user_stats.columns for col in ['User Name', 'Total Quizzes', 'Total Correct', 'Total Questions Attempted', 'Overall Accuracy']):
            # Format the display
            display_user_stats = user_stats.copy()
            display_user_stats['Total Correct'] = display_user_stats['Total Correct'].astype(int)
            display_user_stats['Total Questions Attempted'] = display_user_stats['Total Questions Attempted'].astype(int)
            display_user_stats['Overall Accuracy'] = display_user_stats['Overall Accuracy'].round(1)
            
            st.dataframe(display_user_stats[['User Name', 'Total Quizzes', 'Total Correct', 'Total Questions Attempted', 'Overall Accuracy']], 
                       use_container_width=True)
        else:
            st.error("Missing required columns in user statistics")
        
        # Recent Attempts Section
        st.subheader("🕒 Recent Attempts")
        
        if not session_stats.empty and all(col in session_stats.columns for col in ['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Percentage', 'Date']):
            # Get most recent attempts
            recent_attempts = session_stats.sort_values('Date', ascending=False).head(10)
            
            # Format the display
            display_recent = recent_attempts.copy()
            display_recent['Score'] = display_recent['Score'].astype(str) + '/' + display_recent['Total Questions'].astype(str)
            display_recent = display_recent.rename(columns={'Score': 'Score (Correct/Total)'})
            
            st.dataframe(display_recent[['User Name', 'Exam', 'Section', 'Topic', 'Score (Correct/Total)', 'Percentage', 'Date']], 
                       use_container_width=True)
        else:
            st.error("Missing required columns in recent attempts data")
            
    except Exception as e:
        st.error(f"Error displaying leaderboard: {e}")
        st.info("Please try completing a quiz first to generate leaderboard data.")

def show_leaderboard():
    """Display the leaderboard - COMPLETELY FIXED"""
    st.header("🏆 Leaderboard")
    
    try:
        session_stats, user_stats = get_leaderboard_stats()
        
        if session_stats.empty or user_stats.empty:
            st.info("No quiz results available yet. Complete a quiz to see leaderboard!")
            return
        
        # Debug information
        st.sidebar.write("Sessions found:", len(session_stats))
        st.sidebar.write("Users found:", len(user_stats))
        
        # Top Performers Section
        st.subheader("🏅 Top Performers (Best Scores)")
        
        # Ensure we have the required columns
        if all(col in session_stats.columns for col in ['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Date']):
            # Calculate percentage for each session
            session_stats['Percentage'] = (session_stats['Score'] / session_stats['Total Questions'] * 100).round(1)
            
            # Get top 10 scores by percentage
            top_scores = session_stats.nlargest(10, 'Percentage')[['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Percentage', 'Date']]
            
            if not top_scores.empty:
                # Format the display
                display_top_scores = top_scores.copy()
                display_top_scores['Score'] = display_top_scores['Score'].astype(str) + '/' + display_top_scores['Total Questions'].astype(str)
                display_top_scores = display_top_scores.rename(columns={'Score': 'Score (Correct/Total)'})
                st.dataframe(display_top_scores[['User Name', 'Exam', 'Section', 'Topic', 'Score (Correct/Total)', 'Percentage', 'Date']], 
                           use_container_width=True)
            else:
                st.info("No top scores available.")
        else:
            st.error("Missing required columns in session data")
        
        # Overall User Statistics Section
        st.subheader("📊 Overall User Statistics")
        
        if not user_stats.empty and all(col in user_stats.columns for col in ['User Name', 'Total Quizzes', 'Total Correct', 'Total Questions Attempted', 'Overall Accuracy']):
            # Format the display
            display_user_stats = user_stats.copy()
            display_user_stats['Total Correct'] = display_user_stats['Total Correct'].astype(int)
            display_user_stats['Total Questions Attempted'] = display_user_stats['Total Questions Attempted'].astype(int)
            display_user_stats['Overall Accuracy'] = display_user_stats['Overall Accuracy'].round(1)
            
            st.dataframe(display_user_stats[['User Name', 'Total Quizzes', 'Total Correct', 'Total Questions Attempted', 'Overall Accuracy']], 
                       use_container_width=True)
        else:
            st.error("Missing required columns in user statistics")
        
        # Recent Attempts Section
        st.subheader("🕒 Recent Attempts")
        
        if not session_stats.empty and all(col in session_stats.columns for col in ['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Percentage', 'Date']):
            # Get most recent attempts
            recent_attempts = session_stats.sort_values('Date', ascending=False).head(10)
            
            # Format the display
            display_recent = recent_attempts.copy()
            display_recent['Score'] = display_recent['Score'].astype(str) + '/' + display_recent['Total Questions'].astype(str)
            display_recent = display_recent.rename(columns={'Score': 'Score (Correct/Total)'})
            
            st.dataframe(display_recent[['User Name', 'Exam', 'Section', 'Topic', 'Score (Correct/Total)', 'Percentage', 'Date']], 
                       use_container_width=True)
        else:
            st.error("Missing required columns in recent attempts data")
            
    except Exception as e:
        st.error(f"Error displaying leaderboard: {e}")
        st.info("Please try completing a quiz first to generate leaderboard data.")

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
        'current_topic': ''
    }
    
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

def start_quiz(exam, section, topic, df, user_name):
    """Start a new quiz with selected parameters"""
    # Filter questions based on selection
    filtered_df = df[
        (df['Exam'] == exam) & 
        (df['Section'] == section) & 
        (df['Topic'] == topic)
    ]
    
    if len(filtered_df) < 10:
        st.error(f"Not enough questions available for the selected topic. Only {len(filtered_df)} questions found.")
        return False
    
    # Randomly select 10 questions
    st.session_state.quiz_questions = filtered_df.sample(n=10).reset_index(drop=True)
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
    
    return True

def display_question(question_data, question_num):
    """Display a single question with options"""
    st.subheader(f"Question {question_num + 1}/10")
    
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
    
    cols = st.sidebar.columns(5)
    for i in range(10):
        with cols[i % 5]:
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
            
            if st.button(btn_label, key=f"palette_{i}", type=btn_type):
                st.session_state.current_question = i
                st.session_state.visited_questions.add(i)
                st.rerun()
    
    # Legend
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Legend:**")
    st.sidebar.markdown("📌 Marked  ✅ Answered  ⭕ Visited")

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
    st.balloons()
    
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
    
    # Detailed results table
    st.subheader("Detailed Results")
    st.dataframe(results['results_df'], use_container_width=True)
    
    # Save results
    save_results_data(user_name, exam, section, topic, results)

def save_results_data(user_name, exam, section, topic, results):
    """Prepare and save results data - ensure consistent format"""
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
    
    # Save to Excel
    if save_results(results_df):
        st.success("✅ Results saved successfully!")
        return True
    else:
        st.error("❌ Failed to save results.")
        return False

def show_leaderboard():
    """Display the leaderboard - UPDATED with correct counting"""
    st.header("🏆 Leaderboard")
    
    session_stats, user_stats = get_leaderboard_stats()
    
    if session_stats.empty:
        st.info("No quiz results available yet. Complete a quiz to see leaderboard!")
        return
    
    # Top Performers (Best Scores) - now correctly shows each quiz session once
    st.subheader("Top Performers (Best Scores)")
    top_scores = session_stats.nlargest(10, 'Score')[['User Name', 'Exam', 'Section', 'Topic', 'Score', 'Total Questions', 'Date']]
    top_scores['Percentage'] = (top_scores['Score'] / top_scores['Total Questions'] * 100).round(1)
    
    if not top_scores.empty:
        st.dataframe(top_scores, use_container_width=True)
    else:
        st.info("No top scores available.")
    
    # Overall User Statistics - now shows correct quiz count
    st.subheader("Overall User Statistics")
    if not user_stats.empty:
        # Reorder columns for better display
        overall_stats = user_stats[['User Name', 'Total Quizzes', 'Total Correct', 'Total Questions Attempted', 'Overall Accuracy']]
        st.dataframe(overall_stats, use_container_width=True)
    else:
        st.info("No user statistics available.")
    
    # Recent Attempts - now shows each quiz session once
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
    
    # Sidebar for navigation and leaderboard
    st.sidebar.title("Navigation")
    
    if not st.session_state.quiz_started:
        page = st.sidebar.radio("Go to", ["🏠 Home", "🏆 Leaderboard"])
    else:
        page = "🎯 Quiz"
    
    if page == "🏆 Leaderboard":
        show_leaderboard()
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
        
        # Start quiz button
        if user_name and selected_exam and selected_section and selected_topic:
            if st.button("Start Quiz", type="primary"):
                if start_quiz(selected_exam, selected_section, selected_topic, df, user_name):
                    st.rerun()
    
    # Quiz interface
    else:
        st.header("MCQ Quiz")
        
        # Display question palette in sidebar
        create_question_palette()
        
        # Timer
        if not st.session_state.time_up and st.session_state.start_time:
            elapsed_time = datetime.now() - st.session_state.start_time
            remaining_time = timedelta(minutes=10) - elapsed_time
            
            if remaining_time.total_seconds() <= 0:
                st.session_state.time_up = True
                st.session_state.end_time = datetime.now()
                st.error("⏰ Time's up! Quiz completed automatically.")
            else:
                minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
                st.write(f"⏱️ Time remaining: {minutes:02d}:{seconds:02d}")
        
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
                        st.session_state.quiz_started = False
                        st.session_state.quiz_questions = None
                        st.session_state.user_answers = {}
                        st.session_state.marked_questions = set()
                        st.rerun()
                with col2:
                    if st.button("🏆 View Leaderboard", type="secondary"):
                        st.session_state.quiz_started = False
                        st.rerun()

if __name__ == "__main__":
    main()
