"""Fictional course-project and teaching-task families, fixed before wording."""

PROJECTS = {
    "record_program": {
        "course":"Introduction to Programming", "tools":["{language}"],
        "topics":["library catalogue","course planner","recipe organiser","study-session scheduler"],
        "tasks":["implemented a menu-driven program using functions and collections","added input checks and handled invalid entries","tested representative inputs and recorded expected outputs","documented how records are added, searched and updated"]},
    "data_structures": {
        "course":"Data Structures", "tools":["{language}","Git"],
        "topics":["task queue","contact index","document lookup","event ordering"],
        "tasks":["implemented linked structures and traversal operations","wrote tests for insertion, lookup and deletion","compared alternative data structures for the recorded operations","documented operation costs and boundary cases"]},
    "graph_algorithms": {
        "course":"Algorithms", "tools":["{language}","Git"],
        "topics":["campus route finder","dependency ordering","maze traversal","course prerequisite graph"],
        "tasks":["represented connections using adjacency lists","implemented graph traversal and a route or ordering routine","tested connected, disconnected and cyclic examples","explained algorithm choices and computational complexity"]},
    "software_testing": {
        "course":"Software Engineering", "tools":["{language}","Git"],
        "topics":["date parser","string utility library","calculator module","file validation utility"],
        "tasks":["wrote automated tests for a small software module","designed boundary and invalid-input test cases","isolated a defect using a minimal reproducing example","documented expected behaviour and regression checks"]},
    "database": {
        "course":"Database Systems", "tools":["SQL","SQLite"],
        "topics":["book lending records","course enrolment records","equipment inventory","event registration records"],
        "tasks":["designed related tables and key constraints","wrote queries joining and aggregating sample records","checked missing values and duplicate records","documented the schema and example queries"]},
    "web_interface": {
        "course":"Web Programming", "tools":["JavaScript","HTML","CSS"],
        "topics":["quiz practice interface","study planner interface","local book search interface","flashcard practice interface"],
        "tasks":["built a local browser interface with form inputs","implemented event handling and input validation","tested keyboard interaction and alternate input cases","documented the interface and its local data flow"]},
    "systems": {
        "course":"Computer Systems", "tools":["C","Git"],
        "topics":["buffer management exercise","memory allocation exercise","binary file reader","command-line text utility"],
        "tasks":["implemented a small systems program with explicit memory handling","checked array bounds and error paths","traced program behaviour using a debugger","documented the program structure and test cases"]},
    "discrete_simulation": {
        "course":"Discrete Mathematics", "tools":["{language}"],
        "topics":["finite-state machine simulator","truth-table explorer","set operation explorer","graph property checker"],
        "tasks":["translated discrete mathematical definitions into program functions","constructed examples and counterexamples for the represented rules","tested the implementation against hand-worked cases","explained the connection between the formal definitions and implementation"]},
}

ROLE_TASKS = {
    "Teaching Assistant": ["assisted introductory programming lab sessions","answered student questions during office hours","graded programming exercises using an instructor-provided rubric","prepared worked examples for instructor review","helped organise assignment materials and submission records"],
    "Programming Tutor": ["guided beginning programmers through practice exercises","discussed debugging approaches during tutoring sessions","asked learners to explain the steps in their solutions","prepared practice questions for individual tutoring sessions"],
    "Peer Programming Mentor": ["supported beginner practice sessions","explained worked examples under a course instructor's supervision","facilitated discussion of common programming errors","helped peers trace short programs step by step"],
}

FEEDBACK_CONTEXT = {
    "Teaching Assistant":"the supervising course instructor",
    "Programming Tutor":"the tutoring programme coordinator",
    "Peer Programming Mentor":"the supervising course instructor",
}
