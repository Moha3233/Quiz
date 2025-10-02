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
        # Ensure required columns exist
        required_columns = ['Exam', 'Section', 'Topic', 'Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Correct Answer']
        if not all(col in df.columns for col in required_columns):
            st.error(f"Excel file must contain these columns: {', '.join(required_columns)}")
            return None
        
        # Add ID if not present
        if 'Id' not in df.columns:
            df['Id'] = range(1, len(df) + 1)
            
        return df
    except FileNotFoundError:
        st.error("MCQ data file 'mcq_data.xlsx' not found. Please ensure it exists in the same directory.")
        # Create sample data for demonstration
        st.info("Creating sample data for demonstration...")
        return create_sample_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def create_sample_data():
    """Create sample MCQ data for demonstration"""
    sample_data = {
        'Id': range(1, 21),
        'Exam': ['General Knowledge'] * 20,
        'Section': ['Science'] * 10 + ['History'] * 10,
        'Topic': ['Physics'] * 5 + ['Chemistry'] * 5 + ['Ancient'] * 5 + ['Modern'] * 5,
        'Question': [f'Sample question {i}?' for i in range(1, 21)],
        'Option A': [f'Option A for question {i}' for i in range(1, 21)],
        'Option B': [f'Option B for question {i}' for i in range(1, 21)],
        'Option C': [f'Option C for question {i}' for i in range(1, 21)],
        'Option D': [f'Option D for question {i}' for i in range(1, 21)],
        'Correct Answer': ['A', 'B', 'C', 'D'] * 5
    }
    df = pd.DataFrame(sample_data)
    
    # Save sample data
    try:
        df.to_excel('mcq_data.xlsx', index=False)
        st.success("Sample data created successfully!")
    except Exception as e:
        st.warning(f"Could not save sample data: {e}")
    
    return df

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

def load_leaderboard_data():
    """Load leaderboard data from results file"""
    try:
        df = pd.read_excel('user_results.xlsx')
        
        # Convert Date column to datetime if it exists
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Drop rows where date conversion failed
            df = df.dropna(subset=['Date'])
        
        return df
    except FileNotFoundError:
        st.info("No quiz results found yet. Complete a quiz to see leaderboard!")
        return None
    except Exception as e:
        st.error(f"Error loading leaderboard data: {e}")
        return None

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
            
            # Display PDF using base64 encoding
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            # Download button
            st.download_button(
                label="📥 Download PDF",
                data=pdf_bytes,
                file_name=selected_pdf,
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"Error loading PDF: {e}")

