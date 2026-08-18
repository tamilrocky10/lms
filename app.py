import streamlit as st
import sqlite3
from pathlib import Path
import hashlib

DB = Path("lms.db")
st.set_page_config(page_title="Smart LMS", page_icon="🎓", layout="wide")

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        instructor TEXT,
        duration TEXT,
        lessons INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS enrollments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        course_id INTEGER,
        progress INTEGER DEFAULT 0,
        UNIQUE(user_id, course_id))""")
    if not cur.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        cur.execute("INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)", ("Administrator", "admin", hash_pw("admin123"), "admin"))
    if not cur.execute("SELECT 1 FROM users WHERE username='student'").fetchone():
        cur.execute("INSERT INTO users(name,username,password,role) VALUES(?,?,?,?)", ("Demo Student", "student", hash_pw("student123"), "student"))
    if cur.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        cur.executemany("INSERT INTO courses(title,description,instructor,duration,lessons) VALUES(?,?,?,?,?)", [
            ("Python Programming", "Learn Python from basics to practical programming.", "Smart LMS", "20 Hours", 12),
            ("Web Development", "HTML, CSS, JavaScript and responsive web design.", "Smart LMS", "25 Hours", 15),
            ("Database Management", "SQL, relational databases and database design.", "Smart LMS", "18 Hours", 10),
        ])
    conn.commit(); conn.close()

def authenticate(username, password):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_pw(password))).fetchone()
    conn.close(); return user

def logout():
    st.session_state.clear(); st.rerun()

init_db()
if not st.session_state.get("logged_in"):
    st.markdown("<style>.hero{padding:42px 20px;text-align:center;border-radius:20px;background:linear-gradient(135deg,#2563eb,#7c3aed);color:white}.hero h1{font-size:48px;margin:0 0 8px}</style>", unsafe_allow_html=True)
    st.markdown('<div class="hero"><h1>🎓 Smart LMS</h1><p>Learning Management System powered by Streamlit</p></div>', unsafe_allow_html=True)
    st.write("")
    a,b,c=st.columns(3); a.metric("Courses",3); b.metric("Learning","24/7"); c.metric("Platform","Streamlit")
    with st.form("login"):
        st.subheader("Sign in"); username=st.text_input("Username"); password=st.text_input("Password",type="password")
        if st.form_submit_button("Sign In",use_container_width=True):
            user=authenticate(username.strip(),password)
            if user:
                st.session_state.logged_in=True; st.session_state.user=dict(user); st.rerun()
            else: st.error("Invalid username or password")
    with st.expander("Demo credentials"):
        st.write("Admin: `admin` / `admin123`"); st.write("Student: `student` / `student123`")
    st.stop()

user=st.session_state.user
with st.sidebar:
    st.title("🎓 Smart LMS"); st.caption(f"Logged in as **{user['name']}**")
    pages=["Dashboard","Courses","Add Course","Users"] if user["role"]=="admin" else ["Dashboard","My Courses","Course Catalog"]
    page=st.radio("Navigation",pages); st.divider()
    if st.button("Logout",use_container_width=True): logout()
conn=get_db()

if page=="Dashboard":
    st.title(f"Welcome, {user['name']} 👋")
    if user['role']=='admin':
        a,b,c=st.columns(3); a.metric("Total Courses",conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]); b.metric("Total Users",conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]); c.metric("Enrollments",conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0])
        rows=conn.execute("SELECT c.title,COUNT(e.id) enrollments FROM courses c LEFT JOIN enrollments e ON c.id=e.course_id GROUP BY c.id ORDER BY enrollments DESC").fetchall(); st.dataframe([dict(r) for r in rows],use_container_width=True,hide_index=True)
    else:
        rows=conn.execute("SELECT c.*,e.progress,e.id enrollment_id FROM courses c JOIN enrollments e ON c.id=e.course_id WHERE e.user_id=?",(user['id'],)).fetchall()
        if not rows: st.info("You are not enrolled in any course yet.")
        for r in rows:
            with st.container(border=True):
                st.subheader(r['title']); st.write(r['description']); st.progress(r['progress']/100); st.caption(f"{r['progress']}% completed • {r['duration']}")
                if st.button("Complete Next Lesson",key=f"dash{r['id']}"):
                    p=min(100,r['progress']+max(1,round(100/r['lessons']))); conn.execute("UPDATE enrollments SET progress=? WHERE id=?",(p,r['enrollment_id'])); conn.commit(); st.rerun()
elif page=="Courses":
    st.title("Course Management")
    for c in conn.execute("SELECT * FROM courses ORDER BY id DESC").fetchall():
        with st.container(border=True):
            col1,col2=st.columns([5,1]); col1.subheader(c['title']); col1.write(c['description']); col1.caption(f"{c['instructor']} • {c['duration']} • {c['lessons']} lessons")
            if col2.button("Delete",key=f"del{c['id']}"): conn.execute("DELETE FROM courses WHERE id=?",(c['id'],)); conn.commit(); st.rerun()
elif page=="Add Course":
    st.title("Add New Course")
    with st.form("add_course"):
        title=st.text_input("Course Title"); description=st.text_area("Description"); instructor=st.text_input("Instructor"); duration=st.text_input("Duration",placeholder="e.g. 20 Hours"); lessons=st.number_input("Number of Lessons",min_value=1,value=10)
        if st.form_submit_button("Create Course",use_container_width=True):
            if title.strip(): conn.execute("INSERT INTO courses(title,description,instructor,duration,lessons) VALUES(?,?,?,?,?)",(title,description,instructor,duration,lessons)); conn.commit(); st.success("Course created successfully")
            else: st.error("Course title is required")
elif page=="Users":
    st.title("Users"); st.dataframe([dict(r) for r in conn.execute("SELECT id,name,username,role FROM users ORDER BY id").fetchall()],use_container_width=True,hide_index=True)
elif page=="My Courses":
    st.title("My Courses"); rows=conn.execute("SELECT c.*,e.progress,e.id enrollment_id FROM courses c JOIN enrollments e ON c.id=e.course_id WHERE e.user_id=?",(user['id'],)).fetchall()
    if not rows: st.info("No enrolled courses yet.")
    for c in rows:
        with st.container(border=True):
            st.subheader(c['title']); st.write(c['description']); st.progress(c['progress']/100); st.write(f"Progress: {c['progress']}%")
            if st.button("Complete Next Lesson",key=f"lesson{c['id']}"):
                p=min(100,c['progress']+max(1,round(100/c['lessons']))); conn.execute("UPDATE enrollments SET progress=? WHERE id=?",(p,c['enrollment_id'])); conn.commit(); st.rerun()
elif page=="Course Catalog":
    st.title("Course Catalog")
    for c in conn.execute("SELECT * FROM courses ORDER BY title").fetchall():
        with st.container(border=True):
            st.subheader(c['title']); st.write(c['description']); st.caption(f"{c['duration']} • {c['lessons']} lessons • {c['instructor']}")
            existing=conn.execute("SELECT id FROM enrollments WHERE user_id=? AND course_id=?",(user['id'],c['id'])).fetchone()
            if existing: st.success("Already enrolled")
            elif st.button("Enroll Now",key=f"enroll{c['id']}"): conn.execute("INSERT INTO enrollments(user_id,course_id,progress) VALUES(?,?,0)",(user['id'],c['id'])); conn.commit(); st.rerun()
conn.close()
