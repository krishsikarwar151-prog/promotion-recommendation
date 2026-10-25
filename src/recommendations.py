"""
Skill Gap Analysis & Development Recommendations module.

Produces data-driven but transparent, rule-based recommendations for each employee
when individual-level training history is insufficient for a personalized ML model.

All recommendations are framed as suggestions for HR review — NOT as automated decisions.
"""
import pandas as pd
from typing import List, Dict


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark thresholds (derived from dataset analysis)
# ──────────────────────────────────────────────────────────────────────────────
BENCHMARK = {
    'avg_training_score':    75,   # ~top third of promoted employees
    'previous_year_rating':  4,    # consistent high performers
    'no_of_trainings':       2,    # at least 2 completed trainings
    'kpis_met':              1,    # KPIs met >80%
    'awards_won':            0,    # any award is a bonus
}

SKILL_AREAS = {
    'training_score': {
        'name': 'Technical / Functional Skills',
        'resources': [
            'Enroll in role-specific online certification (Coursera / LinkedIn Learning)',
            'Join internal upskilling bootcamp for the next training cycle',
            'Request structured mentorship from a senior team member',
        ]
    },
    'leadership': {
        'name': 'Leadership & Management Readiness',
        'resources': [
            'Participate in cross-functional project leadership opportunities',
            'Attend organization-level strategy workshops',
            'Shadow a department head for a quarter',
        ]
    },
    'kpi': {
        'name': 'KPI Delivery & Goal Setting',
        'resources': [
            'Review and revise personal OKR framework with manager',
            'Join time-management and prioritization workshop',
            'Implement weekly milestone check-in cadence',
        ]
    },
    'recognition': {
        'name': 'Visibility & Organizational Recognition',
        'resources': [
            'Nominate for internal innovation or excellence award',
            'Present a quarterly project impact summary to leadership',
            'Contribute to organization-wide knowledge-sharing sessions',
        ]
    },
    'tenure': {
        'name': 'Experience & Domain Depth',
        'resources': [
            'Seek stretch assignments in adjacent functional areas',
            'Pursue advanced certification in core domain',
            'Build cross-department collaboration portfolio',
        ]
    }
}


# ──────────────────────────────────────────────────────────────────────────────
def analyse_skill_gaps(employee: dict) -> List[Dict]:
    """
    Analyse an employee record and return a list of identified skill-gap areas.

    Each item in the returned list is:
    {
      'area': str,          # area key
      'name': str,          # display name
      'gap_description': str,
      'priority': str,      # 'High' | 'Medium' | 'Low'
      'resources': List[str]
    }
    """
    gaps = []

    score = employee.get('avg_training_score', 0)
    if score < BENCHMARK['avg_training_score']:
        gap = BENCHMARK['avg_training_score'] - score
        gaps.append({
            'area': 'training_score',
            'name': SKILL_AREAS['training_score']['name'],
            'gap_description': (
                f"Training score is **{score}/100** (benchmark ≥{BENCHMARK['avg_training_score']}). "
                f"A **+{gap} point** improvement is recommended."
            ),
            'priority': 'High' if gap > 20 else 'Medium',
            'resources': SKILL_AREAS['training_score']['resources']
        })

    rating = employee.get('previous_year_rating', 0)
    if rating < BENCHMARK['previous_year_rating']:
        gaps.append({
            'area': 'leadership',
            'name': SKILL_AREAS['leadership']['name'],
            'gap_description': (
                f"Previous year rating is **{rating}/5** (benchmark ≥{BENCHMARK['previous_year_rating']}). "
                "Consistent high performance (4–5) is associated with promotion readiness."
            ),
            'priority': 'High' if rating <= 2 else 'Medium',
            'resources': SKILL_AREAS['leadership']['resources']
        })

    kpi = employee.get('KPIs_met >80%', employee.get('kpis_met', 0))
    if kpi == 0:
        gaps.append({
            'area': 'kpi',
            'name': SKILL_AREAS['kpi']['name'],
            'gap_description': (
                "KPIs were **not met at the >80% threshold** in the last review cycle. "
                "Meeting this benchmark is one of the strongest predictors in the model."
            ),
            'priority': 'High',
            'resources': SKILL_AREAS['kpi']['resources']
        })

    award = employee.get('awards_won?', employee.get('awards_won', 0))
    if award == 0:
        gaps.append({
            'area': 'recognition',
            'name': SKILL_AREAS['recognition']['name'],
            'gap_description': (
                "No awards received during service tenure. "
                "Organizational recognition increases visibility in promotion decisions."
            ),
            'priority': 'Low',
            'resources': SKILL_AREAS['recognition']['resources']
        })

    service = employee.get('length_of_service', 0)
    if service < 3:
        gaps.append({
            'area': 'tenure',
            'name': SKILL_AREAS['tenure']['name'],
            'gap_description': (
                f"Length of service is **{service} year(s)**. "
                "Building deeper domain expertise over time strengthens promotion candidacy."
            ),
            'priority': 'Low',
            'resources': SKILL_AREAS['tenure']['resources']
        })

    # Sort: High → Medium → Low
    priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
    gaps.sort(key=lambda x: priority_order.get(x['priority'], 3))
    return gaps


def build_development_plan(employee: dict, gaps: List[Dict]) -> Dict:
    """
    Generate a structured 90-day development plan based on identified gaps.
    """
    if not gaps:
        return {
            'summary': "✅ No major skill gaps identified. This employee meets key promotion benchmarks.",
            'timeline': [],
            'next_review': "Scheduled performance review recommended in 6 months.",
        }

    timeline = []
    month_map = {'High': '0–30 Days', 'Medium': '30–60 Days', 'Low': '60–90 Days'}

    for gap in gaps:
        window = month_map.get(gap['priority'], '60–90 Days')
        timeline.append({
            'window': window,
            'area': gap['name'],
            'action': gap['resources'][0],   # primary recommendation
            'priority': gap['priority']
        })

    high_count = sum(1 for g in gaps if g['priority'] == 'High')

    summary = (
        f"**{high_count} high-priority** area(s) identified. "
        "Completing the recommended actions within 90 days is expected to meaningfully improve "
        "the employee's promotion readiness profile."
    ) if high_count > 0 else (
        "No high-priority gaps found. Focus on medium/low areas to further strengthen the profile."
    )

    return {
        'summary': summary,
        'timeline': timeline,
        'next_review': "Recommend scheduling a formal performance review in 3–6 months.",
    }
