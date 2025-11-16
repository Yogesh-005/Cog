from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import time
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import hashlib

# Import LLM modules
from llm_reasoner import generate_answer, initialize_model
from context_builder import build_context_prompt
from graph_queries import (
    find_concept_relationships, 
    find_path_between_concepts,
    extract_concepts_from_question,
    summarize_graph_for_concept
)

app = Flask(__name__)
CORS(app)

# In-memory storage
sessions = {}
conceptnet_cache = {}
question_cache = {}  # Cache for repeated questions
STORAGE_FILE = 'stories.json'
CACHE_FILE = 'conceptnet_cache.json'

# Stopwords
STOPWORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'is',
                 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
                 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'i',
                 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their', 'my', 'your',
                 'his', 'her', 'its', 'our', 'this', 'that', 'these', 'those', 'said',
                 'then', 'when', 'where', 'who', 'what', 'which', 'how', 'there', 'here'])

# Cultural context mapping
CULTURAL_CONTEXTS = {
    'knight': 'Western Medieval',
    'samurai': 'Japanese',
    'dragon': 'Western/Eastern Mythology',
    'temple': 'Eastern/Religious',
    'castle': 'Western Medieval',
    'warrior': 'Universal',
    'monk': 'Eastern Religious',
    'sword': 'Universal Warfare',
    'king': 'Western Monarchy',
    'emperor': 'Eastern Monarchy',
    'princess': 'Western Medieval',
    'robot': 'Modern Technology',
    'computer': 'Modern Technology',
    'garden': 'Universal Nature'
}

def load_sessions():
    global sessions
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
            print(f"✓ Loaded {len(sessions)} sessions from disk")
        except Exception as e:
            print(f"✗ Error loading sessions: {e}")
            sessions = {}

def save_sessions():
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        print(f"✗ Error saving sessions: {e}")

def load_cache():
    global conceptnet_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                conceptnet_cache = json.load(f)
            print(f"✓ Loaded {len(conceptnet_cache)} cached concepts")
        except Exception as e:
            print(f"✗ Error loading cache: {e}")
            conceptnet_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(conceptnet_cache, f, indent=2)
    except Exception as e:
        print(f"✗ Error saving cache: {e}")

def extract_concepts(text, limit=7):
    words = re.findall(r'\b[A-Za-z]{3,}\b', text)
    word_freq = Counter()
    for word in words:
        wl = word.lower()
        if wl not in STOPWORDS:
            word_freq[wl] += 1

    sentences = re.split(r'[.!?]+', text)
    proper_nouns = set()
    for sentence in sentences:
        sentence_words = sentence.strip().split()
        for i, word in enumerate(sentence_words):
            if i > 0 and word and word[0].isupper() and len(word) > 2:
                proper_nouns.add(word.lower())

    scored = []
    for w, f in word_freq.items():
        score = f
        if w in proper_nouns:
            score += 3
        if len(w) > 6:
            score += 1
        scored.append((w, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    concepts = [w for w, s in scored[:limit]]
    return concepts, proper_nouns

def fetch_conceptnet_relations(concept, limit=5):
    cache_key = f"{concept}_{limit}"
    if cache_key in conceptnet_cache:
        return conceptnet_cache[cache_key]
    url = f"http://api.conceptnet.io/query?node=/c/en/{concept}&limit={limit}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            edges = []
            for edge in data.get('edges', [])[:limit]:
                start = edge.get('start', {}).get('label', '')
                end = edge.get('end', {}).get('label', '')
                rel = edge.get('rel', {}).get('label', 'related')
                weight = edge.get('weight', 1.0)
                edges.append({'start': start, 'end': end, 'relation': rel, 'weight': weight})
            conceptnet_cache[cache_key] = edges
            save_cache()
            return edges
        else:
            return []
    except Exception as e:
        print(f"✗ Error fetching ConceptNet for '{concept}': {e}")
        return []

def fetch_all_relations_parallel(concepts, limit=5):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_conceptnet_relations, c, limit): c for c in concepts}
        results = {}
        for fut in futures:
            c = futures[fut]
            try:
                results[c] = fut.result()
            except Exception as e:
                print(f"✗ Error in parallel fetch for '{c}': {e}")
                results[c] = []
        return results