def display_leaderboard():
    """Display the leaderboard"""
    st.header("🏆 Leaderboard")
    
    # Load leaderboard data
    df = load_leaderboard_data()
    if df is None or df.empty:
        st.info("No quiz results available yet. Complete a quiz to appear on the leaderboard!")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exams = ["All"] + sorted(df['Exam'].unique())
        selected_exam = st.selectbox("Filter by Exam:", exams, key="leaderboard_exam")
    
    with col2:
        date_range = st.selectbox("Time Period:", ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"])
    
    with col3:
        min_questions = st.slider("Minimum Questions:", min_value=1, max_value=50, value=5)
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_exam != "All":
        filtered_df = filtered_df[filtered_df['Exam'] == selected_exam]
    
    if date_range != "All Time":
        if date_range == "Last 7 Days":
            cutoff_date = datetime.now() - timedelta(days=7)
        elif date_range == "Last 30 Days":
            cutoff_date = datetime.now() - timedelta(days=30)
        else:  # Last 90 Days
            cutoff_date = datetime.now() - timedelta(days=90)
        
        # Ensure Date column is datetime and filter
        filtered_df = filtered_df[filtered_df['Date'] >= cutoff_date]
    
    # Calculate leaderboard
    if not filtered_df.empty:
        # Get unique attempts (user + date combinations)
        attempts = filtered_df.groupby(['User Name', 'Date']).agg({
            'Total Questions': 'first',
            'Score Percentage': 'first'
        }).reset_index()
        
        # Filter by minimum questions
        attempts = attempts[attempts['Total Questions'] >= min_questions]
        
        if attempts.empty:
            st.warning("No results match the current filters.")
            return
        
        # Get best score per user
        leaderboard = attempts.groupby('User Name').agg({
            'Score Percentage': 'max',
            'Total Questions': 'mean',
            'Date': 'count'
        }).reset_index()
        
        leaderboard.columns = ['User Name', 'Best Score (%)', 'Avg Questions', 'Attempts']
        leaderboard['Avg Questions'] = leaderboard['Avg Questions'].round(1)
        
        # Sort by best score
        leaderboard = leaderboard.sort_values('Best Score (%)', ascending=False).reset_index(drop=True)
        leaderboard['Rank'] = leaderboard.index + 1
        
        # Display leaderboard
        st.subheader("Top Performers")
        
        # Metrics for top 3
        if len(leaderboard) >= 1:
            top1 = leaderboard.iloc[0]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🥇 1st Place", f"{top1['User Name']}", f"{top1['Best Score (%)']:.1f}%")
            if len(leaderboard) >= 2:
                top2 = leaderboard.iloc[1]
                with col2:
                    st.metric("🥈 2nd Place", f"{top2['User Name']}", f"{top2['Best Score (%)']:.1f}%")
            if len(leaderboard) >= 3:
                top3 = leaderboard.iloc[2]
                with col3:
                    st.metric("🥉 3rd Place", f"{top3['User Name']}", f"{top3['Best Score (%)']:.1f}%")
        
        # Detailed leaderboard table
        st.subheader("Detailed Leaderboard")
        
        # Format the leaderboard display
        display_df = leaderboard[['Rank', 'User Name', 'Best Score (%)', 'Avg Questions', 'Attempts']].copy()
        display_df['Best Score (%)'] = display_df['Best Score (%)'].round(1)
        
        # Add medal emojis for top 3
        def add_medal_emoji(rank):
            if rank == 1:
                return "🥇"
            elif rank == 2:
                return "🥈"
            elif rank == 3:
                return "🥉"
            else:
                return ""
        
        display_df['Medal'] = display_df['Rank'].apply(add_medal_emoji)
        display_df = display_df[['Rank', 'Medal', 'User Name', 'Best Score (%)', 'Avg Questions', 'Attempts']]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Performance statistics
        st.subheader("Performance Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Participants", len(leaderboard))
        with col2:
            st.metric("Average Score", f"{leaderboard['Best Score (%)'].mean():.1f}%")
        with col3:
            st.metric("Highest Score", f"{leaderboard['Best Score (%)'].max():.1f}%")
        with col4:
            st.metric("Lowest Score", f"{leaderboard['Best Score (%)'].min():.1f}%")
        
        # Recent attempts
        st.subheader("Recent Attempts")
        recent_attempts = attempts.sort_values('Date', ascending=False).head(10)
        recent_display = recent_attempts[['User Name', 'Date', 'Total Questions', 'Score Percentage']].copy()
        recent_display['Score Percentage'] = recent_display['Score Percentage'].round(1)
        
        # Safe date formatting
        if 'Date' in recent_display.columns:
            try:
                # Convert to string format safely
                recent_display['Date'] = recent_display['Date'].apply(
                    lambda x: x.strftime('%Y-%m-%d %H:%M') if pd.notnull(x) else 'Unknown'
                )
            except Exception as e:
                st.warning(f"Could not format dates: {e}")
                # If formatting fails, keep original dates
                recent_display['Date'] = recent_display['Date'].astype(str)
        
        st.dataframe(recent_display, use_container_width=True)
        
    else:
        st.info("No results available for the selected filters.")

def initialize_session_state():
    """Initialize session state variables"""
    default_state = {
        'quiz_started': False,
        'current_question': 0,
        'user_answers': {},
        'quiz_questions': None,
        'start_time': None,
        'time_up': False,
        'marked_questions': set(),
        'visited_questions': set(),
        'user_name': "",
        'current_exam': "",
        'current_section': "",
        'current_topic': "",
        'total_questions': 0,
        'time_limit': 0,
        'quiz_completed': False
    }
    
    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

def start_quiz(exam, section, topic, df, user_name, num_questions):
    """Start a new quiz with selected parameters"""
    try:
        # Filter questions based on selection
        filtered_df = df.copy()
        
        if exam != "All":
            filtered_df = filtered_df[filtered_df['Exam'] == exam]
        if section != "All":
            filtered_df = filtered_df[filtered_df['Section'] == section]
        if topic != "All":
            filtered_df = filtered_df[filtered_df['Topic'] == topic]
        
        if len(filtered_df) == 0:
            st.error("No questions found with the selected filters.")
            return False
            
        if len(filtered_df) < num_questions:
            st.warning(f"Only {len(filtered_df)} questions available. Using all available questions.")
            num_questions = len(filtered_df)
        
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
        st.session_state.quiz_completed = False
        
        return True
    except Exception as e:
        st.error(f"Error starting quiz: {e}")
        return False

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
    
    # Get the index of current answer for the radio button
    current_index = options.index(current_answer) if current_answer in options else 0
    
    user_answer = st.radio(
        "Select your answer:",
        options=options,
        index=current_index,
        key=answer_key,
        format_func=lambda x: f"{x}: {option_texts[options.index(x)]}"
    )
    
    # Save answer immediately when selected
    if user_answer and user_answer != current_answer:
        st.session_state.user_answers[question_data['Id']] = user_answer
    
    return user_answer

def create_question_palette():
    """Create a question navigation palette"""
    st.sidebar.markdown("### 📋 Question Palette")
    
    total_questions = st.session_state.total_questions
    cols_per_row = 5
    rows = (total_questions + cols_per_row - 1) // cols_per_row
    
    for row in range(rows):
        cols = st.sidebar.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            question_idx = row * cols_per_row + col_idx
            if question_idx < total_questions:
                with cols[col_idx]:
                    status = ""
                    btn_label = f"Q{question_idx+1}"
                    
                    if question_idx in st.session_state.visited_questions:
                        if question_idx in st.session_state.marked_questions:
                            status = " 📌"
                        elif st.session_state.quiz_questions.iloc[question_idx]['Id'] in st.session_state.user_answers:
                            status = " ✅"
                        else:
                            status = " ⭕"
                    
                    btn_type = "primary" if question_idx == st.session_state.current_question else "secondary"
                    
                    if st.button(f"{btn_label}{status}", key=f"pal_{question_idx}", type=btn_type, use_container_width=True):
                        st.session_state.current_question = question_idx
                        st.session_state.visited_questions.add(question_idx)
                        st.rerun()

def display_timer():
    """Display the timer"""
    if st.session_state.quiz_started and not st.session_state.time_up and not st.session_state.quiz_completed:
        current_time = datetime.now()
        elapsed_time = (current_time - st.session_state.start_time).total_seconds()
        remaining_time = max(0, st.session_state.time_limit * 60 - elapsed_time)
        
        if remaining_time <= 0:
            st.session_state.time_up = True
            st.error("⏰ Time's up! Auto-submitting your quiz...")
            time.sleep(2)
            st.rerun()
        else:
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            
            if minutes < 1:
                color = "red"
            elif minutes < 3:
                color = "orange"
            else:
                color = "green"
            
            # Progress bar for time
            progress = elapsed_time / (st.session_state.time_limit * 60)
            st.progress(progress)
            
            st.markdown(
                f"<h3 style='color: {color}; text-align: center;'>"
                f"⏱️ Time Remaining: {minutes:02d}:{seconds:02d}"
                f"</h3>", 
                unsafe_allow_html=True
            )

def calculate_results():
    """Calculate and return quiz results"""
    try:
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
        
        score_percentage = (correct_count / len(questions_df)) * 100 if len(questions_df) > 0 else 0
        
        return {
            'results_df': pd.DataFrame(results),
            'total_questions': len(questions_df),
            'attempted': attempted_count,
            'correct': correct_count,
            'incorrect': attempted_count - correct_count,
            'not_attempted': len(questions_df) - attempted_count,
            'score_percentage': score_percentage
        }
    except Exception as e:
        st.error(f"Error calculating results: {e}")
        return None

def display_scorecard(results):
    """Display the scorecard after quiz completion"""
    if results is None:
        st.error("Error calculating results.")
        return
        
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
    
    # Score visualization
    st.subheader("Performance Summary")
    chart_data = pd.DataFrame({
        'Category': ['Correct', 'Incorrect', 'Not Attempted'],
        'Count': [results['correct'], results['incorrect'], results['not_attempted']]
    })
    st.bar_chart(chart_data.set_index('Category'))
    
    # Detailed results
    st.subheader("Detailed Results")
    st.dataframe(results['results_df'], use_container_width=True)
    
    # Save results
    if save_results_data(results):
        st.success("Results saved successfully!")
    else:
        st.error("Failed to save results.")

def save_results_data(results):
    """Prepare and save results data"""
    try:
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
                'Result': row['Result'],
                'Score Percentage': results['score_percentage']
            })
        
        results_df = pd.DataFrame(results_data)
        return save_results(results_df)
    except Exception as e:
        st.error(f"Error preparing results: {e}")
        return False

