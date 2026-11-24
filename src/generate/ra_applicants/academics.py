"""Varied, dated academic records with explicit practical NLP evidence."""

from phd_resumes.sampling import month_index

COURSES = {
    'programming': {'undergraduate': ('Programming Fundamentals','Scientific Programming'), 'graduate': ('Software Development for Research',)},
    'statistics': {'undergraduate': ('Probability and Statistics','Statistical Inference'), 'graduate': ('Statistical Learning','Applied Regression')},
    'data_structures': {'undergraduate': ('Data Structures and Algorithms','Algorithms and Data Structures'), 'graduate': ('Advanced Algorithms',)},
    'linear_algebra': {'undergraduate': ('Linear Algebra','Computational Linear Algebra'), 'graduate': ('Numerical Linear Algebra',)},
    'data_management': {'undergraduate': ('Data Management','Data Wrangling and Management'), 'graduate': ('Graduate Data Analysis','Data Engineering')},
    'machine_learning': {'undergraduate': ('Introduction to Machine Learning','Statistical Pattern Recognition'), 'graduate': ('Machine Learning','Probabilistic Models')},
    'software_engineering': {'undergraduate': ('Software Engineering','Software Testing'), 'graduate': ('Reliable Scientific Software',)},
    'nlp': {'undergraduate': ('Natural Language Processing','Introduction to Text Analysis'), 'graduate': ('Graduate Text Mining','Computational Linguistics')},
}
ELECTIVES = ('data_structures','linear_algebra','data_management','machine_learning','software_engineering','nlp')
MAJOR_WEIGHTS = {
    'Computer Science': (3,1,3,2,2,1),
    'Software Engineering': (3,1,2,1,4,1),
    'Computer Engineering': (3,2,2,2,3,1),
    'Mathematics': (2,4,1,3,1,1),
    'Statistics': (1,3,3,4,1,1),
    'Computational Linguistics': (2,1,2,2,1,5),
}
THEORY = 'Written analysis of language-processing concepts and methods; no assessed coding component.'
PRACTICAL = 'Assessed practical work documented in the linked course project.'
STANDARD = 'Course exercises and examinations; no separate project contribution claimed here.'


def term_ends(start,end):
    return [f'{year}-{month}' for year in range(int(start[:4]),int(end[:4])+1) for month in ('05','12') if start < f'{year}-{month}' <= end]


def completion_for(entry,degree,snapshot):
    choices=[d for d in term_ends(degree['start'],min(degree['end'],snapshot)) if d>=entry['end']]
    return min(choices) if choices else None


def sample_courses(education,entries,academic,graduate,config,rng):
    ug,grad=education;snapshot=config['record_as_of'][:7]
    major=ug['degree'].removeprefix('BS in ')
    choices=list(ELECTIVES);weights=list(MAJOR_WEIGHTS[major]);selected=[]
    for _ in range(3):
        area=rng.choices(choices,weights)[0];i=choices.index(area)
        selected.append(area);choices.pop(i);weights.pop(i)
    areas={'undergraduate':['programming','statistics',*selected], 'graduate':rng.sample(['statistics','data_structures','linear_algebra','data_management','machine_learning','software_engineering','nlp'],2)}
    practical={}
    for level,degree in (('undergraduate',ug),('graduate',grad)):
        role='Undergraduate course project' if level=='undergraduate' else 'Graduate course project'
        candidates=[e for e in entries if e['role']==role and 'nlp' in e['technical_evidence'] and completion_for(e,degree,snapshot)]
        if candidates and ('nlp' in areas[level] or rng.random()<config['practical_nlp_course_probability']):
            e=rng.choice(candidates);practical[level]=e
            if 'nlp' not in areas[level]:areas[level][-1]='nlp'
    courses=[]
    earliest=min(e['start'] for e in entries)
    for level,degree,ability in (('undergraduate',ug,academic),('graduate',grad,graduate)):
        dates=term_ends(degree['start'],min(degree['end'],snapshot))
        for area in areas[level]:
            eligible=dates
            if level=='undergraduate' and area in ('programming','statistics'):
                eligible=[d for d in dates if d<=earliest and month_index(d)-month_index(degree['start'])<=24]
            elif level=='undergraduate':
                eligible=[d for d in dates if month_index(d)-month_index(degree['start'])>=16]
            if not eligible:raise ValueError('No coherent course date for sampled education')
            source=practical.get(level) if area=='nlp' else None
            date=completion_for(source,degree,snapshot) if source else rng.choice(eligible)
            courses.append({'course':rng.choice(COURSES[area][level]),'area':area,'level':level,'date':date,'grade':rng.choices(config['grade_values'],config['grade_probabilities_by_academic_level'][ability])[0],'assessment':PRACTICAL if source else THEORY if area=='nlp' else STANDARD,'practical_source_id':source['id'] if source else None})
    return sorted(courses,key=lambda c:(c['level']=='graduate',c['date'],c['area']))


def validate_courses(courses,education,entries,snapshot):
    if len(courses)!=7:raise ValueError('Expected five selected undergraduate and two selected graduate courses')
    emap={e['id']:e for e in entries};seen=set()
    for c in courses:
        if set(c)!={'course','area','level','date','grade','assessment','practical_source_id'}:raise ValueError('Invalid course fields')
        if c['level'] not in ('undergraduate','graduate') or c['area'] not in COURSES or c['course'] not in COURSES[c['area']][c['level']]:raise ValueError('Unsupported course area/title')
        key=(c['area'],c['level'])
        if key in seen:raise ValueError('Duplicate course area within degree')
        seen.add(key)
        degree=education[c['level']=='graduate']
        if c['date'] not in term_ends(degree['start'],min(degree['end'],snapshot)):raise ValueError('Course outside degree terms/snapshot')
        source=c['practical_source_id']
        if source is not None:
            e=emap.get(source);role='Undergraduate course project' if c['level']=='undergraduate' else 'Graduate course project'
            if not e or c['area']!='nlp' or c['assessment']!=PRACTICAL or e['role']!=role or 'nlp' not in e['technical_evidence']:raise ValueError('Invalid practical coursework source')
            if c['date']!=completion_for(e,degree,snapshot):raise ValueError('Practical coursework predates or misdates its project')
        elif c['assessment']!=(THEORY if c['area']=='nlp' else STANDARD):raise ValueError('Unsupported course assessment')
    if sum(c['level']=='undergraduate' for c in courses)!=5 or sum(c['level']=='graduate' for c in courses)!=2:raise ValueError('Invalid selected course counts')
    if not {('programming','undergraduate'),('statistics','undergraduate')}<=seen:raise ValueError('Missing foundation course evidence')
    first_work=min(e['start'] for e in entries)
    if not all(c['date']<=first_work for c in courses if c['level']=='undergraduate' and c['area'] in ('programming','statistics')):raise ValueError('Work precedes foundation coursework')