def detect_cultural_context(concepts):
    markers = []
    for c in concepts:
        if c in CULTURAL_CONTEXTS:
            markers.append({'concept': c, 'culture': CULTURAL_CONTEXTS[c]})
    if markers:
        cultures = [m['culture'] for m in markers]
        from collections import Counter
        dom = Counter(cultures).most_common(1)[0][0]
    else:
        dom = "Universal"
    return {'dominant_culture': dom, 'markers': markers}

def build_enhanced_graph(concepts, all_relations, proper_nouns):
    all_nodes = {}
    all_edges = []
    for concept in concepts:
        node_id = concept.lower().replace(' ', '_')
        all_nodes[node_id] = {
            'id': node_id,
            'label': concept.capitalize(),
            'type': 'main',
            'from_story': True,
            'size': 70,
            'cultural_context': CULTURAL_CONTEXTS.get(concept, 'Universal')
        }
    for concept, edges in all_relations.items():
        for edge in edges:
            for node_label in [edge['start'], edge['end']]:
                if not node_label:
                    continue
                node_id = node_label.lower().replace(' ', '_')
                if node_id not in all_nodes and node_label.lower() not in STOPWORDS:
                    all_nodes[node_id] = {
                        'id': node_id,
                        'label': node_label,
                        'type': 'related',
                        'from_story': False,
                        'size': 50,
                        'cultural_context': 'Universal'
                    }
            start_id = edge['start'].lower().replace(' ', '_') if edge['start'] else None
            end_id = edge['end'].lower().replace(' ', '_') if edge['end'] else None
            if start_id and end_id and start_id in all_nodes and end_id in all_nodes:
                all_edges.append({
                    'source': start_id,
                    'target': end_id,
                    'label': edge['relation'],
                    'weight': edge.get('weight', 1.0)
                })
    stats = {
        'total_nodes': len(all_nodes),
        'main_concepts': len([n for n in all_nodes.values() if n['from_story']]),
        'related_concepts': len([n for n in all_nodes.values() if not n['from_story']]),
        'total_edges': len(all_edges),
        'depth': 2 if len(all_edges) > 0 else 1
    }
    return {'nodes': list(all_nodes.values()), 'edges': all_edges, 'stats': stats}

def generate_enhanced_response(concepts, categorized, cultural_info, graph_stats):
    parts = []
    parts.append(f"<h3>Analysis Complete ✅</h3>")
    if categorized.get('entities'):
        parts.append("<strong>Main Entities:</strong>")
        parts.append("<ul>" + "".join(f"<li>{e.capitalize()}</li>" for e in categorized['entities']) + "</ul>")
    if categorized.get('themes'):
        parts.append("<strong>Themes:</strong>")
        parts.append("<ul>" + "".join(f"<li>{t.capitalize()}</li>" for t in categorized['themes']) + "</ul>")
    if categorized.get('objects'):
        parts.append("<strong>Key Objects / Concepts:</strong>")
        parts.append("<ul>" + "".join(f"<li>{o.capitalize()}</li>" for o in categorized['objects']) + "</ul>")
    parts.append(f"<p><strong>Cultural Context:</strong> {cultural_info['dominant_culture']}</p>")
    parts.append(f"<p><strong>Knowledge Graph:</strong> {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} relationships, depth {graph_stats['depth']}.</p>")
    if graph_stats['total_edges'] > 0:
        parts.append("<p>Use the <em>Knowledge Graph</em> tab to explore connections visually. You can now ask me questions about the story!</p>")
    return "\n".join(parts)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/sessions', methods=['GET', 'POST'])
def handle_sessions():
    if request.method == 'POST':
        session_id = f"session_{int(time.time() * 1000)}"
        sessions[session_id] = {
            'id': session_id,
            'name': f"Story {len(sessions) + 1}",
            'created': datetime.now().isoformat(),
            'messages': [],
            'story_text': '',  # Store original story
            'graph_data': {'nodes': [], 'edges': []},
            'metadata': {
                'concepts': [],
                'categorized': {},
                'cultural_context': {},
                'graph_stats': {},
                'analyzed': False
            }
        }
        save_sessions()
        return jsonify(sessions[session_id])
    else:
        return jsonify(list(sessions.values()))

