"""
Physics Validator Module
Detects violations of fundamental physics laws in story text
"""
import re
from typing import List, Dict, Tuple

# Physics violation patterns organized by category
PHYSICS_VIOLATIONS = {
    "gravity": {
        "name": "Gravity Violations",
        "patterns": [
            # Upward motion without force
            (r'\b(flew|floated|rose|lifted|ascended)\s+(?:up(?:ward)?|into\s+(?:the\s+)?(?:sky|air|ceiling))\b(?!.*(?:pulled|pushed|threw|tossed|jumped|rocket|balloon|bird|plane|helicopter))', 
             "Upward motion without apparent force or mechanism"),
            # Objects falling upward
            (r'\b(?:fell|dropped|shot)\s+(?:up(?:ward)?|into\s+(?:the\s+)?(?:sky|air|ceiling))\b',
             "Objects falling upward instead of down"),
            # Reversed gravity
            (r'\b(?:gravity|pull)\s+(?:reversed|backwards|upward|inverted)\b',
             "Reversed gravity direction"),
            # Selective gravity
            (r'\b(?:only|just)\s+(?:the\s+)?\w+\s+(?:were?\s+)?(?:affected\s+by|felt|experienced)\s+gravity\b',
             "Selective gravity affecting only certain objects"),
            # Terrain/landscape moving
            (r'\b(?:valley|mountain|hill|terrain|land|ground|earth)\s+(?:flew|floated|moved|shifted|rose|lifted)\b',
             "Impossible movement of large terrain features"),
        ]
    },
    "energy": {
        "name": "Conservation of Energy Violations",
        "patterns": [
            # Energy from nothing
            (r'\bwithout\s+(?:any\s+)?(?:fuel|power|battery|batteries|energy|source|electricity|wires)\b.*\b(?:lit\s+up|powered|ran|worked|glowed|shone)\b',
             "Energy appearing from nowhere"),
            # Perpetual motion
            (r'\b(?:running|spinning|moving|working)\s+(?:for\s+)?(?:\d+\s+)?(?:years?|centuries|forever|continuously|endlessly)\s+(?:without|on\s+its\s+own)\b',
             "Perpetual motion without energy source"),
            # Self-sustaining systems
            (r'\b(?:ran|worked|operated)\s+on\s+its\s+own\b',
             "Self-sustaining operation without energy input"),
        ]
    },
    "mass": {
        "name": "Conservation of Mass Violations",
        "patterns": [
            # Disappearing matter
            (r'\b(?:vanished|disappeared|evaporated)\s+(?:without|into\s+(?:thin\s+)?air)\b(?!.*(?:magic|illusion|trick))',
             "Matter disappearing without explanation"),
            # Duplicating matter
            (r'\b(?:duplicate|copy|copies|clone|clones|multiplied)\s+(?:popped|appeared|materialized)\b',
             "Matter duplicating spontaneously"),
            # Half disappearing
            (r'\bhalf\s+(?:the\s+)?\w+\s+(?:vanished|disappeared|gone)\b',
             "Partial matter disappearance"),
        ]
    },
    "thermodynamics": {
        "name": "Thermodynamics Violations",
        "patterns": [
            # Heat flowing wrong direction
            (r'\b(?:ice|frozen|cold)\b.*\b(?:in\s+(?:the\s+)?(?:sun|heat|fire|hot))\b.*\b(?:froze|colder|freeze|harder)\b',
             "Heat flowing from cold to hot (2nd law violation)"),
            # Instant temperature changes
            (r'\b(?:instantly|immediately|suddenly|within\s+(?:a\s+)?(?:second|moment))\s+(?:froze|melted|boiled|cooled|heated)\b',
             "Instantaneous temperature change"),
            # Temperature paradox
            (r'\b(?:boiled|hot)\b.*\b(?:froze|frozen|ice)\b.*\b(?:flame|fire|burning)\b',
             "Simultaneous contradictory temperatures"),
        ]
    },
    "relativity": {
        "name": "Relativity Violations",
        "patterns": [
            # Faster than light
            (r'\b(?:faster\s+than|overtook|outran)\s+(?:light|beam)\b',
             "Faster-than-light travel"),
            # Time reversal
            (r'\b(?:clocks?|time)\s+(?:ticked|ran|went|moved)\s+backwards?\b(?!.*(?:daylight\s+saving|reset|rewound))',
             "Time flowing backwards"),
            # Time paradox
            (r'\bwalked\s+forward\b.*\bbackwards?\b.*\btime\b',
             "Time direction inconsistency"),
        ]
    },
    "momentum": {
        "name": "Newton's Laws Violations",
        "patterns": [
            # Motion without force
            (r'\b(?:suddenly|just)\s+(?:darted|moved|shot|accelerated)\b.*\b(?:no\s+one|nothing)\s+(?:touched|pushed|pulled)\b',
             "Motion without applied force (Newton's 1st law)"),
            # No recoil
            (r'\b(?:fired|shot)\s+(?:a\s+)?(?:cannon|gun|rocket)\b.*\b(?:didn\'t|did\s+not)\s+(?:move|feel|push|recoil)\b',
             "No recoil from firing projectile (Newton's 3rd law)"),
            # Stationary after collision
            (r'\b(?:hit|struck|crashed\s+into)\b.*\b(?:didn\'t|did\s+not)\s+move\b',
             "No momentum transfer in collision"),
        ]
    },
    "materials": {
        "name": "Material Strength Violations",
        "patterns": [
            # Impossible bending
            (r'\b(?:steel|iron|metal|concrete|stone)\s+(?:bridge|beam|wall|rod)\s+(?:twisted|bent|folded)\b.*\b(?:clay|soft|gently|easily)\b',
             "Impossible bending of rigid materials"),
            # Infinite strength
            (r'\b(?:wooden|small|thin)\s+(?:stool|chair|stick|rod)\s+(?:held|supported)\b.*\b(?:building|elephant|train|truck)\b',
             "Small structure supporting impossibly large load"),
        ]
    },
    "biology": {
        "name": "Biological/Survival Violations",
        "patterns": [
            # No oxygen needed
            (r'\b(?:underwater|submerged)\s+for\s+(?:\d+\s+)?(?:hours?|days?)\b(?!.*(?:submarine|scuba|tank|oxygen))',
             "Surviving without oxygen for extended period"),
            # Indestructibility
            (r'\b(?:train|truck|car|building)\s+(?:hit|struck|crashed)\b.*\b(?:didn\'t|did\s+not)\s+(?:move|injure|hurt)\b',
             "Human surviving unsurvivable impact"),
            # No injury from massive force
            (r'\b(?:crumpled|fell\s+apart)\b.*\b(?:he|she)\s+(?:didn\'t|did\s+not)\s+move\b',
             "No injury despite catastrophic collision"),
        ]
    },
    "planetary": {
        "name": "Planetary Physics Violations",
        "patterns": [
            # Orbit breaking
            (r'\b(?:moon|planet|satellite)\s+(?:paused|stopped|drifted|left|departed)\b(?!.*orbit)',
             "Celestial body leaving stable orbit"),
            # Atmosphere moving
            (r'\batmosphere\b.*\b(?:blew|moved|shifted|drifted)\b',
             "Entire atmosphere moving independently"),
        ]
    },
    "quantum": {
        "name": "Quantum Physics Violations",
        "patterns": [
            # Deterministic quantum
            (r'\b(?:every\s+time|always)\b.*\b(?:electron|particle|quantum)\b.*\b(?:same\s+place|exact|identical)\b',
             "Deterministic quantum behavior (violates uncertainty principle)"),
            # Macroscopic tunneling
            (r'\bwalked\s+(?:into|through)\s+(?:a\s+)?(?:wall|barrier)\b.*\b(?:emerged|came\s+out)\b.*\b(?:without|no)\s+(?:hole|damage)\b',
             "Macroscopic quantum tunneling"),
        ]
    }
}

