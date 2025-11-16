"""
Context Builder Module
Constructs intelligent prompts combining story + graph + question
"""

def build_context_prompt(story, graph_data, question, cultural_info=None, specific_paths=None):
    """
    Build a structured prompt for the LLM
    
    Args:
        story: Original story text
        graph_data: Dict with 'nodes' and 'edges'
        question: User's question
        cultural_info: Optional cultural context dict
        specific_paths: Optional pre-computed paths between concepts
    
    Returns:
        Complete prompt string
    """
    
    # Detect if this is a creative rewrite request
    is_creative_request = any(word in question.lower() for word in ['retell', 'rewrite', 'tell the story', 'narrate', 'style'])
    
    # Extract story concepts (nodes marked from_story=True)
    story_concepts = [n for n in graph_data.get('nodes', []) if n.get('from_story', False)]
    related_concepts = [n for n in graph_data.get('nodes', []) if not n.get('from_story', False)]
    edges = graph_data.get('edges', [])
    
    # Build graph relationships text
    graph_text = format_graph_relationships(story_concepts, related_concepts, edges)
    
    # Build cultural context text
    cultural_text = format_cultural_context(cultural_info)
    
    # Build specific paths if provided
    paths_text = format_specific_paths(specific_paths) if specific_paths else ""
    
    # Different prompt for creative vs analytical questions
    if is_creative_request:
        # Extract the specific style requested
        style_requested = "unknown"
        for style_word in ['indian', 'japanese', 'african', 'chinese', 'western', 'modern', 'ancient', 'medieval']:
            if style_word in question.lower():
                style_requested = style_word.capitalize()
                break
        
        # Provide very specific examples based on style
        if 'japanese' in question.lower():
            example_story = """
EXAMPLE Japanese style retelling (use this as a guide):
"Long ago in feudal Japan, a noble samurai warrior named Takeshi lived in a magnificent castle overlooking the mountains. One day, a fearsome dragon emerged from the peaks and threatened a peaceful village below. Takeshi, bound by the code of bushido and his solemn duty to protect the innocent, donned his armor and took his legendary katana sword. With unwavering honor and courage, he rode forth on his black steed to confront the beast. In an epic duel that lasted from dawn to dusk, the samurai fought with masterful skill and discipline. Through the way of the warrior, Takeshi struck down the dragon and saved the village. The grateful villagers honored him as a hero, and his name lived on in legends told by generations."

YOUR TASK: Write a similar retelling using Japanese cultural elements.
"""
        elif 'indian' in question.lower():
            example_story = """
EXAMPLE Indian style retelling (use this as a guide):
"In ancient India, a valiant kshatriya warrior named Arjun lived in a magnificent palace adorned with golden domes. One day, a fearsome naga serpent demon rose from the depths and attacked a peaceful village. Arjun, remembering his sacred dharma to protect the innocent, prepared for battle. He took his blessed khanda sword, said prayers to the gods, and rode forth on his white stallion. With the divine blessings of Lord Vishnu and great courage in his heart, Arjun fought the naga in a legendary battle. After an epic confrontation where good triumphed over evil, Arjun vanquished the demon and saved the villagers. The people celebrated him as a hero chosen by the gods, and peace returned to the land."

YOUR TASK: Write a similar retelling using Indian cultural elements.
"""
        elif 'african' in question.lower():
            example_story = """
EXAMPLE African style retelling (use this as a guide):
"In ancient times, a mighty warrior named Kwame lived in a great tribal village surrounded by the savannah. One day, a fearsome beast emerged from the wilderness and threatened his people. Kwame, guided by the wisdom of his ancestors' spirits, prepared for battle. He took his sacred spear blessed by the tribal elders and his sturdy shield. With the strength of the lion and courage of his forefathers, Kwame tracked the beast through the grasslands. In a legendary battle that shook the earth, the warrior fought with honor and skill. Through bravery and the protection of ancestral spirits, Kwame defeated the beast and saved his village. The tribal council honored him with a great feast, and his story was told around fires for generations."

YOUR TASK: Write a similar retelling using African cultural elements.
"""
        else:
            example_story = ""
        
        prompt = f"""You are a creative storyteller. Retell the story below in {style_requested} cultural style IN ENGLISH.

ORIGINAL STORY:
{story}

{example_story}

CRITICAL REQUIREMENTS:
1. Write your ENTIRE retelling in ENGLISH language - NO Hindi, Japanese, Chinese, or other languages
2. CHANGE ALL character names to {style_requested} names (like the example above)
3. CHANGE ALL settings to {style_requested} settings (like the example above)  
4. CHANGE ALL weapons/tools to {style_requested} weapons (like the example above)
5. ADD {style_requested} cultural elements (like the example above)
6. Keep the SAME plot: warrior/hero → village threatened → takes weapon → fights threat → defeats it → saves village
7. Write 6-8 complete sentences in English
8. Start with "In ancient..." or "Long ago..." - NO prefixes or headers

REMEMBER: Write in ENGLISH words only. Use {style_requested} NAMES and CULTURAL ELEMENTS but write the story in ENGLISH.

NOW WRITE YOUR {style_requested.upper()} STYLE RETELLING IN ENGLISH:"""
    else:
        prompt = f"""You are a story analysis assistant. Answer questions using ONLY the story provided.

STORY:
{story}

KNOWLEDGE GRAPH (Concept Relationships):
{graph_text}

{cultural_text}

{paths_text}

USER QUESTION:
{question}

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. Answer ONLY using facts from the story above
2. If something is NOT in the story (like "princess", "queen", specific dates, historical figures), you MUST say: "I don't have information about [X] in this story"
3. Do NOT make up events, characters, or details
4. Do NOT say things like "can be inferred", "might be", "would be", "ruled from", "was known for"
5. If asked "what happens after [event]" and the story doesn't say, respond: "The story ends with [last event]. It doesn't provide details about what happens after."
6. Do NOT add historical information (dates, real rulers, real places) unless they're in the story
7. Keep answer focused and based on story facts (3-5 sentences)

ANSWER (using ONLY information from the story):"""
    
    return prompt