@app.route('/sessions/<session_id>', methods=['GET', 'DELETE', 'POST'])
def session_item(session_id):
    if request.method == 'GET':
        if session_id in sessions:
            return jsonify(sessions[session_id])
        else:
            return jsonify({'error': 'Session not found'}), 404
    elif request.method == 'DELETE':
        if session_id in sessions:
            del sessions[session_id]
            save_sessions()
            return jsonify({'message': f'Session {session_id} deleted'})
        else:
            return jsonify({'error': 'Session not found'}), 404
    else:
        data = request.json or {}
        new_name = data.get('name', '').strip()
        if not new_name:
            return jsonify({'error': 'No name provided'}), 400
        if session_id in sessions:
            sessions[session_id]['name'] = new_name
            save_sessions()
            return jsonify({'message': f"Session renamed to '{new_name}'", 'session': sessions[session_id]})
        else:
            return jsonify({'error': 'Session not found'}), 404

@app.route('/sessions/<session_id>/story', methods=['POST'])
def analyze_story(session_id):
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    data = request.json or {}
    story = data.get('story', '').strip()
    if not story:
        return jsonify({'error': 'No story provided'}), 400

    print(f"\n{'='*40}\nAnalyzing story for {session_id}\n{'='*40}")
    
    # Store original story text
    sessions[session_id]['story_text'] = story
    sessions[session_id]['messages'].append({'role': 'user', 'content': story, 'timestamp': datetime.now().isoformat()})
    
    start_time = time.time()
    concepts, proper_nouns = extract_concepts(story, limit=7)
    categorized = {
        'entities': [c for c in concepts if c in proper_nouns],
        'themes': [], 'objects': []
    }
    for c in concepts:
        if c not in categorized['entities']:
            categorized['objects'].append(c)

    print(f"✓ Extracted concepts: {concepts}")
    all_relations = fetch_all_relations_parallel(concepts, limit=5)
    cultural_info = detect_cultural_context(concepts)
    graph_data = build_enhanced_graph(concepts, all_relations, proper_nouns)
    sessions[session_id]['graph_data'] = graph_data
    sessions[session_id]['metadata'] = {
        'concepts': concepts,
        'categorized': categorized,
        'cultural_context': cultural_info,
        'graph_stats': graph_data['stats'],
        'analyzed': True
    }

    ai_message_html = generate_enhanced_response(concepts, categorized, cultural_info, graph_data['stats'])
    sessions[session_id]['messages'].append({
        'role': 'assistant',
        'content': ai_message_html,
        'timestamp': datetime.now().isoformat(),
        'concepts': concepts
    })
    save_sessions()
    total_time = time.time() - start_time
    print(f"✓ Analysis finished in {total_time:.2f}s")

    return jsonify({
        'message': ai_message_html,
        'concepts': concepts,
        'graph_data': graph_data,
        'metadata': sessions[session_id]['metadata'],
        'performance': {'total_time': f"{total_time:.2f}s"}
    })