def analyze_physics_violations(text: str) -> Dict:
    """
    Analyze text for physics violations
    
    Args:
        text: Story text to analyze
    
    Returns:
        Dict with violation categories and detected violations
    """
    text_lower = text.lower()
    
    results = {
        "has_violations": False,
        "total_violations": 0,
        "violations_by_category": {},
        "all_violations": []
    }
    
    for category_id, category_info in PHYSICS_VIOLATIONS.items():
        category_violations = []
        
        for pattern, description in category_info["patterns"]:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                violation = {
                    "category": category_info["name"],
                    "description": description,
                    "matched_text": match.group(0),
                    "position": match.span(),
                    "context": get_context(text, match.span(), 50)
                }
                category_violations.append(violation)
                results["all_violations"].append(violation)
        
        if category_violations:
            results["violations_by_category"][category_info["name"]] = category_violations
            results["has_violations"] = True
    
    results["total_violations"] = len(results["all_violations"])
    
    return results

def get_context(text: str, span: Tuple[int, int], context_chars: int = 50) -> str:
    """Extract context around a match"""
    start, end = span
    context_start = max(0, start - context_chars)
    context_end = min(len(text), end + context_chars)
    
    context = text[context_start:context_end]
    
    # Add ellipsis if truncated
    if context_start > 0:
        context = "..." + context
    if context_end < len(text):
        context = context + "..."
    
    return context

def generate_violation_report(violations: Dict) -> str:
    """
    Generate human-readable HTML report of violations
    
    Args:
        violations: Results from analyze_physics_violations
    
    Returns:
        HTML formatted report
    """
    if not violations["has_violations"]:
        return "<p style='color: #2ecc71;'>✅ <strong>No physics violations detected!</strong> Story follows known physical laws.</p>"
    
    report = [
        f"<h3 style='color: #e74c3c;'>⚠️ Physics Violations Detected: {violations['total_violations']}</h3>",
        "<p>The following violations of fundamental physics laws were found:</p>"
    ]
    
    for category_name, category_violations in violations["violations_by_category"].items():
        report.append(f"<h4 style='color: #e67e22;'>{category_name} ({len(category_violations)} violation{'s' if len(category_violations) > 1 else ''})</h4>")
        report.append("<ul>")
        
        for v in category_violations:
            report.append(f"<li>")
            report.append(f"<strong>{v['description']}</strong><br/>")
            report.append(f"<em>Matched text:</em> \"{v['matched_text']}\"<br/>")
            report.append(f"<em>Context:</em> <span style='background: #fff3cd; padding: 2px 4px;'>{v['context']}</span>")
            report.append(f"</li>")
        
        report.append("</ul>")
    
    return "\n".join(report)

def check_story_physics(story_text: str) -> Tuple[bool, str]:
    """
    Main entry point - check if story violates physics
    
    Args:
        story_text: Story to check
    
    Returns:
        (is_valid, report_html) - True if no violations, False otherwise
    """
    violations = analyze_physics_violations(story_text)
    report = generate_violation_report(violations)
    
    is_valid = not violations["has_violations"]
    
    return is_valid, report