def reset_quiz():
    """Reset the quiz state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def main():
    st.title("📚 MCQ Quiz Application")
    st.markdown("---")
    
    # Initialize session state
    initialize_session_state()
    
    # Load data
    df = load_data()
    if df is None:
        st.error("Failed to load question data. Please check the Excel file.")
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    if not st.session_state.quiz_started or st.session_state.quiz_completed:
        page = st.sidebar.radio("Go to", ["🏠 Home", "📚 Notes", "🏆 Leaderboard"])
    else:
        page = "🎯 Quiz"
    
    if page == "📚 Notes":
        display_pdf_viewer()
        return
    elif page == "🏆 Leaderboard":
        display_leaderboard()
        return
    
    # Home/Quiz page
    if not st.session_state.quiz_started or st.session_state.quiz_completed:
        # Quiz setup
        st.header("Quiz Setup")
        
        user_name = st.text_input("Enter your name:", value=st.session_state.user_name)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exams = ["All"] + sorted(df['Exam'].unique())
            selected_exam = st.selectbox("Select Exam:", exams, index=0)
        
        with col2:
            if selected_exam == "All":
                sections = ["All"]
            else:
                sections = ["All"] + sorted(df[df['Exam'] == selected_exam]['Section'].unique())
            selected_section = st.selectbox("Select Section:", sections, index=0)
        
        with col3:
            if selected_exam == "All" and selected_section == "All":
                topics = ["All"]
            elif selected_section == "All":
                topics = ["All"] + sorted(df[df['Exam'] == selected_exam]['Topic'].unique())
            else:
                topics = ["All"] + sorted(df[(df['Exam'] == selected_exam) & 
                                         (df['Section'] == selected_section)]['Topic'].unique())
            selected_topic = st.selectbox("Select Topic:", topics, index=0)
        
        # Show available questions count
        filtered_df = df.copy()
        if selected_exam != "All":
            filtered_df = filtered_df[filtered_df['Exam'] == selected_exam]
        if selected_section != "All":
            filtered_df = filtered_df[filtered_df['Section'] == selected_section]
        if selected_topic != "All":
            filtered_df = filtered_df[filtered_df['Topic'] == selected_topic]
        
        available_questions = len(filtered_df)
        st.info(f"📊 Available questions with current filters: {available_questions}")
        
        num_questions = st.slider(
            "Number of Questions:",
            min_value=1,
            max_value=min(50, available_questions),
            value=min(10, available_questions)
        )
        
        st.info(f"⏱️ Time allocated: {num_questions} minutes (1 minute per question)")
        
        if user_name:
            if st.button("Start Quiz", type="primary"):
                if start_quiz(selected_exam, selected_section, selected_topic, df, user_name, num_questions):
                    st.rerun()
        else:
            st.warning("Please enter your name to start the quiz.")
    
    else:
        # Quiz interface
        st.header("MCQ Quiz")
        
        # Display question palette
        create_question_palette()
        
        # Display timer
        display_timer()
        
        # Check if time is up or quiz completed
        if st.session_state.time_up or st.session_state.quiz_completed:
            results = calculate_results()
            display_scorecard(results)
            if st.button("Start New Quiz", type="primary"):
                reset_quiz()
            return
        
        # Display current question
        current_q = st.session_state.quiz_questions.iloc[st.session_state.current_question]
        user_answer = display_question(current_q, st.session_state.current_question)
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            if st.session_state.current_question > 0:
                if st.button("⬅️ Previous", type="secondary", use_container_width=True):
                    st.session_state.current_question -= 1
                    st.session_state.visited_questions.add(st.session_state.current_question)
                    st.rerun()
        
        with col2:
            if st.button("🗑️ Clear Answer", type="secondary", use_container_width=True):
                if current_q['Id'] in st.session_state.user_answers:
                    del st.session_state.user_answers[current_q['Id']]
                st.rerun()
        
        with col3:
            if st.session_state.current_question in st.session_state.marked_questions:
                if st.button("❌ Unmark", type="secondary", use_container_width=True):
                    st.session_state.marked_questions.remove(st.session_state.current_question)
                    st.rerun()
            else:
                if st.button("📍 Mark", type="secondary", use_container_width=True):
                    st.session_state.marked_questions.add(st.session_state.current_question)
                    st.rerun()
        
        with col4:
            if st.session_state.current_question < st.session_state.total_questions - 1:
                if st.button("Next ➡️", type="primary", use_container_width=True):
                    st.session_state.current_question += 1
                    st.session_state.visited_questions.add(st.session_state.current_question)
                    st.rerun()
            else:
                if st.button("Finish 🏁", type="primary", use_container_width=True):
                    st.session_state.quiz_completed = True
                    st.rerun()
        
        # Quick navigation info
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Navigation Help")
        st.sidebar.info("""
        - Use **Question Palette** to jump to any question
        - **Mark** questions for review
        - **Clear** your answer if needed
        - **Finish** when you're done
        """)

if __name__ == "__main__":
    main()