@app.route('/sessions/<session_id>/question', methods=['POST'])
def answer_question(session_id):
    """
    LLM-powered question answering grounded in story + knowledge graph
    """
    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    data = request.json or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    session = sessions[session_id]
    meta = session.get('metadata', {})
    
    if not meta.get('analyzed'):
        return jsonify({'error': 'Story not analyzed yet. Send the story first via /story'}), 400

    print(f"\n{'='*40}\nAnswering question for {session_id}\n{'='*40}")
    print(f"Question: {question}")
    
    start_time = time.time()
    
    # Check cache for repeated questions
    cache_key = hashlib.md5(f"{session_id}_{question}".encode()).hexdigest()
    if cache_key in question_cache:
        print("✓ Cache hit - returning cached answer")
        cached_answer = question_cache[cache_key]
        sessions[session_id]['messages'].append({
            'role': 'user', 
            'content': question, 
            'timestamp': datetime.now().isoformat()
        })
        sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': cached_answer,
            'timestamp': datetime.now().isoformat(),
            'cached': True
        })
        save_sessions()
        return jsonify({'message': cached_answer, 'cached': True})
    
    # Extract data from session
    story_text = session.get('story_text', '')
    graph_data = session.get('graph_data', {})
    concepts = meta.get('concepts', [])
    cultural_info = meta.get('cultural_context', {})
    
    # Detect if question mentions specific concepts
    mentioned_concepts = extract_concepts_from_question(question, concepts)
    print(f"Mentioned concepts: {mentioned_concepts}")
    
    # Find specific paths if multiple concepts mentioned
    specific_paths = None
    if len(mentioned_concepts) >= 2:
        print(f"Looking for path between {mentioned_concepts[0]} and {mentioned_concepts[1]}")
        path = find_path_between_concepts(graph_data, mentioned_concepts[0], mentioned_concepts[1])
        if path:
            specific_paths = [path]
            print(f"✓ Found path: {' → '.join(path)}")
    
    # Build context prompt
    context_prompt = build_context_prompt(
        story=story_text,
        graph_data=graph_data,
        question=question,
        cultural_info=cultural_info,
        specific_paths=specific_paths
    )
    
    print("✓ Context built, generating answer with LLM...")
    print("⏳ This may take up to 5 minutes on CPU, please wait...")
    
    # Detect if creative request (needs more tokens)
    is_creative = any(word in question.lower() for word in ['style', 'retell', 'narrate', 'rewrite', 'tell the story'])
    max_tokens = 400 if is_creative else 300
    
    print(f"🎨 Creative request detected: {is_creative}")
    
    # Generate answer WITHOUT any timeout - let it complete no matter how long
    try:
        raw_answer = generate_answer(context_prompt, max_new_tokens=max_tokens, temperature=0.7)
        
        if not raw_answer or len(raw_answer) < 10:
            print("⚠️  LLM response too short, trying again with fallback")
            raw_answer = generate_fallback_answer(question, concepts, graph_data, cultural_info)
    except Exception as e:
        print(f"✗ Error generating answer: {e}")
        import traceback
        traceback.print_exc()
        raw_answer = generate_fallback_answer(question, concepts, graph_data, cultural_info)
    
    print(f"📝 Raw answer length: {len(raw_answer)} characters")
    
    # Post-process answer to check for hallucination
    processed_answer = post_process_answer(raw_answer, concepts, mentioned_concepts, story_text, question)
    
    print(f"✅ Processed answer length: {len(processed_answer)} characters")
    
    # Check if answer was replaced due to hallucination
    if "I don't have information" in processed_answer or "I don't have that" in processed_answer:
        print("🚫 Hallucination detected and blocked!")
    
    # For creative requests, do additional formatting check
    if is_creative:
        # Remove any remaining formatting issues
        processed_answer = clean_creative_answer(processed_answer)
    
    # Format as HTML
    html_answer = f"<h3>Answer</h3><p>{processed_answer}</p>"
    
    # Add referenced concepts if any
    if mentioned_concepts:
        html_answer += "<p><small><em>Referenced concepts: " + ", ".join(c.capitalize() for c in mentioned_concepts) + "</em></small></p>"
    
    # Cache the answer
    question_cache[cache_key] = html_answer
    
    # Save to session
    sessions[session_id]['messages'].append({
        'role': 'user',
        'content': question,
        'timestamp': datetime.now().isoformat()
    })
    sessions[session_id]['messages'].append({
        'role': 'assistant',
        'content': html_answer,
        'timestamp': datetime.now().isoformat(),
        'concepts_referenced': mentioned_concepts
    })
    save_sessions()
    
    total_time = time.time() - start_time
    print(f"✓ Answer generated in {total_time:.2f}s")
    
    return jsonify({
        'message': html_answer,
        'concepts_referenced': mentioned_concepts,
        'graph_paths_used': specific_paths,
        'performance': {'total_time': f"{total_time:.2f}s"}
    })