def format_graph_relationships(story_concepts, related_concepts, edges):
    """Format graph data as readable text"""
    lines = []
    
    if story_concepts:
        lines.append("Main Story Concepts:")
        for node in story_concepts[:10]:  # Limit to top 10
            label = node.get('label', node.get('id', 'Unknown'))
            lines.append(f"  - {label}")
    
    lines.append("\nConcept Relationships:")
    
    # Group edges by source concept
    edge_map = {}
    for edge in edges:
        source = edge.get('source', '')
        if source not in edge_map:
            edge_map[source] = []
        edge_map[source].append(edge)
    
    # Format relationships
    count = 0
    for source_id, source_edges in edge_map.items():
        if count >= 15:  # Increased back to 15 for better context
            break
        
        # Find source label
        source_label = get_node_label(source_id, story_concepts + related_concepts)
        
        for edge in source_edges[:3]:  # Back to 3 edges per source
            target_id = edge.get('target', '')
            target_label = get_node_label(target_id, story_concepts + related_concepts)
            relation = edge.get('label', 'related to')
            
            lines.append(f"  • {source_label} --[{relation}]--> {target_label}")
            count += 1
            
            if count >= 15:
                break
    
    return "\n".join(lines) if lines else "No relationships found."

def format_cultural_context(cultural_info):
    """Format cultural context information"""
    if not cultural_info:
        return ""
    
    lines = ["CULTURAL CONTEXT:"]
    
    dominant = cultural_info.get('dominant_culture', 'Universal')
    lines.append(f"Primary cultural context: {dominant}")
    
    markers = cultural_info.get('markers', [])
    if markers:
        lines.append("Cultural markers:")
        for marker in markers[:5]:  # Limit to 5
            concept = marker.get('concept', '')
            culture = marker.get('culture', '')
            lines.append(f"  - {concept.capitalize()}: {culture}")
    
    return "\n".join(lines)

def format_specific_paths(paths):
    """Format specific paths between concepts"""
    if not paths:
        return ""
    
    lines = ["SPECIFIC CONNECTIONS:"]
    for path in paths:
        path_str = " → ".join(path)
        lines.append(f"  {path_str}")
    
    return "\n".join(lines)

def get_node_label(node_id, nodes):
    """Helper to get readable label for a node ID"""
    for node in nodes:
        if node.get('id') == node_id:
            return node.get('label', node_id)
    return node_id.replace('_', ' ').title()