def generate_fallback_answer(question, concepts, graph_data, cultural_info):
    """
    Generate graph-based answer when LLM unavailable or times out
    """
    q = question.lower()
    
    if any(word in q for word in ['concept', 'concepts', 'main', 'about']):
        return f"The main concepts in this story are: {', '.join(c.capitalize() for c in concepts)}."
    
    elif any(word in q for word in ['culture', 'cultural', 'context']):
        culture = cultural_info.get('dominant_culture', 'Universal')
        return f"This story has a {culture} cultural context."
    
    elif any(word in q for word in ['connect', 'connection', 'relationship', 'relate']):
        stats = graph_data.get('stats', {})
        return f"The knowledge graph shows {stats.get('total_edges', 0)} connections between {stats.get('total_nodes', 0)} concepts. Check the Knowledge Graph tab to explore visually."
    
    else:
        return f"Based on the story, I can tell you about: {', '.join(c.capitalize() for c in concepts[:3])}. The story has {graph_data.get('stats', {}).get('total_edges', 0)} concept relationships in the knowledge graph."

def clean_creative_answer(answer):
    """
    Clean up creative retelling answers - remove formatting issues and non-English text
    """
    # First, check if answer is in a foreign language
    # If more than 50% non-ASCII characters (increased threshold), it's likely in another language
    non_ascii_count = sum(1 for c in answer if ord(c) > 127)
    if len(answer) > 0 and (non_ascii_count / len(answer)) > 0.5:  # Changed from 0.3 to 0.5
        print("⚠️  Warning: Answer appears to be in non-English language!")
        print(f"⚠️  Non-ASCII characters: {non_ascii_count}/{len(answer)}")
        # Answer is in foreign language - reject it
        return "I apologize, but the response was generated in a non-English language. Please try asking the question again. The response should be in English only."
    
    # Remove any non-English text (Hindi, Japanese, Chinese, etc.)
    original_length = len(answer)
    
    # Remove Hindi (Devanagari script)
    answer = re.sub(r'[\u0900-\u097F]+', '', answer)
    # Remove Japanese (Hiragana, Katakana, Kanji)
    answer = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', '', answer)
    # Remove Chinese
    answer = re.sub(r'[\u4E00-\u9FFF]+', '', answer)
    # Remove Arabic
    answer = re.sub(r'[\u0600-\u06FF]+', '', answer)
    
    # Clean up any resulting double spaces
    answer = re.sub(r'\s+', ' ', answer).strip()
    
    # Check how much was removed
    removed = original_length - len(answer)
    if removed > 100:
        print(f"⚠️  Removed {removed} non-English characters from answer")
    
    # If answer is now too short (less than 100 chars instead of 50), it was mostly non-English
    if len(answer) < 100:
        print("⚠️  Answer was mostly non-English text, rejected")
        return "I apologize, but the response was generated in a non-English language. Please try asking the question again. The response should be in English only."
    
    # Remove common prefixes that LLM adds
    bad_prefixes = [
        "INDIAN STYLE",
        "JAPANESE STYLE", 
        "AFRICAN STYLE",
        "CHINESE STYLE",
        "In the land of",
        "Original Story:",
        "Concept Relationships:",
        "Japanese-style retelling",
        "Indian-style retelling"
    ]
    
    for prefix in bad_prefixes:
        if answer.startswith(prefix):
            # Find where the actual story starts
            parts = answer.split('.', 1)
            if len(parts) > 1:
                # Skip the prefix sentence
                answer = parts[1].strip()
            else:
                # If no period, just remove prefix
                answer = answer[len(prefix):].strip()
    
    # If answer is incomplete (ends mid-sentence), truncate to last complete sentence
    if answer and answer[-1] not in '.!?':
        sentences = answer.split('.')
        if len(sentences) > 1:
            # Keep all complete sentences
            answer = '.'.join(sentences[:-1]) + '.'
    
    return answer

def post_process_answer(answer, all_concepts, mentioned_concepts, story_text, question):
    """
    Clean and validate LLM answer - detect and fix hallucinations
    """
    # Remove any leading/trailing whitespace
    answer = answer.strip()
    
    # Remove common LLM artifacts
    if answer.startswith("Answer:"):
        answer = answer[7:].strip()
    
    # Check if question is about something NOT in the story
    story_lower = story_text.lower()
    question_lower = question.lower()
    
    # List of things that might not be in the story
    unrelated_terms = [
        'president', 'prime minister', 'politics', 'election', 'government',
        'covid', 'pandemic', 'virus', 'vaccine',
        'internet', 'website', 'google', 'facebook', 'twitter',
        'iphone', 'android', 'computer', 'laptop',
        'bitcoin', 'cryptocurrency', 'stock market'
    ]
    
    # Check if asking about something completely unrelated
    asking_unrelated = any(term in question_lower for term in unrelated_terms)
    term_not_in_story = asking_unrelated and not any(term in story_lower for term in unrelated_terms)
    
    if term_not_in_story:
        # Question is about something not in the story at all
        return "I don't have information about that in this story. I can only answer questions based on the story content and knowledge graph. Please ask about the characters, events, or concepts that appear in the story."
    
    # Check for obvious hallucinations (mentioning things not in story)
    # Look for phrases that indicate made-up information
    hallucination_phrases = [
        'can be inferred', 'might be called', 'would be referred to',
        'in other parts of the world', 'in other regions',
        'is not mentioned in the given story. However',
        'could be', 'might be', 'would be', 'may be'
    ]
    
    if any(phrase in answer.lower() for phrase in hallucination_phrases):
        # LLM is making things up - check if it's actually in the story
        # Extract what it's claiming
        if 'is not mentioned' in answer.lower() or 'not in the story' in answer.lower():
            # Good - it admits it's not there, but then makes stuff up
            # Find what it's talking about
            for word in question_lower.split():
                if len(word) > 3 and word not in ['what', 'who', 'where', 'when', 'tell', 'the', 'story', 'about']:
                    if word not in story_lower:
                        return f"I don't have information about '{word}' in this story. The story focuses on: {', '.join(c.capitalize() for c in all_concepts[:5])}. Please ask about concepts that appear in the story."
    
    # Check if answer mentions concepts not in the graph
    words_in_answer = set(re.findall(r'\b[a-z]{4,}\b', answer.lower()))
    story_concepts_lower = set(c.lower() for c in all_concepts)
    
    # If answer mentions many words not in concepts, might be hallucinating
    unknown_words = words_in_answer - story_concepts_lower - STOPWORDS
    
    # Check if it's a creative retelling (those should have different words)
    is_creative = any(word in question.lower() for word in ['style', 'retell', 'narrate', 'rewrite', 'tell the story'])
    
    if len(unknown_words) > 10 and not is_creative:
        print(f"⚠️  Warning: Answer contains many unknown words, possible hallucination")
        print(f"⚠️  Unknown words sample: {list(unknown_words)[:5]}")
        # For non-creative questions, this is likely hallucination
        # Check if answer mentions things definitely not in story
        hallucination_indicators = ['elizabeth', 'queen', 'king', 'ruled', 'celebrated', 'music', 'dancing']
        if any(indicator in answer.lower() for indicator in hallucination_indicators):
            # Definitely hallucinating - block it
            for word in question_lower.split():
                if len(word) > 3 and word not in ['what', 'who', 'where', 'when', 'tell', 'the', 'story', 'about', 'does', 'after', 'from']:
                    if word not in story_lower:
                        return f"I don't have information about '{word}' in this story. The story focuses on: {', '.join(c.capitalize() for c in all_concepts[:5])}. Please ask about concepts that appear in the story."
            # Generic block if we can't identify the specific word
            return "I don't have that specific information in the story. I can only answer based on what's explicitly mentioned in the story."
    
    # Ensure answer ends with punctuation
    if answer and answer[-1] not in '.!?':
        answer += '.'
    
    # If answer is too short
    if len(answer) < 20:
        return "I don't have enough information in the story to provide a detailed answer to that question."
    
    return answer

if __name__ == '__main__':
    load_sessions()
    load_cache()
    
    print("\n" + "="*60)
    print("🤖 ROBOT SELF-AWARENESS DEMO - LLM ENHANCED")
    print("="*60)
    
    # Initialize LLM model at startup
    print("Initializing LLM...")
    initialize_model()
    
    print("✓ ConceptNet caching enabled")
    print("✓ Parallel processing enabled")
    print("✓ LLM question answering enabled")
    print("✓ Question caching enabled")
    print("="*60 + "\n")
    
    # Run dev server
    app.run(debug=False, use_reloader=False, port=5000)